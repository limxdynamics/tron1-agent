import numpy as np
import librosa
import soundfile as sf
from scipy.spatial.distance import cosine
from sklearn.preprocessing import StandardScaler
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from pypinyin import lazy_pinyin
from fuzzywuzzy import fuzz
import logging
import re
import string
logger = logging.getLogger(__name__)
import threading
import time
import json
import serial 
from typing import Optional
from pathlib import Path
import collections
FRAME_HEADER = 0xA5
USER_ID = 0x01

class ComDevice(threading.Thread):
    """Thread for handling serial communication with device"""
    def __init__(self, uartname: str = "/dev/wheeltec_mic"):
        super().__init__()
        self.uartname = uartname
        self.ser: Optional[serial.Serial] = None
        self.angle = 0
        self.receive_data = bytearray(1024)
        self.count = 0
        self.frame_len = 0
        self.msg_id = 0
        self.keyword = ""
        self.running = True
        self.if_awake = False  # Wake-up status flag
        self._stop_event = threading.Event()
        self.set_keyword_success = False
        self.set_keyword_msg_id = 0 # Keyword message ID

    def data_trans(self, data_high: int, data_low: int) -> int:
        """Combine two bytes into a 16-bit value"""
        return (data_high << 8) | data_low

    def check_sum(self, count_num: int) -> int:
        """Calculate checksum for received data"""
        checksum = 0
        for i in range(count_num):
            checksum += self.receive_data[i]
        return (~checksum + 1) & 0xFF  # Ensure it's a byte

    def deal_with(self, buffer: int) -> int:
        """Process incoming serial data"""
        if self.count >= 1024:  # Prevent buffer overflow
            self.count = 0
            self.frame_len = 0
            self.msg_id = 0
            return 0

        self.receive_data[self.count] = buffer
        
        # Check frame header and user ID
        if self.receive_data[0] != FRAME_HEADER or (self.count == 1 and self.receive_data[1] != USER_ID):
            self.count = 0
            self.frame_len = 0
            self.msg_id = 0
        else:
            self.count += 1

        # Get message ID and frame length at position 7
        if self.count == 7:
            self.msg_id = self.data_trans(self.receive_data[6], self.receive_data[5])
            self.frame_len = self.data_trans(self.receive_data[4], self.receive_data[3]) + 8  # 7 + 1

        # Process complete frame
        if self.count == self.frame_len and self.frame_len > 0:
            if self.check_sum(self.frame_len - 1) == self.receive_data[self.frame_len - 1]:
                if self.receive_data[2] == 0xff and self.set_keyword_msg_id == self.msg_id:  # Message type 0xff
                    self.set_keyword_success = True
                    print(f"Set wakeword sucess")
                if self.receive_data[2] == 0x04:  # Message type 0x04
                    # Extract JSON string (from index 7 to frame_len-8)
                    json_str = self.receive_data[7:self.frame_len-1].decode('utf-8', errors='ignore')
                    
                    try:
                        # Parse JSON data
                        outer_data = json.loads(json_str)
                        content = outer_data.get("content", {})
                        info_str = content.get("info", "{}")
                        eventType = content.get('eventType')
                        
                        if eventType == 0x04:
                            info_data = json.loads(info_str)
                            ivw = info_data.get("ivw", {})
                            self.angle = ivw.get("angle", 0)
                            self.keyword = ivw.get("keyword", "")
                            self.if_awake = True
                            print(f"Wake-up angle = {self.angle}, keyword = '{self.keyword}'")
                        
                    except json.JSONDecodeError as e:
                        print(f"JSON parse error: {e}")
            else:
                print("Checksum verification failed!")

            # Reset for next frame
            self.count = 0
            self.frame_len = 0
            self.msg_id = 0
            self.receive_data = bytearray(1024)
        
        return 0
    def open_port(self) -> int:
        """Open serial port connection"""
        try:
            self.ser = serial.Serial(
                port=self.uartname,
                baudrate=115200,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_ONE,
                timeout=None,
                xonxoff=False,
                rtscts=False,
                dsrdtr=False
            )
            return 0
        except serial.SerialException as e:
            print(f"Failed to open {self.uartname}: {e}")
            return -1

    def set_opt(self, nSpeed: int, nBits: int, nEvent: str, nStop: int) -> int:
        """Configure serial port settings"""
        if not self.ser or not self.ser.is_open:
            print("Serial port not open")
            return -1

        try:
            # Set baud rate
            self.ser.baudrate = nSpeed

            # Set data bits
            self.ser.bytesize = serial.SEVENBITS if nBits == 7 else serial.EIGHTBITS

            # Set parity
            if nEvent == 'O':
                self.ser.parity = serial.PARITY_ODD
            elif nEvent == 'E':
                self.ser.parity = serial.PARITY_EVEN
            else:  # 'N'
                self.ser.parity = serial.PARITY_NONE
            # Set stop bits
            self.ser.stopbits = serial.STOPBITS_ONE if nStop == 1 else serial.STOPBITS_TWO

            return 0
        except Exception as e:
            print(f"Error configuring serial port: {e}")
            return -1
    
    def create_wakeword_command(self, wakeword: str, threshold: str = "900") -> bytearray:
        """Create command packet for setting wake word according to protocol"""
        # Build JSON payload
        payload = {
            "type": "wakeup_keywords",
            "content": {
                "keyword": wakeword,
                "threshold": threshold
            }
        }
        json_payload = json.dumps(payload).encode('utf-8')
        
        # Construct command frame严格按照协议格式
        frame = bytearray()
        
        # 1. Frame header (1 byte)
        frame.append(FRAME_HEADER)  # 0xA5
        
        # 2. User ID (1 byte)
        frame.append(USER_ID)       # 0x01
        
        # 3. Message type (1 byte): 0x05 (set wake word)
        frame.append(0x05)
        
        # 4. Message length (2 bytes, little-endian, length from msg ID to before checksum)
        msg_len = len(json_payload)  # 2 bytes for msg_id + JSON payload length
        frame.append(msg_len & 0xFF)           # Low byte
        frame.append((msg_len >> 8) & 0xFF)    # High byte
        # 5. Message ID (2 bytes, little-endian, cycle through 0-65535)
        self.set_keyword_msg_id = (self.set_keyword_msg_id + 1) % 65536
        frame.append(self.set_keyword_msg_id & 0xFF)           # Low byte
        frame.append((self.set_keyword_msg_id >> 8) & 0xFF)    # High byte
        
        # 6. Message data (JSON payload)
        frame.extend(json_payload)
        
        # 7. Checksum (1 byte, sum of all bytes except checksum, then two's complement)
        checksum = (~sum(frame) + 1) & 0xFF
        frame.append(checksum)
        
        return frame
    def auto_wakeup_command(self,beam=1):
        """Create command packet for setting wake word according to protocol"""
        # Build JSON payload
        payload = {
            "type": "manual_wakeup",
            "content": {
                "beam":beam
            }
        }
        json_payload = json.dumps(payload).encode('utf-8')
        
        # Construct command frame严格按照协议格式
        frame = bytearray()
        
        # 1. Frame header (1 byte)
        frame.append(FRAME_HEADER)  # 0xA5
        # 2. User ID (1 byte)
        frame.append(USER_ID)       # 0x01
        
        # 3. Message type (1 byte): 0x05 (set wake word)
        frame.append(0x05)
        
        # 4. Message length (2 bytes, little-endian, length from msg ID to before checksum)
        msg_len = len(json_payload)  # 2 bytes for msg_id + JSON payload length
        frame.append(msg_len & 0xFF)           # Low byte
        frame.append((msg_len >> 8) & 0xFF)    # High byte
        
        # 5. Message ID (2 bytes, little-endian, cycle through 0-65535)
        self.set_keyword_msg_id = (self.set_keyword_msg_id + 1) % 65536
        frame.append(self.set_keyword_msg_id & 0xFF)           # Low byte
        frame.append((self.set_keyword_msg_id >> 8) & 0xFF)    # High byte
        
        # 6. Message data (JSON payload)
        frame.extend(json_payload)
        
        # 7. Checksum (1 byte, sum of all bytes except checksum, then two's complement)
        checksum = (~sum(frame) + 1) & 0xFF
        frame.append(checksum)
        
        return frame
    def set_wakeword(self, wakeword: str, threshold: str = "900") -> bool:
        """Set wake word for the microphone array with threshold"""
        
        try_count = 3
        while (not self.ser or not self.ser.is_open) and try_count > 0:
            time.sleep(1)
            try_count -= 1
            
        time.sleep(1)
  
        if not self.ser or not self.ser.is_open:
            return False
            
        self.current_wakeword = wakeword
        self.wakeup_threshold = threshold
        # Create and send wake word setting command
        command = self.create_wakeword_command(wakeword, threshold)
        try:
            self.ser.write(command)
            print(f"Setting wake word to: {wakeword} (threshold: {threshold})")
            return True
        except Exception as e:
            print(f"Failed to send wake word setting command: {e}")
            return False
    def auto_wakeup(self) -> bool:
        """Set wake word for the microphone array with threshold"""
        
        try_count = 3
        while (not self.ser or not self.ser.is_open) and try_count > 0:
            time.sleep(1)
            try_count -= 1
            
        time.sleep(1)
  
        if not self.ser or not self.ser.is_open:
            return False
    
        # Create and send wake word setting command
        command = self.auto_wakeup_command()
        try:
            self.ser.write(command)
            print(f"Setting auto wakeup")
            return True
        except Exception as e:
            print(f"Failed to send wake word setting command: {e}")
            return False

    def run(self):
        """Main thread execution"""
        if self.open_port() < 0:
            return

        if self.set_opt(115200, 8, 'N', 1) < 0:
            self.ser.close()
            return

        try:
            while self.running and not self._stop_event.is_set():
                if self.ser and self.ser.is_open and self.ser.in_waiting > 0:
                    byte = self.ser.read(1)[0]  # Read one byte
                    self.deal_with(byte)
                else:
                  time.sleep(0.001)  # Equivalent to usleep(1000)
                    
        except Exception as e:
            pass
        finally:
            self.stop()  # Ensure resources are cleaned up

    def stop(self):
        """Gracefully stop the thread and close resources"""
        try:
            self.running = False
            self._stop_event.set()
            if self.ser and self.ser.is_open:
                self.ser.close()
        except Exception as e:
            pass
class TextSimilarity:
    """
    文本相似度计算类
    """
    def __init__(self, config):
        text= config.get("base_text")
        self.base_text=collections.defaultdict(list)
        for k,v in text.items():
            self.base_text[k].append(self._text_to_pinyin(v))
        self.threshold = config.get("threshold", 0.6)
        #self.vectorizer = TfidfVectorizer(stop_words=None)
    def add_keywords(self,text,lang):
        self.base_text[lang].append(self._text_to_pinyin(text))
    def _text_to_pinyin(self, text):
        """
        将文本转换为拼音。
        Args:
            text (str): 输入的文本。
        Returns:
            list: 转换后的拼音列表。
        """
        try:
            text = self.remove_punctuation(text)
            if not text.strip():
                logger.warning("Input text is empty after removing punctuation.")
                return ''
            # 使用 pypinyin 将文本转换为拼音
            pinyin_list = lazy_pinyin(text)
            #logger.debug(f"Converted text to pinyin: {pinyin_list}")
            return ' '.join(pinyin_list).lower()
        except Exception as e:
            logger.error(f"An error occurred when converting the text to pinyin: {e}")
            return ''
    def remove_punctuation(self, text):
        """
        去除文本中的中英文标点符号。
        Args:
            text (str): 输入的文本。
        Returns:
            str: 去除标点符号后的文本。
        """
        try:
            # 创建一个翻译表，用于移除中英文标点符号
            punctuation = string.punctuation + "，。！？；：“”‘’（）【】《》、"
            # 去除表情包
            emoji_pattern = re.compile(
                "["
                "\U0001F600-\U0001F64F"  # 表情符号
                "\U0001F300-\U0001F5FF"  # 符号和标志
                "\U0001F680-\U0001F6FF"  # 运输和地图符号
                "\U0001F1E0-\U0001F1FF"  # 国旗
                "]+",
                flags=re.UNICODE,
            )
            text = emoji_pattern.sub(r'', text)

            translator = str.maketrans('', '', punctuation)
            # 使用翻译表移除标点符号
            cleaned_text = text.translate(translator)
            return cleaned_text
        except Exception as e:
            logger.error(f"An error occurred when removing punctuation: {e}")
            return text
    def calculate_text_similarity(self,text,weight=0.1):
        """
        计算两个文本之间的余弦相似度。
        :param text: 文本
        :return: 相似度（余弦相似度）
        """
        text = self._text_to_pinyin(text)
        if not text.strip():
            logger.warning("Input text is empty after processing.")
            return 0.0
        try:
            max_similarity = 0
            best_match_key = None
            for k, base_texts in self.base_text.items():
                for base_text in base_texts:
                    fuzzy_similarity = fuzz.ratio(base_text, text) / 100.0
                    if fuzzy_similarity > max_similarity:
                        max_similarity = fuzzy_similarity
                        best_match_key = k
            if max_similarity > self.threshold:
                return best_match_key, True
            return None, False
        except ValueError as e:
            logger.error(f"Error calculating text similarity: {e}")
            return 0.0

    def text_similarity(self,input_text):
        """
        检查输入文本是否与唤醒词相似。
        :param input_text: 输入文本
        :param wake_word: 预设的唤醒词
        :param threshold: 相似度阈值
        :return: 是否是唤醒词
        """
        similarity = self.calculate_text_similarity(input_text)
        return similarity

class VoiceSimilarity:
    """
    语音相似度计算类
    """

    def __init__(self, config):
        base_voice_paths= config.get("base_voice_path")
        self.threshold= config.get("threshold",0.6)
        self.base_feature={}
        for k,base_voice_path in base_voice_paths.items():
            base_audio, base_sr = self.load_audio(base_voice_path)
            self.base_feature[k]=self.extract_features(base_audio, base_sr)

    def load_audio(self, file_path, sr=16000, duration=5):
        """
        加载音频文件并返回音频数据和采样率。
        只加载音频的前 `duration` 秒以加快处理速度。
        :param file_path: 音频文件路径
        :param sr: 采样率，默认为16000
        :param duration: 加载的音频时长（秒）
        :return: 音频数据，采样率
        """
        try:
            audio, sr = librosa.load(file_path, sr=sr, duration=duration)
            return audio, sr
        except Exception as e:
            logger.info(f"Error loading audio file: {e}")
            return None, None

    def extract_features(self, audio, sr, pre_emphasis = 0.97,n_mfcc=20, delta_order=2):
        """提取增强MFCC特征（包含动态特征）"""
        # 加载音频并统一采样率
        
        # 预加重处理（提升高频）
        audio = np.append(audio[0], audio[1:] - pre_emphasis * audio[:-1])
        
        # 提取基础MFCC特征
        mfcc = librosa.feature.mfcc(y=audio, sr=sr, n_mfcc=n_mfcc,
                                    n_fft=2048, hop_length=512, 
                                    window='hamming')
        
        # 计算动态特征（Δ和ΔΔ）
        delta_features = [mfcc]
        for _ in range(delta_order):
            delta = librosa.feature.delta(delta_features[-1])
            delta_features.append(delta)
        
        # 合并所有特征
        combined_features = np.vstack(delta_features)
        
        # 标准化处理（按帧归一化）
        scaler = StandardScaler()
        normalized_features = scaler.fit_transform(combined_features.T).T
        
        return normalized_features
    def calculate_similarity(self, features1, features2):
        """
        计算两个特征向量之间的相似度。
        使用余弦相似度计算。
        :param features1: 第一个特征向量
        :param features2: 第二个特征向量
        :return: 相似度（余弦相似度）
        """
            # 对齐特征长度
        min_len = min(features1.shape[1], features2.shape[1])
        features1 = features1[:, :min_len]
        features2 = features2[:, :min_len]
        return 1 - cosine(features1.flatten(), features2.flatten())
    def voice_similarity(self,file_path):
        """
        比较两个音频文件的相似度。
        :param file_path1: 第一个音频文件路径
        :param file_path2: 第二个音频文件路径       
        """
        audio, sr = self.load_audio(file_path)
        
        if audio is None:
            return None
        features = self.extract_features(audio, sr)
        max_similarity = 0
        best_match_key = None
        for k, base_feature in self.base_feature.items():
            similarity = self.calculate_similarity(features, base_feature)
            if similarity > max_similarity:
                max_similarity = similarity
                best_match_key = k
        if max_similarity > self.threshold:
            return best_match_key, True
        return None,False

def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")
    
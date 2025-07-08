import websocket
from datetime import datetime
import hashlib
import base64
import hmac
import json
from urllib.parse import urlencode
import ssl
from wsgiref.handlers import format_date_time
import os
import soundfile as sf
import time
import uuid

STATUS_FIRST_FRAME = 0  # 第一帧的标识
STATUS_CONTINUE_FRAME = 1  # 中间帧标识
STATUS_LAST_FRAME = 2  # 最后一帧的标识


class Ws_Param:
    """WebSocket参数生成类"""
    def __init__(self, APPID, APIKey, APISecret, Text):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.Text = Text

        # 公共参数
        self.CommonArgs = {"app_id": self.APPID}
        # 业务参数，更多个性化参数可在官网查看
        self.BusinessArgs = {"aue": "raw", "auf": "audio/L16;rate=16000", "vcn": "x4_yezi", "tte": "utf8"}
        self.Data = {"status": 2, "text": str(base64.b64encode(self.Text.encode('utf-8')), "utf-8")}

    # 生成url
    def create_url(self):
        url = 'wss://tts-api.xfyun.cn/v2/tts'
        # 生成RFC1123格式的时间戳
        now = datetime.now()
        date = self._format_date_time(now)

        # 拼接字符串
        signature_origin = "host: " + "ws-api.xfyun.cn" + "\n"
        signature_origin += "date: " + date + "\n"
        signature_origin += "GET " + "/v2/tts " + "HTTP/1.1"
        
        # 进行hmac-sha256加密
        signature_sha = hmac.new(
            self.APISecret.encode('utf-8'), 
            signature_origin.encode('utf-8'), 
            digestmod=hashlib.sha256
        ).digest()
        signature_sha = base64.b64encode(signature_sha).decode(encoding='utf-8')

        authorization_origin = "api_key=\"%s\", algorithm=\"%s\", headers=\"%s\", signature=\"%s\"" % (
            self.APIKey, "hmac-sha256", "host date request-line", signature_sha)
        authorization = base64.b64encode(authorization_origin.encode('utf-8')).decode(encoding='utf-8')
        
        # 拼接鉴权参数，生成url
        v = {
            "authorization": authorization,
            "date": date,
            "host": "ws-api.xfyun.cn"
        }
        url = url + '?' + urlencode(v)
        return url
    
    def _format_date_time(self, dt):
        """格式化为RFC1123时间格式"""
        return dt.strftime("%a, %d %b %Y %H:%M:%S GMT")


class TTSClient:
    """同步版TTS服务客户端，使用同步WebSocket接口"""
    def __init__(self, APPID, APIKey, APISecret, connect_timeout=10, message_timeout=30):
        self.APPID = APPID
        self.APIKey = APIKey
        self.APISecret = APISecret
        self.ws_url = None
        self.ws = None
        self.is_connected = False
        self.connect_timeout = connect_timeout
        self.message_timeout = message_timeout
        self.sample_rate = 16000
        self.channels = 1
        self.sample_width = 2

    def create_ws(self):
        """创建同步WebSocket连接"""
        try:
            ws_param = Ws_Param(self.APPID, self.APIKey, self.APISecret, "")
            self.ws_url = ws_param.create_url()
            
            # 创建SSL上下文
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = True
            ssl_context.verify_mode = ssl.CERT_REQUIRED
            
            # 连接WebSocket（同步方式）
            self.ws = websocket.create_connection(
                self.ws_url,
                ssl=ssl_context,
                timeout=self.connect_timeout
            )
            self.is_connected = True
            return True
        except websocket.WebSocketTimeoutException:
            print(f"WebSocket连接超时（{self.connect_timeout}秒）")
            return False
        except websocket.WebSocketException as e:
            print(f"WebSocket连接异常: {e}")
            return False
        except Exception as e:
            print(f"创建WebSocket连接时发生错误: {e}")
            return False

    def send_text(self, text):
        """发送文本数据到TTS服务（同步方式）"""
        if not self.is_connected:
            print("错误：尚未建立WebSocket连接")
            return False
            
        try:
            ws_param = Ws_Param(self.APPID, self.APIKey, self.APISecret, text)
            request_data = {
                "common": ws_param.CommonArgs,
                "business": ws_param.BusinessArgs,
                "data": ws_param.Data,
            }
            self.ws.send(json.dumps(request_data))
            return True
        except Exception as e:
            print(f"发送文本时发生错误: {e}")
            return False

    def receive_audio(self):
        """接收音频数据（同步方式）"""
        if not self.is_connected:
            print("错误：尚未建立WebSocket连接")
            return None
            
        audio_data = b''
        try:
            # 接收第一帧数据
            message = self.ws.recv()
        except websocket.WebSocketTimeoutException:
            print(f"接收音频数据超时（{self.message_timeout}秒）")
            return None
        except Exception as e:
            print(f"接收消息时发生错误: {e}")
            return None
            
        try:
            message = json.loads(message)
            code = message["code"]
            sid = message["sid"]
            audio = message["data"]["audio"]
            audio = base64.b64decode(audio)
            status = message["data"]["status"]
            
            if status == 2:
                audio_data += audio
                return audio_data

            if code != 0:
                err_msg = message["message"]
                print(f"错误：sid:{sid}, 错误信息: {err_msg}, 错误码: {code}")
            else:
                audio_data += audio
                # 继续接收后续帧
                while True:
                    try:
                        message = self.ws.recv()
                        message = json.loads(message)
                        code = message["code"]
                        audio = message["data"]["audio"]
                        audio = base64.b64decode(audio)
                        status = message["data"]["status"]
                        
                        audio_data += audio
                        if status == 2:
                            break
                            
                        if code != 0:
                            err_msg = message["message"]
                            print(f"错误：sid:{sid}, 错误信息: {err_msg}, 错误码: {code}")
                    except websocket.WebSocketTimeoutException:
                        print(f"接收后续音频帧超时（{self.message_timeout}秒）")
                        break
                    except Exception as e:
                        print(f"接收后续音频帧时发生错误: {e}")
                        break
                        
        except Exception as e:
            print(f"解析音频数据时发生异常: {e}")
            return None
            
        return audio_data if audio_data else None

    def save_audio(self, audio_data, wav_file):
        """保存音频数据为WAV文件（同步方式）"""
        if not audio_data:
            print("错误：没有音频数据可保存")
            return False
            
        try:
            # 先保存为PCM格式
            pcm_file = wav_file.replace(".wav", ".pcm")
            with open(pcm_file, 'wb') as f:
                f.write(audio_data)
                
            # 转换为WAV格式
            data, _ = sf.read(
                pcm_file,
                samplerate=self.sample_rate,
                channels=self.channels,
                subtype='PCM_16',
                format='RAW'
            )
            sf.write(wav_file, data, self.sample_rate)
            os.remove(pcm_file)  # 删除临时PCM文件
            return True
        except Exception as e:
            print(f"保存音频文件时发生错误: {e}")
            return False

    def process_text(self, text, output_file):
            """处理文本并合成为音频（同步方式），每次调用都重新建立连接"""
            # 确保连接已关闭
            if self.is_connected:
                self.stop()
                
            # 建立新连接
            if not self.start():
                return False
                
            if not self.send_text(text):
                return False
                
            audio_data = self.receive_audio()
            
            # 处理完成后关闭连接
            self.stop()
            
            if not audio_data:
                return False
                
            return self.save_audio(audio_data, output_file)

    def run_demo(self):
        """运行TTS演示（同步方式）"""
        if not self.create_ws():
            return
            
        print("TTS演示已启动，输入文本进行语音合成（输入'exit'退出）:")
        while True:
            text = input("> ")
            if text.lower() == 'exit':
                break
                
            if not text:
                continue
                
            output_file = f"tts_{int(time.time())}_{uuid.uuid4().hex[:8]}.wav"
            if self.process_text(text, output_file):
                print(f"音频已保存至: {output_file}")
            else:
                print("音频合成失败")
                
        self.stop()

    def start(self):
        """启动TTS客户端（同步方式）"""
        return self.create_ws()

    def stop(self):
        """停止TTS客户端，关闭WebSocket连接（同步方式）"""
        if self.ws and self.is_connected:
            try:
                self.ws.close()
                self.is_connected = False
                return True
            except Exception as e:
                print(f"关闭WebSocket连接时发生错误: {e}")
                return False
        return True

    async def synthesize(self, text, output_file):
        """合成语音并保存为文件（同步方式）"""
        if not self.is_connected:
            if not self.start():
                raise ValueError("错误：无法建立连接进行语音合成")
                
        return self.process_text(text, output_file)


# 示例调用
async def main():
    tts_client = TTSClient(APPID='', APIKey='', APISecret='')
    await tts_client.start()
    try:
        output_file = f"{uuid.uuid4()}.wav"
        await tts_client.synthesize("这是一个语音合成示例", output_file)
    finally:
        await tts_client.stop()

if __name__ == "__main__":
    asyncio.run(main())
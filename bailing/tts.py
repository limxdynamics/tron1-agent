import asyncio
import logging
import os
import subprocess
import time
import uuid
from abc import ABC, ABCMeta, abstractmethod
from datetime import datetime
from gtts import gTTS
import edge_tts
#import ChatTTS
import torch
import torchaudio
import soundfile as sf
import numpy as np
import sys
import re
import requests
logger = logging.getLogger(__name__)


class AbstractTTS(ABC):
    __metaclass__ = ABCMeta

    @abstractmethod
    def to_tts(self, text):
        pass


class GTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file")
        self.lang = config.get("lang")

    def _generate_filename(self, extension=".aiff"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"执行时间: {execution_time:.2f} 秒")

    def to_tts(self, text):
        tmpfile = self._generate_filename(".aiff")
        try:
            start_time = time.time()
            tts = gTTS(text=text, lang=self.lang)
            tts.save(tmpfile)
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.debug(f"生成TTS文件失败: {e}")
            return None


class MacTTS(AbstractTTS):
    """
    macOS 系统自带的TTS
    voice: say -v ? 可以打印所有语音
    """

    def __init__(self, config):
        super().__init__()
        self.voice = config.get("voice")
        self.output_file = config.get("output_file")

    def _generate_filename(self, extension=".aiff"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"执行时间: {execution_time:.2f} 秒")

    def to_tts(self, phrase):
        logger.debug(f"正在转换的tts：{phrase}")
        tmpfile = self._generate_filename(".aiff")
        try:
            start_time = time.time()
            res = subprocess.run(
                ["say", "-v", self.voice, "-o", tmpfile, phrase],
                shell=False,
                universal_newlines=True,
            )
            self._log_execution_time(start_time)
            if res.returncode == 0:
                return tmpfile
            else:
                logger.info("TTS 生成失败")
                return None
        except Exception as e:
            logger.info(f"执行TTS失败: {e}")
            return None


class EdgeTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file", "tmp/")
        self.voice = config.get("voice")
        self.delay=config.get("delay",0)

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")

    async def text_to_speak(self, text, output_file):
        communicate = edge_tts.Communicate(text, voice=self.voice)  # Use your preferred voice
        await communicate.save(output_file)
        # Add delay (silence) at the beginning of the audio
        audio, sample_rate = sf.read(output_file)
        silence = np.zeros(int(self.delay * sample_rate))
        audio_with_silence = np.concatenate((silence, audio))
        sf.write(output_file, audio_with_silence, sample_rate)

    def to_tts(self, text,*args, **kwargs):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(text, tmpfile))
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.info(f"Failed to generate TTS file: {e}")
            return None
        
class PiperTTS(AbstractTTS):
    def __init__(self, config):
        self.output_file = config.get("output_file", "tmp/")
        vioce_en=config.get("voice_en","en_US-amy-medium")
        vioce_zh=config.get("voice_zh","zh_CN-huayan-medium")
        model_path_en = os.path.join(config.get("model_dir","models/tts/piper"), vioce_en + '.onnx')
        model_path_zh = os.path.join(config.get("model_dir","models/tts/piper"), vioce_zh + '.onnx')
        self.delay=config.get("delay",0)
        self.model_path={
            "en":model_path_en,
            "zh":model_path_zh
        }

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")

    async def text_to_speak(self, text, output_file,lang):
        # Add spaces around punctuation marks in the text
        text = re.sub(r'([,!?;:，：“‘！？])', r' \1.', text)
        text = re.sub(r'\s+', ' ', text).strip()
        process = subprocess.run(
            ['piper', '--model', self.model_path[lang], '--output_file', output_file,"--noise_w",str(1.2),"--sentence_silence",str(1.5)],
            input=text,
            text=True,
            capture_output=True,
            shell=False
        )
        if process.returncode == 0:
            # Add 0.5 seconds of silence to the beginning of the audio
            audio, sample_rate = sf.read(output_file)
            silence = torch.zeros(int(self.delay * sample_rate))
            audio_with_silence = torch.cat((silence, torch.from_numpy(audio)))
            sf.write(output_file, audio_with_silence.numpy(), sample_rate)
        if process.returncode != 0:
            logger.error(f"Piper TTS generation failed: {process.stderr}")
            raise RuntimeError(f"Piper TTS generation failed with return code {process.returncode}")


    def to_tts(self, text,lang):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(text, tmpfile,lang))
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.info(f"Failed to generate TTS file: {e}")
            return None

class KOKOROTTS(AbstractTTS):
    def __init__(self, config):
        from kokoro import KPipeline,KModel
        self.output_file = config.get("output_file", ".")
        #self.lang = config.get("lang", "z")
        model_dir=config.get("model_dir","models/tts/Kokoro-82M")
        model=KModel(repo_id="hexgrad/Kokoro-82M", config=os.path.join(model_dir,"config.json"),model=os.path.join(model_dir,"kokoro-v1_1-zh.pth"))
        device = 'cuda' if torch.cuda.is_available() else 'cpu'
        pipeline_en = KPipeline(lang_code="a",model=model,device=device)  # <= make sure lang_code matches voice
        pipeline_zh = KPipeline(lang_code="z",model=model,device=device,en_callable=self.en_callable)  # <= make sure lang_code matches voice
        voice_zh = config.get("voice_zh", "voices/zf_xiaoni.pt")
        voice_en = config.get("voice_en", "voices/af_heart.pt")
        self.pipeline={
            "en":pipeline_en,
            'zh':pipeline_zh
        }
        self.voice={
            "en":os.path.join(model_dir,voice_en),
            "zh":os.path.join(model_dir,voice_zh)
        }
        print(f"voices:{self.voice}")
        self.delay=config.get("delay",0)

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")
    def speed_callable(self,len_ps):
        speed = 0.8
        if len_ps <= 83:
            speed = 1
        elif len_ps < 183:
            speed = 1 - (len_ps - 83) / 500
        return speed * 1.1
    def en_callable(self,text):
        return next(self.pipeline["en"](text)).phonemes
    async def text_to_speak(self, text, output_file,lang):
        generator = self.pipeline[lang](
            text, voice=self.voice[lang],  # <= change voice here
            speed=self.speed_callable, split_pattern=r'\n+'
        )
        wavs=[]
        for i, (gs, ps, audio) in enumerate(generator):
            wav = audio
            if i==0 and wavs and self.delay > 0:
                wav = np.concatenate([np.zeros(self.delay), wav])
            wavs.append(wav)

        sf.write(output_file, np.concatenate(wavs), 24000)
    def to_tts(self, text,lang):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(text, tmpfile,lang))
            self._log_execution_time(start_time)
            return tmpfile
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None

class CosyVoiceTTS(AbstractTTS):
    # Please clone the code to the third_party firstly with this commod "cd third_party & git clone https://github.com/FunAudioLLM/CosyVoice.git"
    def __init__(self, config):
        from pathlib import Path
        project_dir = config.get("project_dir", "third_party/CosyVoice")
        # 获取当前脚本的路径
        current_file_path = Path(__file__)

        # 获取当前脚本的父目录
        parent_dir = current_file_path.parent.parent
        # 将项目根目录添加到 sys.path
        sys.path.append(os.path.join(parent_dir,project_dir))
        from third_party.CosyVoice.cosyvoice.cli.cosyvoice import CosyVoice

        voice_zh = config.get("voice_zh", "中文女")
        voice_en = config.get("voice_en", "英文女")
        
        self.output_file = config.get("output_file", ".")
        model_dir = config.get("model_dir", "models/tts/CosyVoice-300M-Instruct")
        self.cosyvoice = CosyVoice(model_dir, load_jit=False, load_trt=False, fp16=True)

        self.voice={
            "en":voice_en,
            "zh":voice_zh
        }
        self.delay=config.get("delay",0)

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")
    async def text_to_speak(self, texts, output_file,lang):
        generator = self.cosyvoice.inference_sft(tts_text=texts, spk_id= self.voice[lang], stream=False)
        wavs=[]
        for i, audio in enumerate(generator):
            wav = audio['tts_speech']
            if i==0 and wavs and self.delay > 0:
                wav = torch.cat((torch.zeros(int(self.delay * self.cosyvoice.sample_rate)), wav))
            wavs.append(wav)

        wavs = torch.cat(wavs,dim=1)
        torchaudio.save(output_file, wavs, self.cosyvoice.sample_rate)
    def to_tts(self, text,lang):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(text, tmpfile,lang))
            self._log_execution_time(start_time)
            return tmpfile    
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None
class MegaTTS(AbstractTTS):
    # Please clone the code to the third_party firstly with this commod "cd third_party & git clone https://github.com/bytedance/MegaTTS3.git"
    def __init__(self, config):
        from pathlib import Path
        project_dir = config.get("project_dir", "third_party/MegaTTS3")
        # 获取当前脚本的路径
        current_file_path = Path(__file__)
        
        # 获取当前脚本的父目录
        parent_dir = current_file_path.parent.parent
        # 将项目根目录添加到 sys.path
        sys.path.insert(0,os.path.join(parent_dir,project_dir))
        from third_party.MegaTTS3.tts.infer_cli import MegaTTS3DiTInfer
        voice_zh_file = config.get("voice_zh", "asset/zf_z.wav")
        voice_en_file = config.get("voice_en", "asset/English_prompt.wav")
        with open(voice_en_file, 'rb') as file:
            voice_en = file.read()
        with open(voice_zh_file, 'rb') as file:
            voice_zh = file.read()
        self.output_file = config.get("output_file", ".")
        ckpt_root = config.get("model_dir", "models/tts/MegaTTS3")
        self.megatts = MegaTTS3DiTInfer(ckpt_root=ckpt_root)
        self.voice={
            "en":(voice_en_file,voice_en),
            "zh":(voice_zh_file,voice_zh)
        }
        self.delay=config.get("delay",0)

    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")
    async def text_to_speak(self, texts, output_file,lang):
        resource_context = self.megatts.preprocess(self.voice[lang][1], latent_file=self.voice[lang][0].replace('.wav', '.npy'))
        wav_bytes = self.megatts.forward(resource_context, texts, time_step=32, p_w=1.6, t_w=2.5)
        with open(output_file, 'wb') as file:
            file.write(wav_bytes)
    def to_tts(self, text,lang):
        tmpfile = self._generate_filename(".wav")
        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(text, tmpfile,lang))
            self._log_execution_time(start_time)
            return tmpfile    
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None
        
class TTSAPI(AbstractTTS):
    def __init__(self, config):
        init_api = config.get('init_api')
        self.api = config.get('api')
        if init_api is  None:
            raise ValueError("API is None, can not init model")
        payload={
           "selected_module":config["selected_module"],
        }
        response = requests.request("POST", init_api,data=payload)
        if response.status_code !=200:
            raise ValueError(f"init TTS model {config['selected_module']} failed")
        else:
            logger.info("MegaTTS has initilaized")
        self.output_file = config.get("output_file", ".")
    def _generate_filename(self, extension=".wav"):
        return os.path.join(self.output_file, f"tts-{datetime.now().date()}@{uuid.uuid4().hex}{extension}")

    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")
    async def text_to_speak(self, data, output_file):
        response = requests.post(self.api, data=data, stream=True)
        # 检查响应状态码
        if response.status_code == 200:

            # 保存音频文件到本地
            with open(output_file, "wb") as f:
                for chunk in response.iter_content(chunk_size=1024):
                    if chunk:  # 过滤掉保持连接的新块
                        f.write(chunk)
        else:
            data=response.json()
            raise ValueError(f"init TTS model {data['message']} failed")
    def to_tts(self, text,lang):
        tmpfile = self._generate_filename(".wav")
        data = {
                "text": text,
                "lang": lang
            }

        start_time = time.time()
        try:
            asyncio.run(self.text_to_speak(data,tmpfile))
            self._log_execution_time(start_time)
            return tmpfile    
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None

            
class KedaTTS(AbstractTTS):
    # Please get the APPID and APIKey,APISecret from the website https://www.xfyun.cn/
    def __init__(self, config):
        from .utils.keda import TTSClient 
        
        self.APPID = config.get('APPID')
        self.APIKey = config.get('APIKey')
        self.APISecret = config.get('APISecret')
        self.output_file = config.get("output_file", ".")
        self.connect_timeout = config.get("connect_timeout", 10)
        self.message_timeout = config.get("message_timeout", 30)
        
        if not all([self.APPID, self.APIKey, self.APISecret]):
            raise ValueError("Keda API凭证缺失")
            
        self.tts_client = TTSClient(
            APPID=self.APPID,
            APIKey=self.APIKey,
            APISecret=self.APISecret,
            connect_timeout=self.connect_timeout,
            message_timeout=self.message_timeout
        )
        logger.info("KedaTTS初始化完成")

    def _generate_filename(self, extension=".wav"):
        filename = f"tts-{datetime.now().strftime('%Y%m%d')}@{uuid.uuid4().hex}{extension}"
        return os.path.join(self.output_file, filename)
    def _log_execution_time(self, start_time):
        end_time = time.time()
        execution_time = end_time - start_time
        logger.debug(f"Execution Time: {execution_time:.2f} seconds")
    def to_tts(self, text, lang="zh"):
        if not text:
            logger.warning("文本为空")
            return None
        tmpfile = self._generate_filename()
        start_time = time.time()
        try:
            success = self.tts_client.process_text(text,tmpfile)
            self._log_execution_time(start_time)
            return tmpfile 
        except Exception as e:
            logger.error(f"Failed to generate TTS file: {e}")
            return None


    def __del__(self):
        self.cleanup()

    def cleanup(self):
        if hasattr(self, 'tts_client'):
            self.tts_client.stop()


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")

if __name__ == "__main__":
    config={    
        "voice_zh": 'zh_CN-huayan-medium', #en_US-amy-medium
        "voice_en": "en_US-amy-medium",
        "output_file": "tmp/",
        "model_dir": "models/tts/piper",
        "delay": 0
    }
    from concurrent.futures import ThreadPoolExecutor, TimeoutError
    executor = ThreadPoolExecutor(max_workers=10)
    text=["你好呀，我是小创！"]
    tts_instance = create_instance("PiperTTS", config)
    for t in text:
        future = executor.submit(tts_instance.to_tts, t,"zh")
        file=future.result()
        print(file)
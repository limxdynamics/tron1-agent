import time
from abc import ABC, abstractmethod
import threading
import queue
import logging
import pyaudio
import subprocess
import os
import re
import numpy as np
logger = logging.getLogger(__name__)


class AbstractRecorder(ABC):
    @abstractmethod
    def start_recording(self, audio_queue: queue.Queue):
        pass

    @abstractmethod
    def stop_recording(self):
        pass
class RecorderArecord(AbstractRecorder):
    def __init__(self, config):
        self.output_file=os.path.join(config.get("output_file","tmp/"), f"recorder-tmp.wav")
        self.running = False
        self.paused=False
        self.hw="plughw:0,0"
        self.thread = None
        self.rate = 16000
        self.chunk = 512  # Buffer size
    def start_recording(self, audio_queue: queue.Queue):
        if self.running:
                raise RuntimeError("Stream already running")

        def stream_thread():
            try:
                command = [
                    "arecord", "-D", self.hw,  "-r", str(self.rate), "-t", "wav"
                ]
                process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.running = True
                while self.running:
                    if self.paused:
                        time.sleep(0.1)
                        continue
                    audio_data = process.stdout.read(self.chunk)
                    if not audio_data:
                        break
                    audio_queue.put(audio_data)
            except Exception as e:
                logger.error(f"Error in arecord stream: {e}")
            finally:
                self.stop_recording()

        self.thread = threading.Thread(target=stream_thread)
        self.thread.start()

    def stop_recording(self):
        if not self.running:
            return
        
        self.running = False

        if self.thread and self.thread.is_alive():
            self.thread.join()
            self.thread = None

        # Kill the arecord process
        command = ["pkill", "-f", "arecord"]
        subprocess.run(command)
    def pause_recording(self):
        """暂停录音"""
        if not self.running:
            raise RuntimeError("Cannot pause, recording is not running")
        self.paused = True
        logger.info("Recording paused.")

    def resume_recording(self):
        """恢复录音"""
        if not self.running:
            raise RuntimeError("Cannot resume, recording is not running")
        if self.paused:
            self.paused = False
            logger.info("Recording resumed.")
        else:
            logger.warning("Recording is already running.")
    def __del__(self):
        # Ensure resources are cleaned up on object deletion
        self.stop_recording()

class RecorderPyAudio(AbstractRecorder):
    def __init__(self, config):
        self.format = pyaudio.paInt16
        self.channels = 1
        self.rate = 16000
        self.chunk = 512  # Buffer size
        self.py_audio = pyaudio.PyAudio()
        self.stream = None
        self.thread = None
        self.running = False
        self.paused=False
        self.device=0
        self.hw="plugw:0,0"

    def start_recording(self, audio_queue: queue.Queue):
        if self.running:
            raise RuntimeError("Stream already running")
        
        def stream_thread():
            try:
                self.stream = self.py_audio.open(
                    format=self.format,
                    channels=self.channels,
                    rate=self.rate,
                    input=True,
                    frames_per_buffer=self.chunk,
                    input_device_index=self.device
                )
                self.running = True
                while self.running:
                    data = self.stream.read(self.chunk, exception_on_overflow=False)
                    if self.paused:
                        time.sleep(0.1)
                        #continue
                    else:
                        audio_queue.put(data)
            except Exception as e:
                logger.error(f"Error in stream: {e}")
                self.stop_recording()
            finally:
                self.stop_recording()

        self.thread = threading.Thread(target=stream_thread)
        self.thread.start()

    def stop_recording(self):
        if not self.running:
            return
        
        self.running = False
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None
        
        if self.py_audio:
            self.py_audio.terminate()

        if self.thread:
            self.thread.join()
            self.thread = None
    def pause_recording(self):
        """暂停录音"""
        if not self.running:
            raise RuntimeError("Cannot pause, recording is not running")
        self.paused = True
        logger.info("Recording paused.")

    def resume_recording(self):
        """恢复录音"""
        if not self.running:
            raise RuntimeError("Cannot resume, recording is not running")
        self.paused = False
        logger.info("Recording resumed.")
    def __del__(self):
        # Ensure resources are cleaned up on object deletion
        self.stop_recording()


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")


if __name__ == "__main__":
    import wave
    audio_queue = queue.Queue()
    config={
        "output_file":"tmp",
        "device": "plughw:1,0",
    }
    recorderPyAudio = RecorderPyAudio(config)
    recorderPyAudio.start_recording(audio_queue)
    frames = []
    for _ in range(0, int(16000 / 512 * 5)):
        data = audio_queue.get()
        frames.append(data)
        
    print("Finished recording.")

    try:
        wf = wave.open("output.wav", 'wb')
        wf.setnchannels(1)
        wf.setsampwidth(recorderPyAudio.py_audio.get_sample_size(pyaudio.paInt16))
        wf.setframerate(16000)
        wf.writeframes(b''.join(frames))
        wf.close()
        print(f"Audio saved to 'output.wav'")
    except Exception as e:
        print(f"Failed to save audio: {e}")



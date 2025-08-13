import logging
import platform
import queue
import subprocess
import threading
import wave
import pyaudio
from pydub import AudioSegment
import pygame
import sounddevice as sd
import numpy as np
from playsound import playsound


logger = logging.getLogger(__name__)


class AbstractPlayer(object):
    def __init__(self, *args, **kwargs):
        super(AbstractPlayer, self).__init__()
        self.is_playing = False
        self.play_queue = queue.Queue()
        self._stop_event = threading.Event()
        self.consumer_thread = threading.Thread(target=self._playing, daemon=True)
        self.consumer_thread.start()

    @staticmethod
    def to_wav(audio_file):
        if audio_file[-4:]!=".wav":
            tmp_file = audio_file + ".wav"
        else:
            tmp_file = audio_file
        wav_file = AudioSegment.from_file(audio_file)
        wav_file.export(tmp_file, format="wav")
        return tmp_file

    def _playing(self):
        while not self._stop_event.is_set():
            data = self.play_queue.get()
            self.is_playing = True
            try:
                self.do_playing(data)
            except Exception as e:
                logger.error(f"Failed to play audio: {e}")
            finally:
                self.play_queue.task_done()
                self.is_playing = False

    def play(self, data):
        logger.info(f"Playing file {data}")
        audio_file = self.to_wav(data)
        self.play_queue.put(audio_file)

    def stop(self):
        self._clear_queue()

    def shutdown(self):
        self._clear_queue()
        self._stop_event.set()
        if self.consumer_thread.is_alive():
            self.consumer_thread.join(timeout=2.0)

    def get_playing_status(self):
        """Playing status is true if currently playing or queue is not empty"""
        return self.is_playing or (not self.play_queue.empty())

    def _clear_queue(self):
        with self.play_queue.mutex:
            self.play_queue.queue.clear()

    def do_playing(self, audio_file):
        """Actual implementation of audio playback, to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement do_playing")
class CmdPlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(CmdPlayer, self).__init__(*args, **kwargs)
        self.p = pyaudio.PyAudio()

    def do_playing(self, audio_file):
        system = platform.system()
        cmd = ["aplay", audio_file] if system == "Darwin" else ["play", audio_file]
        logger.debug(f"Executing command: {' '.join(cmd)}")
        try:
            subprocess.run(cmd, shell=False, universal_newlines=True)
            logger.debug(f"Playback completed: {audio_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e}")
        except Exception as e:
            logger.error(f"Unknown error: {e}")


class PyaudioPlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(PyaudioPlayer, self).__init__(*args, **kwargs)
        self.p = pyaudio.PyAudio()
        self.device=0

    def do_playing(self, audio_file):
        chunk = 1024
        try:
            with wave.open(audio_file, 'rb') as wf:
                stream = self.p.open(format=self.p.get_format_from_width(wf.getsampwidth()),
                                     channels=wf.getnchannels(),
                                     rate=wf.getframerate(),
                                     input_device_index=self.device,
                                     output=True)
                data = wf.readframes(chunk)
                while data:
                    stream.write(data)
                    data = wf.readframes(chunk)
                stream.stop_stream()
                stream.close()
            logger.debug(f"Playback completed: {audio_file}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def stop(self):
        super().stop()
        if self.p:
            self.p.terminate()
class AplayPlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(AplayPlayer, self).__init__(*args, **kwargs)
        self.hw="plughw:1,0"

    def do_playing(self, audio_file):
        try:
            command = f'aplay -D {self.hw} {audio_file}'
            subprocess.run(command, shell=True, check=True)
            logger.debug(f"Playback completed: {audio_file}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Command execution failed: {e}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def stop(self):
        super().stop()

class PygamePlayer(AbstractPlayer):
    def __init__(self, *args, **kwargs):
        super(PygamePlayer, self).__init__(*args, **kwargs)
        pygame.mixer.init()

    def do_playing(self, audio_file):
        try:
            while pygame.mixer.music.get_busy():
                pygame.time.Clock().tick(100)
            logger.debug("PygamePlayer loading audio")
            pygame.mixer.music.load(audio_file)
            logger.debug("PygamePlayer finished loading audio, starting playback")
            pygame.mixer.music.play()
            logger.debug(f"Playback completed: {audio_file}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def get_playing_status(self):
        """Playing status is true if currently playing or queue is not empty"""
        return self.is_playing or (not self.play_queue.empty()) or pygame.mixer.music.get_busy()

    def stop(self):
        super().stop()
        pygame.mixer.music.stop()

class PygameSoundPlayer(AbstractPlayer):
    """Supports preloading"""
    def __init__(self, *args, **kwargs):
        super(PygameSoundPlayer, self).__init__(*args, **kwargs)
        pygame.mixer.init()
        pygame.mixer.music.set_volume(0.5)  # 设置为 50% 音量

    def do_playing(self, current_sound):
        try:
            logger.debug("PygameSoundPlayer playing audio")
            current_sound.play()  # Play audio
            while pygame.mixer.get_busy():  # Check if audio is still playing
                pygame.time.Clock().tick(100)  # Check 100 times per second
            del current_sound
            logger.debug(f"PygameSoundPlayer playback completed")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")
    def play(self, data):
        logger.info(f"Playing file {data}")
        audio_file = self.to_wav(data)
        sound = pygame.mixer.Sound(audio_file)
        self.play_queue.put(sound)

    def stop(self):
        super().stop()
        pygame.mixer.stop()
    def get_playing_status(self):
        """Playing status is true if currently playing or queue is not empty"""
        return self.is_playing or (not self.play_queue.empty()) or pygame.mixer.get_busy()
    def shutdown(self):
        pygame.quit()
        super().shutdown()
        

class SoundDevicePlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        try:
            wf = wave.open(audio_file, 'rb')
            data = wf.readframes(wf.getnframes())
            sd.play(np.frombuffer(data, dtype=np.int16), samplerate=wf.getframerate())
            sd.wait()
            logger.debug(f"Playback completed: {audio_file}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def stop(self):
        super().stop()
        sd.stop()


class PydubPlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        try:
            audio = AudioSegment.from_file(audio_file)
            audio.play()
            logger.debug(f"Playback completed: {audio_file}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def stop(self):
        super().stop()
        # Pydub does not provide a stop method


class PlaysoundPlayer(AbstractPlayer):
    def do_playing(self, audio_file):
        try:
            playsound(audio_file)
            logger.debug(f"Playback completed: {audio_file}")
        except Exception as e:
            logger.error(f"Failed to play audio: {e}")

    def stop(self):
        super().stop()
        # playsound does not provide a stop method


def create_instance(class_name, *args, **kwargs):
    # Get class object
    cls = globals().get(class_name)
    if cls:
        # Create and return instance
        print(args, kwargs)
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")
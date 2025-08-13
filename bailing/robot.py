import json
import queue
import threading
#from tkinter.messagebox import NO
import uuid
from abc import ABC
import logging
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import argparse
import time
import sys
from bailing import (
    recorder,
    player,
    asr,
    llm,
    tts,
    vad,
    memory,
    rag,
    trans,
    keywords,
    audio_device
)
from bailing.dialogue import Message, Dialogue
from bailing.utils.utils import is_interrupt, read_config,toolsback,clean_content,is_valid,correct_function_content,clean_function_content
from bailing.utils.prepos_com import preprocess_asr_result
from plugins.registry import Action
from plugins.task_manager import TaskManager
from config.prompt_simple import get_prompt_all
import os
logger = logging.getLogger(__name__)

class Robot(ABC):
    def __init__(self, config_file):
        config = read_config(config_file)
        self.audio_queue = queue.Queue()

        self.recorder = recorder.create_instance(
            config["selected_module"]["Recorder"],
            config["Recorder"][config["selected_module"]["Recorder"]]
        )

        self.asr = asr.create_instance(
            config["selected_module"]["ASR"],
            config["ASR"][config["selected_module"]["ASR"]]
        )

        self.llm = llm.create_instance(
            config["selected_module"]["LLM"],
            config["LLM"][config["selected_module"]["LLM"]]
        )
        self.tts = tts.create_instance(
            config["selected_module"]["TTS"],
            config["TTS"][config["selected_module"]["TTS"]]
        )

        self.vad = vad.create_instance(
            config["selected_module"]["VAD"],
            config["VAD"][config["selected_module"]["VAD"]]
        )

        self.player = player.create_instance(
            config["selected_module"]["Player"],
            config["Player"][config["selected_module"]["Player"]]
        )
        self.translator=trans.create_instance(
            config["selected_module"]["Translator"],
            config["Translator"][config["selected_module"]["Translator"]]
        )
        self.memory = memory.Memory(config.get("Memory"))
        self.deaulat_language=config["Language"]
        self.language=config["Language"]
        self.prompt=get_prompt_all()
        self.wakeword= config.get("WakeWord",None)
        self.wakeword=self.wakeword.split(",")
        # 初始化单例
        context_zh=rag.Rag(config["Rag"]).query("")  # 第一次初始化
        context_en=self.translator.translate(context_zh,"en")
        context={"en":context_en,
                 "zh":context_zh}
        self.name= config.get("name",None)
        self.name=self.name.split(",")
        self.system_prompt={}
        self.name=config.get("name",None)
        self.name=self.name.split(",")
        if self.language=="en":
            name="or" .join(self.name) 
        if self.language=="zh":
            name="或" .join(self.name) 
        for lang in self.prompt:
            memory_prompt=self.prompt[lang]["memory_prompt"].replace("{memory}", self.memory.get_memory()).strip()
            context_prompt=self.prompt[lang]["context_prompt"].replace("{context}", context[lang]).strip()
            self.system_prompt[lang]=self.prompt[lang]["role_prompt"]+'\n'+memory_prompt+'\n'+context_prompt
            self.system_prompt[lang]=self.system_prompt[lang].replace("{agent_name}",name)
        self.preload_prompts_to_wav()
        self.vad_queue = queue.Queue()
        self.dialogue = Dialogue(config["Memory"]["dialogue_history_path"])
        self.dialogue.put(Message(role="system", content=self.system_prompt[self.deaulat_language]))

        # 保证tts是顺序的
        self.tts_queue = queue.Queue()
        # 初始化线程池
        self.executor = ThreadPoolExecutor(max_workers=10)

        self.vad_start = True

        # 打断相关配置
        self.INTERRUPT = config["interrupt"]
        self.silence_time_ms = int((1000 / 1000) * (16000 / 512))  # ms

        # 线程锁
        self.chat_lock = False
        self.tts_lock=False
        self.device_wakeup=False
        # 事件用于控制程序退出
        self.stop_event = threading.Event()

        self.callback = None
        self.speech = []
        self.use_llm=config.get("use_llm",False)
        if self.wakeword is not None:
            self.wakeword_detector_by_device = keywords.create_instance("ComDevice")
            self.wakeword_detector_by_device.start()
        if config["selected_module"].get("WakeUp",None):
            self.wakeword_detector = keywords.create_instance(config["selected_module"]["WakeUp"],config["WakeUp"][config["selected_module"]["WakeUp"]])
            self.wakeword_detector.start()
        else:
            self.wakeword_detector=None
        self.wakeword_detector_by_text = keywords.create_instance("TextSimilarity",config["WakeUp"]["TextSimilarity"])
        self.wake_word_detected = False if self.wakeword is not None else True 
        self.task_queue = queue.Queue()
        self.task_manager = TaskManager(config.get("TaskManager"), self.task_queue)
        if config["ActionTask"]:
            self.call_tools("init_client",{"robot_ip":config["Communication"]["robot_ip"]})
            self.action_history_path=config["Communication"]["action_history_path"]
        self.start_task_mode = config.get("StartTaskMode")
        self.start_time=time.time()
        self.silence_status=True if self.wakeword is not None else True
        self.timeout=config["timeout"]
        self.sleeptime=config["sleeptime"]
        self.web_enable=config["web_enable"]
        self.usb=config["USB"]
        self.device_wakeup=config["device_wakeup"]
        self.algrithm_wakeup=config["algrithm_wakeup"]
        if config["USB"]:
            audio_device.list_audio_devices()
            devices=audio_device.find_record_and_play_devices()
            play_devices=audio_device.find_usb_audio(devices["play_devices"])
            record_devices=audio_device.find_usb_audio(devices["record_devices"])
            logger.info(f"record_devices：{record_devices}")
            logger.info(f"play_devices:{play_devices}")
            if not record_devices:
                logger.error(f"Ther is no usb record dvices")
                raise ValueError(f"Ther is no usb record dvices")
            self.recorder.device=record_devices[0][0]
            self.recorder.hw=record_devices[0][1]
            logger.info(f"USB record device index: {record_devices[0][0]},hw: {record_devices[0][1]}")
            if not record_devices:
                logger.error(f"Ther is no usb play dvices")
                raise ValueError(f"Ther is no usb play dvices")
            self.player.device=play_devices[0][0]
            self.player.hw=play_devices[0][1]
            logger.info(f"USB play device index: {play_devices[0][0]},hw: {play_devices[0][1]}")

    def _detect_wake_word(self,text=None):
        is_wakeup=self.wakeword_detector_by_device.if_awake
        self.wakeword_detector_by_device.if_awake=False
        lang="zh"
        return lang,is_wakeup

    def listen_dialogue(self, callback):
        self.callback = callback

    def _stream_vad(self):
        def vad_thread():
            while not self.stop_event.is_set():
                try:
                    data = self.audio_queue.get()
                    vad_statue = self.vad.is_vad(data)
                    self.vad_queue.put({"voice": data, "vad_statue": vad_statue})
                except Exception as e:
                    logger.error(f"VAD propossing failed: {e}")
        consumer_audio = threading.Thread(target=vad_thread, daemon=True)
        consumer_audio.start()
    def preload_prompts_to_wav(self):
        """
        Preload self.prompt's preset prompts into WAV files and store them for playback.
        Check against prompt.log to avoid redundant TTS conversions.
        """
        self.prompt_wav_files = {}
        prompt_log_path = "config/prompt.log"

        # Load existing prompt log if it exists
        existing_prompts = {}
        if os.path.exists(prompt_log_path):
            try:
                with open(prompt_log_path, "r", encoding="utf-8") as f:
                    existing_prompts = json.load(f)
            except Exception as e:
                logger.error(f"Failed to read prompt.log: {e}")

        # Compare and preload prompts
        for lang in self.prompt:
            self.prompt_wav_files[lang] = {}
            for key, text in self.prompt[lang].items():
                if text and "prompt" not in key:
                    try:
                        # Check if the prompt exists in the log and matches
                        if existing_prompts.get(lang, {}).get(key) == text:
                            asset_path = f"asset/{key}_{lang}.wav"
                            if os.path.exists(asset_path):
                                self.prompt_wav_files[lang][key] = asset_path
                                logger.info(f"Loaded pre-existing prompt '{key}' from WAV file.")
                                continue

                        # Generate TTS and save to asset
                        tts_file = self.tts.to_tts(text, lang)
                        if tts_file:
                            asset_path = f"asset/{key}_{lang}.wav"
                            with open(asset_path, "wb") as f:
                                f.write(open(tts_file, "rb").read())
                            self.prompt_wav_files[lang][key] = asset_path
                            logger.info(f"Preloaded prompt '{key}' into WAV file.")
                        else:
                            logger.error(f"Failed to convert prompt '{key}' to WAV.")
                    except Exception as e:
                        logger.error(f"Error preloading prompt '{key}': {e}")

        # Update prompt log
        try:
            with open(prompt_log_path, "w", encoding="utf-8") as f:
                json.dump(self.prompt, f, ensure_ascii=False, indent=4)
            logger.info("Updated prompt.log with current prompts.")
        except Exception as e:
            logger.error(f"Failed to update prompt.log: {e}")

    def play_preloaded_prompt(self, prompt_key):
        """
        Play a preloaded prompt by its key.
        """
        if self.usb:
            devices=audio_device.find_record_and_play_devices()
            play_devices=audio_device.find_usb_audio(devices["play_devices"])
            record_devices=audio_device.find_usb_audio(devices["record_devices"])
            if not record_devices:
                logger.error(f"Ther is no usb record dvices")
                raise ValueError(f"Ther is no usb record dvices")
            self.recorder.device=record_devices[0][0]
            self.recorder.hw=record_devices[0][1]
            logger.info(f"USB record device index: {record_devices[0][0]},hw: {record_devices[0][1]}")
            if not record_devices:
                logger.error(f"Ther is no usb play dvices")
                raise ValueError(f"Ther is no usb play dvices")
            self.player.device=play_devices[0][0]
            self.player.hw=play_devices[0][1]
            logger.info(f"USB play device index: {play_devices[0][0]},hw: {play_devices[0][1]}")
        tts_file = self.prompt_wav_files[self.language].get(prompt_key)
        if tts_file:
            future=self.executor.submit(self.player.play,tts_file)
            while self.player.get_playing_status() or not future.done():
                time.sleep(0.1)
        else:
            logger.error(f"Prompt '{prompt_key}' not preloaded or missing.")
    def _tts_priority(self):
        def priority_thread():
            while not self.stop_event.is_set():
                try:
                    future = self.tts_queue.get()
                    try:
                        tts_file = future.result(timeout=60)
                    except TimeoutError:
                        logger.error("TTS timeout")
                        continue
                    except Exception as e:
                        logger.error(f"TTS propossing failed: {e}")
                        continue
                    if tts_file is None:
                        continue
                    self.player.play(tts_file)
                except Exception as e:
                    logger.error(f"tts_priority priority_thread: {e}")
        tts_priority = threading.Thread(target=priority_thread, daemon=True)
        tts_priority.start()
    def monitor_executor(self):
        """
        监控 ThreadPoolExecutor 的线程和任务
        """
        active_threads = len(self.executor._thrknn_classifyeads)
        waiting_tasks = self.executor._work_queue.qsize()
        logger.info(f"Active threads: {active_threads}, Waiting tasks in queue: {waiting_tasks}")
    def interrupt_playback(self):
        """中断当前的语音播放"""
        logger.info("Interrupting current playback.")
        self.player.stop()

    def shutdown(self):
        """关闭所有资源，确保程序安全退出"""
        logger.info("Shutting down Robot...")
        self.executor.shutdown(wait=False)
        self.recorder.stop_recording()
        self.player.shutdown()
        self.wakeword_detector_by_device.stop()
        # Wait for threads to finish
        if self.wakeword_detector_by_device.is_alive():
            self.wakeword_detector_by_device.join(timeout=1.0)
        self.stop_event.set()
        logger.info("Shutdown complete.")

    def start_recording_and_vad(self):
        # Start the recorder
        self.recorder.start_recording(self.audio_queue)
        logger.info("Started recording.")
        # vad 实时识别
        self._stream_vad()
        # tts优先级队列
        self._tts_priority()
    def monitor_player_status(self):
        # 开始监听语音流
        def player_status():
            while not self.stop_event.is_set():
                try:
                    if self.player.get_playing_status():
                        if not self.recorder.paused:
                            try:
                                logger.info("Player is playing, pausing recorder.")
                                self.recorder.pause_recording()
                            except:
                                pass
                    else:
                        if self.recorder.paused:
                            logger.info("Player stopped, resuming recorder.")
                            self.recorder.resume_recording()
                    time.sleep(0.1)  # Avoid busy-waiting
                except Exception as e:
                    logger.error(f"Error monitoring player status: {e}")
            # Start the player status monitoring thread
        player_status_thread = threading.Thread(target=player_status, daemon=True)
        player_status_thread.start()
    def wakeup_interrupt(self):
        if self.chat_lock is True or self.wake_word_detected or self.player.get_playing_status():  # 正在播放，打断场景
            if self.INTERRUPT:
                self.interrupt_playback()
                self.chat_lock = False
                self.tts_lock=False
                self.clear_tasks()
                self.task_manager.cancel_all_tasks()
                logger.info("Interrupting playback and clearing task queue.")
                with self.task_queue.mutex:
                    self.task_queue.queue.clear()  # 清空任务队列
                self.player.play_queue.queue.clear()
        self.silence_status = False
        self.wake_word_detected = True
        self.vad_start = True  # 控制vad输入，播放的时候就不需要在解析语音了
        self.speech = []
        self.start_time=None
        return
    def clear_tasks(self):
        """彻底清空TTS任务并取消执行中的任务"""
        # 取消线程池中的TTS任务
        if self.executor._work_queue.qsize() > 0:
            # 遍历工作队列并尝试取消任务
            with self.executor._work_queue.mutex:
                tasks = list(self.executor._work_queue.queue)
                for task in tasks:
                    task.cancel()
            
        # 清空TTS队列
        while not self.tts_queue.empty():
            try:
                future = self.tts_queue.get()
                if future and not future.done():
                    future.cancel()
            except queue.Empty:
                break
        while not self.player.play_queue.empty():
            try:
                future = self.player.play_queue.get()
                if future and not future.done():
                    future.cancel()
            except queue.Empty:
                break
                    
        # 停止TTS相关线程
        if hasattr(self, 'tts_priority_thread') and self.tts_priority_thread.is_alive():
            self.tts_priority_thread.join(timeout=1.0)
    def _duplex(self):
        """
        双工处理逻辑，实时检测唤醒词并处理指令。
        """
        # 检测唤醒词
        if self.device_wakeup:
            lang,is_wakeup = self._detect_wake_word()
            if self.wakeword and is_wakeup:
                self.language=lang
                self.device_wakeup=True
                self.wakeup_interrupt()
                logger.info("Detected wake word to waking up")
                # 播放启动提示语
                self.play_preloaded_prompt("wakeup")
                return  # 唤醒后直接跳过当前循环
            
        # 从 VAD 队列中获取数据
        data = self.vad_queue.get()
        vad_status = data.get("vad_statue")
                # 识别到vad开始
        if self.vad_start:
            self.speech.append(data)
        # 处理 VAD 状态
        if vad_status is None:
            # 空闲时处理耗时任务
            if not self.task_queue.empty() and not self.vad_start and not self.player.get_playing_status() and self.chat_lock is False:
                result = self.task_queue.get()
                future = self.executor.submit(self.speak_and_play, result.response)
                self.tts_queue.put(future)

            # 休眠模式
            if not self.vad_start and not self.player.get_playing_status() and self.chat_lock is False  and not self.silence_status and self.executor._work_queue.qsize() == 0 and not self.speech and self.task_queue.empty():
                self.start_time = time.time()
                sleep_flag=False
            while not self.vad_start and not self.player.get_playing_status() and self.chat_lock is False and not self.silence_status and self.executor._work_queue.qsize() == 0 and not self.speech and self.task_queue.empty():
                data = self.vad_queue.get()
                vad_status = data.get("vad_statue")
                if vad_status is None:
                    if self.start_time is None:
                        break
                    # 检查是否需要进入休眠状态
                    if abs(time.time() - self.start_time-self.sleeptime//2)<0.005 and not sleep_flag:
                        sleep_flag=True
                        self.play_preloaded_prompt("wait")
                    # 检查是否需要进入休眠状态
                    if abs(time.time() - self.start_time -self.sleeptime)<0.005 and sleep_flag:
                        self.play_preloaded_prompt("sleep")
                        self.silence_status=True
                else:
                    break

            if vad_status is None:
                return

        # VAD 开始状态
        if "start" in vad_status:
            self.vad_start = True
            self.speech.append(data)

        # VAD 结束状态
        elif "end" in vad_status and len(self.speech) > 0:
            try:
                if len(self.speech) < 10:
                    logger.debug("The length of the voice packet is less than 10ms")
                    if not self.wake_word_detected:
                        self.speech = []
                    return
                self.vad_start = False
                voice_data = [d["voice"] for d in self.speech]
                self.speech = []
                
                text, tmpfile, lang_ = self.asr.recognizer(voice_data)
                logger.debug(f"ASR recognition result: {text}")
                # 判断识别到的文本是否无效
                if not text.strip() or not is_valid(text):
                    logger.debug(f"Invalid recognition results. Skip processing: {text}")
                    return
                if self.algrithm_wakeup:
                    lang1,is_wakeup1=self.wakeword_detector_by_text.text_similarity(text) 
                    if is_wakeup1 and self.wakeword:
                        self.language=lang1 if lang1!='' else self.language
                        logger.info("Detected wake word to waking up")
                        self.wakeup_interrupt()
                        self.play_preloaded_prompt("wakeup")
                        logger.info(f"lang1:{lang1}")
                        return  # 唤醒后直接跳过当前循环
                    else:
                        self.language=lang_ if lang_!='' else self.language
                else:
                    self.language=lang_ if lang_!='' else self.language
                # 检查是否为退出指令
                if is_interrupt(text, self.prompt[self.language]["exit_prompt"].split('\n')):
                    logger.info("Exit command received. Shutting down.")
                    self.play_preloaded_prompt("bye")
                    self.call_tools("close_client", {"path": self.action_history_path})
                    self.shutdown()
                    return
                if self.wake_word_detected:
                    if self.callback:
                        self.callback({"role": "user", "content": str(text)})
                    self.tts_lock=True
                    future = self.executor.submit(self.chat, text)
                    # self.wake_word_detected = False if self.wakeword is not None else True
                    # self.silence_status = True
            except Exception as e:
                self.vad_start = False
                self.speech = []
                logger.error(f"ASR recognition failed: {e}")
                return



    def sleep_robot(self):
        self.silence_status=True
        self.wake_word_detected=False if self.wakeword is not None else True
        logger.info("Robot is sleeping.")
        self.play_preloaded_prompt("sleep")
        #self.wakeword_detector_by_device.if_awake=False

    def run(self):
        try:
            self.play_preloaded_prompt("startup")
            self.start_recording_and_vad()  # 监听语音流
            if not self.INTERRUPT:
                self.monitor_player_status() 
            while not self.stop_event.is_set():
                self._duplex()  # 双工处理
        except KeyboardInterrupt:
            self.call_tools("close_client",{"path":self.action_history_path})
            logger.info("Received KeyboardInterrupt. Exiting...")
        except Exception as e:
            self.call_tools("close_client",{"path":self.action_history_path})
            logger.info(f"{e}. Exiting...")
        finally:
            self.shutdown()
            sys.exit(0)
            raise KeyboardInterrupt("模拟键盘中断")


    def speak_and_play(self, text):
        if text is None or len(text)<=0:
            logger.info(f"No TTS conversion is required. The query is empty,{text}")
            return None
        tts_file=self.tts.to_tts(text,self.language)
        if tts_file is None:
            logger.error(f"TTS conversion failed,{text}")
            return None
        if self.tts_lock:
            return tts_file
        else:
            return None
    
    def call_tools(self,function_name,function_arguments,query=""):
        function_id = str(uuid.uuid4().hex)
        # 调用工具
        try:
            logger.info(f"function_name:{function_name}, function_id:{function_id}, function_arguments:{function_arguments}")
            result = self.task_manager.tool_call(function_name, function_arguments)
            # result.response=self.translator.translate(result.response,self.language) if result.response is not None else None ##TODO 增加llm翻译 
            # result.result=self.translator.translate(result.result,self.language) if result.result is not None else None ##TODO 增加llm翻译
            logger.info(f"Funtion result: action:{result.action},result:{result.result},response:{result.response}")
        except Exception as e:
            logger.error(f"Call function failed：{e}")
            return [self.prompt[self.language]['stop_function_prompt']]
        if result.action == Action.NOTFOUND: # = (0, "没有找到函数")
            logger.error(f"Not found function: {function_name}")
            return [self.prompt[self.language]['stop_function_prompt']]
        elif result.action == Action.NONE: # = (1,  "啥也不干")
            return []
        elif result.action == Action.RESPONSE: # = (2, "直接回复")
            future = self.executor.submit(self.speak_and_play, result.response)
            self.tts_queue.put(future)
            return [result.response]
        elif result.action == Action.REQLLM: # = (3, "调用函数后再请求llm生成回复")
            # 添加工具内容step_str
            self.dialogue.put(Message(role='assistant',
                                    tool_calls=[{"id": function_id, "function": {"arguments": json.dumps(function_arguments ,ensure_ascii=False),
                                                                                "name": function_name},
                                                "type": 'function', "index": 0}]))

            self.dialogue.put(Message(role="tool", tool_call_id=function_id, content=result.result))
            rerequry=result.result+query
            dialogue=[{"role":"system","content":self.system_prompt[self.language]},{"role":"user","content":rerequry}]
            response=self.llm.response(dialogue)
            response="".join(response).strip('\n')
            response=clean_content(response)
            future = self.executor.submit(self.speak_and_play, response)
            self.tts_queue.put(future)
            return [response]
        elif result.action == Action.ADDSYSTEM: # = (4, "添加系统prompt到对话中去")
            self.dialogue.put(Message(**result.result))
            return []
        elif result.action == Action.ADDSYSTEMSPEAK: # = (5, "添加系统prompt到对话中去&主动说话")
            self.dialogue.put(Message(role='assistant',
                                    tool_calls=[{"id": function_id, "function": {
                                        "arguments": json.dumps(function_arguments, ensure_ascii=False),
                                        "name": function_name},
                                                "type": 'function', "index": 0}]))

            self.dialogue.put(Message(role="tool", tool_call_id=function_id, content=result.response))
            self.dialogue.put(Message(**result.result))
            self.dialogue.put(Message(role="user", content="ok"))
            return self.chat(result.result)
        elif result.action == Action.ADDTOOLSBACK: # = (6, "添加工具返回的prompt并且主动说话")
            self.dialogue.put(Message(role="tool", tool_call_id=function_id, content=result.result))
            try:
                dialogue=toolsback(result.result,self.language)
                callback_result = self.llm.response(dialogue)
                callback_result=''.join(callback_result)
                self.dialogue.put(Message(role="assistant", tool_call_id=function_id, content=callback_result))
                logger.info(f"tools callback: {callback_result}")
                return [callback_result]
            except Exception as e:
                logger.error(f"Callback failed：{e}")
                return [[self.language]['stop_function_prompt']]
        elif result.action == Action.STOPFUNCTION: # = (7, "添加工具返回的prompt并且主动说话")
            self.dialogue.put(Message(role="tool", tool_call_id=function_id, content=self.prompt[self.language]['stop_function_prompt']))
            response=f"{result.response},and {self.prompt[self.language]['stop_function_prompt']}" if result.response is not None else self.prompt[self.language]['stop_function_prompt']
            future = self.executor.submit(self.speak_and_play,response)
            self.tts_queue.put(future)
            return [self.prompt[self.language]['stop_function_prompt']]
        elif result.action == Action.ADDTOOLSBACK_STOPFUNCTION: # = (8, "添加工具返回的prompt并且主动说话")
            self.dialogue.put(Message(role="tool", tool_call_id=function_id, content=result.result))
            try:
                dialogue=toolsback(result.result,self.language)
                callback_result = self.llm.response(dialogue)
                callback_result=''.join(callback_result)
                self.dialogue.put(Message(role="assistant", tool_call_id=function_id, content=callback_result))
                logger.info(f"tools callback: {callback_result}")
                return [self.prompt[self.language]['stop_function_prompt']]
            except Exception as e:
                logger.error(f"Callback failed：{e}")
                return [self.prompt[self.language]['stop_function_prompt']]
        else:
            logger.error(f"not found action type: {result.action}")
            return [self.prompt[self.language]['stop_function_prompt']]


    def chat_tool_by_content(self, query):
        try:
            _,functions = preprocess_asr_result(query, language=self.language)
            logger.info(f"message content：{functions}")
            response_message=str(functions)
        except:
            functions=None
            response_message=None
        if len(query)>3:
            self.wake_word_detected = False if self.wakeword is not None else True
            self.silence_status = True
        if functions is None or response_message is None:
            if self.use_llm and len(query)>=3:
                try:
                    dialogue=[{"role":"system","content":self.system_prompt[self.language]},{"role":"user","content":query+"/no_think"}]
                    future = self.executor.submit(self.llm.response_call,dialogue,functions_call=self.task_manager.get_functions())
                    timeout=0
                    while not future.done():
                        if not self.chat_lock:
                            logger.warning("chat_lock is False, stopping execution.")
                            future.cancel()
                            return []
                        if time.time()-timeout==self.timeout//2:
                            self.play_preloaded_prompt("think")  # 播放“正在思考中”的提示语音
                    llm_responses = future.result()  # 等待任务完成，不设置超时
                except Exception as e:
                    logger.error(f"LLM processing error {query}: {e}")
                    return None
                functions=[]
                response_message = ""
                for chunk in llm_responses:
                    content, tools_calls = chunk
                    if tools_calls is not None:
                        for tools_call in tools_calls:
                            function_arguments = ""
                            function_name = None
                            if tools_call.function is not None and tools_call.function.name is not None:
                                function_name = tools_call.function.name
                            if tools_call.function is not None and tools_call.function.arguments is not None:
                                function_arguments = tools_call.function.arguments
                            if function_name and function_arguments:
                                functions.append((function_name, function_arguments))
                    if content is not None and len(content) > 0:
                        response_message+=content
                if  "function_name" in response_message:
                    functions=clean_function_content(response_message)
                else:
                    functions=correct_function_content(functions)
                response_message=clean_content(response_message)
                logger.info(f"LLM content：{response_message}")
                logger.info(f"functions content：{functions}")
            else:
                return []
        if functions:
            if len(functions)==1 and "unknow" in functions[0]:
                response_message=self.prompt[self.language]["noise"]

                _, functions= preprocess_asr_result("unknow", language=self.language)
                if os.path.exists(functions[0]):
                    self.player.play(response_message)
                return response_message
            action_len=0
            for function in functions:
                if "TronAction" in str(function):
                    action_len+=1
            if len(functions)==action_len:
                self.play_preloaded_prompt("exe")
                response_message=self.prompt[self.language]["exe"]
            for function in functions:
                logger.debug(f"function:{function}")
                if not self.chat_lock:
                    logger.warning("chat_lock is False, stopping execution.")
                    return []
                try:
                    logger.info(f"function:{function}")
                    if isinstance(function,dict):
                        function_arguments=function["args"]
                        if "unknow" in function_arguments:
                            continue
                        function_name=function["function_name"]  
                        future = self.executor.submit(self.call_tools, function_name,function_arguments,query)
                        response_message=future.result(timeout=60)
                        if not self.chat_lock:
                            logger.warning("chat_lock is False, stopping execution.")
                            return []
                    elif os.path.exists(function):
                        self.player.play(function)
                        continue
                    else:
                        response_message=function
                        if response_message is None:
                            response_message=self.prompt[self.language]["noise"]
                        response_message=self.translator.translate(response_message,self.language)
                        future = self.executor.submit(self.speak_and_play, response_message)
                        self.tts_queue.put(future)
                except TimeoutError:
                    logger.error("call tools time out")
                    return [self.prompt[self.language]["noise"]]
                except Exception as e:
                    logger.info(f"tolls call error:{e}")
                    return []
        else:
            if "noise" in response_message or "噪音" in response_message:
                return []
            elif  ("function_name" in response_message or "TronAction" in response_message): 
                self.play_preloaded_prompt("unknow")
                return ["response error,please try again"]
            elif response_message:
                logger.info(f"response_message:{response_message}")
                try:
                    response_messages= json.loads(response_message.replace("\'","\""))
                    for response_message in response_messages:
                        if os.path.exists(response_message):
                            self.player.play(response_message)
                            response_message=[]
                        else:
                            if response_message is None:
                                response_message=self.prompt[self.language]["noise"]
                            response_message=self.translator.translate(response_message,self.language)
                            future = self.executor.submit(self.speak_and_play, response_message)
                            self.tts_queue.put(future)
                except:
                        if os.path.exists(response_message):
                            self.player.play(response_message)
                            response_message=[]
                        else:
                            if response_message is None:
                                response_message=self.prompt[self.language]["noise"]
                            response_message=self.translator.translate(response_message,self.language)
                            future = self.executor.submit(self.speak_and_play, response_message)
                            self.tts_queue.put(future)
        return [response_message]
    
    def chat(self, query):
        self.dialogue.put(Message(role="user", content=query))
        self.chat_lock = True
        response_message=[]
        if self.start_task_mode:
            response_message = self.chat_tool_by_content(query)
        else:
            try:
                llm_responses = self.llm.response(self.dialogue.get_llm_dialogue())
            except Exception as e:
                self.chat_lock = False
                logger.error(f"LLM processing error {query}: {e}")
                return None

            response_message="".join(llm_responses)
            future = self.executor.submit(self.speak_and_play, response_message)
            self.tts_queue.put(future)
            response_message=[response_message]

        self.chat_lock = False
        if self.callback:
            self.callback({"role": "assistant", "content": "".join(response_message)})

        self.dialogue.put(Message(role="assistant", content="".join(response_message)))
        self.dialogue.dump_dialogue()
        if not response_message:
            self.wake_word_detected = True
            self.silence_status = False
            self.dialogue.dialogue.pop()
        logger.debug(json.dumps(self.dialogue.get_llm_dialogue(), indent=4, ensure_ascii=False))
        return True

if __name__ == "__main__":
    # Create the parser
    parser = argparse.ArgumentParser(description="Tron robot")

    # Add arguments
    parser.add_argument('config_path', type=str, help="cinfig file", default=None)

    # Parse arguments
    args = parser.parse_args()
    config_path = args.config_path

    # 创建 Robot 实例并运行
    robot = Robot(config_path)
    robot.run()


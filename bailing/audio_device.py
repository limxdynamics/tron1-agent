import pyaudio
import re
import logging
import subprocess
logger=logging.getLogger(__name__)

def list_audio_devices():
    """
    列出所有音频设备，并分别标记支持录音和播放的设备。
    """
    p = pyaudio.PyAudio()
    logger.info("Available audio devices:")
    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        input_channels = device_info.get('maxInputChannels', 0)
        output_channels = device_info.get('maxOutputChannels', 0)
        device_name = device_info.get('name')
        
        # 检查是否支持录音或播放
        if input_channels > 0:
            print(f"Device index: {i}, Device name: {device_name}, Type: Record")
        if output_channels > 0:
            print(f"Device index: {i}, Device name: {device_name}, Type: Play")
    p.terminate()

def find_record_and_play_devices():
    """
    分别找到支持录音和播放的设备索引。
    Returns:
        dict: 包含录音设备和播放设备的索引。
    """
    p = pyaudio.PyAudio()
    record_devices = []
    play_devices = []

    for i in range(p.get_device_count()):
        device_info = p.get_device_info_by_index(i)
        input_channels = device_info.get('maxInputChannels', 0)
        output_channels = device_info.get('maxOutputChannels', 0)
        device_name = device_info.get('name')

        # 检查是否支持录音
        if input_channels > 0:
            record_devices.append((i, device_name))
        
        # 检查是否支持播放
        if output_channels > 0:
            play_devices.append((i, device_name))
    
    p.terminate()
    return {"record_devices": record_devices, "play_devices": play_devices}



def find_usb_audio(devices):
    usb_devices=[]
    for index, name in devices:
        if "USB" in name:
            hw=re.findall(r'\((.*?)\)', name)[0]
            usb_devices.append((index,"plug"+hw))
    return usb_devices
def check_aplay_hw_availability(hw):
    """
    使用aplay检查指定的hw是否可用。
    Args:
        hw (str): 硬件设备的hw字符串，例如"hw:1,0"。
    Returns:
        bool: 如果设备可用，返回True；否则返回False。
    """

    try:
        result = subprocess.run(
            ["aplay", "-D", f"{hw}", "./aseet/silence.wav","-t","raw"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(f"Device hw:{hw} is available.")
            return True
        else:
            logger.warning(f"Device hw:{hw} is not available. Error: {result.stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"Error while checking device hw:{hw}: {e}")
        return False
def find_usb_devices_by_command():
    """
    使用aplay -l 和 arecord -l 找到USB音频设备，并根据排列给出Index和hw。
    Returns:
        dict: 包含播放设备和录音设备的USB设备索引、名称及hw。
    """
    usb_play_devices = []
    usb_record_devices = []

    try:
        # 使用aplay -l查找播放设备
        aplay_result = subprocess.run(
            ["aplay", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if aplay_result.returncode == 0:
            aplay_output = aplay_result.stdout.decode()
            index=-1
            for line in aplay_output.splitlines():
                if "card" in line:
                    index+=1
                    if  "USB" in line:
                        match = re.search(r"card (\d+):.*?\[(.*?)\].*?device (\d+):", line)
                        if match:
                            card_index = match.group(1)
                            card_name = match.group(2)
                            device_index = match.group(3)
                            hw = f"hw:{card_index},{device_index}"
                            usb_play_devices.append((index, card_name, "plug"+hw))
        else:
            logger.warning(f"Failed to run aplay -l. Error: {aplay_result.stderr.decode()}")

        # 使用arecord -l查找录音设备
        arecord_result = subprocess.run(
            ["arecord", "-l"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if arecord_result.returncode == 0:
            arecord_output = arecord_result.stdout.decode()
            index=-1
            for line in arecord_output.splitlines():
                if "card" in line:
                    index+=1
                    if  "USB" in line:
                        match = re.search(r"card (\d+):.*?\[(.*?)\].*?device (\d+):", line)
                        if match:
                            #card_index = match.group(1)
                            card_name = match.group(2)
                            device_index = match.group(3)
                            hw = f"hw:{card_index},{device_index}"
                            usb_record_devices.append((index, card_name, "plug"+hw))
        else:
            logger.warning(f"Failed to run arecord -l. Error: {arecord_result.stderr.decode()}")

    except Exception as e:
        logger.error(f"Error while finding USB devices: {e}")

    return {"usb_play_devices": usb_play_devices, "usb_record_devices": usb_record_devices}
def check_arecord_hw_availability(hw: str) -> bool:
    """
    使用arecord检查指定的hw是否可用。
    Args:
        hw (str): 硬件设备的hw字符串，例如"hw:1,0"。
    Returns:
        bool: 如果设备可用，返回True；否则返回False。
    """
    try:
        result = subprocess.run(
            ["arecord", "-D", f"{hw}","-d", "1"],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=5
        )
        if result.returncode == 0:
            logger.info(f"Device hw:{hw} is available.")
            return True
        else:
            logger.warning(f"Device hw:{hw} is not available. Error: {result.stderr.decode()}")
            return False
    except Exception as e:
        logger.error(f"Error while checking device hw:{hw}: {e}")
        return False
    

    
if __name__=="__main__":
    # 列出所有音频设备
    list_audio_devices()
    # 找到录音和播放设备
    devices = find_record_and_play_devices()
    print("\nRecord devices:")
    for index, name in devices["record_devices"]:
        print(f"Index: {index}, Name: {name}")

    print("\nPlay devices:")
    for index, name in devices["play_devices"]:
        print(f"Index: {index}, Name: {name}")
    index,hw=find_usb_audio(devices["play_devices"])[0]
    print(f"play_devices:Index: {index}, Name: {hw}")
    print(f"play device is avaliable:{check_aplay_hw_availability(hw)}")
    index,hw=find_usb_audio(devices["record_devices"])[0]
    print(f"record_devices:Index: {index}, Name: {hw}")
    print(f"record device is avaliable:{check_arecord_hw_availability(hw)}")
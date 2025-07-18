import yaml
import json
import re
import langid
from pydub import AudioSegment
import noisereduce as nr
import logging
logger=logging.getLogger(__name__)

def enhance_and_denoise_audio(audio,sr=16000, gain_dB=10):
    """
    对音频文件进行增益增强和降噪处理。
    
    参数:
    - input_file: 输入音频文件路径
    - output_file: 输出处理后的音频文件路径
    - sr: 采样率，默认为 16000 Hz
    - gain_dB: 增益（以分贝为单位），默认为 10 dB
    """
    
    # 直接对音频进行降噪处理
    reduced_noise = nr.reduce_noise(y=audio, sr=sr)
    # 将降噪后的音频数据转换为 pydub 的 AudioSegment 对象
    audio_segment = AudioSegment(
        reduced_noise.tobytes(),
        frame_rate=sr,
        sample_width=reduced_noise.dtype.itemsize,
        channels=1
    )
    
    # 应用增益增强
    enhanced_audio = audio_segment + gain_dB
    
    return enhanced_audio

def detect_language(text):
    chinese_pattern = re.compile(
        r'[\u4E00-\u9FFF]'
    )
    lang, confidence = langid.classify(text)
    if lang == 'zh' or bool(chinese_pattern.search(text)):
        return "zh"
    elif lang == 'en' or bool(re.fullmatch(r"[A-Za-z\s.,!?\"'-]+", text)):
        return "en"
    else:
        return "unknown"


def toolsback(data,language):
    """
    自定义回调函数，用于处理机器人事件。
    Args:
        data (dict): 包含事件信息的字典，例如 {"role": "user", "content": "识别到的文本"}。
    """
    system_prompt=f"""
    你是控制机器人的助手,名字叫做小创。
    现在有一些机器人工具的返回信息，你需要总结这些信息告诉用户，并给出可能的解决方案。
    例如用户告诉你'***ERROR***Timeout: Failed to enter STAND mode.'，你可以告诉用户'抱歉，小创出现问题了，执行超时，您可以稍后重试哦'
    # 回复要求
    1. 你的回复应该简短、友好、口语化强一些，回复禁止出现表情符号。
    2. 不要多种语言混杂，尽可能保证只有一种响应语言。你的回复语言必须是{language}!你的回复语言必须是{language}!
    """
    dialogue = [{"role": "system", "content":system_prompt},{"role":"user", "content":data}]
    return dialogue
def convert_chinese_to_english_symbols(input_string):
    """
    将中文符号转换为英文符号
    """
    # 定义符号映射表
    symbol_map = {
        '，': ',',
        '。': '.',
        '！': '!',
        '？': '?',
        '；': '',
        '：': ':',
        '（': '(',
        '）': ')',
        '【': '[',
        '】': ']',
        '“': '"',
        '”': '"',
        '‘': "'",
        '’': "'",
        " ": "",
        "`": "",
        "*": "",
        "'": "\"",
    }
    # 使用 str.translate 进行替换
    return input_string.translate(str.maketrans(symbol_map))
def clean_content(input_string):
    """
    清理输入字符串，提取有效的 TronAction 内容。

    Args:
        input_string (str): 原始输入字符串。Sdom.

    Returns:
        str: 清理后的 TronAction 内容。
    """
    symbol_map = {
        '`': '',
        "*": "",
        #"\n": ""
    }
    input_string = re.sub(r'<think>.*?</think>', '', input_string, flags=re.DOTALL)
    cleaned_lines = input_string.translate(str.maketrans(symbol_map))
    matches = re.findall(r'<answer>(.*?)</answer>', cleaned_lines, flags=re.DOTALL)
    cleaned_lines_answer = ''.join(matches)
    cleaned_lines_answer=cleaned_lines_answer if cleaned_lines_answer else cleaned_lines
    return cleaned_lines_answer if cleaned_lines_answer else None
def clean_function_content(input_string):
    """
    清理输入字符串，提取有效的 TronAction 内容。

    Args:
        input_string (str): 原始输入字符串。

    Returns:
        str: 清理后的 TronAction 内容。
    """
    # 定义正则表达式，匹配 {"function_name":"...", "args":{...}}
    if isinstance(input_string, str):
        try:
            input_string = convert_chinese_to_english_symbols(input_string)
        except Exception as e:
            logger.error(f"Filtering failed: {e}")
    else:
        raise ValueError("input_string must be a string")
    input_string = re.sub(r'<think>.*?</think>', '', input_string, flags=re.DOTALL)
    input_string=input_string.replace("\n","")
    pattern = r'\{.*?function_name.*?args.*?\{.*?\}\}\}'
    matches = re.findall(pattern, input_string)
    if not matches:
        pattern = r'\{.*?function_name.*?args.*?\{.*?\}\}\}'
        matches = re.findall(pattern, input_string+'}')
    # 解析匹配的 JSON 对象
    results = []
    for match in matches:
        try:
            # 将字符串转换为 JSON 对象
            json_object = json.loads(match.replace("'", '"'))
            results.append(json_object)
        except json.JSONDecodeError as e:
            logger.info(f"Error JSON: {json_object}")
            logger.info(f"An error occurred when parsing JSON:{e}")
    return results
def correct_function_content(functions):
    """
    清理输入字符串，提取有效的 TronAction 内容。

    Args:
        input_string (str): 原始输入字符串。

    Returns:
        str: 修正的 TronAction 内容。
    """
    functions_new=[]
    for function_name, function_arguments in functions:
        function_arguments=json.loads(function_arguments)
        if function_arguments.get("action",None):
            action=function_arguments["action"]
            function_argument={action:{}}
            for k,v in function_arguments.items():
                if k!="action":
                    function_argument[action][k]=v
            function_arguments=function_argument
        function={"function_name": function_name, "args": function_arguments}
        functions_new.append(function)
    return functions_new
def remove_think_str(input_string):
    return re.sub(r'<think>.*?</think>', '', input_string, flags=re.DOTALL)
def load_prompt(prompt_path):
    with open(prompt_path, "r", encoding="utf-8") as file:
        prompt = file.read()
    return prompt.strip()


def read_json_file(file_path):
    """读取 JSON 文件并返回内容"""or bool(re.fullmatch(r"[A-Za-z\s.,!?\"'-]+", text))
    with open(file_path, 'r', encoding='utf-8') as file:
        try:
            data = json.load(file)
            return data
        except json.JSONDecodeError as e:
            print(f"An error occurred when parsing JSON: {e}")
            return None

def write_json_file(file_path, data):
    """将数据写入 JSON 文件"""
    with open(file_path, 'w', encoding='utf-8') as file:
        json.dump(data, file, ensure_ascii=False, indent=4)


def read_config(config_path):
    with open(config_path, "r",encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def is_segment(tokens):
    if tokens[-1] in (",", ".", "?", "，", "。", "？", "！", "!", ";", "；", ":", "："):
        return True
    else:
        return False

def is_interrupt(query: str,interrupt_prompt):
    try:
        if any(p==query.lower() for p in  interrupt_prompt):
                return True
        return False
    except:
        if any(p in query for p in  interrupt_prompt):
            return True
        return False
def is_valid(query):
    symbol_map = {
        '，': '',
        '。': '',
        '！': '',
        '？': '',
        '；': '',
        '：': '',
        '（': '',
        '）': '',
        '【': '',
        '】': '',
        '“': '',
        '”': '',
        '‘': "",
        '’': "",
        " ": "",
        "`": "",
        "*": "",
        ".":"",
        "'": "",
    }
    query=query.lower()
    for k,v in symbol_map.items():
        query=query.replace(k,v)
    if (not query.strip()) or (len(query) < 2 and query in  ['。','.', ',', '!', '?', '@', '#', '$', '%', '^', '&', '*', '(', ')', '-', '_', '=', '+', '[', ']', '{', '}', '|', '\\', ':', ';', '"', "'", '<', '>', '/', '~', '`'])\
    or query in ["okey","ok","yeah","好","oh","okay"]:
        return False
    return True
def extract_json_from_string(input_string):
    """提取字符串中的 JSON 部分"""
    pattern = r'(\{.*\})'
    match = re.search(pattern, input_string)
    if match:
        return match.group(1)  # 返回提取的 JSON 字符串
    return None

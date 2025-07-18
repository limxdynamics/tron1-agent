import re
import random
import spacy
import copy 
from .keywords import base_action_keywords,identity_keywords,what_keywords,undo_keywords,action_keywords,find_color
keywords={}
keywords.update(base_action_keywords)
keywords.update(identity_keywords)
keywords.update(what_keywords)
keywords.update(undo_keywords)
keywords.update(action_keywords)
# 加载中文模型
nlp_zh = spacy.load("zh_core_web_trf")
# 加载中文模型
nlp_en = spacy.load("en_core_web_trf")
# 定义中文数字映射
CN_NUM = {
    '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
    '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
    '十': 10, '百': 100, '千': 1000, '万': 10000,
    '亿': 100000000
}

# 定义英文数字映射
EN_NUM = {
    'zero': 0, 'one': 1, 'two': 2, 'three': 3, 'four': 4,
    'five': 5, 'six': 6, 'seven': 7, 'eight': 8, 'nine': 9,
    'ten': 10, 'eleven': 11, 'twelve': 12, 'thirteen': 13,
    'fourteen': 14, 'fifteen': 15, 'sixteen': 16, 'seventeen': 17,
    'eighteen': 18, 'nineteen': 19, 'twenty': 20, 'thirty': 30,
    'forty': 40, 'fifty': 50, 'sixty': 60, 'seventy': 70,
    'eighty': 80, 'ninety': 90
}

def chinese_to_arabic(cn_num_str):
    def single_to_arabic(cn_num_unit):
        num = 0
        for i in range(len(cn_num_unit)):
            if cn_num_unit[i] in CN_NUM:
                num += CN_NUM[cn_num_unit[i]]
        return num

    def double_to_arabic(cn_num_unit):
        num = 0
        if cn_num_unit[0] == '十':
            num += 10
        else:
            num += CN_NUM[cn_num_unit[0]] * 10
        if len(cn_num_unit) == 2:
            num += CN_NUM[cn_num_unit[1]]
        return num

    def multi_to_arabic(cn_num_str):
        num = 0
        if '万' in cn_num_str:
            if cn_num_str[0] == '万':
                num += 10000
            else:
                num += CN_NUM[cn_num_str[0]] * 10000
            cn_num_str = cn_num_str[cn_num_str.index('万') + 1:]
        if '千' in cn_num_str:
            if cn_num_str[0] == '千':
                num += 1000
            else:
                num += CN_NUM[cn_num_str[0]] * 1000
            cn_num_str = cn_num_str[cn_num_str.index('千') + 1:]
        if '百' in cn_num_str:
            if cn_num_str[0] == '百':
                num += 100
            else:
                num += CN_NUM[cn_num_str[0]] * 100
            cn_num_str = cn_num_str[cn_num_str.index('百') + 1:]
        if '十' in cn_num_str:
            if cn_num_str[0] == '十':
                num += 10
            else:
                num += CN_NUM[cn_num_str[0]] * 10
            cn_num_str = cn_num_str[cn_num_str.index('十') + 1:]
        if len(cn_num_str) > 0:
            num += CN_NUM[cn_num_str]
        return num

    if len(cn_num_str) == 1:
        return single_to_arabic(cn_num_str)
    elif len(cn_num_str) == 2:
        return double_to_arabic(cn_num_str)
    else:
        return multi_to_arabic(cn_num_str)

def english_to_arabic(en_num_str):
    def single_to_arabic(en_num_unit):
        return EN_NUM[en_num_unit]

    def double_to_arabic(en_num_unit):
        num = 0
        if en_num_unit in EN_NUM:
            num += EN_NUM[en_num_unit]
        else:
            num += EN_NUM[en_num_unit[:len(en_num_unit)-2]] + EN_NUM[en_num_unit[-2:]]
        return num

    def multi_to_arabic(en_num_str):
        num = 0
        if 'hundred' in en_num_str:
            num += EN_NUM[en_num_str[:en_num_str.index('hundred')]] * 100
            en_num_str = en_num_str[en_num_str.index('hundred') + 7:]
        if 'thousand' in en_num_str:
            num += EN_NUM[en_num_str[:en_num_str.index('thousand')]] * 1000
            en_num_str = en_num_str[en_num_str.index('thousand') + 8:]
        if 'million' in en_num_str:
            num += EN_NUM[en_num_str[:en_num_str.index('million')]] * 1000000
            en_num_str = en_num_str[en_num_str.index('million') + 7:]
        if 'billion' in en_num_str:
            num += EN_NUM[en_num_str[:en_num_str.index('billion')]] * 1000000000
            en_num_str = en_num_str[en_num_str.index('billion') + 7:]
        if len(en_num_str) > 0:
            num += double_to_arabic(en_num_str)
        return num

    if len(en_num_str) <= 2:
        return single_to_arabic(en_num_str)
    elif len(en_num_str) <= 10:
        return double_to_arabic(en_num_str)
    else:
        return multi_to_arabic(en_num_str)

def replace_numbers(sentence):
    # 使用正则表达式匹配中文和英文数字
    pattern = re.compile(r'(?:[一二两三四五六七八九十百千万亿零]+)|\b(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion)(?:-(?:zero|one|two|three|four|five|six|seven|eight|nine|ten|eleven|twelve|thirteen|fourteen|fifteen|sixteen|seventeen|eighteen|nineteen|twenty|thirty|forty|fifty|sixty|seventy|eighty|ninety|hundred|thousand|million|billion))*\b', re.IGNORECASE)
    def replace_match(match):
        num_str = match.group(0)
        if num_str.isalpha():
            return str(chinese_to_arabic(num_str))
        else:
            num_str=num_str.split('-')
            return str(sum([english_to_arabic(num.lower()) for num in num_str]))

    try:
        return pattern.sub(replace_match, sentence)
    except:
        return sentence

def extract_location(text,language="zh"):
    if language=="zh":
        doc = nlp_zh(text)
        locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
        return locations
    if language=="en":
        doc = nlp_en(text)
        locations = [ent.text for ent in doc.ents if ent.label_ == "GPE"]
        return locations
def contains_all_phrases(sentence, phrases,thres=0.7):
    """
    判断句子中是否包含所有指定的词组，词组的匹配顺序不固定。

    :param sentence: 要检查的句子
    :param phrases: 要匹配的词组列表
    :return: 如果句子中包含所有词组，返回 True；否则返回 False
    """
    # 对每个词组进行正则匹配
    total_=len(phrases)
    match=0
    for phrase in phrases:
        if re.search(re.escape(phrase), sentence):
            match+=1
    if match/total_>=thres:
        return True
    return False

def preprocess_asr_result(asr_result, language="zh",):
    """
    提前处理 ASR 识别结果，根据关键词直接解析参数内容，包括复合指令和上下文内容。
    
    Args:
        asr_result (str): ASR 识别结果文本。
        language (str): 语言类型，默认为中文 ("zh")。
    
    Returns:
        list or str: 如果匹配关键词，返回解析后的参数内容列表；如果匹配上下文关键词，返回上下文内容；否则返回 None。
    """
    # 初始化结果列表
    actions = []
    # 按顺序扫描输入字符串
    remaining_text = asr_result.lower()
    remaining_text = replace_numbers(remaining_text)  # 转换中文数字和符号为英文数字和符号
    tmp=""
    while remaining_text:
        for keyword, _action in keywords.items():
            matched = False
            if remaining_text.startswith(keyword):
                # 匹配到关键词，添加动作
                matched = True
                start_ind=len(keyword)
                _action_new=copy.deepcopy(_action)
                for a in _action_new:
                    action=[a]
                    if isinstance(a,str):
                        actions.extend(action)
                        continue
                    # 检查是否包含步数信息
                    step_match = re.search(r"(\d+)步|(\d+) steps|(\d+) step|(\d+)圈|(\d+) circles|(\d+) circle|(\d+) centermiters|(\d+) centermiter|(\d+) 厘米", tmp+remaining_text)
                    if step_match and ("twist" in action[0]["args"] or "height" in action[0]["args"]):
                        step_str = step_match.group(1) or step_match.group(2) or step_match.group(3) or step_match.group(4) or step_match.group(5) or step_match.group(6) or step_match.group(7) or step_match.group(8)or step_match.group(9)
                        start_index, end_index = step_match.span()  # 获取匹配文本的起始和结束索引
                        step_str = re.sub(r'[^\w]', '', step_str)  # 移除非字母数字字符
                        if step_str.isdigit():
                            step = int(step_str)  # 如果是数字，直接转换为整数
                        else:
                            step = random.randint(3, 8)  # 默认步数为1
                        if "height" in action[0]["args"]:
                            action[0]["args"]["direction"]*=step//5
                        elif action[0]["args"]["twist"]["z"]!=0:
                            if any(i in tmp for i in ["left","左"]):
                                action[0]["args"]["twist"]["z"]*=-1
                            if step!=1:
                                for _ in range(step-1):
                                    action.insert(0,action[0])
                        else:
                            action[0]["args"]["twist"]["step"] *= step
                        start_ind=end_index+len(tmp)
                    elif "city" in action[0]["args"]:
                        city=extract_location(remaining_text.lower())
                        action[0]["args"]["city"]=city if city!=[] else None
                    elif "light" in action[0]["args"]:
                        color=find_color(remaining_text+tmp)
                        action[0]["args"]['light']["effect"]=color
                    actions.extend(action)
                tmp=""
                remaining_text = remaining_text[start_ind:].strip() 
        if not remaining_text:
            continue
        if not matched:
            tmp+=remaining_text[0]
            # 如果没有匹配到关键词，移除第一个字符继续扫描
            remaining_text = remaining_text[1:].strip()

    # 如果没有匹配到关键词，返回 None
    if actions:
        return None,actions  
    else:
        None,None

from html import unescape
from transformers import pipeline, AutoModelWithLMHead, AutoTokenizer, AutoModelForSeq2SeqLM
import os
from bailing.utils.utils import detect_language
import translators as ts
class Translators:
    def __init__(self, config):
        self.translator = config.get("translator","alibaba")
        self.from_language = {
            "zh":"en",
            "en":"zh"
        }
     # 定义一个函数，将文本分割为多个部分，以适应翻译服务的长度限制
    def split_text_into_chunks(self,text, max_length):
        lines = text.splitlines()
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line
        if current_chunk:
            chunks.append(current_chunk)
        return chunks

    def translate(self,text,lang):
        if lang=="en" and detect_language(text)=="en":
            return text
        elif lang=="zh" and detect_language(text)=="zh":
            return text
        trans_text = ""
        for line in self.split_text_into_chunks(text, 1000):
            translated_line = ts.translate_text(line, self.translator,self.from_language[lang], to_language=lang)
            trans_text += unescape(translated_line)  # 解码 HTML 实体
        return trans_text

class HelsinkiTranslator:
    def __init__(self, config):
        self.weights_file = config.get("model_dir","../models/translation/Helsinki-NLP")
        self.sub_dir_en = f"opus-mt-zh-en"
        self.sub_dir_zh = f"opus-mt-en-zh"
        self.model_name_en = os.path.join(self.weights_file, self.sub_dir_en)
        model_en = AutoModelWithLMHead.from_pretrained(self.model_name_en,local_files_only=True)    
        tokenizer_en = AutoTokenizer.from_pretrained(self.model_name_en,local_files_only=True)
        self.translation_en = pipeline("translation", model=model_en, tokenizer=tokenizer_en)
        self.model_name_zh = os.path.join(self.weights_file, self.sub_dir_zh)
        model_zh = AutoModelWithLMHead.from_pretrained(self.model_name_zh,local_files_only=True)    
        tokenizer_zh = AutoTokenizer.from_pretrained(self.model_name_zh,local_files_only=True)
        self.translation_zh = pipeline("translation", model=model_zh, tokenizer=tokenizer_zh)
        self.lang_model={
            "en":self.model_name_zh,
            "zh":self.translation_zh
        }
    def split_text_into_chunks(self,text, max_length):
        lines = text.splitlines()
        chunks = []
        current_chunk = ""
        for line in lines:
            if len(current_chunk) + len(line) + 1 > max_length:
                chunks.append(current_chunk)
                current_chunk = line
            else:
                if current_chunk:
                    current_chunk += "\n" + line
                else:
                    current_chunk = line
        if current_chunk:
            chunks.append(current_chunk)
        return chunks
    def translate(self,text,lang):
        if lang=="en" and detect_language(text)=="en":
            return text
        elif lang=="zh" and detect_language(text)=="zh":
            return text
        else:
            trans_text = ""
            try:
                for line in text.split("\n"):
                    translated_line = self.lang_model[lang](line, max_length=500)[0]['translation_text']
                    trans_text += translated_line
                return trans_text
            except:
                return text


def create_instance(class_name, *args, **kwargs):
    # 获取类对象
    cls = globals().get(class_name)
    if cls:
        # 创建并返回实例
        return cls(*args, **kwargs)
    else:
        raise ValueError(f"Class {class_name} not found")

if __name__=="__main__":
    # 要翻译的文本
    translated_text = "抱歉,我没听请,可以再说一遍吗"
    config={
        "translator":"alibaba",
        "from_language":"Chinese",
        "to_language":"English",
        "model_dir":"../weights/translation/Helsinki-NLP"
    }
    # translator = Translators(config)
    # trans_text=translator.translate(translated_text)
    # print(trans_text)
    translator = HelsinkiTranslator(config)
    trans_text=translator.translate(translated_text)
    print(trans_text)
from bailing import tts
from bailing.utils import read_config
from flask import Blueprint,request,jsonify,send_file
import os

tts_model=None
_config = read_config("api/config.yaml")

tronagent = Blueprint('visa', __name__)



@tronagent.route('/InitTTS',methods=['POST','GET'])
def InitTTS():
    try:
        config=request.form
        global tts_model
        tts_model=None
        tts_model = tts.create_instance(
            config["selected_module"],
            _config["TTS"][config["selected_module"]]
        )
        return jsonify({"status": "Success", "message": ""})
    except Exception as e:
        return jsonify({"status": "Error", "message": str(e)})
    
@tronagent.route('/Get_TTS',methods=['POST','GET'])
def Get_TTS():
    try:
        data=request.form
        text=data["text"]
        lang=data["lang"]
        if tts_model is not None:
            # 调用 TTS 模型生成音频文件
            tmp_file = tts_model.to_tts(text, lang)
        else:
            return jsonify({"status": "Error", "message": "'MegaTTS' model do not init"})
        # 检查文件是否存在
        if not os.path.exists(tmp_file):
            return jsonify({"status": "Error", "message": "Audio file not found"})

        # 返回音频文件
        return send_file(tmp_file, mimetype="audio/wav", as_attachment=True, download_name=tmp_file)

    except Exception as e:
        # 如果发生错误，返回错误信息
        return jsonify({"status": "Error", "message": str(e)})
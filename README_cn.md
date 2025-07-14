# Tron1-Agent

<span>[ 中文 | <a href="README.md">English</a> ]</span>

用于Tron机器人的实时语音交互，支持聊天、和动作执行等。
## 功能特性

- **语音输入**：通过 FunASR 进行准确的语音识别。
- **语音活动检测**：使用 silero-vad 过滤无效音频，提升识别效率。
- **智能对话生成**：依靠 LLM 提供的强大语言理解能力生成自然的文本回复。
- **语音输出**：通过 edge-tts 等将文本转为语音，为用户提供逼真的听觉反馈。
- **支持打断**：灵活配置打断策略，能够识别关键字和语音打断，确保用户在对话中的即时反馈与控制，提高交互流畅度。
- **支持记忆功能**: 具备持续学习能力，能够记忆用户的偏好与历史对话，提供个性化的互动体验。
- **支持工具调用**: 灵活集成外部工具，用户可通过语音直接请求信息或执行操作，提升助手的实用性。***同时随时可拓展***
- **支持任务管理**: 高效管理用户任务，能够跟踪进度、设置提醒，并提供动态更新，确保用户不错过任何重要事项。
- **超轻量级应用**: 在Jeston Orin NX上可以轻松运行该代码。
## Roadmap

- [x] 基本语音对话功能
- [x] 支持Tron硬件通信
- [x] 支持Tron动作执行调用
- [x] 支持Tron批量动作执行和异常中止
- [x] 支持Agent中英两版输入和响应
- [x] Memory
- [x] 支持语音唤醒和休眠
- [x] 预设提示词模板
- [x] 离线操作
- [x] 多种工具调用
- [x] Rag & Agent
- [x] 打断

## 安装步骤

1. 克隆项目仓库

```bash
git clone 
cd Tron-Agent
```

2. 安装依赖
```bash
conda create -n tronagent
conda activate tronagent
pip install -r requirments.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
python -m spacy download zh_core_web_trf
python -m spacy download en_core_web_trf
pip install WeTextProcessing==1.0.3 #x86
```

3. llm本地部署
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama run modelscope.cn/unsloth/Qwen3-1.7B-GGUF
```

4. 下载相关模型
```bash
mkdir models && cd models
modelscope download --model IndexTeam/IndexTTS-1.5 --local_dir tts/indextts
modelscope download --model iic/SenseVoiceSmall --local_dir SenseVoiceSmall
modelscope download --model BAAI/bge-small-zh --local_dir rag/bge-small-zh
modelscope download --model BAAI/bge-small-en --local_dir rag/bge-small-en
modelscope download --model iic/speech_fsmn_vad_zh-cn-16k-common-pytorch --local_dir fsmn_vad
git lfs install
mkdir -p translation/Helsinki-NLP && cd translation/Helsinki-NLP
git clone https://huggingface.co/Helsinki-NLP/opus-mt-zh-en
git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-zh
cd ../.. && mkdir -p tts/piper && cd tts/piper
#相关模型地址 https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
```

5. arm架构依赖
```bash
cd tools/pynini/openfst-1.8.2
make clean
./configure --enable-grm --enable-static --enable-shared  && make -j$(nproc) && make install && sudo ldconfig 
cd tools/pynini/pynini-2.1.5.post2
python setup.py install
pip install WeTextProcessing==1.0.3 --no-deps
# jetpack6 and cuda12.6
wget https://pypi.jetson-ai-lab.dev/jp6/cu126/+f/027/bb91e7bccb0b9/torch-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=027bb91e7bccb0b92e0d10771b6a6b0e1efcbca0a312c35fe0b4ac1916f30eb0
wget https://pypi.jetson-ai-lab.dev/jp6/cu126/+f/c00/101424798389f/torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=c00101424798389fffa7a3959bf2c564cb92a593e940af0e29bc0bfabd3c562d
wget https://pypi.jetson-ai-lab.dev/jp6/cu126/+f/120/67a637fa6d05e/torchvision-0.23.0-cp310-cp310-linux_aarch64.whl#sha256=12067a637fa6d05e5d21e9d1814aaa718c02f8d5aa252d6616277541093d77f2
pip install torch-2.8.0-cp310-cp310-linux_aarch64.whl
pip install torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl
pip install torchvision-0.23.0-cp310-cp310-linux_aarch64.whl
```

6. 运行项目
```bash
python main.py
```

7. 开机自启
```bash
sudo cp tools/auto_start/tronagent.service /etc/systemd/system/tronagent.servce
sudo systemctl enable tronagent.service
sudo systemctl daemon-reload
```
***相关配置在```config/```下***,可自行修改

# Acknowledgements

本项目的代码开发基于<a href="https://github.com/wwbin2017/bailing/tree/main/bailing">百聆（Bailing）</a>框架实现，在此特别感谢百聆团队提供的技术支持与开源基础。同时，也向为本 Agent 开发提供助力的其他模型及相关贡献者致以诚挚谢意。

# References

<a href="https://github.com/wwbin2017/bailing/tree/main/bailing">百聆</a>

<a href="https://github.com/rhasspy/piper/blob/master/src/python_run">Piper TTS</a>

<a href="https://github.com/modelscope/FunASR">FunASR</a>

<a href="https://huggingface.co/Helsinki-NLP">Helsinki-NLP</a>

<a href="https://www.modelscope.cn/models/unsloth/Qwen3-1.7B-GGUF">Qwen</a>

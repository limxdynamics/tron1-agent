# Tron1-Agent

<span>[ English | <a href="README.md">Chinese</a> ]</span>

Real-time voice interaction for Tron robots, supporting chat, action execution, etc.
## Functional Features

- ** Voice input ** : Accurate voice recognition through FunASR.
- ** Speech Activity Detection ** : Use silero-vad to filter out invalid audio to enhance recognition efficiency.
- ** Intelligent Dialogue Generation ** : Rely on the powerful language understanding capabilities provided by LLMS to generate natural text responses.
- ** Voice output ** : Convert text to voice through edge-tts and other means to provide users with realistic auditory feedback.
- ** Support for interruption ** : Flexibly configure interruption strategies, capable of identifying keyword and voice interruptions, ensuring immediate feedback and control from users during conversations, and enhancing interaction smoothness.
- ** Supports memory function **: It has the ability to continuously learn, can remember users' preferences and historical conversations, and provide personalized interactive experiences.
- ** Support for Tool Invocation **: Flexibly integrate external tools, allowing users to directly request information or perform operations through voice commands, enhancing the practicality of the assistant. It can be expanded at any time
- ** Support for task Management **: Efficiently manage user tasks, capable of tracking progress, setting reminders, and providing dynamic updates to ensure that users do not miss any important matters.
- ** Ultra-lightweight application **: This code can be easily run on Jeston Orin NX.

## Roadmap

- [x] Basic voice dialogue function
- [x] Supports Tron hardware communication
- [x] supports Tron action execution calls
- [x] Supports batch action execution and exception termination on Tron
- [x] Supports both Chinese and English versions of Agent input and response
- [x] Memory
- [x] supports voice wake-up and sleep
- [x] Preset prompt word template
- [x] Offline operation
- [x] Multiple tool calls
- [x] Rag & Agent
- [x] interrupted

## Installation Steps

1. Cloning Project Repository
```bash
git clone 
cd Tron-Agent
```

2. Installation dependencies
```bash
conda create -n tronagent
conda activate tronagent
pip install -r requirments.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
pip install tools/scipy/en_core_web_trf-3.8.0-py3-none-any.whl
pip install tools/scipy/zh_core_web_trf-3.8.0-py3-none-any.whl
pip install WeTextProcessing==1.0.3 #x86
```

3. Local deployment of llm
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama run modelscope.cn/unsloth/Qwen3-1.7B-GGUF
```

4. Download the relevant model
```bash
cd models
modelscope download --model IndexTeam/IndexTTS-1.5 --local_dir tts/indextts
modelscope download --model iic/SenseVoiceSmall --local_dr SenseVoiceSmall
modelscope download --model BAAI/bge-small-zh --local_dir rag/bge-small-zh
modelscope download --model BAAI/bge-small-en --local_dir rag/bge-small-en
modelscope download --model iic/speech_fsmn_vad_zh-cn-16k-common-pytorch --local_dir fsmn_vad
git lfs install
mkdir translation/Helsinki-NLP & cd translation/Helsinki-NLP
git clone https://huggingface.co/Helsinki-NLP/opus-mt-zh-en
git clone https://huggingface.co/Helsinki-NLP/opus-mt-en-zh
cd .. & mkdir tts/piper & cd tts/piper
#Relevant model https://huggingface.co/rhasspy/piper-voices/tree/v1.0.0
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/en/en_US/amy/medium/en_US-amy-medium.onnx.json
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx
wget https://huggingface.co/rhasspy/piper-voices/blob/v1.0.0/zh/zh_CN/huayan/medium/zh_CN-huayan-medium.onnx.json
```

5. Reliance on arm architecture
```bash
cd tools/pynini/openfst-1.8.2
make clean
./configure --enable-grm --enable-static --enable-shared  && make -j$(nproc) && make install && sudo ldconfig 
cd tools/pynini/pynini-2.1.5.post2
python setup.py install
pip install WeTextProcessing==1.0.3 --no-deps
python -m spacy download zh_core_web_trf
python -m spacy download en_core_web_trf
# jetpack6 and cuda12.6
wget https://pypi.jetson-ai-lab.dev/jp6/cu126/+f/027/bb91e7bccb0b9/torch-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=027bb91e7bccb0b92e0d10771b6a6b0e1efcbca0a312c35fe0b4ac1916f30eb0
wget https://pypi.jetson-ai-lab.dev/jp6/cu126/+f/c00/101424798389f/torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl#sha256=c00101424798389fffa7a3959bf2c564cb92a593e940af0e29bc0bfabd3c562d
wget https://pypi.jetson-ai-lab.dev/jp6/cu126/+f/120/67a637fa6d05e/torchvision-0.23.0-cp310-cp310-linux_aarch64.whl#sha256=12067a637fa6d05e5d21e9d1814aaa718c02f8d5aa252d6616277541093d77f2
pip install torch-2.8.0-cp310-cp310-linux_aarch64.whl
pip install torchaudio-2.8.0-cp310-cp310-linux_aarch64.whl
pip install torchvision-0.23.0-cp310-cp310-linux_aarch64.whl
```

6. Run the project
```bash
python main.py
```

7. Auto-start upon startup
```bash
sudo cp tools/auto_start/tronagent.service /etc/systemd/system/tronagent.servce
sudo systemctl enable tronagent.service
sudo systemctl daemon-reload
```
***The relevant configuration is under ```config/```***, and can be modified by yourself.

# Acknowledgements

The development of this project's code is based on the <a href="https://gi, it is highly cost-effectivethub.com/wwbin2017/bailing/tree/main/bailing">Bailing</a> framework. We would like to express our special gratitude to the Bailing team for their technical support and open-source foundation. Additionally, sincere thanks go to other models and relevant contributors that have provided assistance in the development of this Agent.

# References

<a href="https://github.com/wwbin2017/bailing/tree/main/bailing">百聆</a>

<a href="https://github.com/rhasspy/piper/blob/master/src/python_run">Piper TTS</a>

<a href="https://github.com/modelscope/FunASR">FunASR</a>

<a href="https://huggingface.co/Helsinki-NLP">Helsinki-NLP</a>

<a href="https://www.modelscope.cn/models/unsloth/Qwen3-1.7B-GGUF">Qwen</a>

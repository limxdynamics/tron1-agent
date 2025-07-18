#!/bin/bash

export LIBRARY_PATH=/usr/local/lib:/usr/local/lib
export LD_LIBRARY_PATH=/usr/lib:/usr/local/lib:/usr/local/cuda/lib64
export CUDA_HOME=/usr/local/cuda
export PATH=/usr/local/bin:/usr/bin:/usr/local/cuda/bin:/usr/sbin

ollama run modelscope.cn/unsloth/Qwen3-1.7B-GGUF:latest &

sleep 3

/bin/bash /home/guest/tron/tron1-agent/tools/iflytek/iflytek.sh

sleep 3

/usr/bin/python /home/guest/tron/tron1-agent/main.py >> /home/guest/tron/tron1-agent/log.txt
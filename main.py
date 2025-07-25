import argparse
import json
import logging
import requests
import os
import shutil
tmp_dir="tmp/"
# 获取根 logger
logger = logging.getLogger(__name__)
try:
    if os.path.exists(tmp_dir):
        shutil.rmtree(tmp_dir)
    os.makedirs(tmp_dir)
except Exception as e:
    logger.error(f"操作过程中出现错误: {e}")
os.makedirs(tmp_dir, exist_ok=True)
#配置日志记录
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),  # 控制台输出
        logging.FileHandler('tmp/bailing.log')  # 文件输出
    ]
)
from bailing import robot


def push2web(payload):
    try:
        data = json.dumps(payload, ensure_ascii=False)
        url = "http://127.0.0.1:50001/add_message"
        headers = {
          'Content-Type': 'application/json; charset=utf-8'
        }
        response = requests.request("POST", url, headers=headers, data=data.encode('utf-8'))
        logger.info(response.text)
    except Exception as e:
        logger.error(f"callback error：{payload}{e}")

def main():
    # Create the parser
    parser = argparse.ArgumentParser(description="Description of your script.")

    # Add arguments
    parser.add_argument('config_path', type=str, help="配置文件", default=None)
    # Parse arguments
    args = parser.parse_args()
    config_path = args.config_path
    bailing_robot = robot.Robot(config_path)
    bailing_robot.listen_dialogue(push2web)
    bailing_robot.run()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Description of your script.")

    # Add arguments
    parser.add_argument('--config_path', type=str, help="配置文件", default="config/config.yaml")

    # Parse arguments
    args = parser.parse_args()
    config_path = args.config_path

    # 创建 Robot 实例并运行
    robot = robot.Robot(config_path)
    robot.listen_dialogue(push2web)
    robot.run()

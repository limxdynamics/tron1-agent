from unittest import result
import websocket
import threading
import json
import uuid
from datetime import datetime, timezone
import logging
from typing import List
import time
from schema import Memory,Message
# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)



class BaseWebSocket:
    """
    基础 WebSocket 类，提供 WebSocket 客户端的基本功能。
    """

    def __init__(self, robot_ip,memory: Memory = None):
        """
        初始化 BaseWebSocket 实例，并启动 WebSocket 客户端线程。
        """
        self.robot_ip = robot_ip
        logger.info(f"Initializing WebSocket client with robot_ip: {self.robot_ip}")
        # 初始化 WebSocket 客户端
        self.client = websocket.WebSocketApp(
            f'ws://{self.robot_ip}:5000',  # 确保地址正确
            on_open=self.on_open,
            on_message=self.on_message,
            on_close=self.on_close
        )
        self.status = "UNKNOW"
        self.message = {}
        self.received_notify_robot_info = False
        self.accid = ""
        self.memory = Memory() if memory is None else memory
        self.current_request = None  # 保存当前请求
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 8
        logger.info("WebSocket client initialized.")
        self.run_thread=threading.Thread(target=self.client.run_forever, daemon=True).start()
        self.running = True  # 用于控制监听线程的运行状态
        # 启动监听线程
        self.monitor=threading.Thread(target=self._monitor_connection, daemon=True).start()

        # 等待 notify_robot_info 消息
        if self.wait_for_notify_robot_info():
            logger.info("The WebSocket client thread has been started.")
        else:
            logger.error("The initialization of the WebSocket client failed and the notify_robot_info message was not received")
            raise RuntimeError("The initialization of the WebSocket client failed and the notify_robot_info message was not received")

    def generate_guid(self):
        """
        生成唯一标识符 (UUID)。

        Returns:
            str: UUID 字符串。
        """
        return str(uuid.uuid4())

    def send_request(self, title, data=None):
        """
        发送 WebSocket 请求。

        Args:
            title (str): 请求的标题。
            data (dict, optional): 请求的附加数据。默认为 None。
        """
        if data is None:
            data = {}
        # 获取当前时间的 UTC 时间戳（毫秒级）
        timestamp = datetime.now(timezone.utc).timestamp() * 1000
        # 构造 WebSocket 消息
        guid=self.generate_guid()
        if not self.accid:
            logger.error("ERROR: accid is None")
            self.message["message"] += "***ERROR: accid is None***"
            return

        # 序列化消息为 JSON 格式并发送
        message = {
            "accid": self.accid,                           # Robot's serial number
            "title": title,                           # Request type
            "timestamp": timestamp,    # Timestamp in milliseconds
            "guid": guid,                  # Unique identifier for this message
            "data": data,                              # Additional data payload
        }
        self.current_request = message  # 保存当前请求
        try:
            message_str = json.dumps(message)

            logger.info(f"WebSocket-TRON Robot message: {message_str}")
            self.client.send(message_str)
            message["message"] = "***success***"
            logger.info("Message sent successfully")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
            message["message"] = f"***Error when executing command /{title}/: {e}***"
        finally:
            # 处理消息并更新内存
            message["status"]=self.status
            self.update_memory(message=message)

    def on_open(self, ws):
        """
        WebSocket 连接打开时的回调。
        """
        logger.info("WebSocket connection established.")

    def on_message(self, ws, message):
        """
        接收到 WebSocket 消息时的回调。

        Args:
            message (str): 从服务器接收到的消息。
        """
        if not self.client.sock or not self.client.sock.connected:
            logger.warning("WebSocket is disconnected.")
            return True
        logger.info(f"WebSocket-TRON Robot received message: {message}")
        try:
            root = json.loads(message)
            title = root.get("title", "")
            root["message"]="callback"
            if title.startswith("response"):
                logger.info(f"WebSocket-TRON Robot received message: {title}")

            if title == "notify_robot_info":
                data = root.get("data", {})
                self.status = data.get("status", "UNKNOW")
                self.accid = root.get("accid", self.accid)  # 更新 accid
                self.received_notify_robot_info = True  # 标记为已接收到
            root["status"] = self.status
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            root={"message": f"Failed to decode message: {e}"}
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            root={"message": f"Error processing message: {e}"}
        finally:
            self.update_memory(message=root)

    def on_close(self, ws, close_status_code, close_msg):
        """
        WebSocket 连接关闭时的回调。

        Args:
            close_status_code (int): WebSocket 关闭状态码。
            close_msg (str): WebSocket 关闭消息。
        """
        logger.info(f"WebSocket connection closed. Code: {close_status_code}, Message: {close_msg}")

    def close_connection(self):
        """
        优雅关闭 WebSocket 连接。
        """
        self.running = False  # 停止监听线程
        # 等待线程结束（如果需要）
        if self.monitor and self.monitor.is_alive():
            self.monitor.join(timeout=2.0)
            if self.monitor.is_alive():
                logger.warning("WebSocket-monitor thread is still alive after shutdown.")
            else:
                logger.info("WebSocket thread stopped successfully.")
        if self.client:
            try:
                self.client.close()
                logger.info("WebSocket connection closed.")
            except Exception as e:
                logger.error(f"Error closing WebSocket: {e}")
        
        # 等待线程结束（如果需要）
        if self.run_thread and self.run_thread.is_alive():
            self.run_thread.join(timeout=2.0)
            if self.run_thread.is_alive():
                logger.warning("WebSocket thread is still alive after shutdown.")
            else:
                logger.info("WebSocket thread stopped successfully.")
        logger.info("WebSocket connection closed gracefully.")

    def wait_for_notify_robot_info(self, timeout=5):
        """
        等待服务器发送 notify_robot_info 消息。

        Args:
            timeout (int): 超时时间（秒）。

        Returns:
            bool: 如果接收到 notify_robot_info 消息则返回 True，否则返回 False。
        """
        start_time = time.time()
        while not self.received_notify_robot_info:
            if time.time() - start_time > timeout:
                logger.error("Timeout waiting for notify_robot_info.")
                return False
            time.sleep(0.1)
        logger.info("Successfully received notify_robot_info.")
        return True
    
    def _monitor_connection(self):
        """
        持续监听 WebSocket 的连接状态，并在挂断时尝试重新连接。
        """
        while self.running:
            if self.is_disconnected():
                logger.warning("WebSocket disconnected. Attempting to reconnect...")
                self.reconnect()
            time.sleep(5)  # 每隔 5 秒检查一次连接状态
    def is_disconnected(self):
        """
        检查 WebSocket 是否挂断。

        Returns:
            bool: 如果 WebSocket 挂断则返回 True，否则返回 False。
        """
        try:
            # 检查 WebSocket 的连接状态
            if not self.client.sock or not self.client.sock.connected:
                logger.warning("WebSocket is disconnected.")
                return True
            return False
        except Exception as e:
            logger.error(f"Error checking WebSocket connection: {e}")
            return True

    def reconnect(self):
        """
        尝试重新连接 WebSocket。
        """
        try:
            self.reconnect_attempts += 1
            if self.reconnect_attempts > self.max_reconnect_attempts:
                logger.error(f"Reconnect failed after {self.max_reconnect_attempts} attempts. Stopping.")
                self.running = False
                return
            if self.running:
                logger.info("Attempting to reconnect WebSocket...")
                self.client = websocket.WebSocketApp(
                    f'ws://{self.robot_ip}:5000',
                    on_open=self.on_open,
                    on_message=self.on_message,
                    on_close=self.on_close
                )
                threading.Thread(target=self.client.run_forever, daemon=True).start()
                logger.info("WebSocket reconnected successfully.")
                if self.current_request:
                    logger.info("Resending the last request after reconnecting.")
                    self.send_request(self.current_request["title"], self.current_request["data"])
        except Exception as e:
            logger.error(f"Failed to reconnect WebSocket: {e}")

    def update_memory(
        self,
        message:dict,
    ) -> None:
        """Add a message to the agent's memory.

        Args:
            role: The role of the message sender (user, system, assistant, tool).
            content: The message content.
            **kwargs: Additional arguments (e.g., tool_call_id for tool messages).

        Raises:
            ValueError: If the role is unsupported.
        """
        _message=self.process_message(message) # type: ignore
        msg = Message.register_message(**_message) # type: ignore
        self.memory.add_message(msg)

    def process_message(self, message) -> dict:
        """Process a message and add it to memory"""
        # Here you can add any processing logic for the messageself.running = False  # 停止监听线程
        status=message.get("status")
        accid=message.get("accid")
        timestamp=message.get("timestamp")
        guid=message.get("guid")
        _message=message.get("message")
        data=message.get("data")
        title=message.get("title")
        message={"status":status,"accid":accid,"request":title,"guid":guid,"timestamp":timestamp,"message":_message,"data":data}
        return message


    @property
    def messages(self) -> List[Message]:
        """Retrieve a list of messages from the agent's memory."""
        return self.memory.messages

    @messages.setter
    def messages(self, value: List[Message]):
        """Set the list of messages in the agent's memory."""
        self.memory.messages = value


if __name__ == "__main__":
    robot_ip = "127.0.0.1"  # 确保这是正确的 IP 地址
    ws_client = BaseWebSocket(robot_ip=robot_ip,memory=Memory())
    ws_client.send_request("request_stand_mode")

from flask.config import T
from .base_websocket import BaseWebSocket
import time
import logging
from register import BaseActionType
logger = logging.getLogger(__name__)


class TronWebsocket(BaseWebSocket):
    def __init__(self, robot_ip,memory=None):
        super().__init__(robot_ip=robot_ip,memory=memory)

    def request_stand_mode_with_timeout(self,timeout = 10 ):
        start_time = time.time()
        # self.send_request("request_recover")
        self.send_request("request_stand_mode")
        time.sleep(5)
        if self.status == BaseActionType.FALLOVER._value_:
            self.send_request("request_recover")
        while self.status != BaseActionType.STAND._value_ and self.status != BaseActionType.FALLOVER._value_:
            if time.time() - start_time > timeout:
                logger.info("Timeout: Failed to enter STAND mode.")
                return False  # Indicating failure
            time.sleep(1)
        return True  # Indicating success

    def request_walk_mode_with_timeout(self):
        start_time = time.time()
        timeout = 10  # 10 seconds timeout

        self.send_request("request_walk_mode")
        
        while self.status != BaseActionType.WALK._value_:
            if time.time() - start_time > timeout:
                logger.info("Timeout: Failed to enter WALK mode.")
                return False  # Indicating failure
            time.sleep(1)
        return True  # Indicating success

    def stand(self,timeout = 10):
        start_time = time.time()
        if any(self.status.startswith(status) for status in ["UNKNOW", "SIT", "ERROR", "DAMPING"]):
            if self.request_stand_mode_with_timeout():
                return self.request_walk_mode_with_timeout()
        elif self.status == BaseActionType.STAND._value_:
            return self.request_walk_mode_with_timeout()

    def sit(self):
        self.send_request("request_sitdown")
        start_time = time.time()
        timeout = 10  # 10 seconds timeout
        while not any(self.status.startswith(status) for status in ["UNKNOW", "SIT", "ERROR", "DAMPING"]):
            if time.time() - start_time > timeout:
                logger.info("Timeout: Failed to enter SIT mode.")
                return False  # Indicating failureshu
            time.sleep(1)
        return True

    def twist(self, x: float, y: float, theta: float):
        if self.status != BaseActionType.WALK._value_:
            self.stand()
        if self.status == BaseActionType.WALK._value_:
            self.send_request("request_twist", {"x": x, "y": y, "z": theta})
            logger.info("robot is moving")
            time.sleep(0.4)

    def height(self, direction):
        if self.status != BaseActionType.WALK._value_:
            self.stand()
        if self.status == BaseActionType.WALK._value_:
            self.send_request("request_base_height", {"direction": direction})
            logger.info("robot is adjusting the hight")
            time.sleep(0.2)
    def light(self, effect):
        self.send_request("request_light_effect", {"effect": effect})
        logger.info("robot changed the light effect")
        time.sleep(0.2)
        return True

if __name__=="__main__":
    robot_ip="127.0.0.1"
    ws_client = TronWebsocket(robot_ip=robot_ip)
    import time
    time.sleep(10)

    ws_client.stand()
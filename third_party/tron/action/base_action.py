import logging
from communication.tron_websocket import TronWebsocket
from .base import BaseAction, BaseBatchActions, RetryAction
from register import BaseActionType
from pydantic import Field,model_validator
import third_party.tron.app.pocket as pocket
from typing import List, Optional
logger = logging.getLogger(__name__)
import json
from pydantic import Field
import time
class CallSit(BaseAction):
    """
    请求机器人进入坐下模式。
    """
    def prep(self, shared_state):
        return self.flow_params
    
    def exec_core(self, prep_result):
        if "sit" in prep_result:
            self.client.sit()
            logger.info("The robot is sitting...")
            return True
  
        return False
class CallLLM(BaseAction):
    def prep(self, shared_state):
        return shared_state
    
    def exec_core(self, action_commands):

        return action_commands["action_commands"]
    
    def post(self, prep_result, exec_result, shared_state):
        # Check if exec_result contains a valid action
        exec_result=exec_result.split('\n')
        if not exec_result:
            shared_state["actions"] = [{"error": "Missing action in response"}]
            return pocket.DEFAULT_ACTION

        actions = []
        valid_actions = {"stand", "sit", "twist","height","light"}
        for action in exec_result:
            try:
                action = action.replace("'", '"')
                action = json.loads(action)  # Convert action from str to dict
                action_keys = list(action.keys())  # Extract the first key from the dict
                for action_key in action_keys:
                    if action_key in valid_actions:
                        actions.append(action)
                        logger.info(f"Valid action added: {action}")
                    else:
                        actions.append({"error": "Invalid action", "received": action})
            except Exception as e:
                actions.append({"error": "Processing error", "received": action, "details": str(e)})
        shared_state["actions"] = actions
        return pocket.DEFAULT_ACTION
    
class CallStand(BaseAction):
    """
    请求机器人进入站立模式。
    """
    def prep(self, shared_state):
        return self.flow_params
    
    def exec_core(self, prep_result):
        if "stand" in prep_result:
            self.client.stand()
            logger.info("The robot is standing...")
            return True
  
        return False

class CallTwist(RetryAction):
    """
    控制机器人在 3D 空间中的运动。
    """
    def prep(self, shared_state):
        if "twist" in self.flow_params:
            self.max_retries = int(self.flow_params["twist"].get('step', 1))
            self.interval_ms = 1000.0 / 30
        return self.flow_params

    def exec_core(self, prep_result):
        if "twist" in prep_result:
            params = prep_result["twist"]
            self.client.twist(params.get('x', 0.0), params.get('y', 0.0), params.get('z', 0.0))
            logger.info("The robot is moving...")
            time.sleep(1.0 / 30)
class CallHeight(RetryAction):
    """
    控制机器人在 3D 空间中的运动。
    """
    def prep(self, shared_state):
        return self.flow_params
    
    def exec_core(self, prep_result):
        if "height" in prep_result:
            params = prep_result["height"]
            self.client.height(params.get('direction', 1))
            logger.info("The robot is adjusting the height...")
            return True
  
        return False
class CallLight(RetryAction):
    """
    控制机器人在 3D 空间中的运动。
    """
    def prep(self, shared_state):
        return self.flow_params
    
    def exec_core(self, prep_result):
        if "light" in prep_result:
            params = prep_result["light"]
            self.client.light(params.get('effect', 1))
            logger.info("The robot is adjusting the light effect...")
            time.sleep(1.0 / 30)
class BatchActions(BaseAction):

    def post(self, prep_result, exec_result, shared_state):
        if "twist" in self.flow_params:
            return "twist"
        elif "stand" in self.flow_params:
            return "stand"
        elif "sit" in self.flow_params:
            return "sit"
        elif "height" in self.flow_params:
            return "height"
        elif "light" in self.flow_params:
            return "light"
        


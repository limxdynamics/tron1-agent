import sys
#sys.path.append("/home/limx/tron/Tron-Agent")
from plugins.registry import register_function, ToolType, Action, ActionResponse
import logging
logger = logging.getLogger(__name__)
import os
sys.path.append("third_party/tron")
import app.pocket as pocket
from action.base_action import CallSit, CallStand, CallTwist, BatchActions, CallLLM,CallHeight,CallLight
from communication.tron_websocket import TronWebsocket
from flow.base_action_flow import BatchFlow
from schema import Memory
# Configure pydantic to allow custom types
from pydantic import BaseModel, ConfigDict, Field

class TronConfig(BaseModel):
    ws_client: TronWebsocket
    model_config = ConfigDict(arbitrary_types_allowed=True)
ws_client: TronWebsocket = Field(..., description="The communication client")
memory = Memory()
flow = None
@register_function('init_client', ToolType.NONE)
def init_client(robot_ip):
    """
    Start Tron communication.
    """
    try:
        global ws_client
        ws_client = TronWebsocket(robot_ip=robot_ip,memory=memory)
        call_sit = CallSit(client=ws_client)
        call_stand = CallStand(client=ws_client)
        call_twist = CallTwist(client=ws_client)
        call_height = CallHeight(client=ws_client)
        call_light = CallLight(client=ws_client)
        llm_node = CallLLM(client=ws_client)
        batch_actions = BatchActions(client=ws_client)
        # Add actions to batch flow
        batch_actions.add_successor(call_sit, "sit")
        batch_actions.add_successor(call_stand, "stand")
        batch_actions.add_successor(call_twist, "twist")
        batch_actions.add_successor(call_height, "height")
        batch_actions.add_successor(call_light, "light")

        # Create batch flow
        batch_flow = BatchFlow(batch_actions)

        llm_node.add_successor(batch_flow)
        global flow
        flow = pocket.Flow(llm_node)
        logger.info("Tron communication started successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to start Tron communication: {e}")
        return False
@register_function('TronAction', ToolType.WAIT)
def TronAction(**action):
    """
    Invoke batch action flow.
    """
    try:
        logger.info(action)
        _=flow.run({"action_commands": str(action)})
        return ActionResponse(Action.NONE, None, "Execution completed")
    except Exception as e:
        logger.error(f"Failed to invoke action flow: {e}")
        return ActionResponse(Action.STOPFUNCTION, "There is an error in the program and it cannot be executed", "There is an error in the program and it cannot be executed")

@register_function('dump_action_memory', ToolType.NONE)
def dump_action_memory(path):
    """
    Save action memory to a file.
    """
    try:
        path = memory.dump_messages_to_jsonl(path)
        logger.info(f"Tron action memory saved to {path}")
        return True
    except Exception as e:
        return False
@register_function('close_client', ToolType.NONE)
def close_client(path):
    """
    Save action memory to a file.
    """
    try:
        path = memory.dump_messages_to_jsonl(path)
        ws_client.close_connection()
        logger.info(f"Tron action memory saved to {path}")
        return True
    except Exception as e:
        logger.error(f"Failed to close: {e}")
        return False
if __name__ == "__main__":
    robot_ip="10.0.30.110"
    init_client(robot_ip)
    import time
    time.sleep(5)
    config={'height': {'direction': -1}}
    TronAction(**config)
    #pass

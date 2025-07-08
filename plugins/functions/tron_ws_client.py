import sys
from plugins.registry import register_function, ToolType, ActionResponse, Action
import logging
sys.path.append("third_party/tron")
from communication.tron_websocket import TronWebsocket
logger = logging.getLogger(__name__)
ws_client=None
@register_function('tron_ws_client', ToolType.TIME_CONSUMING)
def tron_ws_client(robot_ip):
    """
    Start tron communication.
    """
    try:
        global ws_client 
        ws_client = TronWebsocket(robot_ip)
        return ActionResponse(Action.REQLLM, None, "The tron communication was successfully initiated")
    except Exception as e:
        logger.error(f"The tron communication failed to start: {e}")
        return ActionResponse(Action.RESPONSE, None,f"The tron communication failed to start:{e}")
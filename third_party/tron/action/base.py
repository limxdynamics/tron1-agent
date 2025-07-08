import third_party.tron.app.pocket as pocket
from communication.tron_websocket import TronWebsocket
from schema import Memory,Message
class BaseAction(pocket.BaseNode):
    """
    基础动作类，所有动作类都继承自该类。
    """
    def __init__(
        self, client: TronWebsocket
    ):
        super().__init__()
        self.client = client

class RetryAction(pocket.RetryNode):
    """
    基础动作类，所有动作类都继承自该类。
    """
    def __init__(
        self, client: TronWebsocket
    ):
        super().__init__()
        self.client = client

class BaseBatchActions(BaseAction):
    pass
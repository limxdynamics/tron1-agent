from .base import BatchFlow

class ActionBatchFlow(BatchFlow):
    def prep(self, shared_state):
        return shared_state["actions"]

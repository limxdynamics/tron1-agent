import copy
import time
import asyncio

DEFAULT_ACTION = "default"

class BaseNode(object):
    def __init__(self):
        self.flow_params = {}
        self.successors = {}

    def set_params(self, params):
        self.flow_params = params

    def add_successor(self, new_successor, action=DEFAULT_ACTION):
        if action in self.successors:
            raise ValueError(f"Action {action} already exists")
        self.successors[action] = new_successor

    def get_successor(self, name):
        if name not in self.successors:
            return None
        return self.successors[name]

    def prep(self, shared_state):
        pass

    def exec_wrapper(self, prep_result):
        return self.exec_core(prep_result)

    def exec_core(self, prep_result):
        pass

    def post(self, prep_result, exec_result, shared_state):
        pass

    def run(self, shared_state):
        prep_result = self.prep(shared_state)
        exec_result = self.exec_wrapper(prep_result)
        action = self.post(prep_result, exec_result, shared_state)
        return action

class RetryNode(BaseNode):
    def __init__(self, max_retries = 1, interval_ms = 0):
        super().__init__()
        self.max_retries = max_retries
        self.interval_ms = interval_ms

    def exec_wrapper(self, prep_result):
        exec_result = []
        for _ in range(self.max_retries):
            try:
                exec_result.append(self.exec_core(prep_result))
            except Exception:
                time.sleep(self.interval_ms / 1000)
      
        return exec_result

class Flow(BaseNode):
    def __init__(self, start):
        super().__init__()
        self.start = start

    def _clone(self):
        return Flow(self.start)

    def get_start_node(self):
        return self.start

    def exec_core(self, prep_result):
        raise NotImplementedError("Flow node does not support direct execution")

    def prep(self, shared_state):
        return {}

    def orchestrate(self, shared_state, flow_params=None):
        current_node = self.get_start_node()
        while current_node:
            current_node.set_params(flow_params or self.flow_params)
            action = current_node.run(shared_state)
            current_node = current_node.get_successor(action)

    def run(self, shared_state):
        prep_result = self.prep(shared_state)
        self.orchestrate(shared_state)
        return self.post(prep_result, None, shared_state)

    def post(self, prep_result, exec_result, shared_state):
        return DEFAULT_ACTION


class BatchFlow(Flow):
    def prep(self, shared_state):
        return []

    def run(self, shared_state):
        prep_result_list = self.prep(shared_state)

        result_list = []
        for prep_result in prep_result_list:
            result = self.orchestrate(shared_state, prep_result)
            result_list.append(result)

        return self.post(prep_result_list, result_list, shared_state)

    def post(self, prep_result_list, result_list, shared_state):
        return DEFAULT_ACTION


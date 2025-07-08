import third_party.tron.app.pocket as pocket

class BatchFlow(pocket.BatchFlow):
    def prep(self, shared_state):
        return shared_state["actions"]
    
class Flow(pocket.Flow):
    pass

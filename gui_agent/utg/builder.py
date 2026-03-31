# utg/builder.py
from .state import make_state_id_from_state

class UTGBuilder:
    def __init__(self, utg):
        self.utg = utg

    def update(self, prev_state, action_json, next_state, success=None, meta=None):
        s1 = make_state_id_from_state(prev_state)
        s2 = make_state_id_from_state(next_state)
        self.utg.add_node(s1, meta=meta or {})
        self.utg.add_node(s2, meta=meta or {})
        self.utg.add_edge(s1, action_json, s2, success=success)
        return s1, s2

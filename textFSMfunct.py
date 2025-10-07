# texFSM.py
class FSM:
    def __init__(self, initial_state):
        self.state = initial_state
        self.states = set()
        self.transitions = {}

    def add_state(self, state):
        self.states.add(state)

    def add_transition(self, from_state, input_val, to_state):
        if from_state not in self.transitions:
            self.transitions[from_state] = {}
        self.transitions[from_state][input_val] = to_state

    def input(self, value):
        if self.state in self.transitions and value in self.transitions[self.state]:
            self.state = self.transitions[self.state][value]
        else:
            print(f"⚠ No hay transición definida para {self.state} con entrada '{value}'")

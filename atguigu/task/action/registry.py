from atguigu.domain.action import Action


class ActionRegistry:
    def __init__(self):
        self._actions:dict[str,Action] = {}

    def register(self,action:Action):
        self._actions[action.name] = action

    def get(self,action_name:str):
        return self._actions.get(action_name)



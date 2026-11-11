from atguigu.domain.action import ActionResult, Action
from atguigu.domain.state import DialogueState
from atguigu.task.action.registry import ActionRegistry


class ActionRunner:

    def __init__(self,registry:ActionRegistry):
        self.registry = registry

    async def run(self,action_name,state:DialogueState)->ActionResult:

        action:Action = self.registry.get(action_name)

        return await action.run(state)

from typing import Any
from loguru import logger
from atguigu.domain.action import ActionResult
from atguigu.domain.flow_catalog import FlowCatalog, Flow, FlowStep, StartFlowStep, ResponseFlowStep, CollectSlotStep, \
    ActionFlowStep, EndFlowStep, StaticLink, ConditionLink, FallbackLink
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.task.action.action_runner import ActionRunner
from atguigu.task.response.response_renderer import ResponseRenderer


class FlowExecutor:

    def __init__(self,action_runner: ActionRunner,response_renderer:ResponseRenderer,max_count:int=100):
        self.response_renderer = response_renderer
        self.action_runner = action_runner
        self.max_count = max_count

    async def run_task(self, state:DialogueState, user_message:UserMessage, flow_catalog:FlowCatalog)->list[BotMessage]|None:

        bot_messages:list[BotMessage] = []

        for _ in range(self.max_count):
            active_task = state.task_state.active_task
            if active_task is None:
                return bot_messages

            flow: Flow = flow_catalog.get_flow(active_task.flow_id)
            step: FlowStep = flow.get_step(active_task.step_id)

            logger.info("流程推进器，目前正在处理：{},目前处理步骤：{}", flow.name, step.id)

            if isinstance(step, StartFlowStep):
                # 5.1 开始步骤只是任务开始标识，不处理业务，只需要将流程推进到下一个步骤即可
                self._advance(step, state)
                # 5.2 循环继续
                continue

                # 4.处理步骤类型："response": ResponseFlowStep
            if isinstance(step, ResponseFlowStep):
                bot_message:BotMessage = await self.response_renderer.respond(step.template,state,user_message)
                bot_messages.append(bot_message)
                self._advance(step,state)
                continue

                # 5.处理步骤类型："collect": CollectSlotStep
            if isinstance(step, CollectSlotStep):
                should_wait:bool = await self._run_collect(step, state, user_message, bot_messages)
                if should_wait:
                    return bot_messages
                else:
                    self._advance(step, state)
                    continue

                # 6.处理步骤类型："action": ActionFlowStep
            if isinstance(step, ActionFlowStep):
                action_result:ActionResult = await self.action_runner.run(step.action, state)

                state.task_state.set_slots(action_result.slot_updates)
                if action_result.messages:
                    bot_messages.extend(action_result.messages)
                self._advance(step, state)
                continue

                # 7.处理步骤类型："end": EndFlowStep,
            if isinstance(step, EndFlowStep):
                state.task_state.active_task = None
                return bot_messages

        logger.warning("流程推进超过最大步数 {}，已强制中断当前任务", self.max_count)
        state.task_state.active_task = None
        return bot_messages

    def _advance(self,step:FlowStep,state:DialogueState):
        for link in step.next:
            if isinstance(link,StaticLink):
                state.task_state.active_task.step_id = link.target
                return
            if isinstance(link,ConditionLink) and self.condition_validate(link.condition,{"slots":state.task_state.active_task.slots}):
                state.task_state.active_task.step_id = link.target
                return
            if isinstance(link,FallbackLink):
                state.task_state.active_task.step_id = link.target
                return

    def condition_validate(self,condition:str,data:dict[str,Any])->bool:
        return bool(eval(condition,{"__builtins__":{}},data))

    async def _run_collect(self,step:CollectSlotStep,state:DialogueState,user_message:UserMessage,bot_messages:list[BotMessage])->bool:
        slot_value = state.task_state.active_task.slots.get(step.slot_name)
        if slot_value is None:
            self._try_fill_slot_from_focused_object(step,state)

        slot_value = state.task_state.active_task.slots.get(step.slot_name)

        if slot_value is None:
            bot_message = await self.response_renderer.respond(step.template, state, user_message)
            bot_messages.append(bot_message)
            return True

        if not step.validation:
            return False
        else:
            result = self.condition_validate(step.validation.condition,{"slots":state.task_state.active_task.slots})

            if result:
                return False
            else:
                state.task_state.active_task.slots.pop(step.slot_name)
                bot_message:BotMessage = await self.response_renderer.respond(step.validation.failure_template, state, user_message)
                bot_messages.append(bot_message)
                return True

    def _try_fill_slot_from_focused_object(self,step:CollectSlotStep,state:DialogueState):
        focused_object = state.shared_state.focused_object
        if focused_object is None:
            return

        if step.slot_name == 'order_number' and focused_object.type == 'order':
            state.task_state.set_slots({step.slot_name: focused_object.id})

        if step.slot_name == 'book_id' and focused_object.type == 'book':
            state.task_state.set_slots({step.slot_name: focused_object.id})
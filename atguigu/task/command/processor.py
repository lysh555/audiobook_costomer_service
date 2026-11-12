from loguru import logger

from atguigu.domain.command import Command, StartFlowCommand, SetSlotsCommand, CancelTaskCommand, ResumeTaskCommand
from atguigu.domain.flow_catalog import FlowCatalog, Flow, FlowStep
from atguigu.domain.state import DialogueState, TaskInstance
from atguigu.domain.task_event import TaskEvent


class CommandProcessor:
    def __init__(self):
        pass

    def run(self,commands:list[Command],state:DialogueState,flow_catalog:FlowCatalog)->list[TaskEvent]:
        events:list[TaskEvent] = []
        for command in commands:
            event:TaskEvent = self._apply(command, state, flow_catalog)
            logger.info("命令处理器,已处理命令:{},得到任务事件{}",command,event)
            if event:
                events.append(event)
        return events

    def _apply(self, command: Command, state: DialogueState, flow_catalog: FlowCatalog) -> TaskEvent | None:
        if isinstance(command, StartFlowCommand):
            flow:Flow = flow_catalog.get_flow(command.flow)
            start_step: FlowStep = flow.get_start_step()

            task = TaskInstance(
                flow_id=flow.id,
                step_id=start_step.id
            )
            task_event:TaskEvent = state.task_state.start(task)
            return task_event

        if isinstance(command,SetSlotsCommand):
            if state.task_state.active_task:
                state.task_state.set_slots(command.slots)
            else:
                logger.warning("槽位填充失败，当前没有活动任务，已忽略槽位：{}", command.slots)

            return None

        if isinstance(command,CancelTaskCommand):
            task_event:TaskEvent = state.task_state.cancel(command.task_id)
            return task_event

        if isinstance(command, ResumeTaskCommand):
            task_event:TaskEvent = state.task_state.resume(command.task_id)
            return task_event
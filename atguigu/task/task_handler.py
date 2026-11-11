from atguigu.domain.command import Command
from atguigu.domain.flow_catalog import FlowCatalog
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.state import DialogueState
from atguigu.domain.task_event import TaskEvent
from atguigu.task.command.processor import CommandProcessor
from atguigu.task.flow.flow_executor import FlowExecutor
from atguigu.task.lifecycle.responder import TaskLifecycleResponder


class TaskHandler:
    def __init__(self, command_processor:CommandProcessor, task_lifecycle_responder:TaskLifecycleResponder, flow_executor:FlowExecutor, flow_catalog:FlowCatalog):
        self.command_processor = command_processor
        self.task_lifecycle_responder = task_lifecycle_responder
        self.flow_executor = flow_executor
        self.flow_catalog = flow_catalog

    async def handle(self, commands:list[Command], state:DialogueState, user_message:UserMessage)->list[BotMessage]:
        """任务型对话处理器"""
        all_bot_messages:list[BotMessage] = []
        #1.调用命令处理器CommandProcessor，将命令应用对话状态，产生任务事件列表
        task_events:list[TaskEvent] = self.command_processor.run(commands=commands,state=state,flow_catalog=self.flow_catalog)
        #2.调用任务生命周期响应器TaskLifecycleResponder将任务事件列表转为（客服回复）任务变更相关提示->list[BotMessage]
        task_tips_bot_messages:list[BotMessage] = self.task_lifecycle_responder.respond(task_events=task_events)
        all_bot_messages.extend(task_tips_bot_messages)
        #3.调用流程推进器flow_executor推进流程产生客服回复->list[BotMessage] 将二者产出回复合并后返回
        bot_messages:list[BotMessage] = await self.flow_executor.run_task(state=state, user_message=user_message,flow_catalog=self.flow_catalog)
        all_bot_messages.extend(bot_messages)
        return all_bot_messages
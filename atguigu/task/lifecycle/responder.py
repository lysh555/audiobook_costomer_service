from loguru import logger

from atguigu.domain.flow_catalog import FlowCatalog, Flow
from atguigu.domain.messages import BotMessage
from atguigu.domain.task_event import TaskEvent, TaskSwitched, TaskStarted, TaskResumed, TaskCanceled


class TaskLifecycleResponder:

    def __init__(self, flow_catalog: FlowCatalog):
        """注入系统支持流程清单"""
        self.flow_catalog = flow_catalog

    def respond(self, task_events: list[TaskEvent]) -> list[BotMessage]:
        """
            将命令处理器CommandProcessor参数任务事件列表，转为客服回复列表
        :param task_events: 任务时间列表
        :return:  客服回复消息列表
        """
        messages: list[BotMessage] = []
        for task_event in task_events:
            bot_message: BotMessage = self._message_for(task_event)
            messages.append(bot_message)
        return messages

    def _message_for(self, task_event: TaskEvent) -> BotMessage:
        """将单个任务事件对象转为客服任务提示回复"""
        # 1.处理任务事件类型：TaskStarted
        if isinstance(task_event, TaskStarted):
            # 获取任务时间中 任务引用对象中流程ID查询流程名称
            flow_name: str = self._flow_name(task_event.task.flow_id)
            return BotMessage(text=f"好的，接下来为您处理{flow_name}")
        # 2.处理任务事件类型：TaskSwitched
        if isinstance(task_event, TaskSwitched):
            previous_flow_name = self._flow_name(task_event.previous.flow_id)
            current_flow_name = self._flow_name(task_event.current.flow_id)
            return BotMessage(text=f"好的，先暂停处理{previous_flow_name}，接下来为您处理{current_flow_name}")
        # 3.处理任务事件类型：TaskResumed
        if isinstance(task_event, TaskResumed):
            flow_name: str = self._flow_name(task_event.task.flow_id)
            return BotMessage(text=f"好的，继续为您处理{flow_name}")
        # 4.处理任务事件类型：TaskCanceled
        if isinstance(task_event, TaskCanceled):
            flow_name: str = self._flow_name(task_event.task.flow_id)
            return BotMessage(text=f"好的，已为您取消了{flow_name}，有任何需要可以随时沟通")
        logger.error("任务状态响应器：{}不存在", task_event)
        raise ValueError(f"任务状态事件不支持：{task_event}")

    def _flow_name(self, flow_id: str) -> str:
        """根据流程ID查询流程名称"""
        flow: Flow = self.flow_catalog.get_flow(flow_id)
        return flow.name or flow.id
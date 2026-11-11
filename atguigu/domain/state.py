import time
import uuid
from typing import Any
from dataclasses import dataclass,field

from loguru import logger

from atguigu.domain.messages import UserMessage,BotMessage
from atguigu.domain.task_event import TaskEvent, TaskStarted, TaskRef, TaskSwitched, TaskCanceled, TaskResumed

@dataclass
class Turn:
    turn_id:str
    user_message:UserMessage
    bot_messages:list[BotMessage] = field(default_factory=list)

@dataclass
class Session:
    session_id:str
    started_at:float
    last_activity_at:float
    closed_at:float|None=None
    turns:list[Turn] = field(default_factory=list)

@dataclass
class FocusedObject:
    type:str
    id:str
    title:str|None=None
    attributes:dict[str,Any] = field(default_factory=dict)

@dataclass
class SharedState:
    focused_object:FocusedObject | None = None
    sessions:list[Session] = field(default_factory=list)

    def current_session(self)->Session|None:
        if self.sessions:
            return self.sessions[-1]
        return None

    def start_session(self):

        now = time.time
        session = Session(
            session_id=str(uuid.uuid4()),
            started_at=now(),
            last_activity_at=now()
        )
        self.sessions.append(session)

    def close_current_session(self):
        session = self.current_session()
        session.closed_at = time.time()


@dataclass
class TaskInstance:
    """基于yaml流程产生任务实例 比如退款任务，查询订单任务等"""
    flow_id: str  # 流程ID
    step_id: str  # 当前流程执行到步骤ID
    slots: dict[str, Any] = field(default_factory=dict)  # 任务执行已收到槽位以及值
    task_id: str = field(default_factory=lambda: str(uuid.uuid4()))  # 任务实例ID 取值uuid

    def to_ref(self) -> TaskRef:
        return TaskRef(flow_id=self.flow_id, task_id=self.task_id)

@dataclass
class TaskState:
    active_task:TaskInstance|None = None
    paused: list[TaskInstance] = field(default_factory=list)

    def start(self, task: TaskInstance) -> TaskEvent:
        if self.active_task is None:
            self.active_task = task
            return TaskStarted(task=task.to_ref())
        else:
            previous = self.active_task
            self.paused.append(previous)
            self.active_task = task
            return TaskSwitched(previous=previous.to_ref(), current=task.to_ref())

    def set_slots(self,slots:dict[str,Any]):
        self.active_task.slots.update(slots)

    def cancel(self,task_id:str)->TaskEvent|None:
        if self.active_task and self.active_task.task_id == task_id:
            cancel = self.active_task
            self.active_task = None
            return TaskCanceled(task=cancel.to_ref())

        for paused_task in self.paused:
            if paused_task.task_id == task_id:
                self.paused.remove(paused_task)
                return TaskCanceled(task=paused_task.to_ref())

        logger.warning("任务取消失败，未找到任务ID：{}", task_id)
        return None

    def resume(self,task_id:str)->TaskEvent|None:
        resume:TaskInstance|None = None
        for paused_task in self.paused:
            if paused_task.task_id == task_id:
                resume = paused_task
                break

        if resume is None:
            logger.warning("任务恢复失败，未找到任务ID：{}", task_id)
            return None

        self.paused.remove(resume)

        if self.active_task:
            previous = self.active_task
            self.paused.append(self.active_task)
            self.active_task = resume
            return TaskSwitched(previous=previous.to_ref(), current=resume.to_ref())
        else:
            # 3.如果没有活跃任务，产生任务恢复事件
            self.active_task = resume
            return TaskResumed(task=resume.to_ref())




@dataclass
class DialogueState:
    sender_id:str
    shared_state:SharedState = field(default_factory=SharedState)
    task_state:TaskState = field(default_factory=TaskState)

    def reset_runtime_for_new_session(self):
        self.shared_state.focused_object=None
        self.task_state.active_task=None
        self.task_state.paused.clear()
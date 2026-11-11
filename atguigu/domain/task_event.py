from dataclasses import dataclass
from typing import TypeAlias

from langchain_protocol import TasksEvent


#  任务事件产生任务提示信息：
# 启动任务提示1， 好的，我们先处理{退款申请}
# 任务切换提示2， 好的，我们把{退款申请}放一放、先帮您处理{订单状态查询}
# 任务取消提示3：好的，{退款申请}已帮你取消了
# 任务恢复提示4：好的，继续为您办理{退款申请}

@dataclass
class TaskRef:
    flow_id:str
    task_id:str

@dataclass
class TaskStarted:
    task:TaskRef

@dataclass
class TaskSwitched:
    previous:TaskRef
    current:TaskRef

@dataclass
class TaskResumed:
    task:TaskRef

@dataclass
class TaskCanceled:
    task:TaskRef

TaskEvent:TypeAlias = TaskStarted | TaskSwitched | TaskResumed | TaskCanceled
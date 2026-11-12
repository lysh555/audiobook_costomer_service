from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from atguigu.domain.command import Command


@dataclass
class ChitchatTurnPlan:
    pass

@dataclass
class KnowledgeTurnPlan:
    """知识检索方法"""
    intents:list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls,data:dict[str,Any])->"KnowledgeTurnPlan":
        return cls(**data)

@dataclass
class TaskTurnPlan:
    """任务处理方向"""
    commands:list[Command] = field(default_factory=list)

    @classmethod
    def from_dict(cls,data:dict[str,Any])->"TaskTurnPlan":
        return cls(commands=[Command.from_dict(command_dict) for command_dict in data.get("commands")])

@dataclass
class TurnPlan:
    task:TaskTurnPlan|None = None
    knowledge:KnowledgeTurnPlan|None = None
    chitchat:ChitchatTurnPlan|None = None

    @classmethod
    def from_dict(cls, data:dict[str,Any])->"TurnPlan":
        return cls(
            task=TaskTurnPlan.from_dict(data.get("task")) if data.get("task") is not None else None,
            knowledge=KnowledgeTurnPlan.from_dict(data.get("knowledge")) if data.get("knowledge") is not None else None,
            chitchat=ChitchatTurnPlan() if data.get("chitchat") is not None else None
        )


class ClarifyReason(str,Enum):
    """校验失败原因枚举"""
    MISSING_TRACK = "missing_track"  # 没有任何方向
    MULTIPLE_TRACKS = "multiple_tracks"  # 存在多个方向
    MISSING_TASK_COMMANDS = "missing_task_commands"  # 确定是任务方向，但是commands指令为空
    MISSING_ACTIVE_TASK = "missing_active_task"  # 确定是任务方向，但是填充槽位时既没有活动任务也没有启动流程
    MULTIPLE_START_COMMANDS = "multiple_start_commands"  # 确定是任务方向，但是commands中存在多个启动任务命令
    MULTIPLE_RESUME_COMMANDS = "multiple_resume_commands"  # 确定是任务方向，但是commands中存在多个恢复任务命令
    MISSING_KNOWLEDGE_INTENT = "missing_knowledge_intent"  # 确定是知识检索方向 但intents意图列表为空
    MISSING_FOCUSED_OBJECT = "missing_focused_object"  # 确定是知识检索方向，意图存在,意图要求焦点对象book ,order 为空
    OBJECT_REQUIRES_INTENT = "object_requires_intent"  # 如果消息类型是卡片，但是无法为任务处理填充槽位
    INVALID_TASK_COMMAND = "invalid_task_command"  # 确定是任务方向，但是commands中指令是系统不识别
    UNKNOWN_KNOWLEDGE_INTENT = "unknown_knowledge_intent"  # 确定是知识检索方向，意图是系统不支持的


@dataclass
class TurnPlanValidationResult:
    """轮次校验结果"""
    valid:bool
    reason:ClarifyReason|None = None
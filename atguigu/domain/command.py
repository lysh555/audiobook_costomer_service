from dataclasses import dataclass, field
from typing import Any

@dataclass
class Command:
    command:str
    @classmethod
    def from_dict(cls,data:dict[str,Any])->"Command":
        clz=COMMAND_NAME_TO_CLASS.get(data["command"])
        return clz(**data)

@dataclass
class StartFlowCommand(Command):
    flow: str

@dataclass
class SetSlotsCommand(Command):
    slots:dict[str,Any] = field(default_factory=dict)

@dataclass
class CancelTaskCommand(Command):
    task_id: str

@dataclass
class ResumeTaskCommand(Command):
    task_id: str

COMMAND_NAME_TO_CLASS:dict[str,type[Command]]={
    "start_flow": StartFlowCommand,
    "set_slots": SetSlotsCommand,
    "cancel_task": CancelTaskCommand,
    "resume_task": ResumeTaskCommand,
}
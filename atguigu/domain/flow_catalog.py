from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ResponseMode(Enum):
    STATIC = "static"  # 渲染后直接返回
    REPHRASE = "rephrase"  # 先渲染调用llm进行润色


@dataclass
class ResponseTemplate:
    """用于获取客服回复文本"""
    mode: ResponseMode = ResponseMode.STATIC  # 渲染模型默认值STATIC
    text: str| None  = ""  # 待渲染回复文本
    prompt: str | None = ""  # 提示词

    @classmethod
    def from_dict(cls,data:dict[str,Any])-> "ResponseTemplate":
        return cls(
            mode = ResponseMode(data.get("mode",ResponseMode.STATIC)),
            text = data.get("text", ""),
            prompt = data.get("prompt", "")
        )


@dataclass
class SlotValidation:
    """用于收集槽位步骤校验收集到槽位信息"""
    condition: str | None = None  # 用于校验表达式
    failure_template: ResponseTemplate | None = None  # 校验槽位失败后，响应回复模板


@dataclass
class FlowStepLink:
    """节点跳转next连接线"""
    target: str = ""

    @classmethod
    def build_links(cls,next_data:str|list[dict])->list["FlowStepLink"]:
        if isinstance(next_data,str):
            return [StaticLink(target=next_data)]
        else:
            links:list[FlowStepLink] = []
            for link_dict in next_data:
                if "if" in link_dict:
                    links.append(ConditionLink(condition=link_dict.get("if"), target=link_dict["then"]))
                else:
                    links.append(FallbackLink(target=link_dict.get("else")))
            return links



@dataclass
class StaticLink(FlowStepLink):
    """固定跳转连接线 例如：next: ask_order_number"""
    pass


@dataclass
class ConditionLink(FlowStepLink):
    """带条件连接线
          - if: "slots.get('book_id')" if值是跳转条件
            then: respond  #满足if条件后跳转步骤ID
          - if: "slots.get('book_id')"
            then: respond
    """
    condition: str = ""


@dataclass
class FallbackLink(FlowStepLink):
    """最后的兜底跳转连接线
      - if: "slots.get('book_id')"
        then: respond
      - else: missing_book_context 前面条件跳转条件没有满足则跳转该步骤ID
    """
    pass


class FlowStepType(Enum):
    """步骤/节点类型"""
    START = "start"
    ACTION = "action"
    RESPONSE = "response"
    COLLECT = "collect"
    END = "end"


@dataclass
class FlowStep:
    """流程内固定步骤父类，包含五种步骤类型公共属性"""
    id: str  # 步骤ID
    type: FlowStepType  # 步骤类型 五种步骤类型
    next: list[FlowStepLink] = field(default_factory=list)  # 连接线 决定下一个步骤

    @classmethod
    def from_dict(cls,step_data:dict[str,Any])->"FlowStep":
        clzz = STEP_TYPE_TO_CLASS.get(step_data.get("type"))
        return clzz.from_dict(step_data)

    @classmethod
    def base_fields(cls, step_data:dict[str,Any])-> dict[str,Any]:
        return {
            "id": step_data.get("id"),
            "type": step_data.get("type"),
            "next": FlowStepLink.build_links(step_data.get("next"))
        }

@dataclass
class StartFlowStep(FlowStep):
    """开始步骤"""
    @classmethod
    def from_dict(cls,step_data:dict[str,Any]) ->"StartFlowStep":
        base_field_dict:dict = FlowStep.base_fields(step_data)

        return cls(**base_field_dict)


@dataclass
class ActionFlowStep(FlowStep):
    """执行听书商城后端接口调用步骤"""
    action: str = ""

    @classmethod
    def from_dict(cls,step_data:dict[str,Any]) ->"ActionFlowStep":
        return cls(
            **FlowStep.base_fields(step_data)
            , action=step_data.get("action")
        )


@dataclass
class CollectSlotStep(FlowStep):
    slot_name: str = ""
    template: ResponseTemplate = field(default_factory=ResponseTemplate)  # 要求用户提供信息回复
    validation: SlotValidation | None = None  # 收集到槽位是否校验可选

    @classmethod
    def from_dict(cls,step_data:dict[str,Any]) ->"CollectSlotStep":
        return cls(
            **FlowStep.base_fields(step_data)
            , slot_name=step_data.get("slot_name")
            , template=ResponseTemplate.from_dict(step_data.get("template"))
            , validation=SlotValidation(
                condition=step_data.get("validation").get("condition"),
                failure_template=ResponseTemplate.from_dict(step_data.get("validation").get("failure_template"))
            ) if "validation" in step_data else None
        )

@dataclass
class ResponseFlowStep(FlowStep):
    template: ResponseTemplate = field(default_factory=ResponseTemplate)

    @classmethod
    def from_dict(cls,step_data:dict[str,Any]) ->"ResponseFlowStep":
        return cls(
            **FlowStep.base_fields(step_data)
            , template=ResponseTemplate.from_dict(step_data.get("template"))
        )


@dataclass
class EndFlowStep(FlowStep):
    """结束步骤"""

    @classmethod
    def from_dict(cls,step_data:dict[str,Any]) ->"EndFlowStep":
        return cls(**FlowStep.base_fields(step_data))

STEP_TYPE_TO_CLASS = {
    "start": StartFlowStep,
    "action": ActionFlowStep,
    "collect": CollectSlotStep,
    "response": ResponseFlowStep,
    "end": EndFlowStep,
    }


@dataclass
class FlowSlot:
    """槽位信息"""
    name: str = ""
    type: str = "any"
    label: str = ""
    description: str = ""


@dataclass
class Flow:
    """流程定义"""
    id: str #流程ID
    description: str = "" #流程描述
    steps: list[FlowStep] = field(default_factory=list) # 包含步骤列表
    slots: list[FlowSlot] = field(default_factory=list) # 包含槽位列表
    name: str | None = None # 流程名称

    def get_start_step(self)->StartFlowStep|None:
        for step in self.steps:
            if isinstance(step,StartFlowStep):
                return step
        return None

    def get_step(self,step_id:str)->FlowStep|None:
        for step in self.steps:
            if step.id == step_id:
                return step
        return None


@dataclass
class FlowCatalog:
    """流程定义清单 提供：根据流程ID查询流程信息；根据步骤ID获取当前步骤用于推进流程"""
    flows:dict[str, Flow] = field(default_factory=dict)   # 保存所有流程 字典Key=流程ID Value=流程对象
    slots:dict[str, FlowSlot] = field(default_factory=dict) # 保存所有槽位 字段key=槽位名称 Value=槽位对象

    def get_flow(self,flow_id:str)->Flow:
        return self.flows.get(flow_id)
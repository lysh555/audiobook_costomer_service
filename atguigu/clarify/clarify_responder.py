import json
from dataclasses import asdict

from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import PromptTemplate

from atguigu.clients.llm_client import llm
from atguigu.domain.messages import UserMessage, BotMessage
from atguigu.domain.plan import ClarifyReason
from atguigu.domain.state import DialogueState
from atguigu.prompts.history_builder import HistoryBuilder
from atguigu.prompts.prompt_loader import load_prompt


class ClarifyResponder:

    async def respond(self,reason:ClarifyReason,state:DialogueState,user_message:UserMessage)->list[BotMessage]:

        clarify_message = self._build_clarify_message(reason,state)

        prompt = PromptTemplate(template=load_prompt("clarify_respond"),template_format="jinja2")
        chain = prompt | llm | StrOutputParser()
        text = await chain.ainvoke({
            "reason":reason.value,
            "clarify_message":clarify_message,
            "focused_object":json.dumps(asdict(state.shared_state.focused_object),ensure_ascii=False) if state.shared_state.focused_object else None,
            "history":HistoryBuilder.build(state.shared_state.current_session().turns),
            "user_message":HistoryBuilder.render_user_message(user_message)
        })
        return [BotMessage(text=text)]

    def _build_clarify_message(self, reason: ClarifyReason, state: DialogueState) -> str:
        """生成基础回复文本"""
        if reason is ClarifyReason.MISSING_TRACK:
            return "你是想先处理业务问题，还是先咨询信息呢？"
        if reason is ClarifyReason.MULTIPLE_TRACKS:
            return (
                "你这次同时提到了多个方向。我们先处理一个，"
                "你想先办业务还是先咨询信息呢？"
            )
        if reason is ClarifyReason.MISSING_TASK_COMMANDS:
            return (
                "你这次是想办理什么业务呢？"
                "比如查订单、了解听书详情，或者申请退款。"
            )
        if reason is ClarifyReason.MISSING_KNOWLEDGE_INTENT:
            return (
                "你是想了解听书信息、订单信息，"
                "还是VIP会员权益呢？"
            )
        if reason is ClarifyReason.MISSING_FOCUSED_OBJECT:
            return "请先发送你想咨询的对象（订单或听书），我再继续帮你看。"
        if reason is ClarifyReason.OBJECT_REQUIRES_INTENT:
            focused_object = state.shared_state.focused_object
            if (
                    focused_object is not None
                    and focused_object.type == "order"
            ):
                return (
                    "我已经收到这个订单了。你想查订单状态，"
                    "还是申请退款呢？"
                )
            if (
                    focused_object is not None
                    and focused_object.type == "book"
            ):
                return (
                    "我已经收到这本听书了。你想了解它的详情、"
                    "章节信息，还是相关权益呢？"
                )
        if reason is ClarifyReason.INVALID_TASK_COMMAND:
            return (
                "当前任务状态不支持这个操作，"
                "请告诉我你想开始、继续还是取消哪个任务。"
            )
        if reason is ClarifyReason.UNKNOWN_KNOWLEDGE_INTENT:
            return (
                "我暂时无法识别这个咨询方向，"
                "你可以具体说说想了解的听书、订单或会员权益问题。"
            )
        return (
            "我还需要再确认一下你的意思，"
            "你可以换个更具体的说法告诉我。"
        )
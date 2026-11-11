import json
from abc import ABC, abstractmethod
from typing import Any
from loguru import logger
from atguigu.clients import http_client
from atguigu.conf.config import settings
from atguigu.domain.knowledge import KnowledgeChunk
from atguigu.domain.messages import UserMessage
from atguigu.domain.state import DialogueState


class KnowledgeProvider(ABC):
    provider_id: str

    @abstractmethod
    async def retrieve(self, state: DialogueState, user_message: UserMessage, intent_ids: list[str]) -> list[KnowledgeChunk]:
        pass


class BookAPIProvider(KnowledgeProvider):
    provider_id = "api.book"

    async def retrieve(self, state: DialogueState, user_message: UserMessage, intent_ids: list[str]) -> list[KnowledgeChunk]:
        book_id = state.shared_state.focused_object.id
        if book_id:
            url = f"{settings.audiobook_api_base_url}/books/{book_id}"
            try:
                response = await http_client.http_client.get(url)
            except Exception as error:
                logger.error("听书知识接口调用失败：{}", error)
                return []
            if response.status_code != 200:
                return []
            try:
                data = response.json().get("data") or {}
            except ValueError:
                return []
            if not data:
                return []
            text = json.dumps(data, ensure_ascii=False, indent=2)
            return [KnowledgeChunk(content="听书信息:\n" + text)]
        return []


class OrderAPIProvider(KnowledgeProvider):
    provider_id = "api.order"

    async def retrieve(self, state: DialogueState, user_message: UserMessage, intent_ids: list[str]) -> list[KnowledgeChunk]:
        order_number = state.shared_state.focused_object.id
        if order_number:
            order_payload = await self._fetch_order_info(order_number)
            if not order_payload:
                return []
            content = json.dumps(
                {
                    "order_number": order_number,
                    "order": order_payload,
                }, ensure_ascii=False, indent=2
            )
            return [KnowledgeChunk(content="订单信息:\n" + content)]
        return []

    async def _fetch_order_info(self, order_number) -> dict[str, Any]:
        url = f"{settings.audiobook_api_base_url}/orders/{order_number}"
        try:
            response = await http_client.http_client.get(url)
        except Exception as error:
            logger.error("订单知识接口调用失败：{}", error)
            return {}
        if response.status_code != 200:
            return {}
        try:
            return response.json().get("data") or {}
        except ValueError:
            return {}


class FAQProvider(KnowledgeProvider):
    """常见问题知识库：按知识意图返回对应的业务规则说明"""
    provider_id = "faq.default"

    FAQ_CONTENTS: dict[str, str] = {
        "refund_policy": (
            "退款政策：待支付订单可以直接取消；已完成订单在购买后7天内且未开始收听时，"
            "可以提交退款申请，申请时需要提供订单号和退款原因；审核通过后款项原路退回，"
            "已退款订单不能重复申请。"
        ),
        "vip_policy": (
            "VIP会员权益：会员期内可无限畅听全站听书，并享受高清音质；"
            "会员剩余收听时长可在“我的-VIP”页面查看；用优惠码兑换的会员时长会自动叠加到现有会员期上。"
        ),
        "listening_policy": (
            "收听规则：购买听书或开通VIP后即可收听全集；如果出现无法播放，"
            "请先检查网络，再尝试切换音质或重新进入听书详情页；收听进度会自动同步到账号，可跨设备续听。"
        ),
        "platform_rule": (
            "平台规则：听书内容仅限个人收听，请勿下载传播或用于商业用途；"
            "账号仅限本人使用，不要与他人共享；如发现异常登录，请及时修改密码并联系客服。"
        ),
        "general_audiobook_info": (
            "听书商城目前提供科幻、历史、文学、小说、商业等分类的有声书，支持在线收听与VIP畅听；"
            "你可以发送听书卡片，或告诉我书名、作者、分类，我来帮你查询具体信息。"
        ),
    }

    async def retrieve(self, state: DialogueState, user_message: UserMessage, intent_ids: list[str]) -> list[KnowledgeChunk]:
        chunks: list[KnowledgeChunk] = []
        for intent_id in intent_ids:
            content = self.FAQ_CONTENTS.get(intent_id)
            if content:
                chunks.append(KnowledgeChunk(content=content))
        return chunks


class RAGProvider(KnowledgeProvider):
    """向量检索知识库：当前版本尚未接入正式检索服务，检索不到内容时返回空列表"""
    provider_id = "rag.default"

    async def retrieve(self, state: DialogueState, user_message: UserMessage, intent_ids: list[str]) -> list[KnowledgeChunk]:
        return []


def build_default_providers() -> list[KnowledgeProvider]:
    return [BookAPIProvider(), OrderAPIProvider(), FAQProvider(), RAGProvider()]
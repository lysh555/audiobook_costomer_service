from dataclasses import dataclass, field


@dataclass
class KnowledgeChunk:
    """信息检索后得到相关内容片段"""
    content: str

@dataclass
class KnowledgeIntent:
    id: str
    description: str
    provider_ids:list = field(default_factory=list)
    requires_object:str|None = None

# 意图跟 provider_ids提供者映射
KNOWLEDGE_INTENTS: dict[str, KnowledgeIntent] = {
    "book_info": KnowledgeIntent(
        id="book_info",
        description="指定听书（需要用户先发送听书卡片/对象）的详情咨询",
        provider_ids=["api.book"],
        requires_object="book",
    ),
    "order_info": KnowledgeIntent(
        id="order_info",
        description="指定订单（需要用户先发送订单对象）的详情咨询",
        provider_ids=["api.order"],
        requires_object="order",
    ),
    "refund_policy": KnowledgeIntent(
        id="refund_policy",
        description="退款政策咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "vip_policy": KnowledgeIntent(
        id="vip_policy",
        description="VIP会员权益咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "listening_policy": KnowledgeIntent(
        id="listening_policy",
        description="收听规则与播放问题咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "platform_rule": KnowledgeIntent(
        id="platform_rule",
        description="平台规则咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
    "general_audiobook_info": KnowledgeIntent(
        id="general_audiobook_info",
        description="听书商城通用信息咨询",
        provider_ids=["faq.default", "rag.default"],
    ),
}
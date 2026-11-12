from dataclasses import dataclass,field
from enum import Enum

@dataclass
class MessageObject:
    """业务层卡片对象"""
    type:str
    id:str|None = None
    title:str|None = None
    attributes:dict = field(default_factory=dict)


class MessageType(Enum):
    TEXT = "text"
    OBJECT = "object"

@dataclass
class UserMessage:
    sender_id:str
    message_id:str
    type:MessageType
    text:str|None=None
    object:MessageObject|None=None

@dataclass
class BotMessage:
    text:str|None=None
    object:MessageObject|None=None


def book_card_messages(books:list[dict],limit:int=3)->list[BotMessage]:
    """把后端返回的听书数据转成机器人卡片消息，让搜索和详情结果直接以听书卡片展示"""
    messages:list[BotMessage] = []
    for book in books[:limit]:
        book_id:str = str(book.get("book_id") or book.get("id") or "")
        if not book_id:
            continue
        messages.append(
            BotMessage(
                object=MessageObject(
                    type="book",
                    id=book_id,
                    title=book.get("title") or "未知听书",
                    attributes={
                        "book_id": book_id,
                        "author": book.get("author") or "未知",
                        "narrator": book.get("narrator") or "未知",
                        "category": book.get("category") or "未分类",
                        "price": str(book.get("price") if book.get("price") is not None else ""),
                        "cover_url": book.get("cover_url") or "",
                    },
                )
            )
        )
    return messages

def order_card_messages(orders:list[dict],limit:int=3)->list[BotMessage]:
    """把后端返回的订单数据转成机器人订单卡片消息，让订单列表直接以卡片展示"""
    messages:list[BotMessage] = []
    for order in orders[:limit]:
        order_id:str = str(order.get("order_id") or "")
        if not order_id:
            continue
        messages.append(
            BotMessage(
                object=MessageObject(
                    type="order",
                    id=order_id,
                    title=order.get("title") or "听书订单",
                    attributes={
                        "order_id": order_id,
                        "status": order.get("status") or "",
                        "amount": str(order.get("amount") if order.get("amount") is not None else ""),
                        "created_at": str(order.get("created_at") or ""),
                        "cover_url": order.get("cover_url") or "",
                    },
                )
            )
        )
    return messages

@dataclass
class ProcessResult:
    sender_id:str
    message_id:str
    messages:list[BotMessage]
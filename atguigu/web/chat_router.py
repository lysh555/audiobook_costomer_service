import uuid
from typing import Annotated

from fastapi import APIRouter
from fastapi.params import Depends
from loguru import logger

from atguigu.domain.messages import UserMessage, MessageType, MessageObject, ProcessResult
from atguigu.domain.state import DialogueState
from atguigu.service.dialogue_service import DialogueService
from atguigu.web.dependencies import get_dialogue_service
from atguigu.web.schemas import ChatRequest, ChatResponse, ChatBotMessage, HistoryResponse, HistoryMessage, ChatObject

chat_router = APIRouter(tags=["听书商城智能客服"])

def _build_user_message(chat_request:ChatRequest)->UserMessage:
    return UserMessage(
        sender_id=chat_request.sender_id,
        message_id=chat_request.message_id if chat_request.message_id else str(uuid.uuid4()),
        text=chat_request.text,
        type=MessageType.TEXT if chat_request.text else MessageType.OBJECT,
        object=MessageObject(
            id=chat_request.object.id,
            type=chat_request.object.type,
            title = chat_request.object.title,
            attributes=chat_request.object.attributes,
        ) if chat_request.object else None
    )





def _build_chat_response(process_result:ProcessResult)-> ChatResponse:
    return ChatResponse(
        sender_id=process_result.sender_id,
        message_id=process_result.message_id,
        messages=[ChatBotMessage(
            text=bot_message.text,
            object=_build_chat_object(bot_message.object) if bot_message.object else None
        ) for bot_message in (process_result.messages or [])],
    )


def _build_chat_object(message_object:MessageObject)->ChatObject:
    return ChatObject(
        type=message_object.type,
        id=message_object.id,
        title=message_object.title,
        attributes=message_object.attributes,
    )


@chat_router.post("/api/chat")
async def chat(chat_request:ChatRequest,dialogue_service:Annotated[DialogueService,Depends(get_dialogue_service)])->ChatResponse:
    user_message:UserMessage = _build_user_message(chat_request)
    process_result:ProcessResult = await dialogue_service.process_message(user_message)
    logger.info("本轮消息回复:{}",process_result)
    return _build_chat_response(process_result)

@chat_router.get("/api/chat/history")
async def chat_history(sender_id:str,dialogue_service:Annotated[DialogueService, Depends(get_dialogue_service)])->HistoryResponse:

    state:DialogueState = await dialogue_service.get_state(sender_id)

    history_messages:list[HistoryMessage] = []
    for session in state.shared_state.sessions:
        for turn in session.turns:
            history_messages.append(HistoryMessage(
                role="user",
                text=turn.user_message.text,
                object=_build_chat_object(turn.user_message.object) if turn.user_message.object else None
            ))
            history_messages.extend([HistoryMessage(
                role="bot",
                text=bot_message.text,
                object=_build_chat_object(bot_message.object) if bot_message.object else None
            )for bot_message in turn.bot_messages])
    return HistoryResponse(
        sender_id=sender_id,
        messages=history_messages
    )
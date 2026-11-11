from typing import Annotated, AsyncGenerator
from fastapi.params import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from atguigu.clients import database
from atguigu.engine.builder import build_engine
from atguigu.engine.dialogue_engine import DialogueEngine
from atguigu.repository.dialogue_state_record_repository import DialogueStateRecordRepository
from atguigu.service.dialogue_service import DialogueService


# 声明所有依赖项

async def get_session():
    # 前提：init_db_engine()已经被调用,session_factory对象完成赋值
    async with database.session_factory() as session:
        yield session


async def get_dialogue_state_repository(
        session: Annotated[AsyncSession, Depends(get_session)]) -> DialogueStateRecordRepository:
    return DialogueStateRecordRepository(session)


# 全局变量 需求：希望只初始化一次DialogueEngine
_dialogue_engine: DialogueEngine | None = None

def init_dialogue_engine():
    """项目启动在FastAPI生命周期执行调用一次"""
    global _dialogue_engine
    _dialogue_engine = build_engine()


async def get_dialogue_engine() -> DialogueEngine:
    return _dialogue_engine


async def get_dialogue_service(
        dialogue_state_repository: Annotated[DialogueStateRecordRepository, Depends(get_dialogue_state_repository)],
        dialogue_engine: Annotated[DialogueEngine, Depends(get_dialogue_engine)]
) -> DialogueService:
    return DialogueService(
        dialogue_state_repository=dialogue_state_repository,
        dialogue_engine=dialogue_engine
    )




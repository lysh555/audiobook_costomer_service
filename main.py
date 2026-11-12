from contextlib import asynccontextmanager
import uvicorn
from fastapi import FastAPI
from loguru import logger
from atguigu.clients.database import init_db_engine, close_db_engine
from atguigu.clients.http_client import init_http_client, close_http_client
from atguigu.conf.config import settings
from atguigu.web.chat_router import chat_router
from atguigu.web.dependencies import init_dialogue_engine


# 1.FastAPI生命周期
@asynccontextmanager
async def lifespan(_app:FastAPI):
    init_http_client()
    init_dialogue_engine()
    init_db_engine()
    logger.info("项目启动初始化：http客户端、对话引擎、数据库会话工厂")
    yield
    await close_db_engine()
    await close_http_client()
    logger.info("项目关闭，执行清理资源")

app = FastAPI(lifespan=lifespan)

app.include_router(chat_router)

def main():
    uvicorn.run("main:app",host="0.0.0.0",port=settings.app_port,reload=True)

if __name__ == "__main__":
    main()




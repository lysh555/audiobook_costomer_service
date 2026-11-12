from langchain.chat_models import init_chat_model
from atguigu.conf.config import settings

llm = init_chat_model(
    model_provider="openai",
    model=settings.llm_model,
    api_key=settings.llm_api_key,
    base_url=settings.llm_base_url,
    temperature=settings.llm_temperature,
    timeout=settings.llm_timeout,
).with_retry()
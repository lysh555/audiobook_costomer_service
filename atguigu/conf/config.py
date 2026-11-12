from pathlib import Path
from pydantic_settings import BaseSettings,SettingsConfigDict

ENV_FILE = Path(__file__).parents[2]/".env"
class Settings(BaseSettings):
    # LLM
    llm_api_key: str
    llm_model: str
    llm_base_url: str

    # 数据库
    database_url: str
    db_echo: bool = False

    # 听书商城后端 API
    audiobook_api_base_url: str

    # 服务器
    app_host: str
    app_port: int

    # LLM 调用参数
    llm_temperature: float = 0.4
    llm_timeout: int = 60

    # 会话超时（秒）
    session_timeout_seconds: int = 3600

    model_config = SettingsConfigDict(env_file=ENV_FILE)

settings = Settings()
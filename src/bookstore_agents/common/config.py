from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.5", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_tracing_enabled: bool = Field(default=True, alias="OPENAI_TRACING_ENABLED")
    model_api_url: str | None = Field(default=None, alias="MODEL_API_URL")

    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_api_key: str = Field(default="ollama", alias="OLLAMA_API_KEY")

    database_url: str = Field(
        default="postgresql://bookstore:bookstore@localhost:5432/bookstore",
        alias="DATABASE_URL",
    )

    catalog_mcp_url: str = Field(default="http://localhost:8101/mcp", alias="CATALOG_MCP_URL")
    customer_mcp_url: str = Field(default="http://localhost:8102/mcp", alias="CUSTOMER_MCP_URL")
    store_operations_mcp_url: str = Field(
        default="http://localhost:8103/mcp",
        alias="STORE_OPERATIONS_MCP_URL",
    )

    customer_concierge_agent_url: str = Field(
        default="http://localhost:8201",
        alias="CUSTOMER_CONCIERGE_AGENT_URL",
    )
    store_manager_agent_url: str = Field(
        default="http://localhost:8202",
        alias="STORE_MANAGER_AGENT_URL",
    )
    catalog_specialist_agent_url: str = Field(
        default="http://localhost:8203",
        alias="CATALOG_SPECIALIST_AGENT_URL",
    )
    reservation_specialist_agent_url: str = Field(
        default="http://localhost:8204",
        alias="RESERVATION_SPECIALIST_AGENT_URL",
    )
    message_drafter_agent_url: str = Field(
        default="http://localhost:8205",
        alias="MESSAGE_DRAFTER_AGENT_URL",
    )

    frontend_gateway_port: int = Field(default=8300, alias="FRONTEND_GATEWAY_PORT")
    chatkit_api_path: str = Field(default="/chatkit", alias="CHATKIT_API_PATH")

    approval_required_for_writes: bool = Field(
        default=True,
        alias="APPROVAL_REQUIRED_FOR_WRITES",
    )
    approval_state_store: str = Field(default="postgres", alias="APPROVAL_STATE_STORE")

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_port(env_name: str, default: int) -> int:
    import os

    raw_value = os.getenv(env_name)
    if raw_value is None or raw_value == "":
        return default
    return int(raw_value)

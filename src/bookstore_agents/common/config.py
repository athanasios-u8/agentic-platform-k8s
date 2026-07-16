from functools import lru_cache
from typing import Any

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-5.5", alias="OPENAI_MODEL")
    openai_base_url: str | None = Field(default=None, alias="OPENAI_BASE_URL")
    openai_tracing_enabled: bool = Field(default=True, alias="OPENAI_TRACING_ENABLED")
    model_api_url: str | None = Field(default=None, alias="MODEL_API_URL")

    azure_ai_search_endpoint: str | None = Field(
        default=None,
        alias="AZURE_AI_SEARCH_ENDPOINT",
    )
    azure_ai_search_admin_key: str | None = Field(
        default=None,
        alias="AZURE_AI_SEARCH_ADMIN_KEY",
    )
    azure_ai_search_query_key: str | None = Field(
        default=None,
        alias="AZURE_AI_SEARCH_QUERY_KEY",
    )
    azure_ai_search_use_managed_identity: bool = Field(
        default=False,
        alias="AZURE_AI_SEARCH_USE_MANAGED_IDENTITY",
    )
    azure_ai_search_index_name: str = Field(
        default="srch-index-bookstore-dev",
        alias="AZURE_AI_SEARCH_INDEX_NAME",
    )
    book_review_search_top_k: int = Field(default=15, alias="BOOK_REVIEW_SEARCH_TOP_K")
    book_review_data_path: str = Field(
        default="data/book_reviews/book_reviews.jsonl",
        alias="BOOK_REVIEW_DATA_PATH",
    )
    book_review_min_reviews: int = Field(default=10, alias="BOOK_REVIEW_MIN_REVIEWS")
    book_review_max_reviews: int = Field(default=15, alias="BOOK_REVIEW_MAX_REVIEWS")
    book_review_max_books: int | None = Field(default=None, alias="BOOK_REVIEW_MAX_BOOKS")
    book_review_random_seed: int = Field(default=42, alias="BOOK_REVIEW_RANDOM_SEED")
    book_review_generation_model: str | None = Field(
        default=None,
        alias="BOOK_REVIEW_GENERATION_MODEL",
    )
    azure_openai_endpoint: str | None = Field(default=None, alias="AZURE_OPENAI_ENDPOINT")
    azure_openai_api_version: str = Field(
        default="2025-04-01-preview",
        alias="AZURE_OPENAI_API_VERSION",
    )
    azure_openai_scope: str = Field(
        default="https://cognitiveservices.azure.com/.default",
        alias="AZURE_OPENAI_SCOPE",
    )
    azure_openai_use_managed_identity: bool = Field(
        default=False,
        alias="AZURE_OPENAI_USE_MANAGED_IDENTITY",
    )

    ollama_model: str = Field(default="llama3.2:3b", alias="OLLAMA_MODEL")
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_api_key: str = Field(default="ollama", alias="OLLAMA_API_KEY")
    ollama_timeout_seconds: float = Field(default=300.0, alias="OLLAMA_TIMEOUT_SECONDS")
    a2a_stream_timeout_seconds: float = Field(default=300.0, alias="A2A_STREAM_TIMEOUT_SECONDS")

    tavily_api_key: str | None = Field(default=None, alias="TAVILY_API_KEY")
    tavily_search_url: str = Field(
        default="https://api.tavily.com/search",
        alias="TAVILY_SEARCH_URL",
    )

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
    upcoming_releases_mcp_url: str = Field(
        default="http://localhost:8104/mcp",
        alias="UPCOMING_RELEASES_MCP_URL",
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
    release_scout_agent_url: str = Field(
        default="http://localhost:8206",
        alias="RELEASE_SCOUT_AGENT_URL",
    )
    review_summarizer_agent_url: str = Field(
        default="http://localhost:8207",
        alias="REVIEW_SUMMARIZER_AGENT_URL",
    )

    frontend_gateway_port: int = Field(default=8300, alias="FRONTEND_GATEWAY_PORT")
    chatkit_api_path: str = Field(default="/chatkit", alias="CHATKIT_API_PATH")

    approval_required_for_writes: bool = Field(
        default=True,
        alias="APPROVAL_REQUIRED_FOR_WRITES",
    )
    approval_state_store: str = Field(default="postgres", alias="APPROVAL_STATE_STORE")

    observability_enabled: bool = Field(default=True, alias="OBSERVABILITY_ENABLED")
    observability_capture_content: bool = Field(
        default=True,
        alias="OBSERVABILITY_CAPTURE_CONTENT",
    )
    observability_content_max_chars: int = Field(
        default=6000,
        alias="OBSERVABILITY_CONTENT_MAX_CHARS",
    )

    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @field_validator("book_review_max_books", mode="before")
    @classmethod
    def empty_book_limit_is_unset(cls, value: Any) -> Any:
        if value == "":
            return None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()


def get_port(env_name: str, default: int) -> int:
    import os

    raw_value = os.getenv(env_name)
    if raw_value is None or raw_value == "":
        return default
    return int(raw_value)

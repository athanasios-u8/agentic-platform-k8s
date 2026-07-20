"""Azure AI Search implementation of the vector search backend."""

from bookstore_agents.azure_ai_search.backend import (
    AzureAISearchBackend,
    AzureAISearchConfig,
    AzureAISearchConfigurationError,
    build_review_index,
    escape_odata_string,
)

__all__ = [
    "AzureAISearchBackend",
    "AzureAISearchConfig",
    "AzureAISearchConfigurationError",
    "build_review_index",
    "escape_odata_string",
]

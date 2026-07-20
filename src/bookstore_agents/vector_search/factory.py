from collections.abc import Callable

from bookstore_agents.azure_ai_search.backend import AzureAISearchBackend
from bookstore_agents.common.config import Settings, get_settings
from bookstore_agents.opensearch_search.backend import OpenSearchBackend
from bookstore_agents.vector_search.backend import (
    VectorSearchBackend,
    VectorSearchConfigurationError,
)

BackendFactory = Callable[[Settings], VectorSearchBackend]

_BACKEND_FACTORIES: dict[str, BackendFactory] = {
    "azure_ai_search": AzureAISearchBackend.from_settings,
    "opensearch": OpenSearchBackend.from_settings,
}


def create_vector_search_backend(settings: Settings | None = None) -> VectorSearchBackend:
    settings = settings or get_settings()
    provider = settings.book_review_search_provider
    try:
        factory = _BACKEND_FACTORIES[provider]
    except KeyError as exc:  # defensive: Settings validates supported values
        supported = ", ".join(sorted(_BACKEND_FACTORIES))
        raise VectorSearchConfigurationError(
            f"Unsupported BOOK_REVIEW_SEARCH_PROVIDER={provider!r}; expected one of: {supported}."
        ) from exc
    return factory(settings)

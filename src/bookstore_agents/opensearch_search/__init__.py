"""OpenSearch implementation of the vector search backend."""

from bookstore_agents.opensearch_search.backend import (
    OpenSearchBackend,
    OpenSearchConfig,
    OpenSearchConfigurationError,
    build_review_index_mapping,
)

__all__ = [
    "OpenSearchBackend",
    "OpenSearchConfig",
    "OpenSearchConfigurationError",
    "build_review_index_mapping",
]

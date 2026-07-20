"""Provider-neutral review indexing, search, and document generation."""

from bookstore_agents.vector_search.backend import (
    REVIEW_FIELDS,
    VectorSearchBackend,
    VectorSearchConfigurationError,
)
from bookstore_agents.vector_search.catalog import BookRecord, normalize_title
from bookstore_agents.vector_search.reviews import (
    ReviewDocument,
    ReviewGenerationPlan,
    build_review_plans,
    read_reviews_jsonl,
    write_reviews_jsonl,
)

__all__ = [
    "REVIEW_FIELDS",
    "BookRecord",
    "ReviewDocument",
    "ReviewGenerationPlan",
    "VectorSearchBackend",
    "VectorSearchConfigurationError",
    "build_review_plans",
    "normalize_title",
    "read_reviews_jsonl",
    "write_reviews_jsonl",
]

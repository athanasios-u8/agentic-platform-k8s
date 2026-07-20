from collections.abc import Iterable
from typing import Any, Protocol, runtime_checkable

from bookstore_agents.vector_search.reviews import ReviewDocument


class VectorSearchConfigurationError(RuntimeError):
    """Raised when the selected vector search backend is not configured."""


REVIEW_FIELDS = (
    "id",
    "review_id",
    "book_id",
    "isbn",
    "book_title",
    "book_title_normalized",
    "authors",
    "genre",
    "audience",
    "sentiment_profile",
    "sentiment",
    "rating",
    "headline",
    "review_text",
    "synthetic",
    "generated_at",
)


@runtime_checkable
class VectorSearchBackend(Protocol):
    """Provider-neutral operations used by review indexing and retrieval."""

    provider_name: str
    index_name: str

    def create_or_update_index(self) -> Any: ...

    def count_documents(self) -> int: ...

    def upload_documents(
        self,
        documents: Iterable[ReviewDocument],
        batch_size: int = 500,
    ) -> int: ...

    def search_reviews(
        self,
        book_title_normalized: str,
        query: str,
        top: int,
    ) -> list[dict[str, Any]]: ...

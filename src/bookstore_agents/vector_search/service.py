from bookstore_agents.common.config import get_settings
from bookstore_agents.vector_search.backend import VectorSearchBackend
from bookstore_agents.vector_search.catalog import BookRecord, list_books, resolve_book
from bookstore_agents.vector_search.factory import create_vector_search_backend


class BookReviewSearchService:
    def __init__(self, backend: VectorSearchBackend | None = None) -> None:
        self.settings = get_settings()
        self.backend = backend or create_vector_search_backend(self.settings)

    def resolve_book(self, message: str, book_title: str | None = None) -> BookRecord | None:
        books = list_books()
        if book_title:
            requested = resolve_book(books, book_title)
            if requested:
                return requested
        return resolve_book(books, message)

    def search_for_book(
        self,
        book: BookRecord,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, object]]:
        return self.backend.search_reviews(
            book_title_normalized=book.title_normalized,
            query=query,
            top=top_k or self.settings.book_review_search_top_k,
        )

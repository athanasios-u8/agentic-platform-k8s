"""Azure AI Search helpers for synthetic bookstore review retrieval."""

from bookstore_agents.azure_ai_search.catalog import BookRecord, normalize_title
from bookstore_agents.azure_ai_search.reviews import (
    ReviewDocument,
    ReviewGenerationPlan,
    build_review_plans,
    read_reviews_jsonl,
    write_reviews_jsonl,
)
from bookstore_agents.azure_ai_search.search import (
    AzureSearchConfigError,
    create_or_update_review_index,
    escape_odata_string,
    search_reviews,
    upload_review_documents,
)
from bookstore_agents.azure_ai_search.service import BookReviewSearchService

__all__ = [
    "AzureSearchConfigError",
    "BookRecord",
    "BookReviewSearchService",
    "ReviewDocument",
    "ReviewGenerationPlan",
    "build_review_plans",
    "create_or_update_review_index",
    "escape_odata_string",
    "normalize_title",
    "read_reviews_jsonl",
    "search_reviews",
    "upload_review_documents",
    "write_reviews_jsonl",
]

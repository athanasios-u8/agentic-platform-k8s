from collections.abc import Iterable
from functools import lru_cache
from typing import Any

from bookstore_agents.azure_ai_search.reviews import ReviewDocument
from bookstore_agents.common.config import get_settings


class AzureSearchConfigError(RuntimeError):
    pass


def escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def _azure_imports() -> dict[str, Any]:
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import SearchField, SearchIndex
    except Exception as exc:  # pragma: no cover
        raise AzureSearchConfigError(
            "Install azure-search-documents to use Azure AI Search features."
        ) from exc
    return {
        "AzureKeyCredential": AzureKeyCredential,
        "SearchClient": SearchClient,
        "SearchIndexClient": SearchIndexClient,
        "SearchField": SearchField,
        "SearchIndex": SearchIndex,
    }


@lru_cache(maxsize=1)
def _managed_identity_credential() -> Any:
    try:
        from azure.identity import DefaultAzureCredential
    except Exception as exc:  # pragma: no cover
        raise AzureSearchConfigError(
            "Install azure-identity to use Azure AI Search managed identity authentication."
        ) from exc
    return DefaultAzureCredential()


def _endpoint() -> str:
    settings = get_settings()
    endpoint = settings.azure_ai_search_endpoint
    if not endpoint:
        raise AzureSearchConfigError("AZURE_AI_SEARCH_ENDPOINT is required.")
    return endpoint.rstrip("/")


def _credential_key(admin: bool) -> str:
    settings = get_settings()
    key = settings.azure_ai_search_admin_key if admin else settings.azure_ai_search_query_key
    if not key:
        key = settings.azure_ai_search_admin_key
    if not key:
        raise AzureSearchConfigError("AZURE_AI_SEARCH_ADMIN_KEY is required.")
    return key


def _credential(admin: bool, azure: dict[str, Any]) -> Any:
    settings = get_settings()
    if settings.azure_ai_search_use_managed_identity:
        return _managed_identity_credential()
    return azure["AzureKeyCredential"](_credential_key(admin))


def _index_name() -> str:
    return get_settings().azure_ai_search_index_name


def _index_client(index_client: Any | None = None) -> Any:
    if index_client is not None:
        return index_client
    azure = _azure_imports()
    credential = _credential(admin=True, azure=azure)
    return azure["SearchIndexClient"](endpoint=_endpoint(), credential=credential)


def _search_client(search_client: Any | None = None, *, admin: bool = False) -> Any:
    if search_client is not None:
        return search_client
    azure = _azure_imports()
    credential = _credential(admin=admin, azure=azure)
    return azure["SearchClient"](
        endpoint=_endpoint(),
        index_name=_index_name(),
        credential=credential,
    )


def build_review_index(index_name: str | None = None) -> Any:
    azure = _azure_imports()
    field = azure["SearchField"]
    search_index = azure["SearchIndex"]
    return search_index(
        name=index_name or _index_name(),
        fields=[
            field(name="id", type="Edm.String", key=True, filterable=True, sortable=True),
            field(name="review_id", type="Edm.String", filterable=True, sortable=True),
            field(name="book_id", type="Edm.Int32", filterable=True, sortable=True, facetable=True),
            field(name="isbn", type="Edm.String", filterable=True, sortable=True),
            field(name="book_title", type="Edm.String", searchable=True, filterable=True),
            field(
                name="book_title_normalized",
                type="Edm.String",
                filterable=True,
                sortable=True,
                facetable=True,
            ),
            field(name="authors", type="Edm.String", searchable=True),
            field(
                name="genre",
                type="Edm.String",
                searchable=True,
                filterable=True,
                facetable=True,
            ),
            field(name="audience", type="Edm.String", filterable=True, facetable=True),
            field(name="sentiment_profile", type="Edm.String", filterable=True, facetable=True),
            field(name="sentiment", type="Edm.String", filterable=True, facetable=True),
            field(name="rating", type="Edm.Int32", filterable=True, sortable=True, facetable=True),
            field(name="headline", type="Edm.String", searchable=True),
            field(name="review_text", type="Edm.String", searchable=True),
            field(name="synthetic", type="Edm.Boolean", filterable=True, facetable=True),
            field(name="generated_at", type="Edm.DateTimeOffset", filterable=True, sortable=True),
        ],
    )


def create_or_update_review_index(index_client: Any | None = None) -> Any:
    client = _index_client(index_client)
    return client.create_or_update_index(build_review_index())


def _document_dicts(documents: Iterable[ReviewDocument]) -> list[dict[str, Any]]:
    return [document.model_dump(mode="json") for document in documents]


def upload_review_documents(
    documents: Iterable[ReviewDocument],
    search_client: Any | None = None,
    batch_size: int = 500,
) -> int:
    client = _search_client(search_client, admin=True)
    uploaded = 0
    batch: list[ReviewDocument] = []
    for document in documents:
        batch.append(document)
        if len(batch) >= batch_size:
            uploaded += _upload_batch(client, batch)
            batch = []
    if batch:
        uploaded += _upload_batch(client, batch)
    return uploaded


def _upload_batch(client: Any, batch: list[ReviewDocument]) -> int:
    results = client.upload_documents(documents=_document_dicts(batch))
    failures = [result for result in results if not getattr(result, "succeeded", False)]
    if failures:
        first = failures[0]
        error = getattr(first, "error_message", "unknown Azure AI Search upload error")
        raise RuntimeError(f"Azure AI Search upload failed: {error}")
    return len(batch)


def search_reviews(
    book_title_normalized: str,
    query: str,
    top: int | None = None,
    search_client: Any | None = None,
) -> list[dict[str, Any]]:
    settings = get_settings()
    client = _search_client(search_client)
    filter_value = escape_odata_string(book_title_normalized)
    results = client.search(
        search_text=query or "*",
        filter=f"book_title_normalized eq '{filter_value}'",
        search_fields=["book_title", "headline", "review_text"],
        select=[
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
        ],
        top=top or settings.book_review_search_top_k,
    )
    return [dict(result) for result in results]

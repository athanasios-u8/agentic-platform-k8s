from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from bookstore_agents.vector_search.backend import (
    REVIEW_FIELDS,
    VectorSearchConfigurationError,
)
from bookstore_agents.vector_search.reviews import ReviewDocument

if TYPE_CHECKING:
    from bookstore_agents.common.config import Settings


class AzureAISearchConfigurationError(VectorSearchConfigurationError):
    pass


@dataclass(frozen=True)
class AzureAISearchConfig:
    endpoint: str | None
    index_name: str
    admin_key: str | None = None
    query_key: str | None = None
    use_managed_identity: bool = False


def escape_odata_string(value: str) -> str:
    return value.replace("'", "''")


def _azure_imports() -> dict[str, Any]:
    try:
        from azure.core.credentials import AzureKeyCredential
        from azure.identity import DefaultAzureCredential
        from azure.search.documents import SearchClient
        from azure.search.documents.indexes import SearchIndexClient
        from azure.search.documents.indexes.models import SearchField, SearchIndex
    except Exception as exc:  # pragma: no cover
        raise AzureAISearchConfigurationError(
            "Install azure-search-documents and azure-identity to use Azure AI Search."
        ) from exc
    return {
        "AzureKeyCredential": AzureKeyCredential,
        "DefaultAzureCredential": DefaultAzureCredential,
        "SearchClient": SearchClient,
        "SearchIndexClient": SearchIndexClient,
        "SearchField": SearchField,
        "SearchIndex": SearchIndex,
    }


def build_review_index(index_name: str, azure: dict[str, Any] | None = None) -> Any:
    azure = azure or _azure_imports()
    field = azure["SearchField"]
    search_index = azure["SearchIndex"]
    return search_index(
        name=index_name,
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


class AzureAISearchBackend:
    provider_name = "azure_ai_search"

    def __init__(
        self,
        config: AzureAISearchConfig,
        *,
        index_client: Any | None = None,
        admin_search_client: Any | None = None,
        query_search_client: Any | None = None,
        azure: dict[str, Any] | None = None,
    ) -> None:
        self.config = config
        self.index_name = config.index_name
        self._index_client_override = index_client
        self._admin_search_client_override = admin_search_client
        self._query_search_client_override = query_search_client
        self._azure = azure
        self._managed_identity_credential: Any | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> AzureAISearchBackend:
        return cls(
            AzureAISearchConfig(
                endpoint=settings.azure_ai_search_endpoint,
                index_name=settings.azure_ai_search_index_name,
                admin_key=settings.azure_ai_search_admin_key,
                query_key=settings.azure_ai_search_query_key,
                use_managed_identity=settings.azure_ai_search_use_managed_identity,
            )
        )

    def _imports(self) -> dict[str, Any]:
        if self._azure is None:
            self._azure = _azure_imports()
        return self._azure

    def _endpoint(self) -> str:
        if not self.config.endpoint:
            raise AzureAISearchConfigurationError("AZURE_AI_SEARCH_ENDPOINT is required.")
        return self.config.endpoint.rstrip("/")

    def _credential(self, *, admin: bool) -> Any:
        azure = self._imports()
        if self.config.use_managed_identity:
            if self._managed_identity_credential is None:
                self._managed_identity_credential = azure["DefaultAzureCredential"]()
            return self._managed_identity_credential

        key = self.config.admin_key if admin else self.config.query_key or self.config.admin_key
        if not key:
            required = "AZURE_AI_SEARCH_ADMIN_KEY" if admin else "AZURE_AI_SEARCH_QUERY_KEY"
            raise AzureAISearchConfigurationError(
                f"{required} is required when managed identity is disabled."
            )
        return azure["AzureKeyCredential"](key)

    def _index_client(self) -> Any:
        if self._index_client_override is not None:
            return self._index_client_override
        azure = self._imports()
        self._index_client_override = azure["SearchIndexClient"](
            endpoint=self._endpoint(),
            credential=self._credential(admin=True),
        )
        return self._index_client_override

    def _search_client(self, *, admin: bool) -> Any:
        override_name = (
            "_admin_search_client_override" if admin else "_query_search_client_override"
        )
        client = getattr(self, override_name)
        if client is not None:
            return client
        azure = self._imports()
        client = azure["SearchClient"](
            endpoint=self._endpoint(),
            index_name=self.index_name,
            credential=self._credential(admin=admin),
        )
        setattr(self, override_name, client)
        return client

    def create_or_update_index(self) -> Any:
        return self._index_client().create_or_update_index(
            build_review_index(self.index_name, self._imports())
        )

    def count_documents(self) -> int:
        return int(self._search_client(admin=False).get_document_count())

    def upload_documents(
        self,
        documents: Iterable[ReviewDocument],
        batch_size: int = 500,
    ) -> int:
        client = self._search_client(admin=True)
        uploaded = 0
        batch: list[ReviewDocument] = []
        for document in documents:
            batch.append(document)
            if len(batch) >= batch_size:
                uploaded += self._upload_batch(client, batch)
                batch = []
        if batch:
            uploaded += self._upload_batch(client, batch)
        return uploaded

    @staticmethod
    def _upload_batch(client: Any, batch: list[ReviewDocument]) -> int:
        document_dicts = [document.model_dump(mode="json") for document in batch]
        results = client.upload_documents(documents=document_dicts)
        failures = [result for result in results if not getattr(result, "succeeded", False)]
        if failures:
            error = getattr(failures[0], "error_message", "unknown upload error")
            raise RuntimeError(f"Azure AI Search upload failed: {error}")
        return len(batch)

    def search_reviews(
        self,
        book_title_normalized: str,
        query: str,
        top: int,
    ) -> list[dict[str, Any]]:
        filter_value = escape_odata_string(book_title_normalized)
        results = self._search_client(admin=False).search(
            search_text=query or "*",
            filter=f"book_title_normalized eq '{filter_value}'",
            search_fields=["book_title", "headline", "review_text"],
            select=list(REVIEW_FIELDS),
            top=top,
        )
        return [dict(result) for result in results]

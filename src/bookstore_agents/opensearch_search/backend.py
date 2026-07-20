from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse

from bookstore_agents.vector_search.backend import (
    REVIEW_FIELDS,
    VectorSearchConfigurationError,
)
from bookstore_agents.vector_search.reviews import ReviewDocument

if TYPE_CHECKING:
    from bookstore_agents.common.config import Settings

BulkHelper = Callable[..., tuple[int, list[Any]]]


class OpenSearchConfigurationError(VectorSearchConfigurationError):
    pass


@dataclass(frozen=True)
class OpenSearchConfig:
    endpoint: str | None
    index_name: str
    region: str
    service: str = "es"
    use_aws_auth: bool = True
    username: str | None = None
    password: str | None = None
    verify_certs: bool = True


def _opensearch_imports() -> dict[str, Any]:
    try:
        import boto3  # type: ignore[import-untyped]
        from opensearchpy import AWSV4SignerAuth, OpenSearch, RequestsHttpConnection
        from opensearchpy.helpers import bulk
    except Exception as exc:  # pragma: no cover
        raise OpenSearchConfigurationError(
            "Install boto3 and opensearch-py to use the OpenSearch backend."
        ) from exc
    return {
        "boto3": boto3,
        "AWSV4SignerAuth": AWSV4SignerAuth,
        "OpenSearch": OpenSearch,
        "RequestsHttpConnection": RequestsHttpConnection,
        "bulk": bulk,
    }


def build_review_index_mapping() -> dict[str, Any]:
    return {
        "mappings": {
            "dynamic": "strict",
            "properties": {
                "id": {"type": "keyword"},
                "review_id": {"type": "keyword"},
                "book_id": {"type": "integer"},
                "isbn": {"type": "keyword"},
                "book_title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
                "book_title_normalized": {"type": "keyword"},
                "authors": {"type": "text"},
                "genre": {"type": "keyword"},
                "audience": {"type": "keyword"},
                "sentiment_profile": {"type": "keyword"},
                "sentiment": {"type": "keyword"},
                "rating": {"type": "integer"},
                "headline": {"type": "text"},
                "review_text": {"type": "text"},
                "synthetic": {"type": "boolean"},
                "generated_at": {"type": "date"},
            },
        }
    }


class OpenSearchBackend:
    provider_name = "opensearch"

    def __init__(
        self,
        config: OpenSearchConfig,
        *,
        client: Any | None = None,
        bulk_helper: BulkHelper | None = None,
        imports: dict[str, Any] | None = None,
    ) -> None:
        self.config = config
        self.index_name = config.index_name
        self._client_override = client
        self._bulk_helper_override = bulk_helper
        self._opensearch = imports

    @classmethod
    def from_settings(cls, settings: Settings) -> OpenSearchBackend:
        return cls(
            OpenSearchConfig(
                endpoint=settings.opensearch_endpoint,
                index_name=settings.opensearch_index_name,
                region=settings.aws_region,
                service=settings.opensearch_service,
                use_aws_auth=settings.opensearch_use_aws_auth,
                username=settings.opensearch_username,
                password=settings.opensearch_password,
                verify_certs=settings.opensearch_verify_certs,
            )
        )

    def _imports(self) -> dict[str, Any]:
        if self._opensearch is None:
            self._opensearch = _opensearch_imports()
        return self._opensearch

    def _client(self) -> Any:
        if self._client_override is not None:
            return self._client_override
        if not self.config.endpoint:
            raise OpenSearchConfigurationError("OPENSEARCH_ENDPOINT is required.")

        imports = self._imports()
        parsed = urlparse(
            self.config.endpoint
            if "://" in self.config.endpoint
            else f"https://{self.config.endpoint}"
        )
        if not parsed.hostname:
            raise OpenSearchConfigurationError("OPENSEARCH_ENDPOINT must contain a valid host.")

        use_ssl = parsed.scheme == "https"
        connection_options: dict[str, Any] = {
            "hosts": [
                {
                    "host": parsed.hostname,
                    "port": parsed.port or (443 if use_ssl else 80),
                }
            ],
            "use_ssl": use_ssl,
            "verify_certs": self.config.verify_certs,
            "connection_class": imports["RequestsHttpConnection"],
        }
        if self.config.use_aws_auth:
            credentials = imports["boto3"].Session().get_credentials()
            if credentials is None:
                raise OpenSearchConfigurationError(
                    "AWS credentials are required when OPENSEARCH_USE_AWS_AUTH=true."
                )
            connection_options["http_auth"] = imports["AWSV4SignerAuth"](
                credentials,
                self.config.region,
                self.config.service,
            )
        elif self.config.username:
            if self.config.password is None:
                raise OpenSearchConfigurationError(
                    "OPENSEARCH_PASSWORD is required when OPENSEARCH_USERNAME is set."
                )
            connection_options["http_auth"] = (
                self.config.username,
                self.config.password,
            )

        self._client_override = imports["OpenSearch"](**connection_options)
        return self._client_override

    def create_or_update_index(self) -> Any:
        client = self._client()
        definition = build_review_index_mapping()
        if client.indices.exists(index=self.index_name):
            return client.indices.put_mapping(
                index=self.index_name,
                body=definition["mappings"],
            )
        return client.indices.create(index=self.index_name, body=definition)

    def count_documents(self) -> int:
        response = self._client().count(index=self.index_name)
        return int(response["count"])

    def upload_documents(
        self,
        documents: Iterable[ReviewDocument],
        batch_size: int = 500,
    ) -> int:
        actions = [
            {
                "_index": self.index_name,
                "_id": document.id,
                "_source": document.model_dump(mode="json"),
            }
            for document in documents
        ]
        if not actions:
            return 0
        helper = self._bulk_helper_override or self._imports()["bulk"]
        succeeded, failures = helper(
            self._client(),
            actions,
            chunk_size=batch_size,
            raise_on_error=False,
            raise_on_exception=False,
        )
        if failures:
            raise RuntimeError(f"OpenSearch bulk upload failed: {failures[0]}")
        return succeeded

    def search_reviews(
        self,
        book_title_normalized: str,
        query: str,
        top: int,
    ) -> list[dict[str, Any]]:
        text_query: dict[str, Any]
        if query.strip():
            text_query = {
                "multi_match": {
                    "query": query,
                    "fields": ["book_title^2", "headline^2", "review_text"],
                }
            }
        else:
            text_query = {"match_all": {}}

        response = self._client().search(
            index=self.index_name,
            body={
                "size": top,
                "_source": list(REVIEW_FIELDS),
                "query": {
                    "bool": {
                        "must": [text_query],
                        "filter": [{"term": {"book_title_normalized": book_title_normalized}}],
                    }
                },
            },
        )
        hits = response.get("hits", {}).get("hits", [])
        return [dict(hit.get("_source", {})) for hit in hits]

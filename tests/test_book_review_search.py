from types import SimpleNamespace

from bookstore_agents.azure_ai_search.backend import (
    AzureAISearchBackend,
    AzureAISearchConfig,
    build_review_index,
    escape_odata_string,
)
from bookstore_agents.opensearch_search.backend import (
    OpenSearchBackend,
    OpenSearchConfig,
    build_review_index_mapping,
)
from bookstore_agents.vector_search.factory import create_vector_search_backend
from bookstore_agents.vector_search.reviews import ReviewDocument
from bookstore_agents.vector_search.service import BookReviewSearchService


def review_document(review_id: str = "review-1") -> ReviewDocument:
    return ReviewDocument(
        id=review_id,
        review_id=review_id,
        book_id=1,
        isbn="978-demo",
        book_title="The Lantern Cipher",
        book_title_normalized="the lantern cipher",
        authors="Mara Vale",
        genre="Mystery",
        audience="adult",
        sentiment_profile="positive-heavy",
        sentiment="positive",
        rating=5,
        headline="Loved it",
        review_text="A crisp mystery with a satisfying ending.",
        synthetic=True,
        generated_at="2026-01-01T00:00:00+00:00",
    )


def test_escape_odata_string() -> None:
    assert escape_odata_string("Clockmaker's Witness") == "Clockmaker''s Witness"


def test_build_azure_review_index_schema() -> None:
    class FakeSearchField:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeSearchIndex:
        def __init__(self, name, fields):
            self.name = name
            self.fields = fields

    index = build_review_index(
        "reviews",
        azure={"SearchField": FakeSearchField, "SearchIndex": FakeSearchIndex},
    )
    fields = {field.name: field for field in index.fields}

    assert index.name == "reviews"
    assert fields["id"].key is True
    assert fields["review_text"].searchable is True
    assert fields["book_title_normalized"].filterable is True
    assert fields["sentiment"].facetable is True
    assert fields["rating"].sortable is True


def test_azure_backend_uploads_review_documents() -> None:
    calls = {}

    class FakeSearchClient:
        def upload_documents(self, documents):
            calls["documents"] = documents
            return [SimpleNamespace(succeeded=True)]

    backend = AzureAISearchBackend(
        AzureAISearchConfig(endpoint="https://search.example", index_name="reviews"),
        admin_search_client=FakeSearchClient(),
    )

    uploaded = backend.upload_documents([review_document()])

    assert uploaded == 1
    assert calls["documents"][0]["review_text"] == "A crisp mystery with a satisfying ending."


def test_azure_backend_uses_managed_identity_when_enabled() -> None:
    credential = object()
    backend = AzureAISearchBackend(
        AzureAISearchConfig(
            endpoint="https://search.example",
            index_name="reviews",
            use_managed_identity=True,
        ),
        azure={"DefaultAzureCredential": lambda: credential},
    )

    assert backend._credential(admin=True) is credential


def test_azure_backend_filters_by_normalized_title_and_top_k() -> None:
    calls = {}

    class FakeSearchClient:
        def search(self, **kwargs):
            calls.update(kwargs)
            return [{"book_title": "The Clockmaker's Witness", "headline": "Good"}]

    backend = AzureAISearchBackend(
        AzureAISearchConfig(endpoint="https://search.example", index_name="reviews"),
        query_search_client=FakeSearchClient(),
    )
    rows = backend.search_reviews(
        "the clockmaker's witness",
        "What do readers dislike?",
        top=15,
    )

    assert calls["filter"] == "book_title_normalized eq 'the clockmaker''s witness'"
    assert calls["top"] == 15
    assert calls["search_fields"] == ["book_title", "headline", "review_text"]
    assert rows[0]["headline"] == "Good"


def test_opensearch_index_mapping_has_filter_and_text_fields() -> None:
    properties = build_review_index_mapping()["mappings"]["properties"]

    assert properties["id"]["type"] == "keyword"
    assert properties["book_title_normalized"]["type"] == "keyword"
    assert properties["review_text"]["type"] == "text"
    assert properties["rating"]["type"] == "integer"


def test_opensearch_backend_creates_or_updates_index() -> None:
    calls = {}

    class FakeIndices:
        def exists(self, *, index):
            calls["exists"] = index
            return False

        def create(self, *, index, body):
            calls["create"] = {"index": index, "body": body}
            return {"acknowledged": True}

    client = SimpleNamespace(indices=FakeIndices())
    backend = OpenSearchBackend(
        OpenSearchConfig(endpoint="https://search.example", index_name="reviews", region="eu"),
        client=client,
    )

    result = backend.create_or_update_index()

    assert result["acknowledged"] is True
    assert calls["create"]["index"] == "reviews"
    assert "mappings" in calls["create"]["body"]


def test_opensearch_backend_bulk_upload_is_injected() -> None:
    calls = {}

    def fake_bulk(client, actions, **kwargs):
        calls["client"] = client
        calls["actions"] = actions
        calls["kwargs"] = kwargs
        return len(actions), []

    client = object()
    backend = OpenSearchBackend(
        OpenSearchConfig(endpoint="https://search.example", index_name="reviews", region="eu"),
        client=client,
        bulk_helper=fake_bulk,
    )

    uploaded = backend.upload_documents([review_document()], batch_size=100)

    assert uploaded == 1
    assert calls["client"] is client
    assert calls["actions"][0]["_id"] == "review-1"
    assert calls["actions"][0]["_source"]["headline"] == "Loved it"
    assert calls["kwargs"]["chunk_size"] == 100


def test_opensearch_backend_uses_filtered_multi_match_query() -> None:
    calls = {}

    class FakeClient:
        def search(self, **kwargs):
            calls.update(kwargs)
            return {"hits": {"hits": [{"_source": {"headline": "Good"}}]}}

    backend = OpenSearchBackend(
        OpenSearchConfig(endpoint="https://search.example", index_name="reviews", region="eu"),
        client=FakeClient(),
    )

    rows = backend.search_reviews("the lantern cipher", "What is good?", top=7)

    query = calls["body"]["query"]["bool"]
    assert calls["index"] == "reviews"
    assert calls["body"]["size"] == 7
    assert query["filter"] == [{"term": {"book_title_normalized": "the lantern cipher"}}]
    assert query["must"][0]["multi_match"]["fields"] == [
        "book_title^2",
        "headline^2",
        "review_text",
    ]
    assert rows == [{"headline": "Good"}]


def test_factory_selects_provider_once_from_settings() -> None:
    settings = SimpleNamespace(
        book_review_search_provider="opensearch",
        opensearch_endpoint="https://search.example",
        opensearch_index_name="reviews",
        aws_region="eu-central-1",
        opensearch_service="es",
        opensearch_use_aws_auth=True,
        opensearch_username=None,
        opensearch_password=None,
        opensearch_verify_certs=True,
    )

    backend = create_vector_search_backend(settings)

    assert isinstance(backend, OpenSearchBackend)
    assert backend.index_name == "reviews"


def test_review_service_uses_injected_backend() -> None:
    calls = {}

    class FakeBackend:
        provider_name = "fake"
        index_name = "reviews"

        def search_reviews(self, book_title_normalized, query, top):
            calls.update(title=book_title_normalized, query=query, top=top)
            return [{"headline": "Injected"}]

    backend = FakeBackend()
    service = BookReviewSearchService(backend=backend)
    book = SimpleNamespace(title_normalized="the lantern cipher")

    rows = service.search_for_book(book, "What is good?", top_k=4)

    assert rows == [{"headline": "Injected"}]
    assert calls == {"title": "the lantern cipher", "query": "What is good?", "top": 4}

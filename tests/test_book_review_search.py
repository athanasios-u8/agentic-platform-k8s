from types import SimpleNamespace

from bookstore_agents.azure_ai_search import search
from bookstore_agents.azure_ai_search.reviews import ReviewDocument


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
    assert search.escape_odata_string("Clockmaker's Witness") == "Clockmaker''s Witness"


def test_build_review_index_schema(monkeypatch) -> None:
    class FakeSearchField:
        def __init__(self, **kwargs):
            self.__dict__.update(kwargs)

    class FakeSearchIndex:
        def __init__(self, name, fields):
            self.name = name
            self.fields = fields

    monkeypatch.setattr(
        search,
        "_azure_imports",
        lambda: {"SearchField": FakeSearchField, "SearchIndex": FakeSearchIndex},
    )

    index = search.build_review_index("reviews")
    fields = {field.name: field for field in index.fields}

    assert index.name == "reviews"
    assert fields["id"].key is True
    assert fields["review_text"].searchable is True
    assert fields["book_title_normalized"].filterable is True
    assert fields["sentiment"].facetable is True
    assert fields["rating"].sortable is True


def test_upload_review_documents_calls_search_client() -> None:
    calls = {}

    class FakeSearchClient:
        def upload_documents(self, documents):
            calls["documents"] = documents
            return [SimpleNamespace(succeeded=True)]

    uploaded = search.upload_review_documents([review_document()], search_client=FakeSearchClient())

    assert uploaded == 1
    assert calls["documents"][0]["review_text"] == "A crisp mystery with a satisfying ending."


def test_search_reviews_filters_by_normalized_title_and_top_k() -> None:
    calls = {}

    class FakeSearchClient:
        def search(self, **kwargs):
            calls.update(kwargs)
            return [
                {
                    "book_title": "The Clockmaker's Witness",
                    "headline": "Good",
                    "review_text": "Nice",
                }
            ]

    rows = search.search_reviews(
        "the clockmaker's witness",
        "What do readers dislike?",
        top=15,
        search_client=FakeSearchClient(),
    )

    assert calls["filter"] == "book_title_normalized eq 'the clockmaker''s witness'"
    assert calls["top"] == 15
    assert calls["search_fields"] == ["book_title", "headline", "review_text"]
    assert rows[0]["headline"] == "Good"

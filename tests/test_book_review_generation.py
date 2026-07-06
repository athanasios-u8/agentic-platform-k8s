from pathlib import Path

import pytest

from bookstore_agents.azure_ai_search.catalog import BookRecord
from bookstore_agents.azure_ai_search.reviews import (
    GeneratedReview,
    GeneratedReviewBatch,
    build_review_plans,
    documents_from_batch,
    generate_review_documents,
    read_reviews_jsonl,
    write_reviews_jsonl,
)


def book(book_id: int, title: str) -> BookRecord:
    return BookRecord(
        id=book_id,
        isbn=f"978-demo-{book_id}",
        title=title,
        title_normalized=title.lower().replace(" ", "-"),
        genre="Mystery",
        audience="adult",
        price=18.99,
        description="A twisty bookstore demo title.",
        published_year=2024,
        popularity=80,
        authors=["A. Writer"],
    )


def test_review_plans_cover_profiles_and_count_range() -> None:
    books = [book(index, f"Book {index}") for index in range(1, 10)]

    plans = build_review_plans(books, min_reviews=10, max_reviews=15, seed=123)

    assert {plan.profile for plan in plans.values()} == {
        "positive-heavy",
        "balanced",
        "negative-heavy",
    }
    for plan in plans.values():
        assert 10 <= plan.review_count <= 15
        positives = plan.sentiments.count("positive")
        negatives = plan.sentiments.count("negative")
        if plan.profile == "positive-heavy":
            assert positives > negatives
        if plan.profile == "balanced":
            assert abs(positives - negatives) <= 1
        if plan.profile == "negative-heavy":
            assert negatives > positives


@pytest.mark.asyncio
async def test_generate_review_documents_uses_openai_batches() -> None:
    books = [book(1, "The Lantern Cipher")]

    class FakeGenerator:
        async def generate_for_book(self, book_record, plan):
            return GeneratedReviewBatch(
                reviews=[
                    GeneratedReview(headline=f"Headline {index}", body="A useful short review.")
                    for index in range(plan.review_count)
                ]
            )

    documents = await generate_review_documents(books=books, generator=FakeGenerator())

    assert 10 <= len(documents) <= 15
    assert {document.book_title for document in documents} == {"The Lantern Cipher"}
    assert {document.synthetic for document in documents} == {True}
    assert all(document.review_text == "A useful short review." for document in documents)


def test_review_jsonl_roundtrip(tmp_path: Path) -> None:
    source_book = book(7, "Signal from Glass Moon")
    batch = GeneratedReviewBatch(
        reviews=[GeneratedReview(headline="Bright idea", body="I enjoyed the pacing and ideas.")]
    )
    plans = build_review_plans([source_book], min_reviews=1, max_reviews=1)
    documents = documents_from_batch(
        source_book,
        plans[source_book.id],
        batch,
        "2026-01-01T00:00:00+00:00",
        seed=42,
    )

    output_path = write_reviews_jsonl(documents, tmp_path / "reviews.jsonl")

    assert read_reviews_jsonl(output_path) == documents

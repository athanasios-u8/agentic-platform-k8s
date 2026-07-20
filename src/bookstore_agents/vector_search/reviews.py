import asyncio
from datetime import UTC, datetime
from pathlib import Path
from random import Random
from typing import Any, Literal, cast

from openai import AsyncAzureOpenAI, AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from bookstore_agents.common.config import get_settings
from bookstore_agents.vector_search.catalog import BookRecord, list_books

Sentiment = Literal["positive", "negative", "neutral"]
SentimentProfile = Literal["positive-heavy", "balanced", "negative-heavy"]


class ReviewGenerationPlan(BaseModel):
    book_id: int
    profile: SentimentProfile
    sentiments: list[Sentiment]

    @property
    def review_count(self) -> int:
        return len(self.sentiments)


class GeneratedReview(BaseModel):
    model_config = ConfigDict(extra="forbid")

    headline: str = Field(min_length=3, max_length=90)
    body: str = Field(min_length=20, max_length=900)


class GeneratedReviewBatch(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reviews: list[GeneratedReview]


class ReviewDocument(BaseModel):
    id: str
    review_id: str
    book_id: int
    isbn: str
    book_title: str
    book_title_normalized: str
    authors: str
    genre: str
    audience: str
    sentiment_profile: SentimentProfile
    sentiment: Sentiment
    rating: int = Field(ge=1, le=5)
    headline: str
    review_text: str
    synthetic: bool = True
    generated_at: str


class ReviewGenerationError(RuntimeError):
    pass


def _async_default_credential() -> Any:
    try:
        from azure.identity.aio import DefaultAzureCredential
    except Exception as exc:  # pragma: no cover
        raise ReviewGenerationError(
            "Install azure-identity to generate reviews with Azure workload identity."
        ) from exc
    return DefaultAzureCredential()


def build_review_plans(
    books: list[BookRecord],
    min_reviews: int = 10,
    max_reviews: int = 15,
    seed: int = 42,
) -> dict[int, ReviewGenerationPlan]:
    if min_reviews < 1 or max_reviews < min_reviews:
        raise ValueError("Review count range must be positive and ordered.")

    rng = Random(seed)
    shuffled = list(books)
    rng.shuffle(shuffled)
    profiles: tuple[SentimentProfile, ...] = ("positive-heavy", "balanced", "negative-heavy")
    assigned_profiles = {
        book.id: profiles[index % len(profiles)] for index, book in enumerate(shuffled)
    }

    plans: dict[int, ReviewGenerationPlan] = {}
    for book in books:
        profile = assigned_profiles[book.id]
        count = rng.randint(min_reviews, max_reviews)
        sentiments = _sentiments_for_profile(profile, count, rng)
        plans[book.id] = ReviewGenerationPlan(
            book_id=book.id,
            profile=profile,
            sentiments=sentiments,
        )
    return plans


def _sentiments_for_profile(
    profile: SentimentProfile,
    count: int,
    rng: Random,
) -> list[Sentiment]:
    if profile == "balanced":
        neutral = count % 2
        positive = (count - neutral) // 2
        negative = count - positive - neutral
    elif profile == "positive-heavy":
        neutral = rng.randint(0, min(2, max(count - 2, 0)))
        negative = max(1, count // 4)
        positive = count - neutral - negative
        if positive <= negative:
            positive = negative + 1
            neutral = max(0, count - positive - negative)
    else:
        neutral = rng.randint(0, min(2, max(count - 2, 0)))
        positive = max(1, count // 4)
        negative = count - neutral - positive
        if negative <= positive:
            negative = positive + 1
            neutral = max(0, count - positive - negative)

    sentiments = cast(
        list[Sentiment],
        ["positive"] * positive + ["negative"] * negative + ["neutral"] * neutral,
    )
    rng.shuffle(sentiments)
    return sentiments


def rating_for_sentiment(sentiment: Sentiment, rng: Random) -> int:
    if sentiment == "positive":
        return rng.choice([4, 5])
    if sentiment == "negative":
        return rng.choice([1, 2])
    return 3


class OpenAIReviewGenerator:
    def __init__(self) -> None:
        settings = get_settings()
        api_key = settings.openai_api_key
        base_url = settings.openai_base_url or settings.model_api_url
        self.model = settings.book_review_generation_model or settings.openai_model
        self.azure_credential: Any | None = None
        self.client: AsyncOpenAI | None

        if settings.azure_openai_use_managed_identity:
            if not settings.azure_openai_endpoint:
                raise ReviewGenerationError(
                    "AZURE_OPENAI_ENDPOINT is required for managed identity review generation."
                )
            azure_credential = _async_default_credential()
            self.azure_credential = azure_credential

            async def token_provider() -> str:
                token = await azure_credential.get_token(settings.azure_openai_scope)
                return token.token

            self.client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint.rstrip("/"),
                azure_deployment=self.model,
                api_version=settings.azure_openai_api_version,
                azure_ad_token_provider=token_provider,
            )
        else:
            self.client = (
                AsyncOpenAI(api_key=api_key, base_url=base_url.rstrip("/") if base_url else None)
                if api_key
                else None
            )

    async def close(self) -> None:
        if self.client is not None:
            await self.client.close()
        if self.azure_credential is not None:
            await self.azure_credential.close()

    async def generate_for_book(
        self,
        book: BookRecord,
        plan: ReviewGenerationPlan,
    ) -> GeneratedReviewBatch:
        if self.client is None:
            raise ReviewGenerationError(
                "OPENAI_API_KEY or Azure managed identity is required to generate book reviews."
            )

        prompt = _generation_prompt(book, plan)
        response = await self.client.responses.create(
            model=self.model,
            input=prompt,
            text={
                "format": {
                    "type": "json_schema",
                    "name": "book_review_batch",
                    "strict": True,
                    "schema": GeneratedReviewBatch.model_json_schema(),
                }
            },
        )
        try:
            batch = GeneratedReviewBatch.model_validate_json(response.output_text)
        except ValidationError as exc:
            raise ReviewGenerationError(f"OpenAI returned invalid review JSON: {exc}") from exc
        if len(batch.reviews) != plan.review_count:
            raise ReviewGenerationError(
                f"Expected {plan.review_count} reviews for {book.title}, got {len(batch.reviews)}."
            )
        return batch


def _generation_prompt(book: BookRecord, plan: ReviewGenerationPlan) -> str:
    authors = ", ".join(book.authors) or "unknown author"
    sentiment_lines = "\n".join(
        f"{index + 1}. {sentiment}" for index, sentiment in enumerate(plan.sentiments)
    )
    return f"""
Generate Amazon-style customer reviews for this bookstore catalog title.

Book:
- Title: {book.title}
- Authors: {authors}
- Genre: {book.genre}
- Audience: {book.audience}
- Description: {book.description}

Write exactly {plan.review_count} short reviews. The sentiment of each review must
match this ordered list:
{sentiment_lines}

Each review must have:
- a concise headline
- one small paragraph in the body

Use varied opinions, practical reader language, and plausible praise/criticism.
Return only JSON matching the provided schema.
"""


def documents_from_batch(
    book: BookRecord,
    plan: ReviewGenerationPlan,
    batch: GeneratedReviewBatch,
    generated_at: str,
    seed: int,
) -> list[ReviewDocument]:
    rng = Random(seed + book.id)
    authors = ", ".join(book.authors)
    documents: list[ReviewDocument] = []
    for index, generated in enumerate(batch.reviews):
        sentiment = plan.sentiments[index]
        review_id = f"book-{book.id:04d}-review-{index + 1:02d}"
        documents.append(
            ReviewDocument(
                id=review_id,
                review_id=review_id,
                book_id=book.id,
                isbn=book.isbn,
                book_title=book.title,
                book_title_normalized=book.title_normalized,
                authors=authors,
                genre=book.genre,
                audience=book.audience,
                sentiment_profile=plan.profile,
                sentiment=sentiment,
                rating=rating_for_sentiment(sentiment, rng),
                headline=generated.headline,
                review_text=generated.body,
                synthetic=True,
                generated_at=generated_at,
            )
        )
    return documents


async def generate_review_documents(
    books: list[BookRecord] | None = None,
    generator: OpenAIReviewGenerator | None = None,
) -> list[ReviewDocument]:
    settings = get_settings()
    books = books if books is not None else list_books()
    if settings.book_review_max_books is not None:
        books = books[: settings.book_review_max_books]
    plans = build_review_plans(
        books,
        min_reviews=settings.book_review_min_reviews,
        max_reviews=settings.book_review_max_reviews,
        seed=settings.book_review_random_seed,
    )
    owns_generator = generator is None
    generator = generator or OpenAIReviewGenerator()
    generated_at = datetime.now(UTC).isoformat()

    documents: list[ReviewDocument] = []
    try:
        for book in books:
            batch = await generator.generate_for_book(book, plans[book.id])
            documents.extend(
                documents_from_batch(
                    book,
                    plans[book.id],
                    batch,
                    generated_at,
                    settings.book_review_random_seed,
                )
            )
    finally:
        if owns_generator:
            await generator.close()
    return documents


def write_reviews_jsonl(documents: list[ReviewDocument], path: str | Path) -> Path:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        for document in documents:
            handle.write(document.model_dump_json() + "\n")
    return output_path


def read_reviews_jsonl(path: str | Path) -> list[ReviewDocument]:
    input_path = Path(path)
    documents: list[ReviewDocument] = []
    with input_path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                documents.append(ReviewDocument.model_validate_json(line))
            except ValidationError as exc:
                raise ValueError(f"Invalid review JSONL at line {line_number}: {exc}") from exc
    return documents


def generate_and_write_reviews(path: str | Path | None = None) -> Path:
    settings = get_settings()
    output_path = path or settings.book_review_data_path
    documents = asyncio.run(generate_review_documents())
    return write_reviews_jsonl(documents, output_path)

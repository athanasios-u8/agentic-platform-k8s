import re
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from bookstore_agents.common.database import fetch_all


class BookRecord(BaseModel):
    id: int
    isbn: str
    title: str
    title_normalized: str
    genre: str
    audience: str
    price: float
    description: str
    published_year: int
    popularity: int
    authors: list[str] = Field(default_factory=list)


def normalize_title(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _to_float(value: Any) -> Any:
    return float(value) if isinstance(value, Decimal) else value


def _authors(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [author.strip() for author in value.split(",") if author.strip()]
    return list(value)


def _book_from_row(row: dict[str, Any]) -> BookRecord:
    price = _to_float(row["price"])
    return BookRecord(
        id=int(row["id"]),
        isbn=str(row["isbn"]),
        title=str(row["title"]),
        title_normalized=normalize_title(str(row["title"])),
        genre=str(row["genre"]),
        audience=str(row["audience"]),
        price=float(price),
        description=str(row["description"]),
        published_year=int(row["published_year"]),
        popularity=int(row["popularity"]),
        authors=_authors(row.get("authors")),
    )


def list_books() -> list[BookRecord]:
    rows = fetch_all(
        """
        SELECT
            b.id,
            b.isbn,
            b.title,
            b.genre,
            b.audience,
            b.price,
            b.description,
            b.published_year,
            b.popularity,
            COALESCE(STRING_AGG(a.name, ', ' ORDER BY a.name), '') AS authors
        FROM books b
        LEFT JOIN book_authors ba ON ba.book_id = b.id
        LEFT JOIN authors a ON a.id = ba.author_id
        GROUP BY b.id
        ORDER BY b.id
        """
    )
    return [_book_from_row(row) for row in rows]


def resolve_book(books: list[BookRecord], text: str) -> BookRecord | None:
    normalized_text = normalize_title(text)
    if not normalized_text:
        return None

    exact_matches = [
        book for book in books if book.title_normalized and book.title_normalized in normalized_text
    ]
    if exact_matches:
        return max(exact_matches, key=lambda book: len(book.title_normalized))

    text_tokens = set(normalized_text.split())
    best_score = 0.0
    best_book: BookRecord | None = None
    for book in books:
        title_tokens = set(book.title_normalized.split())
        if not title_tokens:
            continue
        overlap = len(title_tokens & text_tokens)
        score = overlap / len(title_tokens)
        if overlap >= 2 and score > best_score:
            best_score = score
            best_book = book

    return best_book if best_score >= 0.5 else None

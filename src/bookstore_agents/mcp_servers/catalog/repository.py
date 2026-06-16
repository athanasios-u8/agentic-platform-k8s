from decimal import Decimal
from typing import Any

from bookstore_agents.common.database import fetch_all, fetch_one


def _to_float(value: Any) -> Any:
    return float(value) if isinstance(value, Decimal) else value


def _normalize_book(row: dict[str, Any]) -> dict[str, Any]:
    normalized = {key: _to_float(value) for key, value in row.items()}
    authors = normalized.get("authors")
    if isinstance(authors, str):
        normalized["authors"] = [author.strip() for author in authors.split(",") if author.strip()]
    elif authors is None:
        normalized["authors"] = []
    return normalized


class CatalogRepository:
    def search_books(
        self,
        keyword: str | None = None,
        genre: str | None = None,
        max_price: float | None = None,
        audience: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        conditions: list[str] = []
        params: list[Any] = []

        if keyword:
            conditions.append("(LOWER(b.title) LIKE %s OR LOWER(b.description) LIKE %s)")
            pattern = f"%{keyword.lower()}%"
            params.extend([pattern, pattern])
        if genre:
            conditions.append("LOWER(b.genre) = LOWER(%s)")
            params.append(genre)
        if max_price is not None:
            conditions.append("b.price <= %s")
            params.append(max_price)
        if audience:
            conditions.append("LOWER(b.audience) = LOWER(%s)")
            params.append(audience)

        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        rows = fetch_all(
            f"""
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
                COALESCE(STRING_AGG(a.name, ', ' ORDER BY a.name), '') AS authors,
                i.quantity_on_hand,
                i.quantity_reserved,
                (i.quantity_on_hand - i.quantity_reserved) AS available_quantity
            FROM books b
            LEFT JOIN book_authors ba ON ba.book_id = b.id
            LEFT JOIN authors a ON a.id = ba.author_id
            LEFT JOIN inventory i ON i.book_id = b.id
            {where_sql}
            GROUP BY b.id, i.quantity_on_hand, i.quantity_reserved
            ORDER BY b.popularity DESC, b.price ASC
            LIMIT %s
            """,
            params,
        )
        return [_normalize_book(row) for row in rows]

    def get_book_details(self, book_id: int) -> dict[str, Any] | None:
        row = fetch_one(
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
                COALESCE(STRING_AGG(a.name, ', ' ORDER BY a.name), '') AS authors,
                i.quantity_on_hand,
                i.quantity_reserved,
                (i.quantity_on_hand - i.quantity_reserved) AS available_quantity
            FROM books b
            LEFT JOIN book_authors ba ON ba.book_id = b.id
            LEFT JOIN authors a ON a.id = ba.author_id
            LEFT JOIN inventory i ON i.book_id = b.id
            WHERE b.id = %s
            GROUP BY b.id, i.quantity_on_hand, i.quantity_reserved
            """,
            (book_id,),
        )
        return _normalize_book(row) if row else None

    def recommend_books(
        self,
        prompt: str,
        genre: str | None = None,
        max_price: float | None = None,
        audience: str | None = None,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        keyword = None
        lowered = prompt.lower()
        for candidate in ["mystery", "science", "fantasy", "romance", "thriller", "children"]:
            if candidate in lowered and not genre:
                genre = "Science Fiction" if candidate == "science" else candidate.title()
        if "dad" in lowered or "father" in lowered:
            audience = audience or "adult"
        if "under $20" in lowered or "under 20" in lowered:
            max_price = max_price or 20.0
        if not genre:
            keyword = prompt
        return self.search_books(
            keyword=keyword, genre=genre, max_price=max_price, audience=audience, limit=limit
        )

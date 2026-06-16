from datetime import date
from decimal import Decimal
from typing import Any
from uuid import uuid4

from bookstore_agents.common.database import connection, fetch_all, fetch_one


def _to_jsonable(row: dict[str, Any]) -> dict[str, Any]:
    result = {}
    for key, value in row.items():
        if isinstance(value, Decimal):
            result[key] = float(value)
        elif isinstance(value, date):
            result[key] = value.isoformat()
        else:
            result[key] = value
    return result


class StoreOperationsRepository:
    def check_stock(
        self, book_id: int | None = None, title: str | None = None
    ) -> list[dict[str, Any]]:
        conditions = []
        params: list[Any] = []
        if book_id is not None:
            conditions.append("b.id = %s")
            params.append(book_id)
        if title:
            conditions.append("LOWER(b.title) LIKE %s")
            params.append(f"%{title.lower()}%")
        where_sql = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = fetch_all(
            f"""
            SELECT
                b.id AS book_id,
                b.title,
                i.quantity_on_hand,
                i.quantity_reserved,
                (i.quantity_on_hand - i.quantity_reserved) AS available_quantity,
                i.location
            FROM inventory i
            JOIN books b ON b.id = i.book_id
            {where_sql}
            ORDER BY b.title
            """,
            params,
        )
        return [_to_jsonable(row) for row in rows]

    def list_low_stock(self, threshold: int = 2) -> list[dict[str, Any]]:
        rows = fetch_all(
            """
            SELECT
                b.id AS book_id,
                b.title,
                b.genre,
                i.quantity_on_hand,
                i.quantity_reserved,
                (i.quantity_on_hand - i.quantity_reserved) AS available_quantity
            FROM inventory i
            JOIN books b ON b.id = i.book_id
            WHERE (i.quantity_on_hand - i.quantity_reserved) <= %s
            ORDER BY available_quantity ASC, b.popularity DESC
            """,
            (threshold,),
        )
        return [_to_jsonable(row) for row in rows]

    def create_reservation(
        self,
        book_id: int,
        customer_id: int,
        pickup_date: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        requested_pickup_date = date.fromisoformat(pickup_date) if pickup_date else date.today()
        reservation_id = f"res-{uuid4().hex[:12]}"
        with connection() as conn:
            with conn.cursor() as cur:
                inventory = cur.execute(
                    """
                    SELECT quantity_on_hand, quantity_reserved
                    FROM inventory
                    WHERE book_id = %s
                    FOR UPDATE
                    """,
                    (book_id,),
                ).fetchone()
                if not inventory:
                    raise ValueError(f"Book {book_id} has no inventory record.")
                available = inventory["quantity_on_hand"] - inventory["quantity_reserved"]
                if available <= 0:
                    raise ValueError(f"Book {book_id} is not available for reservation.")
                customer = cur.execute(
                    "SELECT id FROM customers WHERE id = %s",
                    (customer_id,),
                ).fetchone()
                if not customer:
                    raise ValueError(f"Customer {customer_id} was not found.")
                cur.execute(
                    """
                    UPDATE inventory
                    SET quantity_reserved = quantity_reserved + 1
                    WHERE book_id = %s
                    """,
                    (book_id,),
                )
                row = cur.execute(
                    """
                    INSERT INTO reservations (
                        reservation_id, book_id, customer_id, status, pickup_date, approval_id
                    )
                    VALUES (%s, %s, %s, 'active', %s, %s)
                    RETURNING
                        reservation_id,
                        book_id,
                        customer_id,
                        status,
                        pickup_date,
                        approval_id,
                        created_at
                    """,
                    (reservation_id, book_id, customer_id, requested_pickup_date, approval_id),
                ).fetchone()
                return _to_jsonable(dict(row))

    def cancel_reservation(
        self, reservation_id: str, approval_id: str | None = None
    ) -> dict[str, Any]:
        with connection() as conn:
            with conn.cursor() as cur:
                reservation = cur.execute(
                    """
                    SELECT reservation_id, book_id, status
                    FROM reservations
                    WHERE reservation_id = %s
                    FOR UPDATE
                    """,
                    (reservation_id,),
                ).fetchone()
                if not reservation:
                    raise ValueError(f"Reservation {reservation_id} was not found.")
                if reservation["status"] != "active":
                    raise ValueError(f"Reservation {reservation_id} is not active.")
                cur.execute(
                    """
                    UPDATE inventory
                    SET quantity_reserved = GREATEST(quantity_reserved - 1, 0)
                    WHERE book_id = %s
                    """,
                    (reservation["book_id"],),
                )
                row = cur.execute(
                    """
                    UPDATE reservations
                    SET
                        status = 'cancelled',
                        approval_id = COALESCE(%s, approval_id),
                        updated_at = NOW()
                    WHERE reservation_id = %s
                    RETURNING
                        reservation_id,
                        book_id,
                        customer_id,
                        status,
                        pickup_date,
                        approval_id,
                        updated_at
                    """,
                    (approval_id, reservation_id),
                ).fetchone()
                return _to_jsonable(dict(row))

    def mark_reservation_picked_up(
        self,
        reservation_id: str,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        with connection() as conn:
            with conn.cursor() as cur:
                reservation = cur.execute(
                    """
                    SELECT r.reservation_id, r.book_id, r.customer_id, r.status, b.price
                    FROM reservations r
                    JOIN books b ON b.id = r.book_id
                    WHERE r.reservation_id = %s
                    FOR UPDATE
                    """,
                    (reservation_id,),
                ).fetchone()
                if not reservation:
                    raise ValueError(f"Reservation {reservation_id} was not found.")
                if reservation["status"] != "active":
                    raise ValueError(f"Reservation {reservation_id} is not active.")
                cur.execute(
                    """
                    UPDATE inventory
                    SET
                        quantity_on_hand = GREATEST(quantity_on_hand - 1, 0),
                        quantity_reserved = GREATEST(quantity_reserved - 1, 0)
                    WHERE book_id = %s
                    """,
                    (reservation["book_id"],),
                )
                cur.execute(
                    """
                    INSERT INTO sales (book_id, customer_id, quantity, unit_price, sale_date)
                    VALUES (%s, %s, 1, %s, CURRENT_DATE)
                    """,
                    (reservation["book_id"], reservation["customer_id"], reservation["price"]),
                )
                row = cur.execute(
                    """
                    UPDATE reservations
                    SET
                        status = 'picked_up',
                        approval_id = COALESCE(%s, approval_id),
                        updated_at = NOW()
                    WHERE reservation_id = %s
                    RETURNING
                        reservation_id,
                        book_id,
                        customer_id,
                        status,
                        pickup_date,
                        approval_id,
                        updated_at
                    """,
                    (approval_id, reservation_id),
                ).fetchone()
                return _to_jsonable(dict(row))

    def adjust_inventory(
        self,
        book_id: int,
        quantity_delta: int,
        reason: str,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        with connection() as conn:
            with conn.cursor() as cur:
                row = cur.execute(
                    """
                    UPDATE inventory
                    SET quantity_on_hand = quantity_on_hand + %s
                    WHERE book_id = %s
                      AND quantity_on_hand + %s >= quantity_reserved
                    RETURNING book_id, quantity_on_hand, quantity_reserved, location
                    """,
                    (quantity_delta, book_id, quantity_delta),
                ).fetchone()
                if not row:
                    raise ValueError(
                        f"Inventory adjustment for book {book_id} would make stock invalid."
                    )
                result = _to_jsonable(dict(row))
                result["reason"] = reason
                result["approval_id"] = approval_id
                return result

    def list_today_pickups(self) -> list[dict[str, Any]]:
        rows = fetch_all(
            """
            SELECT
                r.reservation_id,
                r.status,
                r.pickup_date,
                b.title,
                c.name AS customer_name,
                c.email
            FROM reservations r
            JOIN books b ON b.id = r.book_id
            JOIN customers c ON c.id = r.customer_id
            WHERE r.pickup_date = CURRENT_DATE
              AND r.status = 'active'
            ORDER BY r.status, c.name
            """
        )
        return [_to_jsonable(row) for row in rows]

    def daily_sales_summary(self, sale_date: str | None = None) -> dict[str, Any]:
        requested_date = date.fromisoformat(sale_date) if sale_date else date.today()
        row = fetch_one(
            """
            SELECT
                %s::date AS sale_date,
                COALESCE(SUM(quantity), 0) AS units_sold,
                COALESCE(SUM(quantity * unit_price), 0) AS revenue,
                COUNT(*) AS transaction_count
            FROM sales
            WHERE sale_date = %s
            """,
            (requested_date, requested_date),
        )
        return _to_jsonable(row or {})

    def top_selling_books(self, days: int = 7, limit: int = 5) -> list[dict[str, Any]]:
        rows = fetch_all(
            """
            SELECT
                b.id AS book_id,
                b.title,
                b.genre,
                SUM(s.quantity) AS units_sold,
                SUM(s.quantity * s.unit_price) AS revenue
            FROM sales s
            JOIN books b ON b.id = s.book_id
            WHERE s.sale_date >= CURRENT_DATE - (%s::int * INTERVAL '1 day')
            GROUP BY b.id
            ORDER BY units_sold DESC, revenue DESC
            LIMIT %s
            """,
            (days, limit),
        )
        return [_to_jsonable(row) for row in rows]

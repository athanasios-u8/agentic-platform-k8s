from typing import Any

from bookstore_agents.common.database import connection, fetch_all, fetch_one


class CustomerRepository:
    def get_customer(
        self, customer_id: int | None = None, email: str | None = None
    ) -> dict[str, Any] | None:
        if customer_id is None and email is None:
            raise ValueError("customer_id or email is required")
        if customer_id is not None:
            customer = fetch_one("SELECT * FROM customers WHERE id = %s", (customer_id,))
        else:
            customer = fetch_one("SELECT * FROM customers WHERE LOWER(email) = LOWER(%s)", (email,))
        if not customer:
            return None
        customer["preferences"] = fetch_all(
            """
            SELECT id, genre, author, notes, created_at
            FROM customer_preferences
            WHERE customer_id = %s
            ORDER BY created_at DESC
            """,
            (customer["id"],),
        )
        return customer

    def lookup_loyalty_status(self, customer_id: int) -> dict[str, Any] | None:
        customer = fetch_one(
            "SELECT id, name, loyalty_tier FROM customers WHERE id = %s",
            (customer_id,),
        )
        if not customer:
            return None
        benefits = {
            "standard": ["Standard pickup"],
            "silver": ["Standard pickup", "5 percent discount on selected titles"],
            "gold": ["Priority pickup", "10 percent discount on selected titles"],
        }
        customer["benefits"] = benefits.get(customer["loyalty_tier"], benefits["standard"])
        return customer

    def update_customer_preferences(
        self,
        customer_id: int,
        genre: str | None = None,
        author: str | None = None,
        notes: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        with connection() as conn:
            with conn.cursor() as cur:
                customer = cur.execute(
                    "SELECT id FROM customers WHERE id = %s",
                    (customer_id,),
                ).fetchone()
                if not customer:
                    raise ValueError(f"Customer {customer_id} was not found.")
                row = cur.execute(
                    """
                    INSERT INTO customer_preferences (customer_id, genre, author, notes)
                    VALUES (%s, %s, %s, %s)
                    RETURNING id, customer_id, genre, author, notes, created_at
                    """,
                    (
                        customer_id,
                        genre,
                        author,
                        notes or f"Updated through approval {approval_id}.",
                    ),
                ).fetchone()
                return dict(row)

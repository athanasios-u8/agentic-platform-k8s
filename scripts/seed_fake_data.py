from datetime import date, timedelta
from random import Random

from bookstore_agents.common.database import connection

RANDOM = Random(42)

BOOKS = [
    ("978-1-00001-001-1", "The Lantern Cipher", "Mystery", "adult", 18.99, 2019, 92, ["Mara Vale"]),
    (
        "978-1-00001-002-8",
        "Midnight at Briar Lane",
        "Mystery",
        "adult",
        16.50,
        2021,
        88,
        ["Elias Rowan"],
    ),
    (
        "978-1-00001-003-5",
        "The Clockmaker's Witness",
        "Mystery",
        "adult",
        21.00,
        2017,
        79,
        ["Nora Field"],
    ),
    (
        "978-1-00001-004-2",
        "Last Train to Alderwick",
        "Mystery",
        "adult",
        14.95,
        2020,
        84,
        ["Mara Vale"],
    ),
    (
        "978-1-00001-005-9",
        "The Blue Door Society",
        "Mystery",
        "young adult",
        12.99,
        2022,
        81,
        ["Jun Park"],
    ),
    (
        "978-1-00001-006-6",
        "Orbit House",
        "Science Fiction",
        "adult",
        23.00,
        2018,
        90,
        ["Leah Stern"],
    ),
    (
        "978-1-00001-007-3",
        "Signal from Glass Moon",
        "Science Fiction",
        "adult",
        17.75,
        2024,
        95,
        ["Owen Hart"],
    ),
    (
        "978-1-00001-008-0",
        "The Kind Machine",
        "Science Fiction",
        "adult",
        19.50,
        2020,
        87,
        ["Priya Nair"],
    ),
    (
        "978-1-00001-009-7",
        "Children of the Red Comet",
        "Science Fiction",
        "young adult",
        13.50,
        2021,
        76,
        ["Leah Stern"],
    ),
    (
        "978-1-00001-010-3",
        "A Small Map of Mars",
        "Science Fiction",
        "middle grade",
        10.99,
        2023,
        72,
        ["Theo Quinn"],
    ),
    (
        "978-1-00001-011-0",
        "The Orchard House Letters",
        "Historical Fiction",
        "adult",
        18.25,
        2016,
        73,
        ["Clara Booth"],
    ),
    (
        "978-1-00001-012-7",
        "Winter Harbor",
        "Historical Fiction",
        "adult",
        15.99,
        2018,
        68,
        ["Mae Larkin"],
    ),
    (
        "978-1-00001-013-4",
        "The Silk Road Violin",
        "Historical Fiction",
        "young adult",
        13.95,
        2020,
        71,
        ["Hana Ito"],
    ),
    (
        "978-1-00001-014-1",
        "Letters from the Observatory",
        "Historical Fiction",
        "adult",
        22.50,
        2022,
        83,
        ["Clara Booth"],
    ),
    (
        "978-1-00001-015-8",
        "The Garden at Number Seven",
        "Romance",
        "adult",
        12.99,
        2019,
        80,
        ["Rose Calder"],
    ),
    (
        "978-1-00001-016-5",
        "Every Summer After Rain",
        "Romance",
        "adult",
        17.25,
        2021,
        86,
        ["Mina Blake"],
    ),
    (
        "978-1-00001-017-2",
        "The Lighthouse Promise",
        "Romance",
        "adult",
        15.50,
        2023,
        77,
        ["Rose Calder"],
    ),
    ("978-1-00001-018-9", "A Bakery in April", "Romance", "adult", 11.95, 2020, 74, ["Iris Bell"]),
    (
        "978-1-00001-019-6",
        "Twelve Good Knots",
        "Nonfiction",
        "adult",
        20.00,
        2024,
        70,
        ["Graham Pike"],
    ),
    ("978-1-00001-020-2", "Quiet Mornings", "Nonfiction", "adult", 14.99, 2022, 82, ["Lena Moss"]),
    (
        "978-1-00001-021-9",
        "The Practical Stargazer",
        "Nonfiction",
        "adult",
        24.50,
        2021,
        69,
        ["Nadia Sol"],
    ),
    (
        "978-1-00001-022-6",
        "A Cook's Map of Herbs",
        "Nonfiction",
        "adult",
        18.75,
        2020,
        65,
        ["Ben Vale"],
    ),
    (
        "978-1-00001-023-3",
        "Dragon in the Pantry",
        "Fantasy",
        "middle grade",
        9.99,
        2022,
        89,
        ["Theo Quinn"],
    ),
    (
        "978-1-00001-024-0",
        "The Glass Forest",
        "Fantasy",
        "young adult",
        13.99,
        2023,
        91,
        ["Jun Park"],
    ),
    (
        "978-1-00001-025-7",
        "River of Small Spells",
        "Fantasy",
        "adult",
        19.95,
        2021,
        85,
        ["Aria Stone"],
    ),
    (
        "978-1-00001-026-4",
        "The City of Borrowed Names",
        "Fantasy",
        "adult",
        22.00,
        2019,
        78,
        ["Aria Stone"],
    ),
    (
        "978-1-00001-027-1",
        "The Pocket Dragon Atlas",
        "Fantasy",
        "middle grade",
        8.99,
        2020,
        67,
        ["Theo Quinn"],
    ),
    (
        "978-1-00001-028-8",
        "The Patient River",
        "Literary Fiction",
        "adult",
        16.99,
        2017,
        75,
        ["Samuel Reed"],
    ),
    (
        "978-1-00001-029-5",
        "Three Rooms Facing East",
        "Literary Fiction",
        "adult",
        18.50,
        2021,
        79,
        ["Elena Cross"],
    ),
    (
        "978-1-00001-030-1",
        "The Book of Ordinary Weather",
        "Literary Fiction",
        "adult",
        14.25,
        2022,
        72,
        ["Samuel Reed"],
    ),
    (
        "978-1-00001-031-8",
        "The Saturday Code Club",
        "Children",
        "middle grade",
        7.99,
        2023,
        83,
        ["Nadia Sol"],
    ),
    (
        "978-1-00001-032-5",
        "Milo and the Missing Map",
        "Children",
        "middle grade",
        8.50,
        2021,
        64,
        ["Ben Vale"],
    ),
    (
        "978-1-00001-033-2",
        "The Very Small Orchestra",
        "Children",
        "picture book",
        6.99,
        2020,
        66,
        ["Hana Ito"],
    ),
    (
        "978-1-00001-034-9",
        "How to Hear a Cloud",
        "Children",
        "picture book",
        7.50,
        2022,
        62,
        ["Iris Bell"],
    ),
    (
        "978-1-00001-035-6",
        "Dead Drop at Dawn",
        "Thriller",
        "adult",
        18.00,
        2023,
        93,
        ["Elias Rowan"],
    ),
    ("978-1-00001-036-3", "North Exit", "Thriller", "adult", 15.75, 2021, 76, ["Nora Field"]),
    (
        "978-1-00001-037-0",
        "The Courier's Shadow",
        "Thriller",
        "adult",
        20.50,
        2024,
        87,
        ["Owen Hart"],
    ),
    ("978-1-00001-038-7", "Switchback", "Thriller", "adult", 13.99, 2018, 69, ["Graham Pike"]),
    (
        "978-1-00001-039-4",
        "The Beginner's Bread Table",
        "Nonfiction",
        "adult",
        16.25,
        2024,
        81,
        ["Iris Bell"],
    ),
    (
        "978-1-00001-040-0",
        "Kindling for New Readers",
        "Nonfiction",
        "adult",
        12.50,
        2023,
        77,
        ["Lena Moss"],
    ),
]

CUSTOMERS = [
    (
        "Maria Chen",
        "maria@example.com",
        "gold",
        [("Mystery", "Mara Vale", "Prefers clever puzzles under $20.")],
    ),
    (
        "Theo Martin",
        "theo@example.com",
        "standard",
        [("Science Fiction", None, "Likes approachable first-contact stories.")],
    ),
    (
        "Ava Robinson",
        "ava@example.com",
        "silver",
        [("Romance", "Rose Calder", "Enjoys cozy, low-conflict reads.")],
    ),
    (
        "Jon Bell",
        "jon@example.com",
        "standard",
        [("Fantasy", None, "Shopping for middle grade gifts.")],
    ),
    (
        "Priya Shah",
        "priya@example.com",
        "gold",
        [("Nonfiction", "Lena Moss", "Interested in calm productivity.")],
    ),
    (
        "Sam Carter",
        "sam@example.com",
        "standard",
        [("Thriller", "Elias Rowan", "Fast-paced weekend reads.")],
    ),
    (
        "Nina Flores",
        "nina@example.com",
        "silver",
        [("Historical Fiction", "Clara Booth", "Book club selections.")],
    ),
    (
        "Omar Haddad",
        "omar@example.com",
        "standard",
        [("Children", None, "Picture books for age 5.")],
    ),
    (
        "Grace Kim",
        "grace@example.com",
        "gold",
        [("Literary Fiction", "Samuel Reed", "Shorter novels preferred.")],
    ),
    ("Leo Hughes", "leo@example.com", "standard", [("Mystery", None, "Buying for father.")]),
    (
        "Ivy Patel",
        "ivy@example.com",
        "silver",
        [("Fantasy", "Aria Stone", "Likes lyrical worldbuilding.")],
    ),
    (
        "Noah Evans",
        "noah@example.com",
        "standard",
        [("Science Fiction", "Leah Stern", "Prefers space settings.")],
    ),
]


def clear_data() -> None:
    with connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                TRUNCATE TABLE
                    sales,
                    reservations,
                    approvals,
                    customer_preferences,
                    customers,
                    inventory,
                    book_authors,
                    books,
                    authors
                RESTART IDENTITY CASCADE
                """
            )


def seed_authors_and_books() -> dict[str, int]:
    author_names = sorted({author for *_, authors in BOOKS for author in authors})
    with connection() as conn:
        with conn.cursor() as cur:
            for name in author_names:
                cur.execute("INSERT INTO authors (name) VALUES (%s)", (name,))

            author_ids = {
                row["name"]: row["id"]
                for row in cur.execute("SELECT id, name FROM authors").fetchall()
            }

            book_ids: dict[str, int] = {}
            for isbn, title, genre, audience, price, year, popularity, authors in BOOKS:
                row = cur.execute(
                    """
                    INSERT INTO books (
                        isbn, title, genre, audience, price, description, published_year, popularity
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id
                    """,
                    (
                        isbn,
                        title,
                        genre,
                        audience,
                        price,
                        f"{title} is a {genre.lower()} pick for {audience} readers.",
                        year,
                        popularity,
                    ),
                ).fetchone()
                book_id = row["id"]
                book_ids[title] = book_id
                for author in authors:
                    cur.execute(
                        "INSERT INTO book_authors (book_id, author_id) VALUES (%s, %s)",
                        (book_id, author_ids[author]),
                    )

                quantity = RANDOM.randint(1, 14)
                if title in {
                    "The Clockmaker's Witness",
                    "A Small Map of Mars",
                    "The Very Small Orchestra",
                }:
                    quantity = 1
                cur.execute(
                    """
                    INSERT INTO inventory (book_id, quantity_on_hand, quantity_reserved, location)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (book_id, quantity, 0, RANDOM.choice(["front-room", "window", "back-room"])),
                )
            return book_ids


def seed_customers() -> dict[str, int]:
    with connection() as conn:
        with conn.cursor() as cur:
            customer_ids: dict[str, int] = {}
            for name, email, loyalty_tier, preferences in CUSTOMERS:
                row = cur.execute(
                    """
                    INSERT INTO customers (name, email, loyalty_tier)
                    VALUES (%s, %s, %s)
                    RETURNING id
                    """,
                    (name, email, loyalty_tier),
                ).fetchone()
                customer_id = row["id"]
                customer_ids[name] = customer_id
                for genre, author, notes in preferences:
                    cur.execute(
                        """
                        INSERT INTO customer_preferences (customer_id, genre, author, notes)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (customer_id, genre, author, notes),
                    )
            return customer_ids


def seed_reservations(book_ids: dict[str, int], customer_ids: dict[str, int]) -> None:
    today = date.today()
    rows = [
        ("res-demo-001", "The Lantern Cipher", "Maria Chen", "active", today),
        ("res-demo-002", "Signal from Glass Moon", "Theo Martin", "active", today),
        (
            "res-demo-003",
            "The Garden at Number Seven",
            "Ava Robinson",
            "picked_up",
            today - timedelta(days=1),
        ),
        (
            "res-demo-004",
            "Dragon in the Pantry",
            "Jon Bell",
            "cancelled",
            today + timedelta(days=1),
        ),
        ("res-demo-005", "Dead Drop at Dawn", "Sam Carter", "active", today),
    ]
    with connection() as conn:
        with conn.cursor() as cur:
            for reservation_id, title, customer, status, pickup_date in rows:
                cur.execute(
                    """
                    INSERT INTO reservations (
                        reservation_id, book_id, customer_id, status, pickup_date
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (reservation_id, book_ids[title], customer_ids[customer], status, pickup_date),
                )
                if status == "active":
                    cur.execute(
                        """
                        UPDATE inventory
                        SET quantity_reserved = quantity_reserved + 1
                        WHERE book_id = %s
                        """,
                        (book_ids[title],),
                    )


def seed_sales(book_ids: dict[str, int], customer_ids: dict[str, int]) -> None:
    titles = list(book_ids)
    customers = list(customer_ids.values())
    start = date.today() - timedelta(days=14)
    with connection() as conn:
        with conn.cursor() as cur:
            for offset in range(15):
                sale_date = start + timedelta(days=offset)
                for _ in range(RANDOM.randint(3, 8)):
                    title = RANDOM.choice(titles)
                    customer_id = RANDOM.choice(customers + [None, None])
                    quantity = RANDOM.choice([1, 1, 1, 2])
                    price = next(book[4] for book in BOOKS if book[1] == title)
                    cur.execute(
                        """
                        INSERT INTO sales (book_id, customer_id, quantity, unit_price, sale_date)
                        VALUES (%s, %s, %s, %s, %s)
                        """,
                        (book_ids[title], customer_id, quantity, price, sale_date),
                    )


def main() -> None:
    clear_data()
    book_ids = seed_authors_and_books()
    customer_ids = seed_customers()
    seed_reservations(book_ids, customer_ids)
    seed_sales(book_ids, customer_ids)
    print("Fake bookstore data seeded.")


if __name__ == "__main__":
    main()

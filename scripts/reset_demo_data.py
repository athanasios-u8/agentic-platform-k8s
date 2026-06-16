from scripts.init_db import main as init_db
from scripts.seed_fake_data import main as seed_data


def main() -> None:
    init_db()
    seed_data()
    print("Demo data reset.")


if __name__ == "__main__":
    main()

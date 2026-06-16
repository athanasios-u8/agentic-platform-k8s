.PHONY: sync lock lint test build up down logs init-db seed-db reset-db frontend

sync:
	uv sync

lock:
	uv lock

lint:
	uv run ruff check .

test:
	uv run pytest

build:
	docker compose build

up:
	docker compose up

down:
	docker compose down

logs:
	docker compose logs -f

init-db:
	docker compose run --rm bookstore-cli .venv/bin/python -m scripts.init_db

seed-db:
	docker compose run --rm bookstore-cli .venv/bin/python -m scripts.seed_fake_data

reset-db:
	docker compose run --rm bookstore-cli .venv/bin/python -m scripts.reset_demo_data

frontend:
	@echo "Open http://localhost:3000"

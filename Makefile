BACKEND_IMAGE_PREFIX ?= bookstore
FRONTEND_IMAGE_PREFIX ?= bookstore
IMAGE_TAG ?= local

.PHONY: sync lock lint test build up down logs init-db seed-db reset-db frontend
.PHONY: docker-build-backend-base docker-build-catalog-mcp docker-build-customer-mcp
.PHONY: docker-build-store-operations-mcp docker-build-upcoming-releases-mcp
.PHONY: docker-build-customer-concierge-agent
.PHONY: docker-build-store-manager-agent docker-build-catalog-specialist-agent
.PHONY: docker-build-reservation-specialist-agent docker-build-message-drafter-agent
.PHONY: docker-build-release-scout-agent
.PHONY: docker-build-frontend-gateway docker-build-frontend docker-build-agent-mcp-images
.PHONY: docker-build-backend-images docker-build-all-images

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
	docker compose run --rm bookstore-cli python -m scripts.init_db

seed-db:
	docker compose run --rm bookstore-cli python -m scripts.seed_fake_data

reset-db:
	docker compose run --rm bookstore-cli python -m scripts.reset_demo_data

frontend:
	@echo "Open http://localhost:3000"

docker-build-backend-base:
	docker build -t $(BACKEND_IMAGE_PREFIX)/backend:$(IMAGE_TAG) .

docker-build-catalog-mcp:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.mcp_servers.catalog.server -t $(BACKEND_IMAGE_PREFIX)/catalog-mcp:$(IMAGE_TAG) .

docker-build-customer-mcp:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.mcp_servers.customer.server -t $(BACKEND_IMAGE_PREFIX)/customer-mcp:$(IMAGE_TAG) .

docker-build-store-operations-mcp:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.mcp_servers.store_operations.server -t $(BACKEND_IMAGE_PREFIX)/store-operations-mcp:$(IMAGE_TAG) .

docker-build-upcoming-releases-mcp:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.mcp_servers.upcoming_releases.server -t $(BACKEND_IMAGE_PREFIX)/upcoming-releases-mcp:$(IMAGE_TAG) .

docker-build-customer-concierge-agent:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.agents.customer_concierge.server -t $(BACKEND_IMAGE_PREFIX)/customer-concierge-agent:$(IMAGE_TAG) .

docker-build-store-manager-agent:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.agents.store_manager.server -t $(BACKEND_IMAGE_PREFIX)/store-manager-agent:$(IMAGE_TAG) .

docker-build-catalog-specialist-agent:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.agents.catalog_specialist.server -t $(BACKEND_IMAGE_PREFIX)/catalog-specialist-agent:$(IMAGE_TAG) .

docker-build-reservation-specialist-agent:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.agents.reservation_specialist.server -t $(BACKEND_IMAGE_PREFIX)/reservation-specialist-agent:$(IMAGE_TAG) .

docker-build-message-drafter-agent:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.agents.message_drafter.server -t $(BACKEND_IMAGE_PREFIX)/message-drafter-agent:$(IMAGE_TAG) .

docker-build-release-scout-agent:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.agents.release_scout.server -t $(BACKEND_IMAGE_PREFIX)/release-scout-agent:$(IMAGE_TAG) .

docker-build-frontend-gateway:
	docker build --build-arg BOOKSTORE_SERVICE_MODULE=bookstore_agents.frontend_gateway.server -t $(BACKEND_IMAGE_PREFIX)/frontend-gateway:$(IMAGE_TAG) .

docker-build-frontend:
	docker build -t $(FRONTEND_IMAGE_PREFIX)/frontend:$(IMAGE_TAG) frontend

docker-build-agent-mcp-images: docker-build-catalog-mcp docker-build-customer-mcp docker-build-store-operations-mcp docker-build-upcoming-releases-mcp docker-build-customer-concierge-agent docker-build-store-manager-agent docker-build-catalog-specialist-agent docker-build-reservation-specialist-agent docker-build-message-drafter-agent docker-build-release-scout-agent

docker-build-backend-images: docker-build-backend-base docker-build-agent-mcp-images docker-build-frontend-gateway

docker-build-all-images: docker-build-backend-images docker-build-frontend

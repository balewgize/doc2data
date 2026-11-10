.PHONY: up down reset logs build prod prod-down dev-backend dev-frontend test check ollama-proxy

up:
	docker compose up --build

down:
	docker compose down

reset:
	docker compose down -v

logs:
	docker compose logs -f

build:
	docker compose build

prod:
	docker compose -f docker-compose.prod.yml up -d --build

prod-down:
	docker compose -f docker-compose.prod.yml down

# Native (no Docker) hot-reload runs
dev-backend:
	cd backend && uv run uvicorn app.main:app --reload --port 8000

dev-frontend:
	cd frontend && pnpm dev -p 3000

# On Linux, Ollama listens on 127.0.0.1 by default. Bridge it to the Docker
# host gateway so the backend container can reach the host model.
ollama-proxy:
	socat TCP-LISTEN:11434,bind=$$(docker network inspect bridge -f '{{(index .IPAM.Config 0).Gateway}}'),fork,reuseaddr TCP:127.0.0.1:11434

test:
	cd backend && uv run pytest

check: test
	cd frontend && pnpm build

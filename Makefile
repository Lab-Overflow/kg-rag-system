.PHONY: up down logs seed bench fmt lint test mcp

up:
	docker compose up -d --build

down:
	docker compose down

logs:
	docker compose logs -f backend

seed:
	docker compose exec backend python -m scripts.seed_data

bench:
	docker compose exec backend python -m app.eval.benchmark --dataset musique --mode agentic --limit 100

fmt:
	cd backend && ruff format . && ruff check --fix .
	cd frontend && npm run format

lint:
	cd backend && ruff check . && mypy app
	cd frontend && npm run lint

test:
	cd backend && pytest -q
	cd frontend && npm test

mcp:
	docker compose exec backend python -m app.mcp.server

.PHONY: install dev backend frontend lint test clean

# Install all dependencies
install: install-backend install-frontend

install-backend:
	cd backend && python -m pip install -e ".[dev]"

install-frontend:
	cd frontend && npm install

# Development servers
dev: dev-backend dev-frontend

dev-backend:
	cd backend && uvicorn gls.main:app --reload --port 8000

dev-frontend:
	cd frontend && npm run dev

# Linting and formatting
lint: lint-backend lint-frontend

lint-backend:
	cd backend && ruff check src tests
	cd backend && ruff format --check src tests
	cd backend && mypy src

lint-frontend:
	cd frontend && npm run lint
	cd frontend && npm run check

format: format-backend format-frontend

format-backend:
	cd backend && ruff format src tests
	cd backend && ruff check --fix src tests

format-frontend:
	cd frontend && npm run format

# Testing
test: test-backend test-frontend

test-backend:
	cd backend && pytest

test-frontend:
	cd frontend && npm run test

# Clean build artifacts
clean:
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .mypy_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .ruff_cache -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name node_modules -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .svelte-kit -exec rm -rf {} + 2>/dev/null || true
	rm -rf backend/dist frontend/build

# Pre-commit hooks
hooks:
	pre-commit install

# Database
db-init:
	cd backend && python -m gls.infrastructure.database.init

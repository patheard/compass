.PHONY: dev run install

dev:
	uv run uvicorn app.main:app --reload --host localhost --port 8000

run:
	uv run uvicorn app.main:app --host localhost --port 8000

install:
	uv sync

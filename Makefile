.PHONY: run install test fmt lint security i18n-extract i18n-update i18n-compile

run:
	uv run uvicorn app.main:app --reload --host localhost

install:
	uv sync

fmt:
	uv run ruff format .

lint:
	uv run ruff check .

security:
	uv run bandit -r app/

i18n-extract:
	uv run pybabel extract -F babel.cfg -k _l -o app/locales/messages.pot app/

i18n-update:
	uv run pybabel update -i app/locales/messages.pot -d app/locales

i18n-compile:
	uv run pybabel compile -d app/locales

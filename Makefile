.PHONY: dev run install i18n-extract i18n-update i18n-compile

dev:
	uv run uvicorn app.main:app --reload --host localhost

run:
	uv run uvicorn app.main:app --host localhost

install:
	uv sync

i18n-extract:
	uv run pybabel extract -F babel.cfg -k _l -o app/locales/messages.pot app/

i18n-update:
	uv run pybabel update -i app/locales/messages.pot -d app/locales

i18n-compile:
	uv run pybabel compile -d app/locales

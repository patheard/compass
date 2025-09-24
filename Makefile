.PHONY: deploy-lambda docker dynamodb-admin dynamodb-admin-install fmt i18n-compile i18n-extract i18n-update install lint local run security deploy-lambda

dynamodb-admin:
	AWS_REGION=ca-central-1 \
	AWS_ACCESS_KEY_ID=dummy \
	AWS_SECRET_ACCESS_KEY=dummy \
	DYNAMO_ENDPOINT=http://localhost:9000 \
	dynamodb-admin

dynamodb-admin-install:
	npm install -g dynamodb-admin

fmt:
	uv run ruff format .

i18n-compile:
	uv run pybabel compile -d app/locales

i18n-extract:
	uv run pybabel extract -F babel.cfg -k _l -o app/locales/messages.pot app/

i18n-update:
	uv run pybabel update -i app/locales/messages.pot -d app/locales

install:
	uv sync

lint:
	uv run ruff check .

local:
	docker-compose up -d

run: local
	uv run uvicorn app.main:app --reload --host localhost

security:
	uv run bandit -r app/

docker:
	set -o allexport; . .env; set +o allexport; \
	docker build -t compass -f Dockerfile.app --platform linux/arm64 . && \
	docker build -t compass-job-processor -f Dockerfile.job_processor --platform linux/arm64 . && \
	docker tag compass:latest $$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/compass:latest && \
	docker tag compass-job-processor:latest $$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/compass-job-processor:latest && \
	docker push $$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/compass:latest --platform linux/arm64 && \
	docker push $$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/compass-job-processor:latest --platform linux/arm64

deploy-lambda:
	set -o allexport; . .env; set +o allexport; \
	aws lambda update-function-code --function-name compass --image-uri $$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/compass:latest && \
	aws lambda update-function-code --function-name compass-job-processor --image-uri $$AWS_ACCOUNT_ID.dkr.ecr.$$AWS_REGION.amazonaws.com/compass-job-processor:latest



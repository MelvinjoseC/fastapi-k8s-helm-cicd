.PHONY: help install test test-cov lint lint-ruff format typecheck run migrate seed load-test benchmark health backup export-schema \
	    compose-up compose-down compose-obs docker-build kind-up kind-down \
	    k8s-deploy-dev k8s-deploy-staging k8s-deploy-prod k8s-delete-dev helm-install helm-upgrade helm-test

help:
	@echo "--- Development & Testing ---"
	@echo "make install         - install Python dependencies into .venv"
	@echo "make test            - run pytest test suite"
	@echo "make test-cov        - run pytest with terminal and HTML coverage reports"
	@echo "make lint            - run flake8 + black check"
	@echo "make lint-ruff       - run ultra-fast ruff linter on app and scripts"
	@echo "make format          - format code with ruff"
	@echo "make typecheck       - run mypy static type checking"
	@echo "make run             - run the API locally with uvicorn"
	@echo "make migrate         - run Alembic database migrations"
	@echo "make seed            - seed database with realistic demo task records"
	@echo "make load-test       - run concurrent load test against API"
	@echo "make benchmark       - run benchmark with latency percentiles and RPS report"
	@echo "make health          - run deployment health and readiness verifier"
	@echo "make backup          - take automated database snapshot to backups/"
	@echo "make export-schema   - export static docs/openapi.json"
	@echo ""
	@echo "--- Containers & Docker Compose ---"
	@echo "make compose-up      - start api + postgres + redis"
	@echo "make compose-down    - tear down docker compose stack"
	@echo "make compose-obs     - start stack with Prometheus and Jaeger observability"
	@echo "make docker-build    - build hardened container image"
	@echo ""
	@echo "--- Kubernetes & Helm ---"
	@echo "make kind-up         - create a local kind cluster"
	@echo "make kind-down       - delete the local kind cluster"
	@echo "make k8s-deploy-dev  - apply dev Kustomize overlay"
	@echo "make k8s-deploy-staging - apply staging Kustomize overlay"
	@echo "make k8s-deploy-prod - apply prod Kustomize overlay"
	@echo "make helm-install    - install/upgrade via Helm chart"
	@echo "make helm-upgrade    - upgrade Helm chart with production values"
	@echo "make helm-test       - run Helm test hook verification"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r app/requirements-dev.txt -r app/requirements.txt

test:
	cd app && ../.venv/bin/pytest -v

test-cov:
	cd app && ../.venv/bin/pytest -v --cov=. --cov-report=term-missing --cov-report=html:../htmlcov

lint:
	cd app && ../.venv/bin/flake8 --max-line-length=110 --extend-ignore=E203,W503 . --exclude=tests/__pycache__,alembic
	cd app && ../.venv/bin/black --check .

lint-ruff:
	ruff check app scripts
	ruff format --check app scripts

format:
	ruff format app scripts

typecheck:
	mypy app

run:
	cd app && CACHE_ENABLED=false ../.venv/bin/uvicorn main:app --reload --port 8000

migrate:
	python app/migrate.py

seed:
	python scripts/seed_data.py --url http://localhost:8000 --count 15

load-test:
	python scripts/load_test.py --url http://localhost:8000 -n 100 -c 10

benchmark:
	python scripts/benchmark.py --url http://localhost:8000 -n 150 -c 15

health:
	python scripts/health_check.py --url http://localhost:8000

backup:
	python scripts/backup_restore.py backup

export-schema:
	python scripts/export_openapi.py

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

compose-obs:
	docker compose up --build prometheus jaeger api postgres redis

docker-build:
	docker build -t taskapi:local ./app

kind-up:
	kind create cluster --name taskapi-dev

kind-down:
	kind delete cluster --name taskapi-dev

k8s-deploy-dev:
	kubectl apply -k k8s/overlays/dev
	kubectl rollout status deployment/taskapi -n taskapi-dev

k8s-deploy-staging:
	kubectl apply -k k8s/overlays/staging
	kubectl rollout status deployment/taskapi -n taskapi-staging

k8s-deploy-prod:
	kubectl apply -k k8s/overlays/prod
	kubectl rollout status deployment/taskapi -n taskapi-prod

k8s-delete-dev:
	kubectl delete -k k8s/overlays/dev

helm-install:
	helm upgrade --install taskapi ./helm/taskapi --namespace taskapi --create-namespace

helm-upgrade:
	helm upgrade taskapi ./helm/taskapi --namespace taskapi -f helm/taskapi/values-prod.yaml

helm-test:
	helm test taskapi --namespace taskapi

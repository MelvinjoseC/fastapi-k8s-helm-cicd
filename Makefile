.PHONY: help install test lint run compose-up compose-down docker-build \
        k8s-deploy-dev k8s-deploy-prod k8s-delete-dev helm-install helm-upgrade kind-up kind-down

help:
	@echo "make install        - install Python dependencies into .venv"
	@echo "make test           - run pytest"
	@echo "make lint           - run flake8 + black --check"
	@echo "make run            - run the API locally with uvicorn (sqlite, no cache)"
	@echo "make compose-up     - start api+postgres+redis with docker compose"
	@echo "make compose-down   - tear down docker compose stack"
	@echo "make docker-build   - build the container image"
	@echo "make kind-up        - create a local kind cluster"
	@echo "make k8s-deploy-dev - kustomize apply the dev overlay"
	@echo "make k8s-deploy-prod- kustomize apply the prod overlay"
	@echo "make helm-install   - install via Helm chart"
	@echo "make kind-down      - delete the local kind cluster"

install:
	python3 -m venv .venv
	.venv/bin/pip install --upgrade pip
	.venv/bin/pip install -r app/requirements-dev.txt

test:
	cd app && ../.venv/bin/pytest -v

lint:
	cd app && ../.venv/bin/flake8 --max-line-length=110 --extend-ignore=E203,W503 . --exclude=tests/__pycache__
	cd app && ../.venv/bin/black --check .

run:
	cd app && CACHE_ENABLED=false ../.venv/bin/uvicorn main:app --reload --port 8000

compose-up:
	docker compose up --build

compose-down:
	docker compose down -v

docker-build:
	docker build -t taskapi:local ./app

kind-up:
	kind create cluster --name taskapi-dev

kind-down:
	kind delete cluster --name taskapi-dev

k8s-deploy-dev:
	kubectl apply -k k8s/overlays/dev
	kubectl rollout status deployment/taskapi -n taskapi-dev

k8s-deploy-prod:
	kubectl apply -k k8s/overlays/prod
	kubectl rollout status deployment/taskapi -n taskapi-prod

k8s-delete-dev:
	kubectl delete -k k8s/overlays/dev

helm-install:
	helm upgrade --install taskapi ./helm/taskapi --namespace taskapi --create-namespace

helm-upgrade:
	helm upgrade taskapi ./helm/taskapi --namespace taskapi -f helm/taskapi/values-prod.yaml

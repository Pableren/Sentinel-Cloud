
.PHONY: up build up-build up-build-no-cache down \
	down-python-api \
	restart-python-api restart-minio restart-spark-master restart-spark-worker \
	restart-airflow-webserver restart-airflow-scheduler

up:
	docker compose up

build:
	docker compose build

up-build:
	docker compose up --build

up-build-no-cache:
	docker compose up --build --no-cache

down:
	docker compose down

# Python API Commands
down-python-api:
	docker compose stop python-api && docker compose rm -f python-api

restart-python-api:
	docker compose restart python-api

# MinIO Commands
restart-minio:
	docker compose restart minio

# Spark Commands
restart-spark-master:
	docker compose restart spark-master

restart-spark-worker:
	docker compose restart spark-worker

# Airflow Commands
restart-airflow-webserver:
	docker compose restart airflow-webserver

restart-airflow-scheduler:
	docker compose restart airflow-scheduler

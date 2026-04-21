.PHONY: up up-build down logs shell


up:
	docker compose up

up-build:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f

shell:
	docker compose run --rm python-lab /bin/bash

## Copilot / AI agent quick guidance for this repo

Keep guidance short and actionable. Edit only when you can verify the change locally (see dev commands below).

- Big picture
  - This repo simulates an end-to-end local Lakehouse pipeline using containers: a FastAPI data generator (`src/python-api`), a MinIO data lake, and a Dash dashboard (`src/dashboard`). See `docs/arquitectura.md` for the mermaid diagram and component roles.
  - Data flow: API -> MinIO `raw-data` (JSON unified files) -> (future) Spark reads `raw-data` and writes Parquet to `processed-data` -> Trino for queries.

- Key files you will edit
  - `src/python-api/main.py` — FastAPI endpoints and background task patterns (use BackgroundTasks, global `app_state`).
  - `src/python-api/data_generator.py` — core synthetic data generation (metrics, logs, traffic). Contains deterministic seeds and explicit dirty-data injections; downstream processing must tolerate these quirks.
  - `src/python-api/minio_client.py` — MinIO helper used to upload JSON and Parquet. Use env vars: `MINIO_ENDPOINT`, `MINIO_ACCESS_KEY`, `MINIO_SECRET_KEY`.
  - `src/python-api/config_data.py` — canonical seeds (instances, routes, service catalog). Update seeds here, not inside generator logic.
  - `docker-compose.yml`, `Makefile` — local development orchestration and common commands.

- Dev / run commands (verifiable)
  - Start full stack: `make up` (runs `docker compose up`).
  - Rebuild: `make up-build` or `make up-build-no-cache`.
  - Run API only (dev): `cd src/python-api && uvicorn main:app --host 0.0.0.0 --port 8000 --reload`.
  - Run dashboard only (dev): `python src/dashboard/app.py` (or via docker-compose). Ports: API=8000, MinIO=9000/9001, Dashboard=8050, cAdvisor=8080.

- Patterns & conventions
  - Background tasks: use FastAPI BackgroundTasks for long-running jobs; signal state via `app_state` dict as in `main.py`.
  - Uploads: unified JSON payloads are uploaded with `MinioClient.upload_json_unified` to `raw-data`. File prefixes use YYYYMM/ or explicit prefixes like `raw-historical-data/`.
  - Seeds/config: static domain data lives in `config_data.py`. Prefer changing seeds there rather than hardcoding values.
  - Error handling: initialization failures raise RuntimeError early (see `main.py`). Keep this pattern so containers fail fast if dependencies are misconfigured.

- Important data quirks (handle downstream)
  - `data_generator` intentionally injects "dirty" values: `cpu_percent` sometimes as string with comma, `instancia_id` with leading/trailing spaces, protocol case variations, service-name prefixes like `LEGACY_` or `UNK-`.
  - File naming: realtime files named `rawData_YYYYMMDD_HHMMSS.json`; historical files `historicalData_{start}_to_{end}.json`.

- Dependencies & verifications
  - Python deps for API: see `src/python-api/requirements.txt` (pandas, numpy, fastapi, uvicorn, minio, pydantic). Match versions when adding new packages.
  - Quick sanity checks: after edits, run the API locally and create a small historical simulation via `/simulation/historical` or `minio_client`'s __main__ tests to verify MinIO uploads.

- When you change public behavior (endpoints, file formats, bucket names)
  - Update `docs/api_endpoints.md` and `docs/arquitectura.md` accordingly.
  - Keep backward-compatible uploads: prefer adding new prefixes or buckets instead of changing existing raw filenames.

If anything in these notes is unclear or you want more examples (e.g., how to add a new endpoint or how to parse the dirty-data patterns), tell me which area and I will expand with concrete edits and tests.

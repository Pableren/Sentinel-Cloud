# SKILL: Apache Airflow Orchestration

**Profile:** Orchestration Engineer
**Context:** This file governs DAGs and Airflow configuration (`src/airflow`).

## ⚠️ CRITICAL CONSTRAINTS

### 1. Philosophy: Orchestration vs Processing
*   **Rule:** Airflow is for **Triggering** and **Monitoring**.
*   **Anti-Pattern:** DO NOT process heavy data (Pandas/Arrays) inside Airflow Tasks/Workers.
*   **Operators:** Use `DockerOperator` or `SparkSubmitOperator` to offload work.

### 2. Idempotency & Determinism
*   **Rule:** DAGs must be re-runnable without side effects (duplication).
*   **Filtering:** Use Jinja templates `{{ ds }}` (Execution Date) to filter data processing windows.
    *   *Bad:* `datetime.now()`
    *   *Good:* `{{ execution_date }}`

### 3. Reliability & Retries
*   **Configuration:** All tasks MUST have `retries` configured.
    ```python
    default_args = {
        'retries': 3,
        'retry_delay': timedelta(minutes=5),
    }
    ```

### 4. Sensors & Dependencies
*   **Pattern:** Use `Sensors` (e.g., `S3KeySensor`) to wait for data arrival in MinIO/S3 before starting processing tasks.
*   **Logic:** Detect -> Trigger Spark Job -> Verify.

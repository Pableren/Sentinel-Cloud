# SKILL: Python Backend & Data Generation

**Profile:** Python Backend Developer
**Context:** This file governs the Data Generator API (`src/python-api`).

## ⚠️ CRITICAL CONSTRAINTS

### 1. Synthetic Data Generation
*   **Library:** Use the `Faker` library for generating realistic synthetic data (Names, IPs, User Agents, etc.).
*   **Quality:** Ensure generated data matches the expected schema of the `raw-data` zone.

### 2. Storage Interaction
*   **Protocol:** Upload generated JSONs DIRECTLY to MinIO buckets.
*   **Library:** Use `boto3` client configured for MinIO.
    ```python
    s3_client = boto3.client('s3', endpoint_url='http://minio:9000', ...)
    s3_client.put_object(Bucket='raw-data', Key=..., Body=...)
    ```

### 3. API Design
*   **Endpoints:** Keep endpoints asynchronous (`async def`).
*   **Response:** Return strict confirmation of data upload (count/IDs), not the data itself if large.

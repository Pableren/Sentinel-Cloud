# SKILL: Apache Spark & PySpark

**Profile:** Senior Data Engineer
**Context:** This file governs all Spark infrastructure (`src/spark`) and Processing Jobs (`src/spark-jobs`).

## ⚠️ CRITICAL CONSTRAINTS

### 1. Spark Session Management
*   **Pattern:** Use a Singleton pattern. Do not create multiple sessions.
*   **Master URL:** Connect explicitly to `spark://spark-master:7077`.
*   **Config:**
    ```python
    spark = SparkSession.builder \
        .appName("JobName") \
        .master("spark://spark-master:7077") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .getOrCreate()
    ```

### 2. I/O Operations (Storage)
*   **Protocol:** ALWAYS use `s3a://` for MinIO interaction.
*   **Formats:** 
    *   **Read:** JSON (raw), Parquet (processed).
    *   **Write:** PREFER `parquet` or `delta`.
*   **Paths:**
    *   Raw: `s3a://raw-data/...`
    *   Processed: `s3a://processed-data/...`

### 3. Schema Enforcement
*   **Production Rule:** NEVER infer schema (`inferSchema=True`) in production jobs.
*   **Requirement:** Always adhere to a strict `StructType` definition.
    ```python
    schema = StructType([
        StructField("id", StringType(), False),
        StructField("timestamp", TimestampType(), True),
        # ...
    ])
    ```

### 4. Performance & Optimization
*   **Partitioning:** ENFORCE `partitionBy` on writes for large datasets (e.g., by date/year/month).
*   **Broadcasting:** Use `broadcast(df)` when joining small lookup tables.
*   **Anti-Pattern:** WARNING - Avoid `df.collect()` on large DataFrames. Use `df.show()` or write to storage.
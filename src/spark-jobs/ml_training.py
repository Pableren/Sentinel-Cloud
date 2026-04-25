from pyspark.sql import SparkSession
from pyspark.ml.feature import VectorAssembler
from pyspark.ml.regression import LinearRegression
from pyspark.ml import Pipeline

def init_spark():
    """Inicializa la sesión de Spark con las configuraciones necesarias para MinIO."""
    spark = SparkSession.builder \
        .appName("SentinelCloud_ML_Training") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.network.timeout", "600s") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()
    return spark

def train_model(spark):
    """Entrena el modelo de regresión lineal para predecir la latencia."""
    input_path = "s3a://processed-data/"
    output_path = "s3a://models/lr_latency_model/"

    print(f"--- Iniciando lectura de datos desde {input_path} ---")

    try:
        # Leer todos los Parquets dentro del bucket
        df = spark.read.option("recursiveFileLookup", "true").parquet(input_path)

        # Filtrar posibles valores nulos en las columnas de interés
        feature_cols = [
            "throughput_rpm", 
            "error_rate_percent", 
            "cpu_percent", 
            "memory_usage_percent", 
            "active_connections_count"
        ]
        label_col = "latency_p95_ms"
        
        df = df.dropna(subset=feature_cols + [label_col])
        df = df.sample(withReplacement=False, fraction=0.1, seed=42)

        # Asegurarse de que el df no esté vacío
        if df.rdd.isEmpty():
            print("--- No se encontraron datos procesados para entrenar. ---")
            return

        print("--- Preparando las características (Features) ---")
        assembler = VectorAssembler(
            inputCols=feature_cols,
            outputCol="features"
        )

        print("--- Configurando LinearRegression ---")
        lr = LinearRegression(featuresCol="features", labelCol=label_col)

        pipeline = Pipeline(stages=[assembler, lr])

        print("--- Entrenando el modelo ---")
        model = pipeline.fit(df)

        print(f"--- Guardando el modelo en {output_path} ---")
        model.write().overwrite().save(output_path)

        print("--- Proceso de entrenamiento finalizado exitosamente ---")
    
    except Exception as e:
        print(f"--- ERROR CRÍTICO EN EL ENTRENAMIENTO: {str(e)} ---")
        raise e

if __name__ == "__main__":
    spark = init_spark()
    train_model(spark)
    spark.stop()

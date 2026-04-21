from pyspark.sql import SparkSession
from pyspark.sql.functions import col, trim, upper, regexp_replace, when, date_format
from pyspark.sql.types import StructType, StructField, StringType, IntegerType, FloatType, TimestampType, DoubleType

def init_spark():
    """Inicializa la sesión de Spark con las configuraciones necesarias para MinIO."""
    spark = SparkSession.builder \
        .appName("SentinelCloud_ETL_RawToSilver") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.network.timeout", "600s") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()
    return spark

def get_schema():
    """Define el esquema esperado de los datos crudos."""
    return StructType([
        StructField("timestamp", StringType(), True), # Leemos como string inicialmente para parsear seguro
        StructField("instancia_id", StringType(), True),
        StructField("nombre_servicio", StringType(), True),
        StructField("protocolo", StringType(), True),
        StructField("throughput_rpm", DoubleType(), True), # Cambiado a Double para soportar 1529.0
        StructField("error_rate_percent", DoubleType(), True),
        StructField("latency_p95_ms", DoubleType(), True), # Cambiado a Double para soportar 91.0
        StructField("cpu_percent", StringType(), True), 
        StructField("memory_usage_percent", DoubleType(), True),
        StructField("active_connections_count", DoubleType(), True) # Cambiado a Double para soportar 149.9
    ])

def process_data(spark):
    """Lectura, limpieza y escritura de datos."""
    
    # 1. Definir rutas
    # Usamos s3a:// para conectar a MinIO
    input_path = "s3a://raw-data/*.json"
    output_path = "s3a://processed-data/"

    print(f"--- Iniciando lectura desde {input_path} ---")

    try:
        # 2. Leer JSONs crudos
        # Leemos todos los JSONs recursivamente si están en subdirectorios particionados
        # Spark suele manejar wildcards o recursividad automáticamente con option("recursiveFileLookup", "true") si fuera necesario
        # Pero s3a://bucket/*.json leerá la raíz, probar input_path = "s3a://raw-data/*/*/*/*.ndjson" si es particionado a 3 niveles
        # O simplemente "s3a://raw-data/" y dejar que Spark descubra particiones
        
        # Ajuste para leer recursivamente JSON/NDJSON de forma robusta
        # "path" debe ser la raiz del bucket para que la búsqueda recursiva funcione mejor
        raw_df = spark.read \
            .option("recursiveFileLookup", "true") \
            .schema(get_schema()) \
            .json("s3a://raw-data/")

        # Verificamos si hay datos antes de proceder
        if raw_df.rdd.isEmpty():
            print("--- No se encontraron datos en raw-data. Finalizando job. ---")
            return

        print(f"--- Datos crudos leídos. ---")

        # 3. Aplicar Limpieza (Silver Layer Logic)
        # Reglas de Negocio definidas en PROYECT_CONTEXT.md:
        cleaned_df = raw_df \
            .withColumn("instancia_id", trim(col("instancia_id"))) \
            .withColumn("protocolo", upper(trim(col("protocolo")))) \
            .withColumn("cpu_percent_clean", 
                        regexp_replace(col("cpu_percent"), ",", ".").cast(DoubleType())) \
            .withColumn("active_connections_count", 
                        when(col("active_connections_count").isNull(), 0).otherwise(col("active_connections_count"))) \
            .withColumn("timestamp", col("timestamp").cast(TimestampType())) \
            .filter((col("memory_usage_percent") >= 0) & (col("memory_usage_percent") <= 100)) \
            .drop("cpu_percent") \
            .withColumnRenamed("cpu_percent_clean", "cpu_percent")

        # Agregar columnas de partición (Year, Month, Day)
        cleaned_with_partitions = cleaned_df \
            .withColumn("year", date_format("timestamp", "yyyy")) \
            .withColumn("month", date_format("timestamp", "MM")) \
            .withColumn("day", date_format("timestamp", "dd"))

        # Reordenar columnas para que quede prolijo
        final_cols = ["timestamp", "instancia_id", "nombre_servicio", "protocolo", 
                      "throughput_rpm", "error_rate_percent", "latency_p95_ms", 
                      "cpu_percent", "memory_usage_percent", "active_connections_count",
                      "year", "month", "day"]
        
        final_df = cleaned_with_partitions.select(final_cols)

        print("--- Muestra de datos limpios: ---")
        final_df.show(5)

        # 4. Escribir a Silver Layer (Parquet) con Particionamiento Personalizado (Sin Hive Style year=...)
        # Estrategia: Obtener las particiones únicas y escribir en loop (no muy eficiente para volúmenes masivos pero cumple el requisito estricto de nombres de carpeta)
        # O, si asumimos batch diario (lo cual es el caso por Airflow), tomamos la fecha del primer registro.
        
        # Optimizacion: Usar forEachBatch no sirve aqui porque es batch standard.
        # Vamos a recolectar las fechas distintas (debería ser 1 o pocas) y escribir filtrando.
        
        distinct_dates = final_df.select("year", "month", "day").distinct().collect()
        
        for row in distinct_dates:
            y, m, d = row["year"], row["month"], row["day"]
            custom_output_path = f"{output_path}{y}/{m}/{d}/"
            
            print(f"--- Escribiendo partición {y}/{m}/{d} en {custom_output_path} ---")
            
            final_df.filter(
                (col("year") == y) & (col("month") == m) & (col("day") == d)
            ).drop("year", "month", "day") \
             .write.mode("append").parquet(custom_output_path)

        print("--- Proceso ETL finalizado exitosamente ---")
    
    except Exception as e:
        print(f"--- ERROR CRÍTICO EN EL JOB: {str(e)} ---")
        raise e

if __name__ == "__main__":
    spark = init_spark()
    process_data(spark)
    spark.stop()

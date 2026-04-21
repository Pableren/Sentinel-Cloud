from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import DoubleType

def iniciar_spark():
    """
    Inicializa la sesión de Spark usando Spark Connect (Modo Cliente Remoto).
    Esto permite que este script (que corre en Airflow) se comunique via API gRPC
    con el clúster Spark, sin necesitar binarios de Java/Hadoop locales.
    """
    spark = SparkSession.builder \
        .appName("ETL_Limpieza_Sentinel") \
        .remote("sc://spark-master:15002") \
        .getOrCreate()
    return spark

def limpiar_datos(df):
    """
    Aplica las reglas de negocio para limpiar los 'Datos Sucios' inyectados.
    Explicación PySpark: A diferencia de Pandas, aquí no modificamos los datos en memoria inmediatamente.
    Estamos construyendo un 'Plan de Ejecución' (Lazy Evaluation). Spark optimizará todas estas
    operaciones antes de ejecutar nada.
    """
    
    # 1. Limpieza de 'instancia_id': Eliminar espacios en blanco (trim)
    # df.withColumn('nombre_columna', transformación) crea una nueva versión del DataFrame con esa columna modificada.
    df_clean = df.withColumn("instancia_id", F.trim(F.col("instancia_id")))

    # 2. Limpieza de 'protocolo': Estandarizar a mayúsculas
    # Se normaliza todo a string mayúscula.
    df_clean = df_clean.withColumn("protocolo", 
        F.when(F.col("protocolo").isNotNull(), 
             F.upper(F.col("protocolo"))
        ).otherwise("UNKNOWN")
    )

    # 3. Limpieza de 'cpu_percent':
    # El generador inyecta strings con coma "25,5". Necesitamos reemplazar ',' por '.' y castear a Double.
    df_clean = df_clean.withColumn("cpu_percent_clean", 
        F.regexp_replace(F.col("cpu_percent"), ",", ".").cast(DoubleType())
    )

    # 4. Filtrado de valores imposibles en 'memory_usage_percent'
    # Valores < 0 o > 100 son errores de sensor.
    # En Spark usamos .filter() o .where()
    df_clean = df_clean.filter(
        (F.col("memory_usage_percent") >= 0) & 
        (F.col("memory_usage_percent") <= 100)
    )

    # 5. Imputación de nulos en 'active_connections_count' (llenar con 0)
    df_clean = df_clean.fillna({"active_connections_count": 0})

    return df_clean

import sys

def main():
    spark = iniciar_spark()

    # --- 1. LECTURA (EXTRACT) ---
    # Capturamos la fecha del argumento (YYYY-MM-DD) enviado por Airflow
    # Si no hay argumento, usamos una fecha default para pruebas manuales
    target_date = sys.argv[1] if len(sys.argv) > 1 else "2025-12-21"
    
    # Convertimos YYYY-MM-DD a formato de ruta YYYY/MM/DD
    execution_date_path = target_date.replace("-", "/")
    
    # Ruta de entrada NDJSON particionada
    # Usamos búsqueda recursiva (**) para capturar los archivos ndjson dentro de la carpeta del día
    # Ejemplo: file:///data/raw-data/2025/12/21/*.ndjson
    
    # Nota: Spark supporta globbing.
    input_path = f"file:///data/raw-data/{execution_date_path}/*.ndjson"

    print(f"--- Iniciando Lectura para fecha: {target_date} ---")
    print(f"--- Ruta de búsqueda: {input_path} ---")
    
    try:
        # read.json maneja NDJSON automáticamente si detecta múltiples líneas JSON
        df_raw = spark.read.json(input_path)
    except Exception as e:
        print(f"Error crítico leyendo datos: {e}")
        # Es importante terminar con error para que Airflow sepa que falló
        sys.exit(1)

    print("--- Esquema Inferido (Raw) ---")
    df_raw.printSchema()

    # --- 2. TRANSFORMACIÓN (TRANSFORM) ---
    df_processed = limpiar_datos(df_raw)

    print("--- Datos Procesados (Preview) ---")
    # show() ejecuta el plan (Acción) y trae datos al driver para mostrarlos.
    df_processed.show(5)

    # --- 3. ESCRITURA (LOAD) ---
    # Guardamos en formato Parquet (columnar, comprimido).
    # mode("overwrite") sobrescribe si ya existe.
    output_path = "file:///data/processed-data/clean_metrics"
    
    print(f"--- Guardando en Parquet: {output_path} ---")
    df_processed.write.mode("overwrite").parquet(output_path)
    
    print("--- ETL Finalizado con Éxito ---")
    spark.stop()

if __name__ == "__main__":
    main()

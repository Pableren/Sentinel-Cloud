# Spark Explained: Arquitectura y Optimización en Sentinel Cloud

Esta guía detalla los principios de funcionamiento de Apache Spark aplicados en el ecosistema Sentinel Cloud, desde el procesamiento masivo (ETL) hasta la operacionalización de modelos (MLOps).

## Índice
1. [Arquitectura Distribuida: Driver vs Workers](#sección-1---arquitectura-distribuida)
2. [Lazy Evaluation y el Grafo Lógico (DAG)](#sección-2---lazy-evaluation-y-el-dag)
3. [Modo Económico y Optimización de Recursos](#sección-3---modo-económico-y-optimización-de-recursos)

---

## Sección 1 - Arquitectura Distribuida

En Sentinel Cloud, Spark opera bajo un modelo maestro-esclavo distribuido, incluso cuando se ejecuta dentro de contenedores Docker.

### El Rol del Driver y los Workers
- **Driver**: Es el proceso de Python (ejecutado en el contenedor `spark_master` o `airflow_scheduler`) que contiene el `main` de nuestra aplicación. Su función es analizar el código, crear el plan de ejecución y solicitar recursos al Master.
- **Workers**: Son los contenedores Docker (`spark_worker`) que ejecutan las tareas reales. Reciben instrucciones del Driver y procesan los fragmentos de datos (particiones) en paralelo.

### Inicialización de la SparkSession
En el script de entrenamiento (`ml_training.py`), el Driver inicia la comunicación con el cluster mediante la `SparkSession`:

```python
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
```

Al ejecutar este bloque, el Driver se registra ante el Master y prepara el entorno para el acceso a MinIO a través del protocolo S3A.

---

## Sección 2 - Lazy Evaluation y el DAG

Apache Spark destaca por su **Lazy Evaluation** (Evaluación Perezosa). Esto significa que Spark no ejecuta las transformaciones inmediatamente; en su lugar, construye un grafo lógico de ejecución llamado **DAG** (Directed Acyclic Graph).

### Transformaciones (Construcción del DAG)
En `etl_processing.py`, definimos cómo queremos que se limpien los datos. Líneas como estas **NO** mueven datos en el momento de ser escritas:

```python
# 1. Limpieza de espacios en IDs
.withColumn("instancia_id", trim(col("instancia_id")))

# 2. Normalización de protocolos a mayúsculas
.withColumn("protocolo", upper(trim(col("protocolo"))))

# 3. Conversión de formato decimal (coma a punto) y casteo de tipo
.withColumn("cpu_percent_clean", 
            regexp_replace(col("cpu_percent"), ",", ".").cast(DoubleType()))
```

Estas instrucciones son meras "promesas". Spark las acumula en el DAG para poder optimizarlas (por ejemplo, combinando filtros) antes de la ejecución física.

### Acciones (Ejecución del DAG)
El DAG solo se "despierta" y se envía a los Workers cuando se invoca una **Acción**. En nuestro job ETL, la acción final que desencadena todo el procesamiento es:

```python
.write.mode("append").parquet(custom_output_path)
```

Al llegar a este punto, Spark optimiza el plan, divide los archivos en particiones y lanza las tareas distribuidas hacia los Workers para persistir los resultados en MinIO.

---

## Sección 3 - Modo Económico y Optimización de Recursos

Dada la restricción de recursos (Ryzen 5 de 6 nucleos y 12 hilos) y la naturaleza de nuestras tareas, hemos implementado estrategias de optimización para reducir la huella de memoria y CPU.

### Optimización en Inferencia (MLOps)
En la API de predicción (`app.py`), utilizamos una configuración minimalista de Spark:

```python
spark = SparkSession.builder \
    .appName("MLOpsInference") \
    .master("local[1]") \
    .config("spark.ui.enabled", "false") \
    .config("spark.executor.instances", "1") \
    .config("spark.driver.memory", "512m") \
    # ...
```

- **`.master("local[1]")`**: Al ser una tarea de baja latencia que procesa un solo registro por petición, forzamos a Spark a correr en un solo hilo local. Esto elimina el overhead de red y coordinación entre procesos distribuido.
- **`spark.ui.enabled="false"`**: Deshabilitar la interfaz web de Spark libera memoria y ciclos de CPU que de otro modo se gastarían en telemetría innecesaria para un servicio de inferencia.
- **`spark.driver.memory="512m"`**: Ajustamos la JVM al mínimo operativo para que conviva con otros servicios sin disparar el OOM (Out Of Memory).

### Optimización en Entrenamiento
Para acelerar el ciclo de desarrollo en `ml_training.py`, aplicamos una reducción de volumen:

```python
df = df.sample(withReplacement=False, fraction=0.1, seed=42)
```

Esta técnica de **muestreo (sampling)** nos permite entrenar el modelo de Regresión Lineal sobre el 10% de los datos. Esto reduce drásticamente el tiempo de CPU y uso de disco, manteniendo una representatividad estadística suficiente para que el modelo aprenda las tendencias de latencia sin necesidad de procesar millones de registros en cada prueba.

---

## Sección 4 - Feature Engineering: El VectorAssembler

En Spark MLlib, los algoritmos de Machine Learning (como la Regresión Lineal) no operan directamente sobre múltiples columnas independientes. Requieren que todas las variables de entrada (*features*) estén consolidadas en una sola columna de tipo **Vector**.

### ¿Por qué colapsar los datos?
Spark está optimizado para realizar operaciones de álgebra lineal masivas en la JVM. Al agrupar las columnas en un solo vector, Spark puede pasar este objeto a sus rutinas matemáticas internas de forma mucho más eficiente que si tuviera que coordinar múltiples punteros a diferentes columnas de un DataFrame.

En `ml_training.py`, utilizamos el `VectorAssembler` para este propósito:

```python
assembler = VectorAssembler(
    inputCols=[
        "throughput_rpm", 
        "error_rate_percent", 
        "cpu_percent", 
        "memory_usage_percent", 
        "active_connections_count"
    ],
    outputCol="features"
)
```

Este componente actúa como una transformación en nuestro pipeline, preparando los datos para que el modelo pueda "entenderlos" como una matriz de características.

---

## Sección 5 - Entrenamiento y Persistencia

### LinearRegression y Predicción de Latencia
El corazón de nuestra lógica predictiva es un modelo de **Regresión Lineal**. Su objetivo en Sentinel Cloud es encontrar la relación matemática entre el estado de la infraestructura (CPU, Memoria, Conexiones) y la latencia resultante (`latency_p95_ms`).

### Persistencia del Modelo en el Data Lake
A diferencia de otros frameworks que guardan un archivo binario único (como un `.pkl` de Scikit-Learn), Spark guarda los modelos como **directorios estructurados**. Al ejecutar:

```python
model.write().overwrite().save("s3a://models/lr_latency_model/")
```

Spark crea una carpeta en MinIO que contiene metadatos, etapas del pipeline y los pesos del modelo. Esto permite que el modelo sea **recuperable de forma distribuida**: diferentes Workers podrían cargar partes del modelo en paralelo si fuera necesario.

### Carga para Inferencia (MLOps)
En la API de inferencia (`app.py`), recuperamos este estado guardado al arrancar la aplicación:

```python
ml_models["lr_model"] = PipelineModel.load("s3a://models/lr_latency_model/")
```

Esto garantiza que la API use exactamente el mismo pipeline (incluyendo el `VectorAssembler`) que se definió durante el entrenamiento.

---

## Sección 6 - Storage & Lakehouse: ¿Por qué Parquet?

En Sentinel Cloud, hemos pasado de **NDJSON** (Bronze Layer) a **Parquet** (Silver Layer). Esta es una transición crítica de una orientación a filas a una **orientación a columnas**.

### Beneficios Técnicos de Parquet
1. **Almacenamiento Columnar**: Si nuestro modelo de ML solo necesita 5 columnas de las 20 disponibles, Spark **solo lee esas 5 columnas** del disco. En un JSON, Spark tendría que leer y parsear el archivo completo, desperdiciando I/O.
2. **Compresión Extrema**: Parquet aplica algoritmos de compresión por columna (como Snappy). Dado que los datos en una misma columna suelen ser del mismo tipo y rango, la compresión es órdenes de magnitud más eficiente que en un archivo de texto.

### Partitioning y Partition Pruning
Organizamos nuestros datos en MinIO siguiendo una estructura de carpetas por fecha (`YYYY/MM/DD`). Esto habilita el **Partition Pruning**:

Si un Job de Spark busca datos de "ayer", Spark simplemente ignora todas las carpetas de otros años o meses. No llega siquiera a abrir los archivos. Esto reduce el estrés en el procesador Ryzen y permite que el sistema escale a medida que el Data Lake acumula años de telemetría.

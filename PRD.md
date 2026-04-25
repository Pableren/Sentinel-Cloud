# PRD — Sentinel Cloud: Plataforma de Big Data & MLOps

**Versión:** 1.0  
**Estado:** En desarrollo  
**Propietario:** Data Engineering Team

---

## 1. Propósito y Visión del Producto

**Sentinel Cloud** es una plataforma de Big Data diseñada para simular un entorno de ingeniería de datos de producción completo, de extremo a extremo.

El sistema simula la operación de un MSP (Managed Service Provider) que gestiona infraestructura para clientes de la industria fintech. El objetivo es demostrar el dominio del ciclo de vida completo del dato: **ingesta → procesamiento → almacenamiento → entrenamiento de modelo → predicción en batch**, con las tecnologías del ecosistema Big Data moderno.

> **Alcance:** Sistema local containerizado con Docker, reproducible en cualquier máquina de desarrollo. No está diseñado para producción cloud, sino para demostrar patrones y competencias de Data Engineering y MLOps.

---

## 2. Contexto del Negocio

Sentinel Cloud monitoriza la salud de la infraestructura de sus clientes (servidores, servicios, bases de datos). Para ello registra métricas de observabilidad continuas:

- **Throughput** (peticiones por minuto)
- **Latencia P95** (ms)
- **Tasa de error** (%)
- **Uso de CPU y Memoria** (%)
- **Conexiones activas**
- **Tráfico entre servicios** (llamadas origen → destino, protocolo, bytes, status code)

El sistema ingiere esta telemetría, la limpia, y entrena un modelo de regresión para predecir la latencia futura de los servicios en función de las métricas actuales.

### Clientes y servicios simulados

| Cliente | Industria | Instancias |
|---|---|---|
| Stripe | Fintech | 4 |
| Chime | Fintech | 4 |
| Plaid | Fintech | 4 |
| Coinbase | Fintech | 4 |
| BierzoSEO | E-commerce | 4 |

**20 instancias totales** que reproducen servicios reales: API Gateway, Load Balancer, Lambda, ECS, EC2, RDS, DynamoDB, ElastiCache, S3, SageMaker, CloudWatch, IAM.

---

## 3. Stack Tecnológico

| Componente | Tecnología | Rol |
|---|---|---|
| **Data Lake** | MinIO (S3-compatible) | Almacenamiento de datos crudos y procesados |
| **Ingesta / Simulador** | FastAPI + Python | Genera y deposita datos sintéticos en el Data Lake |
| **Procesamiento** | Apache Spark 3.5 (PySpark) | ETL batch y entrenamiento del modelo |
| **Orquestación** | Apache Airflow 2.7 | Detección de eventos y disparo de jobs Spark |
| **Inferencia** | FastAPI (MLOps API) | Expone predicciones del modelo entrenado |
| **Containerización** | Docker + Docker Compose | Despliegue local reproducible |

---

## 4. Arquitectura y Flujo de Datos

```
[python-api]  →  MinIO (raw-data)  →  [Airflow Trigger 1]
                                              ↓
                                     Spark ETL Job
                                              ↓
                              MinIO (processed-data/Parquet)
                                              ↓
                                     [Airflow Trigger 2]
                                              ↓
                                  Spark MLlib Training Job
                                              ↓
                               MinIO (models/lr_model)
                                              ↓
                                  MLOps API: POST /predict
                                              ↓
                               Predicciones de Latencia (batch)
```

### 4.1 Zonas del Data Lake (MinIO)

| Bucket | Contenido | Formato |
|---|---|---|
| `raw-data` | Telemetría cruda generada por python-api | NDJSON, particionado `YYYY/MM/DD/` |
| `processed-data` | Datos limpios y normalizados (Silver Layer) | Parquet, particionado `YYYY/MM/DD/` |
| `models` | Modelos ML entrenados con Spark MLlib | Formato nativo Spark ML Pipeline |

---

## 5. Componentes Detallados

### 5.1 API de Ingesta de Datos (`src/python-api`)

Simula la fuente de datos externa. En un entorno real, esta capa sería reemplazada por un sistema de telemetría como Datadog, Prometheus o un agente de logs.

**Responsabilidades:**
- Generar datos sintéticos de observabilidad mediante `ObservabilityGenerator`
- Inyectar **datos sucios intencionalmente** para que el ETL tenga trabajo real que hacer:
  - `cpu_percent`: 25% de registros con coma como separador decimal (`"25,4"`)
  - `memory_usage_percent`: 5% de registros con valores imposibles (`-10.0`, `105.0`)
  - `active_connections_count`: 5% de registros con `NaN`
  - `instancia_id`: 20% de registros con espacios en blanco extra
- Subir los datos al bucket `raw-data` de MinIO en formato NDJSON

**Endpoint principal:**
```
POST /simulation/historical
Body: { "start_date": "YYYY-MM-DD", "end_date": "YYYY-MM-DD", "frequency_seconds": 600 }
```

### 5.2 Procesamiento ETL con Spark (`src/spark-jobs`)

Job de limpieza que transforma los datos crudos en datos confiables para el modelo.

**Reglas de limpieza aplicadas:**
1. `instancia_id`: eliminar espacios en blanco (`.trim()`)
2. `protocolo`: estandarizar a mayúsculas (`.upper()`)
3. `cpu_percent`: reemplazar `,` por `.` y castear a `DoubleType`
4. `memory_usage_percent`: filtrar registros fuera del rango `[0, 100]`
5. `active_connections_count`: imputar `NaN` con `0`

**Salida:** Parquet particionado por `YYYY/MM/DD/` en `processed-data`.

### 5.3 Entrenamiento del Modelo con Spark MLlib (`src/spark-jobs`)

Job de entrenamiento que consume los datos limpios y produce un modelo de regresión lineal.

**Objetivo del modelo:** Predecir `latency_p95_ms` a partir de las métricas de rendimiento actuales.

**Features de entrada:**
- `throughput_rpm`
- `error_rate_percent`
- `cpu_percent`
- `memory_usage_percent`
- `active_connections_count`

**Target:** `latency_p95_ms`

**Diseño simplificado (intencional):**
- El modelo es un `LinearRegression` de Spark MLlib
- Se limita el número de filas de entrenamiento (muestra controlada del Parquet)
- No se implementa feature engineering avanzado
- No hay validación cruzada ni búsqueda de hiperparámetros
- El propósito es demostrar que **Spark puede entrenar un modelo en batch** sobre datos del Data Lake y **realizar predicciones en batch** sobre nuevas particiones de datos

**Salida:** Modelo serializado en `s3a://models/lr_latency_model/`

### 5.4 Orquestación con Airflow (`src/airflow/dags`)

Airflow actúa exclusivamente como **director de eventos**, no procesa datos directamente.

#### DAG 1 — Trigger de Ingesta: `sentinel_etl_pipeline`

**Propósito:** Demostrar que Airflow puede detectar automáticamente la llegada de nuevos datos y disparar el procesamiento.

**Flujo:**
```
S3KeySensor (espera *.ndjson en raw-data) >> SparkSubmitOperator (ejecuta etl_processing.py)
```

**Comportamiento:**
- Sensor revisa MinIO cada 2 minutos
- En cuanto detecta un archivo NDJSON en el path del día actual, dispara el job ETL de Spark
- Resultado validado: ✅ el trigger funciona correctamente

#### DAG 2 — Trigger de Entrenamiento: `sentinel_training_pipeline` *(a implementar)*

**Propósito:** Demostrar que, una vez que los datos procesados están listos en `processed-data`, Airflow puede detectarlo y disparar el entrenamiento del modelo automáticamente.

**Flujo:**
```
S3KeySensor (espera *.parquet en processed-data) >> SparkSubmitOperator (ejecuta ml_training.py)
```

**Comportamiento esperado:**
- Sensor detecta la presencia de Parquet en `processed-data/YYYY/MM/DD/`
- Dispara el job de entrenamiento de Spark MLlib
- El modelo entrenado queda disponible en `s3a://models/` para la API de inferencia

### 5.5 API de Inferencia MLOps (`src/mlops`)

Servicio FastAPI que carga el modelo entrenado desde MinIO y expone un endpoint REST para predicciones.

**Endpoint:**
```
POST /predict
Body: { "throughput_rpm": 3200, "error_rate_percent": 0.02, "cpu_percent": 35.5,
        "memory_usage_percent": 62.1, "active_connections_count": 312 }
Response: { "predicted_latency_p95_ms": 142.7, "model_version": "v1.0" }
```

**Predicción en batch:** El endpoint también puede recibir múltiples registros para predicción en lote, simulando la inferencia sobre una partición completa de datos del día.

---

## 6. Criterios de Éxito (Definition of Done)

El sistema está completo cuando se puede ejecutar el siguiente flujo de extremo a extremo **sin intervención manual**:

1. ✅ `POST /simulation/historical` deposita datos NDJSON en MinIO `raw-data`
2. ✅ Airflow DAG 1 detecta los datos y dispara el job ETL de Spark automáticamente
3. ✅ Spark limpia y escribe Parquet en `processed-data`
4. ⬜ Airflow DAG 2 detecta el Parquet y dispara el job de entrenamiento MLlib
5. ⬜ Spark entrena el modelo de regresión lineal y lo guarda en `models`
6. ⬜ MLOps API carga el modelo y devuelve predicciones correctas vía `POST /predict`

---

## 7. Fuera de Alcance

Los siguientes elementos están explícitamente **fuera del alcance** de este proyecto:

- Streaming en tiempo real (Kafka, Spark Streaming)
- Consultas SQL ad-hoc sobre el Data Lake (Trino/Presto eliminado del stack)
- Dashboard de monitoreo de métricas en tiempo real
- Autenticación y autorización en las APIs
- Despliegue en cloud (AWS, GCP, Azure)
- Alta disponibilidad o tolerancia a fallos de producción
- Versionado avanzado de modelos (MLflow)
- Validación de calidad de datos (Great Expectations / Deequ)

---

## 8. Estructura del Repositorio

```
DataEngineerP/
├── docker-compose.yml          # Stack completo: MinIO, Spark, Airflow, APIs
├── Makefile                    # Comandos de ciclo de vida (up, down, restart-*)
├── PRD.md                      # Este documento
├── README.md                   # Descripción general del proyecto
├── src/
│   ├── python-api/             # API generadora de datos sintéticos
│   │   ├── main.py             # FastAPI app + explorador web MinIO
│   │   ├── data_generator.py   # Motor de generación de telemetría sintética
│   │   ├── minio_client.py     # Cliente para subir/bajar archivos de MinIO
│   │   └── config_data.py      # Datos semilla: clientes, instancias, rutas
│   ├── spark-jobs/             # Jobs PySpark ETL y ML
│   │   ├── etl_processing.py   # Job ETL: raw-data → processed-data (s3a://)
│   │   ├── etl_limpieza.py     # Job ETL alternativo: Spark Connect (gRPC)
│   │   └── ml_training.py      # [PENDIENTE] Job entrenamiento LinearRegression
│   ├── airflow/                # Configuración y DAGs de Airflow
│   │   ├── Dockerfile          # Imagen con PySpark + providers instalados
│   │   └── dags/
│   │       ├── sentinel_pipeline.py        # DAG 1: Sensor ingesta → ETL Spark
│   │       └── sentinel_training_pipeline.py  # [PENDIENTE] DAG 2: Sensor processed → Training
│   ├── mlops/                  # API de inferencia del modelo
│   │   └── app.py              # FastAPI: carga modelo desde MinIO, POST /predict
│   └── skills/                 # Constraints arquitectónicas para agentes IA
│       ├── spark/SKILL.md
│       ├── airflow/SKILL.md
│       ├── mlops/SKILL.md
│       └── python-api/SKILL.md
└── docs/                       # Documentación adicional
    └── PRD_Data_Engineer.md    # PRD técnico de referencia del stack
```

---

## 9. Notas de Implementación

- **Credenciales:** Las credenciales de MinIO (`minioadmin/minioadmin`) y la Fernet Key de Airflow son solo para desarrollo local. Nunca usar en producción.
- **SQLite en Airflow:** Se usa `SequentialExecutor + SQLite` para máxima simplicidad. Implica que solo se ejecuta una tarea a la vez — aceptable para este proyecto demostrativo.
- **Spark Connect:** `etl_limpieza.py` usa el modo cliente gRPC (`.remote("sc://spark-master:15002")`), lo que permite ejecutar el script desde el contenedor de Airflow sin necesitar Java/Hadoop instalados localmente.
- **Modelo simplificado:** El `LinearRegression` de MLlib se entrena con un subconjunto acotado de filas del Parquet. El objetivo no es la precisión del modelo sino demostrar el pipeline completo de entrenamiento y predicción batch con Spark.

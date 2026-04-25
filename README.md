# Sentinel Cloud - Data Engineering & MLOps

![Logo](resources/images/logo_sentinel.png)

## 🚀 Proyecto Data Engineer & MLOps

**Sentinel Cloud** líder en la industria de las empresas MSP (Managed Service Provider), compitiendo al nivel mundial con grandes empresas como Rackspace Technology o SADA Systems.

Este proyecto implementa una arquitectura moderna de **Ingeniería de Datos y MLOps**, diseñada para la ingesta, procesamiento masivo y operacionalización de modelos de Machine Learning utilizando tecnologías Big Data.

---

## 📋 Tabla de Contenidos
1. [Contexto y Caso de Uso](#contexto-y-caso-de-uso)
2. [Stack Tecnológico](#stack-tecnológico)
3. [Arquitectura del Sistema](#arquitectura-del-sistema)
4. [Instalación y Requisitos](#instalación-y-requisitos)

---

## 🌐 Contexto y Caso de Uso

En el ecosistema crítico de Sentinel Cloud, donde la tolerancia a fallos es nula, evolucionamos de una postura reactiva a una de **resiliencia proactiva**.

El sistema tiene dos objetivos principales:
1.  **Data Engineering (Big Data):** Ingesta y procesamiento masivo de telemetría (Throughput, Latencia, Errores) para visibilizar la salud de la infraestructura.
2.  **MLOps (Machine Learning Operations):** Entrenar modelos predictivos con Spark MLlib y **exponerlos en producción** mediante una API dedicada para realizar inferencia en tiempo real sobre anomalías o latencia futura.

---

## 🛠️ Stack Tecnológico

El proyecto se despliega localmente utilizando **Docker** para simular un entorno de producción completo.

### 1. Ingesta y Data Lake (MinIO)
*   **Rol:** Base de la arquitectura "Lakehouse".
*   **Función:**
    *   `raw-data`: Almacena la data cruda generada por los sistemas.
    *   `processed-data`: Almacena datos limpios en formato **Parquet**.
    *   `models`: Repositorio de modelos entrenados (Model Registry).

### 2. Procesamiento Distribuido (Apache Spark)
*   **Rol:** Motor ETL y Entrenamiento ML.
*   **Función:**
    *   **ETL:** Limpieza, transformación y enriquecimiento de datos a gran escala.
    *   **Training:** Entrenamiento de modelos de Machine Learning (ej. Regresión Lineal) y guardado en el Data Lake.

### 3. Orquestación (Apache Airflow)
*   **Rol:** Director del Pipeline.
*   **Función:** Programa y supervisa los flujos de trabajo (DAGs):
    *   Detección de nuevos datos.
    *   Ejecución de jobs ETL en Spark.
    *   Reentrenamiento automático de modelos.

### 4. MLOps & Inferencia Real-Time (FastAPI)
*   **Rol:** Servicio de Predicción (Model Serving).
*   **Función:**
    *   Carga el modelo entrenado desde MinIO al arrancar.
    *   Expone un endpoint REST (`POST /predict`) para recibir datos en tiempo real y devolver predicciones inmediatas.
    *   Simula el despliegue productivo de un modelo de ML.

---

## 🏗️ Arquitectura del Sistema

El flujo de datos sigue un patrón ETL + ML:

1.  **Generación:** La API simuladora (`fastapi_data_generator`) envía telemetría a MinIO (`raw-data`).
2.  **Orquestación:** Airflow detecta los datos y dispara un job de Spark.
3.  **Procesamiento:** Spark lee, limpia y transforma los datos, guardando el resultado en `processed-data`.
4.  **Training:** Spark entrena un modelo con los datos históricos y lo guarda en `models`.
5.  **Serving:** El servicio **MLOps** (`model-inference-api`) carga el nuevo modelo y queda listo para recibir peticiones de predicción en tiempo real.

---

## 💻 Instalación y Requisitos

### Prerrequisitos
- **Docker** y **Docker Compose**
- **Python 3.12+** (para scripts locales)

### Ejecución

1. **Iniciar todos los servicios:**
   ```bash
   docker compose up -d --build
   ```

2. **Acceder a las Interfaces de Usuario:**
   - **MinIO Console:** [http://localhost:9001](http://localhost:9001) (User/Pass: `minioadmin` / `minioadmin`)
   - **Airflow Web UI:** [http://localhost:8081](http://localhost:8081) (User/Pass: `admin` / `admin`)
   - **Spark Master UI:** [http://localhost:18080](http://localhost:18080)
   - **Inference API Docs (Swagger):** [http://localhost:8001/docs](http://localhost:8001/docs)

3. **Ejecutar el Pipeline en Airflow:**
   Ingresa a Airflow, busca el DAG `sentinel_training_pipeline`, quita la pausa (Unpause) y presiona "Trigger DAG". Esto iniciará el entrenamiento del modelo Spark y lo guardará en MinIO.

4. **Validar el Modelo en Producción (Inferencia en Tiempo Real):**
   Una vez que el modelo esté entrenado y el servicio `model-inference-api` esté corriendo, puedes simular una petición de inferencia:
   ```bash
   curl -X 'POST' 'http://localhost:8001/predict' \
     -H 'Content-Type: application/json' \
     -d '{"throughput_rpm": 3000, "error_rate_percent": 0.05, "cpu_percent": 45.0, "memory_usage_percent": 70.0, "active_connections_count": 150}'
   ```
   La API devolverá un JSON con la latencia predecida (`predicted_latency_p95_ms`), indicando que el modelo de Machine Learning fue cargado y ejecutado exitosamente.

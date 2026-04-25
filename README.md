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
(Instrucciones pendientes de actualización tras la reestructuración de servicios)

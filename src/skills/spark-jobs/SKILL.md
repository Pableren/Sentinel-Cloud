# Habilidad: Spark Jobs (ETL & ML)

## 📝 Descripción
Esta habilidad se centra en el desarrollo de la lógica de negocio mediante scripts de PySpark. Aquí reside la inteligencia del procesamiento de datos y el entrenamiento de modelos.

## 🎯 Objetivos
*   Crear pipelines ETL eficientes y escalables.
*   Implementar modelos de Machine Learning con Spark MLlib.
*   Escribir código modular y testeable.

## 🛠️ Tareas Comunes
1.  **ETL (Extract, Transform, Load):**
    *   Leer datos crudos (JSON) desde MinIO (`raw-data`).
    *   Limpiar, validar y transformar datos.
    *   Escribir datos procesados (Parquet) en MinIO (`processed-data`).
2.  **Machine Learning:**
    *   Preprocesamiento de features (VectorAssembler, Scaling).
    *   Entrenamiento de modelos (ej. Regresión Lineal).
    *   Guardado de modelos pipeline en MinIO (`models`).
3.  **Optimización:**
    *   Uso correcto de particiones.
    *   Evitar shuffles innecesarios.
    *   Uso de caché/persistencia cuando sea apropiado.

## 📦 Estructura de Archivos Relacionada
*   `src/spark-jobs/`: Directorio donde residen los scripts `.py`.
    *   `etl/`: Scripts de limpieza y transformación.
    *   `ml/`: Scripts de entrenamiento e inferencia batch.

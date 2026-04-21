from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta
import os

# --- Default Arguments ---
default_args = {
    'owner': 'SentinelDataEngineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# --- DAG Definition ---
with DAG(
    'sentinel_etl_pipeline',
    default_args=default_args,
    description='Pipeline ETL diario: Sensor S3 -> Spark Processing',
    schedule_interval='@daily',
    catchup=False,
    tags=['spark', 'etl', 'minio']
) as dag:

    # 1. Sensor: Detectar archivo en MinIO (Raw Data)
    # Patrón esperado: year=YYYY/month=MM/day=DD/*.ndjson
    # Usamos s3_key con wildecards. El bucket se pasa en bucket_key o bucket_name dependiendo de la versión,
    # pero el standard moderno es s3://bucket/key o bucket_key relative to connection default bucket.
    # Asumimos conexión 'aws_default' apuntando a MinIO.
    
    wait_for_raw_data = S3KeySensor(
        task_id='wait_for_raw_data',
        bucket_key='s3://raw-data/{{ execution_date.year }}/{{ execution_date.strftime("%m") }}/{{ execution_date.strftime("%d") }}/*.ndjson',
        wildcard_match=True,
        aws_conn_id='minio_conn', # Usaremos una conexión dedicada para MinIO
        timeout=18 * 60 * 60, # 18 horas de timeout
        poke_interval=120,    # Verificar cada 2 minutos
        mode='poke'
    )

    # 2. Spark Operator: Procesar datos con Spark
    # Se conecta al cluster Spark Master definido en la conexión 'spark_default'
    # El script debe estar disponible en el contenedor de Airflow o en un volumen compartido.
    # En nuestro docker-compose, spark-jobs está montado en /app/jobs tanto en Spark como en Airflow.
    
    process_data = SparkSubmitOperator(
        task_id='process_data_spark',
        application='/app/jobs/etl_processing.py',
        conn_id='spark_default',
        conf={
            "spark.hadoop.fs.s3a.endpoint": "http://minio:9000",
            "spark.hadoop.fs.s3a.access.key": "minioadmin",
            "spark.hadoop.fs.s3a.secret.key": "minioadmin",
            "spark.hadoop.fs.s3a.path.style.access": "true",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.hadoop.fs.s3a.connection.ssl.enabled": "false"
        },
        packages="org.apache.hadoop:hadoop-aws:3.3.4",
        verbose=True
    )

    # --- Dependencias ---
    wait_for_raw_data >> process_data

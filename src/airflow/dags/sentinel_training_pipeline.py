from airflow import DAG
from airflow.providers.amazon.aws.sensors.s3 import S3KeySensor
from airflow.providers.apache.spark.operators.spark_submit import SparkSubmitOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'SentinelDataEngineer',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

with DAG(
    'sentinel_training_pipeline',
    default_args=default_args,
    description='Pipeline de ML: Sensor S3 -> Spark MLlib',
    schedule_interval='@weekly',
    catchup=False,
    tags=['spark', 'ml', 'minio']
) as dag:

    wait_for_processed_data = S3KeySensor(
        task_id='wait_for_processed_data',
        bucket_key='s3://processed-data/*/*/*/*.parquet',
        wildcard_match=True,
        aws_conn_id='minio_conn',
        timeout=18 * 60 * 60,
        poke_interval=120,
        mode='poke'
    )

    train_ml_model = SparkSubmitOperator(
        task_id='train_ml_model',
        application='/app/jobs/ml_training.py',
        conn_id='spark_default',
        conf={
            "spark.hadoop.fs.s3a.endpoint": "http://minio:9000",
            "spark.hadoop.fs.s3a.access.key": "minioadmin",
            "spark.hadoop.fs.s3a.secret.key": "minioadmin",
            "spark.hadoop.fs.s3a.path.style.access": "true",
            "spark.hadoop.fs.s3a.impl": "org.apache.hadoop.fs.s3a.S3AFileSystem",
            "spark.hadoop.fs.s3a.connection.ssl.enabled": "false"
        },
        packages="org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262",
        verbose=True
    )

    wait_for_processed_data >> train_ml_model

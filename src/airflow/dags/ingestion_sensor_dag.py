from datetime import datetime, timedelta
from airflow import DAG
from airflow.sensors.python import PythonSensor
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import os
import glob

default_args = {
    'owner': 'data-engineer',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def check_for_new_files():
    """
    Verifica si existen archivos NDJSON en el bucket 'raw-data' de MinIO.
    Busca recursivamente en la estructura de directorios YYYY/MM/DD/.
    """
    # Usamos búsqueda recursiva (**) para encontrar archivos en cualquier subcarpeta
    path = '/data/raw-data/**/*.ndjson'
    files = glob.glob(path, recursive=True)
    
    if files:
        print(f"¡Archivos NDJSON detectados! Cantidad: {len(files)}")
        print(f"Ejemplo: {files[0]}")
        return True
    
    print("Esperando archivos NDJSON en raw-data/...")
    return False

with DAG(
    'procesamiento_pasivo_sensor',
    default_args=default_args,
    description='Pipeline que espera pasivamente archivos en Landing Zone',
    schedule_interval=timedelta(minutes=5), # Verifica cada 5 minutos si hay archivos
    start_date=datetime(2023, 1, 1),
    catchup=False,
    max_active_runs=1
) as dag:

    # 1. Sensor Pasivo (FileSensor Logic)
    # Espera hasta que aparezcan archivos en el Data Lake
    sensor_archivos = PythonSensor(
        task_id='sensor_landing_zone',
        python_callable=check_for_new_files,
        poke_interval=30, # Revisa cada 30 segundos
        timeout=60*60,    # Espera máximo 1 hora
        mode='poke'
    )

    # 2. Trigger Spark (Spark Connect Client Pattern)
    # Ejecutamos el script Python LOCALMENTE en el contenedor de Airflow.
    # Gracias a Spark Connect (configurado en el script), este proceso actuará como
    # un cliente gRPC que envía las instrucciones al cluster Spark remoto.
    trigger_spark = BashOperator(
        task_id='trigger_spark_etl',
        bash_command='python /app/jobs/etl_limpieza.py "{{ ds }}"'
    )

    sensor_archivos >> trigger_spark

# -*- coding: utf-8 -*-

"""
Módulo Cliente de MinIO.

Este módulo proporciona una clase de cliente para interactuar con un servidor MinIO.
Está diseñado para leer la configuración desde variables de entorno, lo que facilita
su uso en contenedores Docker.
"""

import os
import io
import json
import logging
from minio import Minio
from minio.error import S3Error
import pandas as pd

# Configuración de logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class MinioClient:
    """
    Cliente para gestionar la conexión y operaciones con MinIO.
    """
    def __init__(self):
        """
        Inicializa el cliente de MinIO usando variables de entorno.
        """
        self.client = self._get_client()

    def _get_client(self):
        """
        Crea y configura una instancia del cliente de MinIO.

        Returns:
            Minio: Una instancia del cliente de MinIO, o None si falla la conexión.
        """
        try:
            endpoint = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
            access_key = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
            secret_key = os.getenv('MINIO_SECRET_KEY', 'minioadmin')

            client = Minio(
                endpoint,
                access_key=access_key,
                secret_key=secret_key,
                secure=False  # Cambiar a True si se usa HTTPS
            )
            logging.info(f"Conexión exitosa con MinIO en {endpoint}")
            return client
        except (TypeError, S3Error) as e:
            logging.error(f"Error al conectar con MinIO: {e}")
            return None

    def upload_string_data(self, data_str: str, prefix: str, filename: str, bucket_name: str = 'raw-data', content_type: str = 'text/plain'):
        """
        Sube una cadena de texto (como NDJSON o CSV) a MinIO.

        Args:
            data_str (str): El contenido en string.
            prefix (str): Prefijo de ruta.
            filename (str): Nombre del archivo.
            bucket_name (str): Nombre del bucket.
            content_type (str): Tipo MIME del contenido.

        Returns:
            bool: True si tuvo éxito.
        """
        if self.client is None:
            logging.error("El cliente de MinIO no está inicializado.")
            return False
        
        object_name = f"{prefix}{filename}"

        try:
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                logging.info(f"Bucket '{bucket_name}' creado.")

            # Convert string to bytes
            data_bytes = data_str.encode('utf-8')
            data_buffer = io.BytesIO(data_bytes)
            
            self.client.put_object(
                bucket_name,
                object_name,
                data=data_buffer,
                length=len(data_bytes),
                content_type=content_type
            )
            logging.info(f"Objeto '{object_name}' subido exitosamente.")
            return True
        except S3Error as e:
            logging.error(f"Error S3 al subir datos: {e}")
            return False
        except Exception as e:
            logging.error(f"Error inesperado al subir datos: {e}")
            return False

    def upload_json_unified(self, data: dict, prefix: str, filename: str, bucket_name: str = 'raw-data'):
        """
        Convierte un diccionario a una cadena JSON y lo sube a MinIO con un prefijo.

        Args:
            data (dict): El diccionario a subir.
            prefix (str): El prefijo de la ruta del objeto (ej: '202511/').
            filename (str): El nombre del archivo (objeto) en MinIO.
            bucket_name (str): El nombre del bucket. Por defecto es 'raw-data'.

        Returns:
            bool: True si la subida fue exitosa, False en caso contrario.
        """
        if self.client is None:
            logging.error("El cliente de MinIO no está inicializado. No se puede subir el archivo.")
            return False
        
        object_name = f"{prefix}{filename}"

        try:
            # Asegurarse de que el bucket exista
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                logging.info(f"Bucket '{bucket_name}' creado exitosamente.")

            # Convertir diccionario a JSON en memoria. default=str maneja tipos no serializables como datetime.
            json_data = json.dumps(data, default=str).encode('utf-8')
            json_buffer = io.BytesIO(json_data)
            
            # Subir el objeto
            self.client.put_object(
                bucket_name,
                object_name,
                data=json_buffer,
                length=len(json_data),
                content_type='application/json'
            )
            logging.info(f"Archivo '{object_name}' subido exitosamente al bucket '{bucket_name}'.")
            return True
        except S3Error as e:
            logging.error(f"Error al subir el archivo JSON a MinIO: {e}")
            return False
        except Exception as e:
            logging.error(f"Un error inesperado ocurrió al subir JSON: {e}")
            return False

    def upload_dataframe(self, df: pd.DataFrame, filename: str, bucket_name: str = 'raw-data'):
        """
        Convierte un DataFrame de Pandas a formato Parquet y lo sube a MinIO.

        Args:
            df (pd.DataFrame): El DataFrame a subir.
            filename (str): El nombre del archivo (objeto) en MinIO.
            bucket_name (str): El nombre del bucket. Por defecto es 'raw-data'.

        Returns:
            bool: True si la subida fue exitosa, False en caso contrario.
        """
        if self.client is None:
            logging.error("El cliente de MinIO no está inicializado. No se puede subir el archivo.")
            return False
        
        if not filename.endswith('.parquet'):
            filename += '.parquet'

        try:
            # Asegurarse de que el bucket exista
            found = self.client.bucket_exists(bucket_name)
            if not found:
                self.client.make_bucket(bucket_name)
                logging.info(f"Bucket '{bucket_name}' creado exitosamente.")

            # Convertir DataFrame a Parquet en memoria
            parquet_buffer = io.BytesIO()
            df.to_parquet(parquet_buffer, index=False)
            parquet_buffer.seek(0)  # Rebobinar el buffer al principio

            # Subir el objeto
            self.client.put_object(
                bucket_name,
                filename,
                data=parquet_buffer,
                length=parquet_buffer.getbuffer().nbytes,
                content_type='application/octet-stream'
            )
            logging.info(f"Archivo '{filename}' subido exitosamente al bucket '{bucket_name}'.")
            return True
        except S3Error as e:
            logging.error(f"Error al subir el archivo a MinIO: {e}")
            return False
        except Exception as e:
            logging.error(f"Un error inesperado ocurrió: {e}")
            return False

if __name__ == '__main__':
    # Ejemplo de uso (para pruebas locales)
    # Asegúrate de tener un servidor MinIO corriendo y las variables de entorno configuradas.
    
    # Crear un DataFrame de ejemplo
    data = {'col1': [1, 2], 'col2': [3, 4]}
    sample_df = pd.DataFrame(data=data)
    
    # Inicializar cliente
    minio_cli = MinioClient()
    
    # Subir DataFrame
    if minio_cli.client:
        success = minio_cli.upload_dataframe(
            df=sample_df,
            filename="test_df.parquet",
            bucket_name="test-bucket"
        )
        if success:
            print("Prueba de subida de Parquet completada exitosamente.")
        
        # Probar el nuevo método JSON
        sample_dict = {"metrics": [{"a":1}], "logs": [{"b": 2}]}
        success_json = minio_cli.upload_json_unified(
            data=sample_dict,
            prefix="test/",
            filename="test.json",
            bucket_name="test-bucket"
        )
        if success_json:
            print("Prueba de subida de JSON completada exitosamente.")
        else:
            print("La prueba de subida de JSON falló.")

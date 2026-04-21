# -*- coding: utf-8 -*-

"""
Módulo Principal de la API de Generación de Datos.

Este módulo utiliza FastAPI para exponer endpoints que controlan la generación
y carga de datos sintéticos de observabilidad a un Data Lake en MinIO.
Implementa una estrategia de ingesta unificada en formato JSON particionado.

También incluye un explorador web minimalista para visualizar el contenido
de los buckets (JSON y Parquet).
"""

import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, BackgroundTasks, HTTPException, Request
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel, Field
import json
import os
import io
import uuid
import pandas as pd

# Importaciones de los módulos locales
from data_generator import ObservabilityGenerator
from minio_client import MinioClient

# --- Configuración de Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Inicialización de la Aplicación y Clientes ---
app = FastAPI(
    title="API de Generación de Datos de Observabilidad",
    description="Genera y sube datos sintéticos unificados a MinIO y permite visualizarlos.",
    version="1.3.0"
)

# Configuración de Templates
templates = Jinja2Templates(directory="templates")

# --- Instancias Globales de Clientes ---
try:
    generator = ObservabilityGenerator()
    minio_client = MinioClient()
    # Verificación opcional de conexión al inicio
    # if minio_client.client: ... 
except Exception as e:
    logging.error(f"Error crítico durante la inicialización: {e}")

# --- Modelos de Datos ---
class HistoricalRequest(BaseModel):
    start_date: str = Field(..., example="2024-01-01", description="Fecha de inicio (YYYY-MM-DD)")
    end_date: str = Field(..., example="2024-01-03", description="Fecha de fin (YYYY-MM-DD)")
    frequency_seconds: int = Field(600, example=600, description="Frecuencia de muestreo en segundos")

# --- Endpoints de Simulación ---

@app.post("/simulation/historical", status_code=202)
async def run_historical_simulation(request: HistoricalRequest, background_tasks: BackgroundTasks):
    """
    Ejecuta una simulación histórica y sube los datos como un único archivo JSON a MinIO.
    """
    logging.info(f"Recibida petición para simulación histórica de {request.start_date} a {request.end_date}")

    def historical_task():
        logging.info("Generando lote de datos histórico unificado...")
        metrics_df, logs_df, traffic_df = generator.generate_batch(
            start_date=request.start_date,
            end_date=request.end_date,
            frequency_seconds=request.frequency_seconds
        )
        
        # Unificar los 3 DataFrames
        metrics_df['record_type'] = 'metric'
        metrics_df['timestamp'] = metrics_df['timestamp'].astype(str)

        logs_df['record_type'] = 'log'
        if not logs_df.empty:
            logs_df['timestamp'] = logs_df['timestamp'].astype(str)

        traffic_df['record_type'] = 'traffic'
        if not traffic_df.empty:
            traffic_df['timestamp'] = traffic_df['timestamp'].astype(str)
        
        full_df = pd.concat([metrics_df, logs_df, traffic_df], ignore_index=True)
        ndjson_str = full_df.to_json(orient='records', lines=True)

        start_dt = datetime.strptime(request.start_date, "%Y-%m-%d")
        prefix = f"{start_dt.year}/{start_dt.month:02d}/{start_dt.day:02d}/"
        filename = f"historical_dump_{request.start_date}_{request.end_date}.ndjson"

        minio_client.upload_string_data(
            data_str=ndjson_str,
            prefix=prefix,
            filename=filename,
            bucket_name='raw-data',
            content_type='application/x-ndjson'
        )

        local_dir = "/app/data"
        os.makedirs(local_dir, exist_ok=True)
        local_path = os.path.join(local_dir, filename)
        with open(local_path, "w", encoding="utf-8") as f:
            f.write(ndjson_str)
        logging.info(f"Copia local guardada en: {local_path}")
        
    background_tasks.add_task(historical_task)
    return {"message": "Simulación histórica iniciada en segundo plano."}

# --- HELPER: Leer archivo a DataFrame ---
def read_file_to_df(bucket, filename):
    response = minio_client.client.get_object(bucket, filename)
    file_content = response.read()
    response.close()
    response.release_conn()

    if filename.endswith(".json") or filename.endswith(".ndjson"):
        try:
            return pd.read_json(io.BytesIO(file_content), lines=True), "JSON", len(file_content)
        except ValueError:
            return pd.read_json(io.BytesIO(file_content)), "JSON", len(file_content)
    elif filename.endswith(".parquet"):
        return pd.read_parquet(io.BytesIO(file_content)), "Parquet", len(file_content)
    return None, "Unknown", 0


# --- UNIFIED EXPLORER ENDPOINTS ---

@app.get("/explorer", response_class=HTMLResponse)
async def list_files(request: Request, bucket: str = None, prefix: str = ""):
    if not bucket:
        buckets = minio_client.client.list_buckets()
        return templates.TemplateResponse("explorer.html", {
            "request": request, "buckets": buckets, "title": "Buckets"
        })
    else:
        objects = minio_client.client.list_objects(bucket, prefix=prefix, recursive=False)
        return templates.TemplateResponse("explorer.html", {
            "request": request, "bucket": bucket, "prefix": prefix, "objects": objects, "title": f"Files in {bucket}"
        })

@app.get("/explorer/view", response_class=HTMLResponse)
async def view_file(request: Request, bucket: str, filename: str):
    try:
        df, format_type, size_bytes = read_file_to_df(bucket, filename)
        
        if df is None:
            return templates.TemplateResponse("viewer.html", {
                "request": request, "bucket": bucket, "filename": filename,
                "error": "Unsupported file format.", "title": "Error"
            })

        # Mostrar solo los primeros 50 registros
        table_html = df.head(50).to_html(classes="table", border=0, index=False)
        
        return templates.TemplateResponse("viewer.html", {
            "request": request,
            "bucket": bucket,
            "filename": filename,
            "table_html": table_html,
            "count": min(len(df), 50),
            "format": format_type,
            "size_kb": round(size_bytes / 1024, 2),
            "title": f"Viewing {filename}"
        })
            
    except Exception as e:
        logging.error(f"Error viewing file: {e}")
        return templates.TemplateResponse("viewer.html", {
            "request": request, "bucket": bucket, "filename": filename, "error": str(e), "title": "Error"
        })

@app.get("/explorer/download_preview")
async def download_preview(bucket: str, filename: str):
    """Descarga los primeros 50 registros como CSV"""
    try:
        df, _, _ = read_file_to_df(bucket, filename)
        if df is None:
             raise HTTPException(status_code=400, detail="Unsupported file format")
        
        stream = io.StringIO()
        df.head(50).to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        response.headers["Content-Disposition"] = f"attachment; filename=preview_50_{filename}.csv"
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/explorer/download_full")
async def download_full(bucket: str, filename: str):
    """Descarga el archivo completo como CSV"""
    try:
        df, _, _ = read_file_to_df(bucket, filename)
        if df is None:
             raise HTTPException(status_code=400, detail="Unsupported file format")
        
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        response = StreamingResponse(iter([stream.getvalue()]), media_type="text/csv")
        base_name = os.path.splitext(filename)[0] # Remover extensión original
        response.headers["Content-Disposition"] = f"attachment; filename={base_name}.csv"
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from pydantic import BaseModel
from pyspark.ml import PipelineModel
from pyspark.sql import SparkSession

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

ml_models = {}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing SparkSession...")
    spark = SparkSession.builder \
        .appName("MLOpsInference") \
        .master("local[1]") \
        .config("spark.ui.enabled", "false") \
        .config("spark.executor.instances", "1") \
        .config("spark.driver.memory", "512m") \
        .config("spark.jars.packages", "org.apache.hadoop:hadoop-aws:3.3.4,com.amazonaws:aws-java-sdk-bundle:1.12.262") \
        .config("spark.hadoop.fs.s3a.endpoint", "http://minio:9000") \
        .config("spark.hadoop.fs.s3a.access.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.secret.key", "minioadmin") \
        .config("spark.hadoop.fs.s3a.path.style.access", "true") \
        .config("spark.hadoop.fs.s3a.impl", "org.apache.hadoop.fs.s3a.S3AFileSystem") \
        .config("spark.hadoop.fs.s3a.connection.ssl.enabled", "false") \
        .getOrCreate()
        
    logger.info("Loading PipelineModel from MinIO...")
    ml_models["lr_model"] = PipelineModel.load("s3a://models/lr_latency_model/")
    ml_models["spark"] = spark
    yield
    spark.stop()

app = FastAPI(lifespan=lifespan)

class PredictionRequest(BaseModel):
    throughput_rpm: float
    error_rate_percent: float
    cpu_percent: float
    memory_usage_percent: float
    active_connections_count: float

class PredictionResponse(BaseModel):
    predicted_latency_p95_ms: float
    model_version: str
    latency_ms: float

@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    start_time = time.time()
    
    spark = ml_models["spark"]
    model = ml_models["lr_model"]
    
    data = [(
        request.throughput_rpm,
        request.error_rate_percent,
        request.cpu_percent,
        request.memory_usage_percent,
        request.active_connections_count
    )]
    columns = [
        "throughput_rpm", 
        "error_rate_percent", 
        "cpu_percent", 
        "memory_usage_percent", 
        "active_connections_count"
    ]
    df = spark.createDataFrame(data, columns)
    
    predictions = model.transform(df)
    
    pred_row = predictions.select("prediction").first()
    predicted_latency = pred_row["prediction"] if pred_row else 0.0
    
    end_time = time.time()
    latency_ms = (end_time - start_time) * 1000
    model_version = "v1.0"
    
    logger.info(f"Prediction Request - Input Shape: (1, {len(columns)}), Prediction Latency: {latency_ms:.2f} ms, Model Version: {model_version}")
    
    return PredictionResponse(
        predicted_latency_p95_ms=predicted_latency,
        model_version=model_version,
        latency_ms=latency_ms
    )

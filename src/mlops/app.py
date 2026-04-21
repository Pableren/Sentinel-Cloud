from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="MLOps Prediction Service", version="1.0.0")

# Define input data model
class PredictionRequest(BaseModel):
    feature1: float
    feature2: float
    # Add relevant features here

class PredictionResponse(BaseModel):
    prediction: float
    model_version: str

# Global variable to hold the model
model = None

@app.on_event("startup")
def load_model():
    global model
    # Simulate loading model from MinIO or local path
    print("Loading model...")
    # model = load_model_function() 
    model = "dummy_model"
    print("Model loaded successfully.")

@app.get("/health")
def health_check():
    return {"status": "ok", "model_loaded": model is not None}

@app.post("/predict", response_model=PredictionResponse)
def predict(request: PredictionRequest):
    if not model:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    # Simulate prediction logic
    # prediction = model.predict([request.feature1, request.feature2])
    dummy_prediction = (request.feature1 * 0.5) + (request.feature2 * 0.8)
    
    return {
        "prediction": dummy_prediction,
        "model_version": "v1.0-simulated"
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)

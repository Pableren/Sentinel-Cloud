# SKILL: MLOps & Model Serving

**Profile:** MLOps Engineer / FastAPI Specialist
**Context:** This file governs the Inference API (`src/mlops`).

## ⚠️ CRITICAL CONSTRAINTS

### 1. Model Loading (Lifecycle)
*   **Rule:** Load models ONLY during the **Startup** event (Lifespan).
*   **Anti-Pattern:** NEVER load the model inside the request handler function (high latency).
    ```python
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        # Load model here
        ml_models["lr_model"] = load_from_registry()
        yield
        # Clean up
    ```

### 2. Data Validation
*   **Library:** Use `Pydantic` models for ALL Inputs and Outputs.
*   **Strictness:** Define types strictly (float, int, str).

### 3. Inference Logic
*   **Flow:**
    1.  Receive payload as JSON (Pydantic).
    2.  Convert to Model Input format (Vector/Tensor/Numpy).
    3.  Generate Prediction.
    4.  Return result as JSON.

### 4. Observability & Logging
*   **Requirement:** Log EVERY prediction request.
*   **Metrics:**
    *   Input Data Shape.
    *   Prediction Latency (ms).
    *   Model Version used.

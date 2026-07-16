"""
app.py — the prediction service. Downloads model from S3 and serves predictions.

This is the thing that gets containerized, automated, and deployed. It is
intentionally stateless: no database, no cache. It downloads the model from
S3 at startup, loads it into memory, and answers requests. That's it.

Run locally:  MODEL_PATH=model.joblib uvicorn app:app --reload --port 8000
Interactive docs:  http://localhost:8000/docs
"""
import os
import joblib
import pandas as pd
import boto3
from fastapi import FastAPI
from pydantic import BaseModel, Field

MODEL_PATH = os.getenv("MODEL_PATH", "/tmp/model.joblib")
MODEL_S3_BUCKET = os.getenv("MODEL_S3_BUCKET")

app = FastAPI(title="Churn Prediction API", version="1.0.0")

# Download model from S3 if bucket is configured, otherwise load from local file.
if MODEL_S3_BUCKET:
    s3 = boto3.client("s3")
    s3.download_file(MODEL_S3_BUCKET, "model.joblib", MODEL_PATH)

# Load once at startup, not per-request.
_bundle = joblib.load(MODEL_PATH)
_model = _bundle["model"]
_features = _bundle["features"]
_trained_accuracy = _bundle["accuracy"]


class Customer(BaseModel):
    tenure_months: int = Field(..., ge=0, examples=[5])
    monthly_charges: float = Field(..., ge=0, examples=[89.5])
    total_charges: float = Field(..., ge=0, examples=[450.0])
    contract_type: int = Field(..., ge=0, le=2, examples=[0],
                               description="0=month-to-month, 1=one year, 2=two year")
    has_tech_support: int = Field(..., ge=0, le=1, examples=[0])
    has_online_security: int = Field(..., ge=0, le=1, examples=[0])
    is_electronic_check: int = Field(..., ge=0, le=1, examples=[1])


@app.get("/health")
def health():
    """Liveness/readiness probe target for Kubernetes."""
    return {"status": "ok", "trained_accuracy": round(_trained_accuracy, 3)}


@app.post("/predict")
def predict(customer: Customer):
    row = pd.DataFrame([{f: getattr(customer, f) for f in _features}])
    proba = float(_model.predict_proba(row)[0][1])
    return {
        "churn": bool(proba >= 0.5),
        "churn_probability": round(proba, 4),
    }

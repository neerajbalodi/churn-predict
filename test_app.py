"""
test_app.py — the tests Jenkins runs before building the image.

Two flavors of test, which is the whole point of ML CI:
  1. Normal app tests: does the endpoint work, is the response shaped right.
  2. Behavioral test: does the model make *sensible* predictions
     (a clearly high-risk customer should score higher than a low-risk one).

Run:  pytest -q
"""
from fastapi.testclient import TestClient
from app import app

client = TestClient(app)

HIGH_RISK = {
    "tenure_months": 2, "monthly_charges": 95.0, "total_charges": 190.0,
    "contract_type": 0, "has_tech_support": 0, "has_online_security": 0,
    "is_electronic_check": 1,
}
LOW_RISK = {
    "tenure_months": 60, "monthly_charges": 40.0, "total_charges": 2400.0,
    "contract_type": 2, "has_tech_support": 1, "has_online_security": 1,
    "is_electronic_check": 0,
}


def test_health_ok():
    r = client.get("/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_predict_response_shape():
    r = client.post("/predict", json=HIGH_RISK)
    assert r.status_code == 200
    body = r.json()
    assert "churn" in body and "churn_probability" in body
    assert 0.0 <= body["churn_probability"] <= 1.0


def test_validation_rejects_bad_input():
    bad = dict(HIGH_RISK, contract_type=9)  # out of allowed range 0-2
    assert client.post("/predict", json=bad).status_code == 422


def test_model_behaves_sensibly():
    high = client.post("/predict", json=HIGH_RISK).json()["churn_probability"]
    low = client.post("/predict", json=LOW_RISK).json()["churn_probability"]
    assert high > low, "high-risk customer should out-score low-risk one"

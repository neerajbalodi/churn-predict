"""
train.py — trains the churn model and saves it to model.joblib.

The "data science" of this course is deliberately tiny: we generate a
synthetic-but-realistic churn dataset (no external download to break the lab),
train a simple pipeline, and gate on accuracy. Everything downstream
(Docker, Jenkins, Kubernetes) treats model.joblib as an opaque artifact.

Run:  python train.py
"""
import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score
import joblib

RANDOM_STATE = 42
MODEL_PATH = "model.joblib"
# CI gate: Jenkins refuses to ship a model below this. This is the line that
# makes ML CI different from app CI.
ACCURACY_THRESHOLD = 0.78

FEATURES = [
    "tenure_months",
    "monthly_charges",
    "total_charges",
    "contract_type",       # 0 = month-to-month, 1 = one year, 2 = two year
    "has_tech_support",    # 0 / 1
    "has_online_security", # 0 / 1
    "is_electronic_check", # 0 / 1
]


def make_dataset(n=5000, seed=RANDOM_STATE):
    """Synthetic churn data. Churn rises with: short tenure, high monthly
    charges, month-to-month contracts, no support, electronic-check payment."""
    rng = np.random.default_rng(seed)

    tenure = rng.integers(1, 72, n)
    monthly = rng.uniform(20, 120, n).round(2)
    total = (monthly * tenure * rng.uniform(0.9, 1.05, n)).round(2)
    contract = rng.choice([0, 1, 2], n, p=[0.55, 0.25, 0.20])
    tech = rng.integers(0, 2, n)
    security = rng.integers(0, 2, n)
    echeck = rng.integers(0, 2, n)

    # Build a churn "risk score", then sample the label from it.
    score = (
        1.8
        - 0.060 * tenure
        + 0.022 * monthly
        - 1.2 * contract
        - 0.7 * tech
        - 0.6 * security
        + 0.8 * echeck
        + rng.normal(0, 0.35, n)
    )
    prob = 1 / (1 + np.exp(-score))
    # Label is the thresholded boundary (with the noise already baked into
    # `score`), so a well-fit model can clear the gate while the data stays noisy.
    churn = (prob > 0.5).astype(int)
    # Flip ~8% of labels so the model isn't perfectly separable and predicted
    # probabilities look realistic (e.g. 0.83) instead of saturating at 1.0.
    flip = rng.uniform(0, 1, n) < 0.08
    churn[flip] = 1 - churn[flip]

    return pd.DataFrame({
        "tenure_months": tenure,
        "monthly_charges": monthly,
        "total_charges": total,
        "contract_type": contract,
        "has_tech_support": tech,
        "has_online_security": security,
        "is_electronic_check": echeck,
        "churn": churn,
    })


def main():
    df = make_dataset()
    X, y = df[FEATURES], df["churn"]
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=RANDOM_STATE, stratify=y
    )

    model = Pipeline([
        ("scaler", StandardScaler()),
        ("clf", LogisticRegression(max_iter=1000)),
    ])
    model.fit(X_train, y_train)

    acc = accuracy_score(y_test, model.predict(X_test))
    print(f"Churn rate in data : {y.mean():.1%}")
    print(f"Test accuracy      : {acc:.3f}")
    print(f"Accuracy threshold : {ACCURACY_THRESHOLD}")

    if acc < ACCURACY_THRESHOLD:
        raise SystemExit(
            f"FAIL: accuracy {acc:.3f} < threshold {ACCURACY_THRESHOLD}. "
            "Refusing to save a sub-par model."
        )

    joblib.dump({"model": model, "features": FEATURES, "accuracy": acc}, MODEL_PATH)
    print(f"PASS: saved {MODEL_PATH}")


if __name__ == "__main__":
    main()

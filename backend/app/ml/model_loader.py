from pathlib import Path

import joblib


BASE_DIR = Path(__file__).resolve().parent.parent.parent

MODEL_DIR = BASE_DIR / "trained_models"


risk_model = joblib.load(
    MODEL_DIR / "risk_model.pkl"
)

risk_features = joblib.load(
    MODEL_DIR / "risk_features.pkl"
)

fraud_model = joblib.load(
    MODEL_DIR / "fraud_model.pkl"
)

fraud_vectorizer = joblib.load(
    MODEL_DIR / "fraud_vectorizer.pkl"
)
import pandas as pd

from app.ml.model_loader import risk_features


def prepare_risk_features(data: dict) -> pd.DataFrame:
    """
    Convert incoming financial data into the same feature
    format used during model training.
    """

    df = pd.DataFrame([data])

    # One-hot encode categorical columns
    df = pd.get_dummies(
        df,
        columns=[
            "Industry_Type",
            "Firm_Size",
        ],
    )

    # Add missing columns
    for column in risk_features:
        if column not in df.columns:
            df[column] = 0

    # Keep only training columns in correct order
    df = df[risk_features]

    return df
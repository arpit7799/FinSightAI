from app.ml.model_loader import risk_model
from app.ml.preprocessing import prepare_risk_features


class RiskPredictor:

    @staticmethod
    def predict(data: dict):

        features = prepare_risk_features(data)

        prediction = risk_model.predict(features)[0]

        probability = risk_model.predict_proba(features)[0]

        return {
            "prediction": (
                "Distressed"
                if prediction == 1
                else "Non_Distressed"
            ),
            "confidence": round(
                float(max(probability)),
                4,
            ),
            "probabilities": {
                "Non_Distressed": round(
                    float(probability[0]),
                    4,
                ),
                "Distressed": round(
                    float(probability[1]),
                    4,
                ),
            },
        }
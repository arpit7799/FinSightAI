from app.ml.model_loader import (
    fraud_model,
    fraud_vectorizer,
)


class FraudPredictor:

    @staticmethod
    def predict(text: str):

        features = fraud_vectorizer.transform(
            [text]
        )

        prediction = fraud_model.predict(
            features
        )[0]

        probability = fraud_model.predict_proba(
            features
        )[0]

        return {
            "prediction": (
                "Fraud"
                if prediction == 1
                else "Non_Fraud"
            ),
            "confidence": round(
                float(max(probability)),
                4,
            ),
            "probabilities": {
                "Non_Fraud": round(
                    float(probability[0]),
                    4,
                ),
                "Fraud": round(
                    float(probability[1]),
                    4,
                ),
            },
        }
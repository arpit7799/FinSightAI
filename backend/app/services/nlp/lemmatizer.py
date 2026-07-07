from nltk.stem import WordNetLemmatizer


class Lemmatizer:

    _lemmatizer = WordNetLemmatizer()

    @staticmethod
    def lemmatize(tokens: list[str]) -> list[str]:
        return [
            Lemmatizer._lemmatizer.lemmatize(token)
            for token in tokens
        ]
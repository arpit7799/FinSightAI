from nltk.corpus import stopwords


class StopwordRemover:

    STOP_WORDS = set(stopwords.words("english"))

    @staticmethod
    def remove(tokens: list[str]) -> list[str]:
        return [
            token
            for token in tokens
            if token.lower() not in StopwordRemover.STOP_WORDS
        ]
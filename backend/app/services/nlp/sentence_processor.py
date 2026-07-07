from nltk.tokenize import sent_tokenize


class SentenceProcessor:

    @staticmethod
    def process(text: str) -> list[str]:
        return sent_tokenize(text)
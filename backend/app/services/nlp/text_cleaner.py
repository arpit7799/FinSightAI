import re


class TextCleaner:

    @staticmethod
    def clean(text: str) -> str:
        text = text.replace("\n", " ")
        text = text.replace("\t", " ")

        text = re.sub(r"\s+", " ", text)

        return text.strip()
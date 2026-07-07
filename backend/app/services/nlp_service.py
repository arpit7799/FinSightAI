from app.services.nlp.text_cleaner import TextCleaner
from app.services.nlp.tokenizer import Tokenizer
from app.services.nlp.stopword_remover import StopwordRemover
from app.services.nlp.lemmatizer import Lemmatizer
from app.services.nlp.sentence_processor import SentenceProcessor


class NLPService:

    @staticmethod
    def process(text: str):

        cleaned_text = TextCleaner.clean(text)

        tokens = Tokenizer.tokenize(cleaned_text)

        filtered_tokens = StopwordRemover.remove(tokens)

        lemmas = Lemmatizer.lemmatize(filtered_tokens)

        processed_sentences = SentenceProcessor.process(
            cleaned_text
        )

        return {
            "cleaned_text": cleaned_text,
            "tokens": tokens,
            "filtered_tokens": filtered_tokens,
            "lemmas": lemmas,
            "processed_sentences": processed_sentences,
        }
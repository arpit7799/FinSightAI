from app.services.nlp.text_cleaner import TextCleaner
from app.services.nlp.tokenizer import Tokenizer
from app.services.nlp.stopword_remover import StopwordRemover
from app.services.nlp.lemmatizer import Lemmatizer
from app.services.nlp.sentence_processor import SentenceProcessor
from app.services.nlp.ner import NERService
from app.services.nlp.keyword_extractor import KeywordExtractor


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

        named_entities = NERService.extract_entities(
            cleaned_text
        )

        financial_keywords = KeywordExtractor.extract(
            filtered_tokens
        )

        return {
            "cleaned_text": cleaned_text,
            "tokens": tokens,
            "filtered_tokens": filtered_tokens,
            "lemmas": lemmas,
            "processed_sentences": processed_sentences,
            "named_entities": named_entities,
            "financial_keywords": financial_keywords,
        }
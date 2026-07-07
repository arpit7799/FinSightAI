import spacy


class NERService:

    _nlp = spacy.load("en_core_web_sm")

    @classmethod
    def extract_entities(cls, text: str) -> list[dict]:
        doc = cls._nlp(text)

        entities = []

        for entity in doc.ents:
            entities.append(
                {
                    "text": entity.text,
                    "label": entity.label_,
                }
            )

        return entities
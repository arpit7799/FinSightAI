class KeywordExtractor:

    FINANCIAL_KEYWORDS = {
        "revenue",
        "income",
        "profit",
        "loss",
        "assets",
        "liabilities",
        "equity",
        "cash",
        "inventory",
        "receivables",
        "debt",
        "eps",
        "dividend",
        "margin",
        "operating",
        "expense",
        "expenses",
        "sales",
        "earnings",
        "share",
        "shares",
        "capital",
        "investment",
        "tax",
        "interest",
        "finance",
    }

    @classmethod
    def extract(cls, tokens: list[str]) -> list[str]:

        keywords = []

        for token in tokens:
            word = token.lower()

            if word in cls.FINANCIAL_KEYWORDS:
                keywords.append(token)

        return sorted(set(keywords))
# app/engines/rag/llm_generator.py
"""
Generates answers using Llama 3 via Ollama.

This is RAG (Retrieval Augmented Generation):
  1. We retrieve relevant chunks (done in retriever.py)
  2. We pass those chunks as context to Llama 3
  3. Llama 3 generates an answer grounded in the context
  4. We parse out which chunks were cited

The key rule: Llama 3 must ONLY use the provided context.
It should never make up financial numbers.
"""

import httpx
import json
from app.core.config import settings


# System prompt that tells Llama 3 how to behave as a financial analyst
SYSTEM_PROMPT = """You are a financial analyst assistant for FinSight AI.
You answer questions about company annual reports based ONLY on the provided context chunks.

Rules:
1. Only use information from the provided context. Do not use any outside knowledge.
2. Always cite which context chunk (by number) you got the information from.
3. If the answer is not in the context, say "I could not find this information in the report."
4. Be concise and professional.
5. Never make up financial numbers or statistics.
6. Format citations as [Chunk N] at the end of each statement.
"""


def _build_prompt(query: str, chunks: list[dict]) -> str:
    """
    Build the full prompt for Llama 3.
    Context chunks are numbered so the model can cite them.
    """
    context_text = ""
    for i, chunk in enumerate(chunks):
        page_info = f"Page {chunk['page_number']}" if chunk.get("page_number") else "Unknown page"
        section = chunk.get("section_type", "UNKNOWN")
        context_text += f"\n[Chunk {i+1}] ({section} — {page_info}):\n{chunk['chunk_text']}\n"

    prompt = f"""Context from the annual report:
{context_text}

Question: {query}

Answer based only on the above context. Cite chunk numbers like [Chunk 1]:"""

    return prompt


class LLMGenerator:
    """
    Calls Llama 3 via Ollama HTTP API to generate grounded answers.

    Ollama must be running locally:
        ollama serve
        ollama pull llama3

    Usage:
        generator = LLMGenerator()
        result = generator.generate(query, chunks)
    """

    def __init__(self):
        self.base_url = settings.OLLAMA_BASE_URL
        self.model = settings.OLLAMA_MODEL

    def generate(self, query: str, chunks: list[dict]) -> dict:
        """
        Generate an answer for a query using the provided context chunks.

        Returns:
            {
                "answer": "The company faces three major risks... [Chunk 2]",
                "citations": [
                    {"chunk_index": 1, "chunk_text": "...", "page_number": 23, "section_type": "RISK_FACTORS"},
                ],
                "model": "llama3",
            }
        """
        if not chunks:
            return {
                "answer": "No relevant information found in the document for this question.",
                "citations": [],
                "model": self.model,
            }

        prompt = _build_prompt(query, chunks)

        # Call Ollama API
        response = httpx.post(
            f"{self.base_url}/api/generate",
            json={
                "model": self.model,
                "prompt": prompt,
                "system": SYSTEM_PROMPT,
                "stream": False,   # wait for full response
                "options": {
                    "temperature": 0.1,   # low temp = more factual, less creative
                    "num_predict": 1024,  # max tokens in response
                },
            },
            timeout=120,  # Llama 3 can take a while locally
        )

        response.raise_for_status()
        result = response.json()
        answer = result.get("response", "").strip()

        # Figure out which chunks were cited in the answer
        citations = self._extract_citations(answer, chunks)

        return {
            "answer": answer,
            "citations": citations,
            "model": self.model,
        }

    def _extract_citations(self, answer: str, chunks: list[dict]) -> list[dict]:
        """
        Find which chunks were referenced in the answer.
        Looks for patterns like [Chunk 1], [Chunk 2], etc.
        """
        import re
        cited_indices = re.findall(r'\[Chunk (\d+)\]', answer)
        cited_indices = list(set(int(i) for i in cited_indices))  # unique

        citations = []
        for idx in cited_indices:
            chunk_pos = idx - 1  # convert to 0-indexed
            if 0 <= chunk_pos < len(chunks):
                chunk = chunks[chunk_pos]
                citations.append({
                    "chunk_index": idx,
                    "chunk_text": chunk["chunk_text"][:300] + "..." if len(chunk["chunk_text"]) > 300 else chunk["chunk_text"],
                    "page_number": chunk.get("page_number"),
                    "section_type": chunk.get("section_type", "UNKNOWN"),
                })

        return citations
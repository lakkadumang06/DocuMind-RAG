"""Prompt templates for answering, query rewriting and the refusal messages."""

from __future__ import annotations

from app.schemas import RetrievedChunk

NO_ANSWER_TOKEN = "NO_ANSWER"

SYSTEM_PROMPT = f"""You are DocuMind, an assistant that answers questions about company documents.

Rules:
1. Answer ONLY with information from the numbered context passages below. Never use
   outside knowledge.
2. Cite every factual statement with the passage number in square brackets, e.g.
   "24 months [2]". Use several markers when several passages support a sentence.
3. If the passages do not contain the answer, reply with exactly: {NO_ANSWER_TOKEN}
4. Answer in the language of the question (German question -> German answer, English ->
   English), even if the passages are in another language.
5. Be concise and precise: keep numbers, units and conditions exactly as written in the
   passages.
6. End your reply with a final line "CONFIDENCE: x" where x is a number between 0 and 1
   expressing how completely the passages answer the question."""

REFUSAL_MESSAGES = {
    "en": (
        "I don't know. The uploaded documents do not contain information that answers "
        "this question."
    ),
    "de": (
        "Das weiß ich nicht. Die hochgeladenen Dokumente enthalten keine Informationen, "
        "die diese Frage beantworten."
    ),
}

QUERY_REWRITE_PROMPT = """Rewrite the user's latest message as a complete, standalone search \
question using the conversation so far. Resolve pronouns and references like "it", "that", \
"the warranty" to the concrete subject. Keep the language of the latest message. Reply with \
the rewritten question only.

Conversation:
{history}

Latest message: {question}

Standalone question:"""


def format_context(chunks: list[RetrievedChunk]) -> str:
    """Number the passages so the model can cite them as [1], [2], ..."""
    parts = []
    for i, item in enumerate(chunks, start=1):
        c = item.chunk
        where = f"{c.document_name}" + (f", page {c.page}" if c.page else "")
        if c.section:
            where += f", section '{c.section}'"
        parts.append(f"[{i}] ({where})\n{c.text}")
    return "\n\n".join(parts)


def build_user_message(question: str, chunks: list[RetrievedChunk]) -> str:
    return f"Context passages:\n\n{format_context(chunks)}\n\nQuestion: {question}"

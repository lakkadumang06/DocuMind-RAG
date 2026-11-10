"""Per-session conversation memory and follow-up query rewriting.

Memory is an in-process dict, which is enough for a single API instance and for demos.
For several workers it would move to Redis behind the same two methods.
"""

from __future__ import annotations

import logging
from collections import defaultdict, deque
from dataclasses import dataclass

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

from app.rag.prompts import QUERY_REWRITE_PROMPT

logger = logging.getLogger(__name__)


@dataclass
class Turn:
    question: str
    answer: str


class ConversationMemory:
    """Keeps the last `max_turns` question/answer pairs per session id."""

    def __init__(self, max_turns: int = 6) -> None:
        self.max_turns = max_turns
        self._sessions: dict[str, deque[Turn]] = defaultdict(lambda: deque(maxlen=max_turns))

    def history(self, session_id: str | None) -> list[Turn]:
        if not session_id:
            return []
        return list(self._sessions.get(session_id, []))

    def add(self, session_id: str | None, question: str, answer: str) -> None:
        if session_id:
            self._sessions[session_id].append(Turn(question, answer))

    def clear(self, session_id: str) -> None:
        self._sessions.pop(session_id, None)

    def format_history(self, session_id: str | None) -> str:
        return "\n".join(
            f"User: {t.question}\nAssistant: {t.answer}" for t in self.history(session_id)
        )


def rewrite_query(
    llm: BaseChatModel, memory: ConversationMemory, session_id: str | None, question: str
) -> str:
    """Turn a follow-up like "and what about the warranty?" into a standalone question.

    Without history the question is returned unchanged and no LLM call is made.
    """
    history = memory.format_history(session_id)
    if not history:
        return question
    prompt = QUERY_REWRITE_PROMPT.format(history=history, question=question)
    try:
        rewritten = str(llm.invoke([HumanMessage(content=prompt)]).content).strip().strip('"')
    except Exception as exc:  # noqa: BLE001 - fall back to the raw question
        logger.warning("query rewrite failed: %s", exc)
        return question
    if not rewritten or len(rewritten) > 4 * len(question) + 200:
        return question
    logger.info("rewrote %r -> %r", question, rewritten)
    return rewritten

"""Evaluate DocuMind on the golden dataset and write evals/results.md.

Metrics
  retrieval : hit rate@k and MRR (is a chunk from the expected document + page/section
              in the top k, and at which rank) for dense, bm25 and hybrid, and for
              several chunk sizes (each chunk size gets its own temporary index)
  answers   : correctness (LLM judge, 0-2 rubric vs. reference answer), faithfulness
              (LLM judge: every claim supported by the cited chunks), refusal accuracy
              on the unanswerable questions, latency and approximate cost
Generation metrics run for the configured CHUNK_SIZE only; retrieval metrics run for
every size in --chunk-sizes, because re-answering 35 questions per size is slow locally.

Run:  python -m evals.run_evals [--modes hybrid,dense,bm25] [--chunk-sizes 500,800,1000]
      [--no-judge] [--limit 5] [--out evals/results.md]
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import statistics
import sys
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path

from app.config import Settings, get_settings
from app.ingest.pipeline import IngestionPipeline
from app.ingest.store import VectorStore
from app.llm import (
    DEFAULT_CHAT_MODELS,
    DEFAULT_EMBEDDING_MODELS,
    estimate_cost,
    get_embeddings,
    get_llm,
)
from app.rag.answer import RagAnswerer
from app.rag.prompts import SYSTEM_PROMPT, build_user_message
from app.retrieval.bm25 import BM25Retriever
from app.retrieval.hybrid import HybridRetriever
from app.retrieval.vector import DenseRetriever
from app.schemas import ChatAnswer, ChatRequest, RetrievedChunk
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage

logger = logging.getLogger("evals")
EVALS_DIR = Path(__file__).resolve().parent
MODES = ["hybrid", "dense", "bm25"]

CORRECTNESS_PROMPT = """You are grading an answer from a document assistant.

Question: {question}
Reference answer: {reference}
Candidate answer: {candidate}

Rubric:
2 = the candidate states the same facts as the reference (numbers, units and conditions \
match; extra correct detail is fine)
1 = partially correct: the key fact is right but something is missing or slightly wrong
0 = wrong, missing, or the candidate refused although the reference exists

Reply with JSON only: {{"score": <0|1|2>, "reason": "<one sentence>"}}"""

FAITHFULNESS_PROMPT = """Check whether an answer is fully supported by the source passages.

Passages:
{passages}

Answer: {answer}

Is EVERY factual claim in the answer supported by the passages? Ignore the [n] markers.
Reply with JSON only: {{"supported": true|false, "unsupported_claims": ["..."]}}"""


# --------------------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------------------


def approx_tokens(text: str) -> int:
    """Rough token count (about 4 characters per token for English and German)."""
    return max(1, len(text) // 4)


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    try:
        return json.loads(match.group(0)) if match else {}
    except json.JSONDecodeError:
        return {}


def is_hit(item: RetrievedChunk, q: dict) -> bool:
    """A retrieved chunk counts as a hit if it comes from the expected document and
    the expected page (PDF) or section (DOCX/TXT, where there are no pages)."""
    c = item.chunk
    if c.document_name != q["source_doc"]:
        return False
    if q["source_page"] is not None:
        return c.page == q["source_page"]
    return (c.section or "") == q["source_section"]


@dataclass
class RetrievalResult:
    mode: str
    chunk_size: int
    hits: list[bool] = field(default_factory=list)
    reciprocal_ranks: list[float] = field(default_factory=list)
    misses: list[str] = field(default_factory=list)

    @property
    def hit_rate(self) -> float:
        return sum(self.hits) / len(self.hits) if self.hits else 0.0

    @property
    def mrr(self) -> float:
        return statistics.mean(self.reciprocal_ranks) if self.reciprocal_ranks else 0.0


@dataclass
class AnswerRecord:
    qid: str
    mode: str
    answerable: bool
    answer: ChatAnswer
    latency_s: float
    cost_usd: float
    correctness: int | None = None
    faithful: bool | None = None
    judge_reason: str = ""


# --------------------------------------------------------------------------------------
# building indexes per chunk size
# --------------------------------------------------------------------------------------


def build_retriever(settings: Settings, chunk_size: int, docs_dir: Path) -> HybridRetriever:
    """Ingest the sample docs with a given chunk size into a dedicated collection."""
    eval_settings = settings.model_copy(
        update={
            "chunk_size": chunk_size,
            "chunk_overlap": min(settings.chunk_overlap, chunk_size // 4),
            "qdrant_collection": f"{settings.qdrant_collection}_eval_{chunk_size}",
            "index_dir": settings.index_dir / f"eval_{chunk_size}",
        }
    )
    embeddings = get_embeddings(settings=eval_settings)
    store = VectorStore(embeddings, settings=eval_settings)
    pipeline = IngestionPipeline(embeddings, store, settings=eval_settings)
    infos = pipeline.ingest_directory(docs_dir)
    logger.info(
        "chunk_size=%d: %d documents, %d chunks",
        chunk_size,
        len(infos),
        sum(i.num_chunks for i in infos),
    )
    return HybridRetriever(
        DenseRetriever(store),
        BM25Retriever(index=pipeline.bm25),
        top_k=settings.top_k,
        candidate_k=settings.candidate_k,
    )


# --------------------------------------------------------------------------------------
# metrics
# --------------------------------------------------------------------------------------


def eval_retrieval(
    retriever: HybridRetriever, questions: list[dict], mode: str, chunk_size: int, k: int
) -> RetrievalResult:
    result = RetrievalResult(mode=mode, chunk_size=chunk_size)
    for q in questions:
        if not q["answerable"]:
            continue
        ranked = retriever.retrieve(q["question"], mode=mode, top_k=k)  # type: ignore[arg-type]
        rank = next((i for i, item in enumerate(ranked, start=1) if is_hit(item, q)), None)
        result.hits.append(rank is not None)
        result.reciprocal_ranks.append(1.0 / rank if rank else 0.0)
        if rank is None:
            result.misses.append(q["id"])
    return result


def judge_answer(judge: BaseChatModel, q: dict, record: AnswerRecord, judge_model: str) -> None:
    """Fill correctness (answerable) and faithfulness (if an answer was given)."""
    if q["answerable"]:
        prompt = CORRECTNESS_PROMPT.format(
            question=q["question"], reference=q["expected_answer"], candidate=record.answer.answer
        )
        reply = judge.invoke([HumanMessage(content=prompt)]).text
        parsed = parse_json(reply)
        record.correctness = (
            int(parsed.get("score", 0)) if str(parsed.get("score", "")).isdigit() else 0
        )
        record.judge_reason = str(parsed.get("reason", ""))[:160]
        record.cost_usd += estimate_cost(judge_model, approx_tokens(prompt), approx_tokens(reply))
    if record.answer.answer_found:
        cited = record.answer.citations or []
        passages = "\n\n".join(f"[{c.marker}] {c.quote}" for c in cited) or "(no passages cited)"
        prompt = FAITHFULNESS_PROMPT.format(passages=passages, answer=record.answer.answer)
        reply = judge.invoke([HumanMessage(content=prompt)]).text
        parsed = parse_json(reply)
        record.faithful = bool(parsed.get("supported", False)) and bool(cited)
        record.cost_usd += estimate_cost(judge_model, approx_tokens(prompt), approx_tokens(reply))


def eval_answers(
    answerer: RagAnswerer,
    questions: list[dict],
    mode: str,
    judge: BaseChatModel | None,
    chat_model: str,
    judge_model: str,
) -> list[AnswerRecord]:
    records = []
    for q in questions:
        request = ChatRequest(question=q["question"], retrieval_mode=mode)  # type: ignore[arg-type]
        start = time.perf_counter()
        answer = answerer.answer(request)
        latency = time.perf_counter() - start
        prompt_tokens = approx_tokens(
            SYSTEM_PROMPT + build_user_message(q["question"], answer.retrieved)
        )
        cost = estimate_cost(chat_model, prompt_tokens, approx_tokens(answer.answer))
        record = AnswerRecord(q["id"], mode, q["answerable"], answer, latency, cost)
        if judge is not None:
            judge_answer(judge, q, record, judge_model)
        records.append(record)
        status = "found" if answer.answer_found else "REFUSED"
        logger.info(
            "%s [%s] %s %.1fs corr=%s faithful=%s",
            q["id"],
            mode,
            status,
            latency,
            record.correctness,
            record.faithful,
        )
    return records


# --------------------------------------------------------------------------------------
# report
# --------------------------------------------------------------------------------------


def pct(x: float) -> str:
    return f"{100 * x:.0f} %"


def summarise(records: list[AnswerRecord]) -> dict:
    answerable = [r for r in records if r.answerable]
    unanswerable = [r for r in records if not r.answerable]
    judged = [r for r in answerable if r.correctness is not None]
    faith = [r for r in answerable if r.faithful is not None]
    latencies = [r.latency_s for r in records]
    return {
        "n": len(records),
        "answered": sum(r.answer.answer_found for r in answerable) / max(1, len(answerable)),
        "correct": sum(r.correctness == 2 for r in judged) / len(judged) if judged else None,
        "mean_score": statistics.mean(r.correctness for r in judged) / 2 if judged else None,  # type: ignore[misc]
        "faithful": sum(bool(r.faithful) for r in faith) / len(faith) if faith else None,
        "refusal_acc": sum(not r.answer.answer_found for r in unanswerable)
        / max(1, len(unanswerable)),
        "latency_mean": statistics.mean(latencies) if latencies else 0.0,
        "latency_p95": sorted(latencies)[int(0.95 * (len(latencies) - 1))] if latencies else 0.0,
        "cost_total": sum(r.cost_usd for r in records),
    }


def fmt(v: float | None, kind: str = "pct") -> str:
    if v is None:
        return "n/a"
    return pct(v) if kind == "pct" else f"{v:.2f}"


def write_report(
    out: Path,
    settings: Settings,
    chat_model: str,
    judge_model: str | None,
    retrieval: list[RetrievalResult],
    answers: dict[str, list[AnswerRecord]],
    questions: list[dict],
    k: int,
) -> None:
    n_ans = sum(q["answerable"] for q in questions)
    n_un = len(questions) - n_ans
    lines = [
        "# Evaluation results",
        "",
        f"Generated {datetime.now(UTC):%Y-%m-%d %H:%M} UTC by `python -m evals.run_evals`.",
        "",
        f"- Dataset: {n_ans} answerable + {n_un} unanswerable questions over the 8 sample "
        "documents (English and German, see `evals/dataset.json`)",
        f"- LLM: `{chat_model}` via {settings.llm_provider}; embeddings: "
        f"`{settings.embedding_model or DEFAULT_EMBEDDING_MODELS[settings.embedding_provider]}` "
        f"via {settings.embedding_provider}; judge: `{judge_model or 'disabled'}`",
        f"- Retrieval: top_k={k}, candidate_k={settings.candidate_k}, RRF k=60, "
        f"refusal threshold={settings.min_relevance_score}, "
        f"re-ranking={'on' if settings.enable_rerank else 'off'}",
        "",
        "## Retrieval quality (dense vs BM25 vs hybrid, chunk sizes)",
        "",
        "A hit means a chunk from the expected document *and* page (PDF) or section (DOCX/TXT) "
        f"is in the top {k}. MRR rewards finding it early.",
        "",
        f"| Chunk size | Mode | Hit rate@{k} | MRR | Misses |",
        "|---|---|---|---|---|",
    ]
    for r in retrieval:
        misses = ", ".join(r.misses) or "–"
        lines.append(f"| {r.chunk_size} | {r.mode} | {pct(r.hit_rate)} | {r.mrr:.3f} | {misses} |")

    lines += [
        "",
        f"## Answer quality (chunk size {settings.chunk_size})",
        "",
        "Correct = judge score 2 of 2 against the reference answer. Faithful = every claim in the "
        "answer is supported by the cited chunks. Refusal accuracy = share of unanswerable "
        "questions that were refused.",
        "",
        "| Mode | Answered | Correct | Mean score | Faithful | Refusal acc. | Latency mean "
        "| Latency p95 | Est. cost |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for mode, records in answers.items():
        s = summarise(records)
        lines.append(
            f"| {mode} | {pct(s['answered'])} | {fmt(s['correct'])} | {fmt(s['mean_score'])} | "
            f"{fmt(s['faithful'])} | {pct(s['refusal_acc'])} | {s['latency_mean']:.1f} s | "
            f"{s['latency_p95']:.1f} s | ${s['cost_total']:.4f} |"
        )

    failures = [
        (mode, r)
        for mode, records in answers.items()
        for r in records
        if (
            r.answerable
            and (r.correctness is not None and r.correctness < 2 or not r.answer.answer_found)
        )
        or (not r.answerable and r.answer.answer_found)
        or r.faithful is False
    ]
    lines += ["", "## Failures worth a look", ""]
    if not failures:
        lines.append("None.")
    for mode, r in failures:
        q = next(q for q in questions if q["id"] == r.qid)
        why = []
        if r.answerable and not r.answer.answer_found:
            why.append("refused although answerable")
        if not r.answerable and r.answer.answer_found:
            why.append("answered an unanswerable question")
        if r.correctness is not None and r.correctness < 2:
            why.append(f"correctness {r.correctness}/2: {r.judge_reason}")
        if r.faithful is False:
            why.append("unsupported claim")
        lines.append(f"- **{r.qid} / {mode}** – {q['question']}  ")
        lines.append(f"  answer: {r.answer.answer[:200].replace(chr(10), ' ')}  ")
        lines.append(f"  issue: {'; '.join(why)}")

    lines += [
        "",
        "## Notes",
        "",
        "- Cost is estimated from an approximate token count (4 characters per token) and the "
        "price table in `app/llm.py`; local Ollama models cost $0.",
        "- Latency includes retrieval, the LLM call and, for follow-ups, query rewriting. On a "
        "laptop with Ollama it is dominated by token generation.",
        "- The judge is an LLM and can be wrong; spot-check the failures section.",
        "",
    ]
    out.write_text("\n".join(lines), encoding="utf-8")
    logger.info("wrote %s", out)


# --------------------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--modes", default=",".join(MODES))
    parser.add_argument("--chunk-sizes", default="500,800,1000")
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--no-judge", action="store_true", help="skip the LLM-as-judge metrics")
    parser.add_argument(
        "--judge-model", default=None, help="model name for the judge (same provider)"
    )
    parser.add_argument("--limit", type=int, default=None, help="only the first N questions")
    parser.add_argument("--docs", type=Path, default=None, help="documents directory")
    parser.add_argument("--out", type=Path, default=EVALS_DIR / "results.md")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)
    settings = get_settings()
    docs_dir = args.docs or settings.sample_docs_dir
    questions = json.loads((EVALS_DIR / "dataset.json").read_text(encoding="utf-8"))["questions"]
    if args.limit:
        answerable = [q for q in questions if q["answerable"]][: args.limit]
        questions = (
            answerable + [q for q in questions if not q["answerable"]][: max(1, args.limit // 6)]
        )
    modes = [m.strip() for m in args.modes.split(",") if m.strip()]
    chunk_sizes = [int(c) for c in args.chunk_sizes.split(",")]
    if settings.chunk_size not in chunk_sizes:
        chunk_sizes.insert(0, settings.chunk_size)

    chat_model = settings.llm_model or DEFAULT_CHAT_MODELS[settings.llm_provider]
    judge_model = None if args.no_judge else (args.judge_model or chat_model)
    llm = get_llm(settings=settings)
    judge = None if args.no_judge else get_llm(model=judge_model, settings=settings)

    retrievers = {size: build_retriever(settings, size, docs_dir) for size in chunk_sizes}
    retrieval_results = [
        eval_retrieval(retrievers[size], questions, mode, size, args.k)
        for size in chunk_sizes
        for mode in modes
    ]
    for r in retrieval_results:
        logger.info(
            "retrieval chunk=%d %-6s hit@%d=%.0f%% mrr=%.3f",
            r.chunk_size,
            r.mode,
            args.k,
            100 * r.hit_rate,
            r.mrr,
        )

    answerer = RagAnswerer(llm, retrievers[settings.chunk_size], settings=settings)
    answers = {
        mode: eval_answers(answerer, questions, mode, judge, chat_model, judge_model or chat_model)
        for mode in modes
    }
    write_report(
        args.out, settings, chat_model, judge_model, retrieval_results, answers, questions, args.k
    )
    for mode, records in answers.items():
        s = summarise(records)
        quality = f"correct={fmt(s['correct'])} faithful={fmt(s['faithful'])}"
        print(
            f"{mode:>6}: {quality} refusal={pct(s['refusal_acc'])} latency={s['latency_mean']:.1f}s"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())

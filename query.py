"""Milestone 5 — grounded answer generation for The Unofficial Guide.

``ask(question)`` retrieves the top-k most relevant review chunks (Milestone 4),
passes them to Groq's ``llama-3.3-70b-versatile`` under a strict grounding
prompt, and returns the answer together with programmatically-derived source
attribution.

Grounding is enforced two ways:
  1. The system prompt instructs the model to answer ONLY from the supplied
     reviews and to reply with a fixed refusal phrase otherwise.
  2. Source attribution is built from the retrieved chunks' metadata in code —
     not left to the model to produce — so citations can't be hallucinated.

Run directly to exercise a few in-scope queries plus the out-of-scope refusal:

    python query.py
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from groq import Groq

from retrieve import Result, retrieve

load_dotenv(Path(__file__).parent / ".env")

MODEL = "llama-3.3-70b-versatile"
TOP_K = 4
REFUSAL = "I don't have enough information on that."

SYSTEM_PROMPT = (
    "You are The Unofficial Guide. You answer questions about university "
    "computer-science professors using ONLY the student reviews provided in the "
    "context below. Follow these rules strictly:\n"
    "- Base your answer solely on the provided reviews. Never use outside or "
    "prior knowledge about any professor, course, or school.\n"
    f'- If the reviews do not contain enough information to answer, reply with '
    f'exactly: "{REFUSAL}"\n'
    "- Do not invent professors, courses, grades, or facts that are not in the "
    "reviews.\n"
    "- When the reviews disagree, reflect that disagreement instead of taking a "
    "side.\n"
    "- Be concise: 2-5 sentences."
)


@dataclass
class Answer:
    answer: str
    sources: list[str]
    results: list[Result]


def _format_context(results: list[Result]) -> str:
    return "\n\n".join(f"[Review {i}] {r.text}" for i, r in enumerate(results, 1))


def _client() -> Groq:
    key = os.getenv("GROQ_API_KEY")
    if not key:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."
        )
    return Groq(api_key=key)


def _attributions(results: list[Result]) -> list[str]:
    """Unique 'Professor (School) — file' source strings, in retrieval order."""
    seen, sources = set(), []
    for r in results:
        m = r.metadata
        src = m.get("source")
        if src and src not in seen:
            seen.add(src)
            sources.append(f"{m.get('professor')} ({m.get('school')}) — {src}")
    return sources


def ask(question: str, k: int = TOP_K, where: dict | None = None) -> Answer:
    """Answer a question grounded in the retrieved review chunks."""
    results = retrieve(question, k=k, where=where)
    if not results:
        return Answer(REFUSAL, [], [])

    response = _client().chat.completions.create(
        model=MODEL,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": (
                    f"Context — student reviews:\n\n{_format_context(results)}\n\n"
                    f"Question: {question}"
                ),
            },
        ],
    )
    answer = response.choices[0].message.content.strip()

    # Only attribute sources when the model actually answered from the reviews.
    grounded = REFUSAL.lower() not in answer.lower()
    sources = _attributions(results) if grounded else []
    return Answer(answer=answer, sources=sources, results=results)


def main() -> None:
    queries = [
        "What is the workload like in Donald Lafond's networking classes at FSCJ?",
        "Is Philip Ritchey at Texas A&M an easy or a hard grader?",
        "What do students say about Aakash Tyagi's exams and teaching?",
        "What do students say about Professor Frank Shipman's teaching?",  # out of scope
    ]
    for q in queries:
        print("=" * 90)
        print(f"Q: {q}")
        result = ask(q)
        print(f"\nANSWER:\n{result.answer}")
        print("\nSOURCES:")
        print("\n".join(f"  • {s}" for s in result.sources) or "  (none)")
        print()


if __name__ == "__main__":
    main()

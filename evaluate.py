"""Milestone 6 — evaluation harness for The Unofficial Guide.

Runs the 5 evaluation-plan questions (4 in-scope + 1 out-of-scope refusal test)
end-to-end through ``query.ask`` and prints, for each: the question, the
expected answer, the system's actual answer, the cited sources, and the
retrieved chunks with their distance scores. Accuracy judgments for the README
are made by a human from this output.

    python evaluate.py
"""
from __future__ import annotations

from query import ask

# (question, expected answer from the reviews) — mirrors planning.md.
EVAL = [
    (
        "What is the workload like in Donald Lafond's networking classes at FSCJ?",
        "Heavy / lots of homework (Cisco NetAcad) but manageable if you keep up; "
        "lectures clear and engaging; ~93% would take again.",
    ),
    (
        "How do students describe Cheryl Schmidt's communication and responsiveness at FSCJ?",
        "Divided — some praise her as very responsive/quick to reply; others say "
        "she is slow to answer email, dismissive, or rude. Workload called heavy.",
    ),
    (
        "Is Philip Ritchey at Texas A&M an easy or a hard grader?",
        "A hard / harsh grader — convoluted grading criteria, letter-grade drops, "
        "heavy workload; only ~23% would take him again.",
    ),
    (
        "What do students say about Aakash Tyagi's exams at Texas A&M?",
        "Per planning.md: exams light/manageable. (Reviews actually skew toward "
        "'exams are hard, projects easy' — see failure-case analysis.)",
    ),
    (
        "What do students say about Professor Frank Shipman's teaching?",
        "Out-of-scope — no reviews of Shipman in the corpus; system should refuse.",
    ),
]


def main() -> None:
    for i, (question, expected) in enumerate(EVAL, 1):
        print("=" * 95)
        print(f"Q{i}: {question}")
        print(f"\nEXPECTED: {expected}")
        result = ask(question)
        print(f"\nSYSTEM ANSWER:\n{result.answer}")
        print("\nCITED SOURCES:")
        print("\n".join(f"  • {s}" for s in result.sources) or "  (none)")
        print("\nRETRIEVED CHUNKS (distance | source):")
        for r in result.results:
            m = r.metadata
            print(f"  [{r.distance:.3f}] {m.get('professor')} ({m.get('school')}) "
                  f"{m.get('course')} {m.get('date')}")
            print(f"        {r.text[:160]}")
        print()


if __name__ == "__main__":
    main()

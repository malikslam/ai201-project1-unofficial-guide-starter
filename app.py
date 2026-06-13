"""Milestone 5 — Gradio query interface for The Unofficial Guide.

A minimal web UI over ``query.ask``: type a question, get a grounded answer plus
the review sources it was drawn from.

    python app.py        # then open http://localhost:7860
"""
from __future__ import annotations

import gradio as gr

from query import ask

EXAMPLES = [
    "Is Philip Ritchey at Texas A&M an easy or a hard grader?",
    "What is the workload like in Donald Lafond's networking classes?",
    "How do students describe Cheryl Schmidt's communication?",
    "What do students say about Aakash Tyagi's exams?",
]


def handle_query(question: str):
    if not question or not question.strip():
        return "Please enter a question.", ""
    result = ask(question)
    sources = "\n".join(f"• {s}" for s in result.sources)
    if not sources:
        sources = "(no sources — this question is outside the review collection)"
    return result.answer, sources


with gr.Blocks(title="The Unofficial Guide") as demo:
    gr.Markdown(
        "# The Unofficial Guide\n"
        "Ask about CS professors at **Florida State College at Jacksonville** and "
        "**Texas A&M University** — answers are grounded in real student reviews, "
        "with sources shown."
    )
    inp = gr.Textbox(
        label="Your question",
        placeholder="e.g. Is Philip Ritchey a hard grader?",
    )
    btn = gr.Button("Ask", variant="primary")
    answer = gr.Textbox(label="Answer", lines=8)
    sources = gr.Textbox(label="Retrieved from", lines=4)

    gr.Examples(examples=EXAMPLES, inputs=inp)

    btn.click(handle_query, inputs=inp, outputs=[answer, sources])
    inp.submit(handle_query, inputs=inp, outputs=[answer, sources])


if __name__ == "__main__":
    demo.launch()

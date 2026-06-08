"""Milestone 3 — chunking for The Unofficial Guide.

Splits each cleaned document from ``ingest.py`` into **one chunk per student
review**. Reviews are delimited by their course-code + date header (e.g.
"CET2600 Apr 26th, 2025"); the text between one header and the next is a single
self-contained review. A ~700-char / ~120-char-overlap sliding window is used as
a fallback only for any text that precedes the first detected header (so nothing
is silently dropped).

Each chunk carries source-attribution metadata: source filename, professor,
school, course, date, and a per-document chunk_index.

Run directly to chunk all documents, print 5 sample chunks, and report the
total chunk count:

    python chunk.py
"""
from __future__ import annotations

import random
import re
from dataclasses import dataclass, field

from ingest import REVIEW_HEADER, Document, load_documents

# Sliding-window fallback for un-delimited text.
WINDOW_SIZE = 700
WINDOW_OVERLAP = 120
MIN_CHUNK_CHARS = 25  # drop fragments shorter than this


@dataclass
class Chunk:
    text: str
    metadata: dict = field(default_factory=dict)


def _collapse(text: str) -> str:
    """Join a review's lines into clean prose and squeeze whitespace."""
    return re.sub(r"\s+", " ", text.replace("\n", " ")).strip()


def _sliding_window(text: str) -> list[str]:
    text = _collapse(text)
    if len(text) <= WINDOW_SIZE:
        return [text] if text else []
    step = WINDOW_SIZE - WINDOW_OVERLAP
    return [text[i:i + WINDOW_SIZE] for i in range(0, len(text), step)]


def chunk_document(doc: Document) -> list[Chunk]:
    """Split one cleaned document into per-review chunks."""
    text = doc.clean_text
    # Locate every review header; each marks the start of a review.
    headers = list(REVIEW_HEADER.finditer(text))
    chunks: list[Chunk] = []
    idx = 0

    base_meta = {
        "source": doc.source,
        "professor": doc.professor,
        "school": doc.school,
    }

    # Any text before the first header has no review boundary -> windowed.
    if headers and headers[0].start() > 0:
        for body in _sliding_window(text[: headers[0].start()]):
            if len(body) >= MIN_CHUNK_CHARS:
                chunks.append(Chunk(body, {**base_meta, "course": None,
                                           "date": None, "chunk_index": idx}))
                idx += 1
    elif not headers:
        for body in _sliding_window(text):
            if len(body) >= MIN_CHUNK_CHARS:
                chunks.append(Chunk(body, {**base_meta, "course": None,
                                           "date": None, "chunk_index": idx}))
                idx += 1
        return chunks

    # One chunk per review (header .. next header).
    for i, h in enumerate(headers):
        course, date = h.group(1), h.group(2)
        end = headers[i + 1].start() if i + 1 < len(headers) else len(text)
        body = _collapse(text[h.end():end])
        if len(body) < MIN_CHUNK_CHARS:
            continue
        # Prefix with attribution context so each chunk is self-describing.
        header_line = f"[{doc.professor} — {doc.school} — {course}, {date}]"
        chunks.append(
            Chunk(
                f"{header_line} {body}",
                {**base_meta, "course": course, "date": date, "chunk_index": idx},
            )
        )
        idx += 1

    return chunks


def chunk_all() -> list[Chunk]:
    chunks: list[Chunk] = []
    for doc in load_documents():
        chunks.extend(chunk_document(doc))
    return chunks


def main() -> None:
    chunks = chunk_all()
    print(f"Total chunks across {len(set(c.metadata['source'] for c in chunks))} "
          f"documents: {len(chunks)}\n")

    lengths = [len(c.text) for c in chunks]
    print(f"Chunk length (chars): min={min(lengths)} "
          f"max={max(lengths)} avg={sum(lengths) // len(lengths)}\n")

    random.seed(1)
    print("--- 5 random sample chunks ---")
    for c in random.sample(chunks, 5):
        m = c.metadata
        print(f"\n[{m['source']} | {m['school']} | "
              f"{m['course']} {m['date']} | idx {m['chunk_index']}]")
        print(c.text)


if __name__ == "__main__":
    main()

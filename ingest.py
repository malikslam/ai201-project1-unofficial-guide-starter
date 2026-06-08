"""Milestone 3 — document ingestion for The Unofficial Guide.

Loads the 14 Rate My Professors review PDFs from ``documents/``, extracts their
text with pdfplumber, and strips the RMP page boilerplate (rating-distribution
sidebar, repeated page headers, "Helpful" vote counts, tag chips) so that
``chunk.py`` can split the result into one chunk per student review.

Each RMP PDF is a single professor's page, so the professor name and school are
derived from the filename and carried forward as source-attribution metadata.

Run directly to (re)generate cleaned text under ``processed/`` and print a
sample so you can eyeball the cleaning before chunking:

    python ingest.py
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import pdfplumber

DOCS_DIR = Path(__file__).parent / "documents"
OUT_DIR = Path(__file__).parent / "processed"

# --- review boundary marker (shared with chunk.py) --------------------------
# A review starts with a course code + date header, e.g. "CET2600 Apr 26th, 2025".
COURSE = r"[A-Z]{2,4}\d{3,4}[A-Z]?"
DATE = (
    r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
    r"\s+\d{1,2}(?:st|nd|rd|th),\s+\d{4}"
)
REVIEW_HEADER = re.compile(rf"({COURSE})\s+({DATE})")

# --- boilerplate filters ----------------------------------------------------
# Lines containing any of these (case-sensitive) substrings are page furniture.
_DROP_SUBSTR = (
    "Computer Science",            # "Professor in the Computer Science ..."
    "Florida State College",       # school line (incl. mangled variants)
    "College at Jacksonville",     # school line where "Florida State" is scrambled
    "at College Station",          # Texas A&M school line variant
    "Texas A&M",                   # school line
    "Rating Distribution",
    "Similar Professors",
    "Overall Quality",
    "Student Ratings",
    "Would take",                  # "Would take Level of" header (lowercase t)
    "again Difficulty",
    "I'm Professor",
    "Helpful",                     # "Helpful 0 0" vote counts
    "ratings",                     # "on 177 ratings"
)

# Lines exactly equal to one of these are dropped.
_DROP_EXACT = {
    "QUALITY", "DIFFICULTY", "Rate", "Compare", "Rate Compare",
    "All", "courses",
}

# Structural patterns for sidebar numbers / rating rows.
_DROP_PATTERNS = (
    re.compile(r"^(Awesome|Great|Good|OK|Awful)\s+\d\s+\d+$"),  # "Awesome 5 149"
    re.compile(r"^\d{1,3}%\s+\d\.\d$"),                          # "93% 2.3"
    re.compile(r"^\d\.\d{1,2}$"),                                # scores "4.0","4.80"
    re.compile(r"^\d+$"),                                        # stray integers
)

# Review metadata lines: keep only the informative ones (grade / would-take-again).
_META_FIELD = re.compile(r"(For Credit:|Attendance:|Textbook:|Online Class:|"
                         r"Would Take Again:|Grade:)")
_META_KEEP = re.compile(r"(Would Take Again:|Grade:)")

# Tag chips: ALL-CAPS labels with no lowercase letters and no sentence
# punctuation, e.g. "TOUGH GRADER GET READY TO", "AMAZING LECTURES".
_TAG_CHIP = re.compile(r"^[A-Z0-9&'/+\- ]{3,}$")

# RMP "Rate"/"Compare" buttons and the page footer bleed into the text at page
# breaks, usually as "<Professor name> <TAG CHIPS> Rate" or the © footer line.
_RATE_BUTTON = re.compile(r"\b(Rate|Compare)\b")

# Column interleaving merges QUALITY/DIFFICULTY labels and whole-star scores
# (always N.0, N in 1-5) into the middle of comment lines, e.g.
# "knows her 1.0 Computer Networking" or "strong DIFFICULTY independent". Scrub
# these tokens inline; RMP star ratings are never fractional so this is safe.
_INLINE_NOISE = re.compile(r"\b(QUALITY|DIFFICULTY|[1-5]\.0)\b")


def _scrub_inline(line: str) -> str:
    return re.sub(r"\s+", " ", _INLINE_NOISE.sub(" ", line)).strip()


@dataclass
class Document:
    source: str        # filename, used for attribution
    professor: str
    school: str
    raw_text: str
    clean_text: str


def school_for(filename: str) -> str:
    return "Texas A&M" if "texasA&M" in filename else "FSCJ"


def professor_for(filename: str) -> str:
    stem = Path(filename).stem.replace("_texasA&M", "").replace("_reviews", "")
    return " ".join(part.capitalize() for part in stem.split("-"))


def _is_boilerplate(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    if s in _DROP_EXACT:
        return True
    if any(sub in s for sub in _DROP_SUBSTR):
        return True
    if any(p.match(s) for p in _DROP_PATTERNS):
        return True
    if _RATE_BUTTON.search(s):
        return True
    if _META_FIELD.search(s):
        # Keep grade / would-take-again; drop the rest of the metadata block.
        return not _META_KEEP.search(s)
    if _TAG_CHIP.match(s) and not any(c.islower() for c in s):
        return True
    return False


def clean_text(raw: str) -> str:
    """Drop the page preamble and per-line boilerplate, keep reviews."""
    lines = raw.splitlines()

    # Everything before the first review header is sidebar / rating distribution.
    first = next((i for i, ln in enumerate(lines) if REVIEW_HEADER.search(ln)), 0)
    lines = lines[first:]

    kept = (_scrub_inline(ln) for ln in lines if not _is_boilerplate(ln))
    return "\n".join(ln for ln in kept if ln)


def load_documents() -> list[Document]:
    docs: list[Document] = []
    for pdf_path in sorted(DOCS_DIR.glob("*.pdf")):
        with pdfplumber.open(pdf_path) as pdf:
            raw = "\n".join(p.extract_text() or "" for p in pdf.pages)
        docs.append(
            Document(
                source=pdf_path.name,
                professor=professor_for(pdf_path.name),
                school=school_for(pdf_path.name),
                raw_text=raw,
                clean_text=clean_text(raw),
            )
        )
    return docs


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    docs = load_documents()
    for doc in docs:
        out = OUT_DIR / f"{Path(doc.source).stem}.txt"
        out.write_text(doc.clean_text, encoding="utf-8")

    print(f"Ingested {len(docs)} documents -> {OUT_DIR}/\n")
    sample = docs[0]
    print(f"--- sample cleaned text: {sample.source} "
          f"({sample.professor}, {sample.school}) ---")
    print(sample.clean_text[:1500])


if __name__ == "__main__":
    main()

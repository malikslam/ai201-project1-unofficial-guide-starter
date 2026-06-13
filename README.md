# The Unofficial Guide — Project 1

A Retrieval-Augmented Generation (RAG) system that makes student-generated CS
professor reviews searchable and answerable. Ask a plain-language question
("Is Philip Ritchey a hard grader?") and get a grounded, cited answer drawn only
from real Rate My Professors reviews.

**Pipeline:** PDF ingestion (pdfplumber) → per-review chunking → embedding
(`all-MiniLM-L6-v2`) → vector store (ChromaDB) → retrieval (top-k semantic) →
grounded generation (Groq `llama-3.3-70b-versatile`) → Gradio UI.

**Run it:**
```bash
pip install -r requirements.txt          # see note below about gradio/transformers versions
cp .env.example .env                     # then add your GROQ_API_KEY
python ingest.py                         # PDFs -> cleaned text in processed/
python embed_store.py                    # build the ChromaDB vector store
python app.py                            # open http://localhost:7860
```

---

## Domain

Student reviews of **computer-science professors at two schools — Florida State
College at Jacksonville (FSCJ) and Texas A&M University**. This knowledge is
valuable because official course catalogs describe *content* but never *teaching
style, exam difficulty, grading fairness, workload, or which professor actually
gives useful feedback* — exactly what students weigh when choosing a section. It
is hard to find through official channels because it lives scattered across Rate
My Professors in inconsistent, opinion-heavy, unstructured form. Spanning two
schools also means a question may name a professor at a specific school, so the
school is tracked as metadata to keep professors from different schools cleanly
separated.

---

## Document Sources

14 Rate My Professors review pages (one PDF per professor): 8 at FSCJ, 6 at Texas
A&M. Each PDF contains many individual student reviews across multiple courses
and years. Full URLs are also in `document_source_link.txt`.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | Donald Lafond (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/394993 → `documents/donald-lafond_reviews.pdf` |
| 2 | Kevin Hampton (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/355109 → `documents/kevin-hampton_reviews.pdf` |
| 3 | Sebena Masline (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/103853 → `documents/sebena-masline_reviews.pdf` |
| 4 | Gail Gehrig (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/1134669 → `documents/gail-gehrig_reviews.pdf` |
| 5 | Andrea McKeon (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/392720 → `documents/andrea-mcKeon_reviews.pdf` |
| 6 | Rosalyn Amaro (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/276065 → `documents/rosalyn-amaro_reviews.pdf` |
| 7 | Steven Difranco (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/194733 → `documents/steven-difranco_reviews.pdf` |
| 8 | Cheryl Schmidt (FSCJ) | Rate My Professors | https://www.ratemyprofessors.com/professor/290506 → `documents/cheryl-schmidt_reviews.pdf` |
| 9 | Shreyas Kumar (Texas A&M) | Rate My Professors | https://www.ratemyprofessors.com/professor/3041478 → `documents/shreyas-kumar_texasA&M_reviews.pdf` |
| 10 | Philip Ritchey (Texas A&M) | Rate My Professors | https://www.ratemyprofessors.com/professor/2012889 → `documents/philip-ritchey_texasA&M_reviews.pdf` |
| 11 | Hyunyoung Lee (Texas A&M) | Rate My Professors | https://www.ratemyprofessors.com/professor/2046254 → `documents/hyunyoung-lee_texasA&M_reviews.pdf` |
| 12 | Teresa Leyk (Texas A&M) | Rate My Professors | https://www.ratemyprofessors.com/professor/609101 → `documents/teresa-leyk_texasA&M_reviews.pdf` |
| 13 | Robert Lightfoot (Texas A&M) | Rate My Professors | https://www.ratemyprofessors.com/professor/2327118 → `documents/robert-lightfoot_texasA&M_reviews.pdf` |
| 14 | Aakash Tyagi (Texas A&M) | Rate My Professors | https://www.ratemyprofessors.com/professor/1967267 → `documents/aakash-tyagi_texasA&M_reviews.pdf` |

---

## Chunking Strategy

Implemented in `ingest.py` (load + clean) and `chunk.py` (split).

**Chunk size:** One chunk **per individual student review**. Reviews are delimited
in the extracted text by a course-code + date header (e.g. `CET2600 Apr 26th,
2025`); the text between one header and the next becomes one chunk, prefixed with
a self-describing attribution line `[Professor — School — Course, Date]`.

**Overlap:** **None** between reviews — each review is already a complete,
independent opinion, so overlap would only duplicate content. A ~700-char /
~120-char-overlap sliding window is kept as a *fallback* only for any text before
the first detected header, so nothing is silently dropped.

**Why these choices fit your documents:** RMP reviews are short (1–3 sentence)
self-contained opinions. One-chunk-per-review keeps a complete, retrievable
thought intact — splitting mid-review produces meaningless fragments, while
merging many reviews into one chunk dilutes the embedding so specific queries
can't match precisely.

**Preprocessing before chunking:** RMP page text is noisy, with UI furniture
interleaved into the reviews. We strip the rating-distribution / "Similar
Professors" sidebar (everything before the first review), repeated page headers
(professor name + "Computer Science" + school line, including mangled variants
like `Florida State College at JacHkIsLAoRnIvOilUleS`), `Helpful 0 0` vote counts,
"Rate"/"Compare" buttons, the `© Rate My Professors` footer, the `Reviewed: <date>`
footer, and all-caps tag chips. Column interleaving also merges single tokens into
prose lines (e.g. `knows her 1.0 Computer Networking`, `strong DIFFICULTY
independent`), so `QUALITY`/`DIFFICULTY` labels and whole-star scores (always N.0,
N=1–5) are scrubbed inline. Each chunk is tagged with `source`, `professor`,
`school`, `course`, `date`, and `chunk_index` metadata.

**Final chunk count:** **1,492 chunks** across 14 documents (avg 358 chars,
range 31–1,360) — comfortably inside the healthy 50–2,000 band.

### Sample chunks (labeled with source)

1. **`cheryl-schmidt_reviews.pdf` (FSCJ — CNT2210, May 22nd 2015):**
   "Prof. Schmidt is one of the best Professors I ever had. This Professor really
   knows her Computer Networking in Cisco. I highly recommend her for Cisco classes."
2. **`sebena-masline_reviews.pdf` (FSCJ — CGS2525, Mar 29th 2005):**
   "If you are not VERY familiar with computers, if you are not a strong independent
   student….DO NOT TAKE THIS CLASS. … She is very slow to respond, and never says
   enough to help you. ugh"
3. **`andrea-mcKeon_reviews.pdf` (FSCJ — MAN2021, Feb 20th 2019):**
   "Would Take Again: Yes  Grade: Not sure yet. I love the feedback she gives and
   will help you and responds quickly to messages. Made the class creative and
   engaging I would definitely take again!"
4. **`gail-gehrig_reviews.pdf` (FSCJ — COP1000, Jul 29th 2010):**
   "She is a nice person. She is very patient answering questions, very
   approachable. She has an open door policy if you need extra help."
5. **`cheryl-schmidt_reviews.pdf` (FSCJ — CNT2102C, Apr 20th 2022):**
   "Would Take Again: Yes  Grade: A. Cheryl was an incredible teacher … very savvy
   in the subjects she teaches, but she's also very helpful and interactive … 
   Assignments are few and easy, but still very informative."

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers`, stored in ChromaDB
with **cosine** distance. It runs locally with no API key and no rate limits, and
gives strong general-purpose semantic quality on short text — a good fit for short
opinion reviews.

**Production tradeoff reflection:** If this were deployed for real users and cost
weren't a constraint, I'd weigh: larger/API-hosted models (OpenAI
`text-embedding-3-large`, Voyage, Cohere) for higher accuracy on domain-specific
slang and professor nicknames and for longer context windows; multilingual support
if the corpus spanned languages; and latency plus local-vs-API privacy (student
reviews can be sensitive). MiniLM wins on cost, latency, and privacy; a hosted
model would win on raw retrieval accuracy and context length. A concrete weakness
(see Failure Case) is that short reviews embed their *dominant* sentiment, so a
larger model — or hybrid keyword search — would better separate sub-topics like
"responsiveness" from general praise.

---

## Retrieval Test Results

Three evaluation queries, top chunks with cosine distance (lower = closer). Full
output: `python retrieve.py`.

**Query A — "What is the workload like in Donald Lafond's networking classes at FSCJ?"**
| dist | source | chunk (excerpt) |
|------|--------|-----------------|
| 0.318 | Lafond — CET2600 | "…brings networking to life with his engaging lectures. The workload is manageable if you stay on top of it." |
| 0.318 | Lafond — CET2600 | "…clear realistic description of networking … the routine of each week's assignments." |
| 0.351 | Lafond — CET2600 | "…lectures were plenty in-depth … The course has a lot of work…" |

*Why these are relevant:* all three are Lafond's networking course (CET2600) and
directly discuss workload and lecture quality — exactly the question's subject.
Distances of ~0.32 are strong matches, and metadata filtering kept every result in
the correct professor's file.

**Query B — "Is Philip Ritchey at Texas A&M an easy or a hard grader?"**
| dist | source | chunk (excerpt) |
|------|--------|-----------------|
| 0.265 | Ritchey — CSCE606 | "…the worst prof at A&M. Convoluted grading criteria … overly harsh grading and grade drops…" |
| 0.295 | Ritchey — CSCE331 | "…if you get less than 70% on any of them your letter grade drops, unclear expectations…" |
| 0.307 | Ritchey — CSCE315 | "…Lol just wow" (Grade: A — the lone positive outlier) |

*Why these are relevant:* the top two speak directly to grading harshness (the
question's subject) with the lowest distances in the whole eval set (~0.27–0.30),
and the third surfaces a dissenting data point, which is what lets the generator
acknowledge the outlier.

**Query C — "What do students say about Aakash Tyagi's exams at Texas A&M?"** — top
distance 0.311, all from Tyagi's file; results mix "exams are light work" with
"unreasonably hard," correctly surfacing a divided opinion.

---

## Grounded Generation

Implemented in `query.py`. Grounding is enforced **two ways**:

**System prompt grounding instruction** (verbatim, abbreviated): *"You answer
questions about CS professors using ONLY the student reviews provided in the
context. Base your answer solely on the provided reviews. Never use outside or
prior knowledge. If the reviews do not contain enough information to answer, reply
with exactly: 'I don't have enough information on that.' Do not invent professors,
courses, grades, or facts that are not in the reviews. When the reviews disagree,
reflect that disagreement instead of taking a side."* The model runs at
`temperature=0`, and the retrieved reviews are passed as numbered `[Review N]`
context blocks.

**How source attribution is surfaced:** Attribution is built **programmatically
from the retrieved chunks' metadata**, not generated by the model — so citations
can't be hallucinated. `ask()` returns the answer plus a deduplicated list of
`Professor (School) — filename` sources. If the model returns the refusal phrase,
the system returns **no sources** (nothing was grounded), which is how the
out-of-scope case stays honest.

---

## Example Responses

**Example 1 (in-scope, cited):**
> **Q:** Is Philip Ritchey at Texas A&M an easy or a hard grader?
> **A:** According to the reviews, Philip Ritchey is considered a hard grader.
> Reviewers mention "overly harsh grading and grade drops" and that scoring under
> 70% on any component drops your letter grade. However, one review reports an A
> grade, an outlier among mostly negative reviews.
> **Sources:** • Philip Ritchey (Texas A&M) — philip-ritchey_texasA&M_reviews.pdf

**Example 2 (in-scope, cited, reflects disagreement):**
> **Q:** What do students say about Aakash Tyagi's exams at Texas A&M?
> **A:** Students have differing opinions. Some find the exams "light work" and easy
> if they do the practice problems; another found them "unreasonably hard" and
> unrelated to the course material.
> **Sources:** • Aakash Tyagi (Texas A&M) — aakash-tyagi_texasA&M_reviews.pdf

**Example 3 (out-of-scope refusal, no sources):**
> **Q:** What do students say about Professor Frank Shipman's teaching?
> **A:** I don't have enough information on that.
> **Sources:** (none)

(Frank Shipman appears only in RMP's "Similar Professors" sidebar; no reviews of
him were collected, so a grounded system must decline.)

---

## Query Interface

A Gradio web app (`app.py`, run with `python app.py` → http://localhost:7860).

- **Input:** a single text box, *"Your question"* (Enter or the **Ask** button
  submits). Example questions are provided as clickable chips.
- **Output:** two read-only text boxes — *"Answer"* (the grounded response) and
  *"Retrieved from"* (the cited source list, or a note that the question is outside
  the collection).

**Sample interaction transcript:**
```
Your question:  How do students describe Cheryl Schmidt's communication?
Answer:         Students have mixed reviews. Some describe her as "very clear with
                her teaching" and "friendly"; another claims she is "rude in
                responses to questions." Overall the reviews disagree.
Retrieved from: • Cheryl Schmidt (FSCJ) — cheryl-schmidt_reviews.pdf
```

---

## Evaluation Report

Run with `python evaluate.py`. Retrieval quality: Relevant / Partially relevant /
Off-target. Response accuracy: Accurate / Partially accurate / Inaccurate.

| # | Question | Expected answer | System response (summarized) | Retrieval | Accuracy |
|---|----------|-----------------|------------------------------|-----------|----------|
| 1 | Workload in Donald Lafond's networking classes (FSCJ)? | Heavy but manageable; engaging lectures; ~93% would take again | "Manageable if you stay on top of it; a lot of work but not overwhelming." | Relevant (all Lafond CET2600) | **Accurate** |
| 2 | Cheryl Schmidt's communication & responsiveness (FSCJ)? | Divided — some say very responsive/quick, others slow to email / rude | "Mixed: 'very clear'/'friendly' vs. 'rude in responses.'" Captures the divide but on general communication, not email responsiveness. | Partially relevant | **Partially accurate** |
| 3 | Is Philip Ritchey (Texas A&M) an easy or hard grader? | Hard/harsh grader; grade drops; ~23% would take again | "Considered a hard grader … overly harsh grading and grade drops," notes the lone A outlier. | Relevant (all Ritchey, dist 0.27–0.31) | **Accurate** |
| 4 | What do students say about Aakash Tyagi's exams (Texas A&M)? | *(spec said light/manageable)* | "Differing opinions: some 'light work,' another 'unreasonably hard.'" | Relevant (all Tyagi) | **Accurate to reviews; spec's expected answer was wrong** |
| 5 | What do students say about Professor Frank Shipman? | Out-of-scope — should refuse | "I don't have enough information on that." (no sources) | Off-target by design (no Shipman in corpus) | **Accurate (correct refusal)** |

---

## Failure Case Analysis

**Question that failed:** "How do students describe Cheryl Schmidt's communication
and **responsiveness**?" (eval Q2).

**What the system returned:** A reasonable but *off-target* answer about her general
communication clarity ("very clear"/"friendly" vs. "rude in responses"). It did
**not** surface the reviews that specifically discuss **email responsiveness**,
even though they exist in the corpus — e.g. "the course was very organized … however,
Professor Schmidt's communication skills were awful," and (seen elsewhere) "any
emails you send aren't answered timely."

**Root cause (tied to a specific pipeline stage):** This is a **retrieval** failure,
not a generation one. With `k=4`, the top results were general teaching-quality
reviews; the responsiveness-specific review ranked **#8 (distance 0.395)** — below
the cutoff. Two pipeline causes: (1) **one-chunk-per-review embedding captures each
short review's dominant sentiment**, so a broad query like "communication" matches
generic praise/criticism more strongly than the narrow sub-topic of email response
time; and (2) Schmidt has **many near-duplicate positive reviews** that crowd the
top-k and push the specific review out of the window. (A handful of these chunks
also carry residual two-column scramble artifacts like `Ra o te` and
`ComDpIFuFteICr UScLTieYnce`, a secondary cleaning limitation.)

**What you would change to fix it:** (a) raise `k` (k≥8 surfaces the responsiveness
review here); (b) add the planned **hybrid BM25 + semantic search** so literal terms
like "email"/"responsive" boost the specific review; or (c) de-duplicate
near-identical reviews before filling the top-k so diverse perspectives survive.

---

## Spec Reflection

**One way the spec helped you during implementation:** The Chunking Strategy in
`planning.md` (one chunk per review, with `source`/`school` metadata) translated
almost directly into code. Because I'd already decided reviews were the natural unit
and that two schools required school metadata, `chunk.py` just had to detect review
boundaries and attach the planned fields — and that metadata is exactly what made
per-professor and per-school source attribution and filtering work later. Having the
five evaluation questions written up front also gave `evaluate.py` a ready-made spec.

**One way your implementation diverged from the spec, and why:** The spec assumed
reasonably clean review boundaries; the reality of RMP PDFs required far more
cleaning than anticipated — column interleaving merges scores and `QUALITY`/
`DIFFICULTY` labels into prose, page headers and a `Reviewed:` footer bleed in, and
some text scrambles mid-word. I added a multi-stage boilerplate filter and inline
scrubbing that weren't in the plan. The spec's *expected answer* for Tyagi's exams
("light/manageable") also diverged from reality: the fuller corpus shows reviews are
genuinely split, so I documented that as an honest finding rather than forcing a
pass. Finally, dependency versions diverged — adding Gradio 6.x forced upgrading
`transformers`/`sentence-transformers` to 5.x to resolve a `huggingface-hub` conflict.

---

## AI Usage

**Instance 1 — Ingestion & chunking cleanup**
- *What I gave the AI:* the `planning.md` Documents + Chunking Strategy sections and
  asked it to implement `ingest.py`/`chunk.py` for the RMP PDFs.
- *What it produced:* a working pdfplumber loader + per-review chunker, but the first
  cleaning pass left artifacts — inline star-scores in prose, scrambled school lines,
  `Rate`/`Compare` buttons, and a `Reviewed:` footer.
- *What I changed or overrode:* I directed it to iterate against a printed-chunk
  inspection: add targeted denylist/regex filters and inline `QUALITY`/`DIFFICULTY`
  + `N.0` score scrubbing, then re-run an artifact scan until it hit **0** residual
  artifacts. I rejected "good enough" and required the verification loop.

**Instance 2 — Dependency conflict resolution**
- *What I gave the AI:* the failing `pip install gradio` chain after it broke the
  embedder (`huggingface-hub` 1.x vs. `transformers <1.0`).
- *What it produced:* a diagnosis (gradio 6.x needs hf-hub 1.x, which the old
  transformers rejected) and a proposed upgrade of `transformers`.
- *What I changed or overrode:* I required it to *verify retrieval still worked*
  (identical 0.274 distance) before trusting the env, then pin a cleanly-resolving
  set in `requirements.txt` (validated with `pip check` + a dry-run) rather than
  leaving a warning behind.

**Instance 3 — Honest evaluation**
- *What I gave the AI:* the 5 eval questions and the planning.md expected answers.
- *What it produced:* eval output showing Tyagi's exam reviews were split, not
  "light/manageable" as the spec claimed.
- *What I changed or overrode:* instead of editing the answer to match the spec, I
  directed it to document the mismatch as a divergence and to dig out a genuine
  pipeline failure case (the Schmidt responsiveness retrieval drift, evidenced by the
  #8 rank) rather than reporting a suspiciously perfect run.

---

## Demo Video

*(3–5 min — to be recorded.)* Shows: 3+ queries with visible source citations; one
query where retrieval works well (Ritchey grading — narrate why the chunks are
relevant); one where the system struggles (Schmidt responsiveness — the failure
case); and a walkthrough of this evaluation report.

> **Setup note:** `requirements.txt` is pinned to a set that resolves cleanly
> together — Gradio 6.x pulls `huggingface-hub` 1.x, which requires `transformers`
> and `sentence-transformers` 5.x, so those move as a group (verified with
> `pip check`).

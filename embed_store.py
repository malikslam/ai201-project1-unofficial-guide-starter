"""Milestone 4 — embedding + vector store for The Unofficial Guide.

Embeds the per-review chunks from ``chunk.py`` with the local
``all-MiniLM-L6-v2`` sentence-transformer (no API key, no rate limits) and
stores them in a persistent ChromaDB collection along with their
source-attribution metadata (source, professor, school, course, date,
chunk_index).

Run directly to (re)build the vector store:

    python embed_store.py
"""
from __future__ import annotations

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from chunk import chunk_all

DB_DIR = str(Path(__file__).parent / "chroma_db")
COLLECTION = "professor_reviews"
EMBED_MODEL = "all-MiniLM-L6-v2"
BATCH = 256


def get_collection(reset: bool = False):
    """Return the ChromaDB collection, configured with the MiniLM embedder."""
    client = chromadb.PersistentClient(path=DB_DIR)
    embed_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=EMBED_MODEL
    )
    if reset:
        try:
            client.delete_collection(COLLECTION)
        except Exception:
            pass
    # cosine distance matches normalized sentence-transformer embeddings.
    return client.get_or_create_collection(
        name=COLLECTION,
        embedding_function=embed_fn,
        metadata={"hnsw:space": "cosine"},
    )


def build() -> int:
    """Chunk all documents and (re)embed them into a fresh collection."""
    chunks = chunk_all()
    collection = get_collection(reset=True)

    for start in range(0, len(chunks), BATCH):
        batch = chunks[start:start + BATCH]
        collection.add(
            ids=[f"{c.metadata['source']}#{c.metadata['chunk_index']}"
                 for c in batch],
            documents=[c.text for c in batch],
            metadatas=[
                {k: ("" if v is None else v) for k, v in c.metadata.items()}
                for c in batch
            ],
        )
        print(f"  embedded {min(start + BATCH, len(chunks))}/{len(chunks)}")

    return collection.count()


def main() -> None:
    print(f"Building vector store '{COLLECTION}' with {EMBED_MODEL} ...")
    n = build()
    print(f"\nDone. {n} chunks stored in {DB_DIR}")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Document-Aware Q&A Bot (RAG)

Pipeline:  load -> chunk -> embed -> store (Chroma, on disk)
           question -> retrieve top-k chunks -> LLM answer grounded in those chunks
           -> print answer + the source chunks that were used

Usage:
    python rag_bot.py ingest ./docs            # index PDFs / .txt / .md files
    python rag_bot.py ask "What is the refund policy?"
    python rag_bot.py chat                     # interactive Q&A loop
    python rag_bot.py ingest ./docs --reset    # wipe the index and rebuild
"""

from __future__ import annotations

import argparse
import os
import sys
import textwrap
from pathlib import Path

from langchain_anthropic import ChatAnthropic
from langchain_chroma import Chroma
from langchain_community.document_loaders import PyPDFLoader, TextLoader
from langchain_core.documents import Document
from langchain_core.prompts import ChatPromptTemplate
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --------------------------------------------------------------------------- #
# Configuration (override with environment variables)
# --------------------------------------------------------------------------- #
PERSIST_DIR = os.getenv("RAG_PERSIST_DIR", "./chroma_db")
COLLECTION = os.getenv("RAG_COLLECTION", "documents")
EMBED_MODEL = os.getenv("RAG_EMBED_MODEL", "sentence-transformers/all-MiniLM-L6-v2")
LLM_MODEL = os.getenv("RAG_LLM_MODEL", "claude-sonnet-5-5")

CHUNK_SIZE = int(os.getenv("RAG_CHUNK_SIZE", "800"))      # characters
CHUNK_OVERLAP = int(os.getenv("RAG_CHUNK_OVERLAP", "150"))  # characters
TOP_K = int(os.getenv("RAG_TOP_K", "4"))

SUPPORTED = {".pdf", ".txt", ".md"}

PROMPT = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            "You answer questions using ONLY the numbered context excerpts provided.\n"
            "Rules:\n"
            "- If the context does not contain the answer, say you could not find it "
            "in the documents. Do not use outside knowledge.\n"
            "- Cite the excerpts you relied on inline like [1], [2].\n"
            "- Be concise and accurate.",
        ),
        ("human", "Context:\n{context}\n\nQuestion: {question}"),
    ]
)


# --------------------------------------------------------------------------- #
# Components
# --------------------------------------------------------------------------- #
def get_vectorstore() -> Chroma:
    """Open (or create) the persistent Chroma store."""
    embeddings = HuggingFaceEmbeddings(
        model_name=EMBED_MODEL,
        encode_kwargs={"normalize_embeddings": True},
    )
    return Chroma(
        collection_name=COLLECTION,
        embedding_function=embeddings,
        persist_directory=PERSIST_DIR,
        collection_metadata={"hnsw:space": "cosine"},
    )


def find_files(path: Path) -> list[Path]:
    if path.is_file():
        return [path] if path.suffix.lower() in SUPPORTED else []
    return sorted(p for p in path.rglob("*") if p.suffix.lower() in SUPPORTED)


def load_file(path: Path) -> list[Document]:
    """Load one file into Documents (one per PDF page, or one per text file)."""
    if path.suffix.lower() == ".pdf":
        docs = PyPDFLoader(str(path)).load()
    else:
        docs = TextLoader(str(path), encoding="utf-8", autodetect_encoding=True).load()
    for d in docs:
        d.metadata["source"] = str(path)
    return docs


# --------------------------------------------------------------------------- #
# Ingestion
# --------------------------------------------------------------------------- #
def ingest(path: str, reset: bool = False) -> None:
    root = Path(path)
    if not root.exists():
        sys.exit(f"Path not found: {root}")

    files = find_files(root)
    if not files:
        sys.exit(f"No supported files ({', '.join(sorted(SUPPORTED))}) found in {root}")

    store = get_vectorstore()
    if reset:
        store.reset_collection()
        print("Existing index cleared.")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],  # prefer paragraph/sentence breaks
        add_start_index=True,
    )

    total_chunks = 0
    for f in files:
        try:
            pages = load_file(f)
        except Exception as exc:  # keep going if one file is bad
            print(f"  ! Skipping {f}: {exc}")
            continue

        chunks = splitter.split_documents(pages)
        if not chunks:
            print(f"  ! No text extracted from {f} (scanned PDF?)")
            continue

        # Deterministic IDs + deleting old chunks of this file makes
        # re-ingesting idempotent (no duplicates, edits are picked up).
        store.delete(where={"source": str(f)})
        ids = [f"{f}:{i}" for i in range(len(chunks))]
        store.add_documents(chunks, ids=ids)

        total_chunks += len(chunks)
        print(f"  + {f}  ({len(pages)} page(s) -> {len(chunks)} chunks)")

    print(f"\nIndexed {total_chunks} chunks into '{PERSIST_DIR}'.")


# --------------------------------------------------------------------------- #
# Retrieval + generation
# --------------------------------------------------------------------------- #
def format_context(results: list[tuple[Document, float]]) -> str:
    blocks = []
    for i, (doc, _) in enumerate(results, 1):
        blocks.append(f"[{i}] (source: {describe_source(doc)})\n{doc.page_content}")
    return "\n\n".join(blocks)


def describe_source(doc: Document) -> str:
    name = Path(doc.metadata.get("source", "unknown")).name
    page = doc.metadata.get("page")
    return f"{name}, page {page + 1}" if isinstance(page, int) else name


def answer(question: str, store: Chroma, llm: ChatAnthropic) -> None:
    # Chroma returns cosine *distance*; similarity = 1 - distance.
    results = store.similarity_search_with_score(question, k=TOP_K)
    if not results:
        print("The index is empty. Run `ingest` first.")
        return

    chain = PROMPT | llm
    response = chain.invoke({"context": format_context(results), "question": question})

    print("\nAnswer:\n" + textwrap.fill(response.content, 100, replace_whitespace=False))
    print("\nSources used:")
    for i, (doc, dist) in enumerate(results, 1):
        snippet = " ".join(doc.page_content.split())[:220]
        print(f"  [{i}] {describe_source(doc)}  (similarity {1 - dist:.2f})")
        print(f"      \"{snippet}...\"")
    print()


def get_llm() -> ChatAnthropic:
    if not os.getenv("ANTHROPIC_API_KEY"):
        sys.exit("Set ANTHROPIC_API_KEY first (export ANTHROPIC_API_KEY=...).")
    return ChatAnthropic(model=LLM_MODEL, temperature=0, max_tokens=1024)


def chat() -> None:
    store, llm = get_vectorstore(), get_llm()
    print("Ask questions about your documents. Type 'exit' to quit.")
    while True:
        try:
            q = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if q.lower() in {"exit", "quit", ""}:
            if q:
                break
            continue
        answer(q, store, llm)


# --------------------------------------------------------------------------- #
# CLI
# --------------------------------------------------------------------------- #
def main() -> None:
    parser = argparse.ArgumentParser(description="Document-aware Q&A bot (RAG)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_ing = sub.add_parser("ingest", help="Load, chunk, embed and store documents")
    p_ing.add_argument("path", help="File or folder of .pdf/.txt/.md files")
    p_ing.add_argument("--reset", action="store_true", help="Clear the index first")

    p_ask = sub.add_parser("ask", help="Ask a single question")
    p_ask.add_argument("question")

    sub.add_parser("chat", help="Interactive Q&A session")

    args = parser.parse_args()
    if args.cmd == "ingest":
        ingest(args.path, args.reset)
    elif args.cmd == "ask":
        answer(args.question, get_vectorstore(), get_llm())
    else:
        chat()


if __name__ == "__main__":
    main()

# Document-Aware Q&A Bot (RAG)

CLI app: load PDFs/text -> chunk -> embed -> Chroma (persisted) -> retrieve top-k -> Claude answers with citations.

## Setup
    pip install -r requirements.txt
    export ANTHROPIC_API_KEY=your_key

## Use
    python rag_bot.py ingest ./docs          # index documents (safe to re-run)
    python rag_bot.py ask "What does the report say about X?"
    python rag_bot.py chat                   # interactive mode
    python rag_bot.py ingest ./docs --reset  # rebuild from scratch

## Design choices
- **Chunking:** RecursiveCharacterTextSplitter, 800 chars / 150 overlap, splits on paragraphs -> lines -> sentences first to keep chunks coherent.
- **Embeddings:** local `all-MiniLM-L6-v2` (no API key, normalized, cosine space).
- **Persistence:** Chroma writes to `./chroma_db`; documents are not re-embedded on each run. Re-ingesting a file replaces its old chunks (no duplicates).
- **Grounding:** the prompt restricts the LLM to numbered excerpts, forbids outside knowledge, and requires `[n]` citations. If the answer isn't in the docs, it says so.
- **Attribution:** every answer prints the retrieved chunks with file, page, similarity score and a snippet.
- **Config:** env vars `RAG_CHUNK_SIZE`, `RAG_CHUNK_OVERLAP`, `RAG_TOP_K`, `RAG_EMBED_MODEL`, `RAG_LLM_MODEL`, `RAG_PERSIST_DIR`.

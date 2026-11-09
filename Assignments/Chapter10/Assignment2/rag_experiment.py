"""
Compare embedding models x chunking configs for retrieval quality.

Setup:
  pip install sentence-transformers numpy pandas
  docs/            -> your .txt documents (same set for every run)
  questions.json   -> [{"question": "...", "answer": "exact answer-bearing snippet from a doc"}, ...]

Relevance rule: a retrieved chunk is correct if it CONTAINS the gold answer snippet
(whitespace/case-normalised). So a chunk boundary that splits the answer = a miss,
which is exactly the chunking effect we want to measure.

Run: python rag_experiment.py
"""
import glob, json, re
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

MODELS = {
    # name: (hf id, query prefix, doc prefix)
    "MiniLM-L6": ("sentence-transformers/all-MiniLM-L6-v2", "", ""),
    "BGE-small": ("BAAI/bge-small-en-v1.5",
                  "Represent this sentence for searching relevant passages: ", ""),
    "MPNet-base": ("sentence-transformers/all-mpnet-base-v2", "", ""),
}
CHUNKINGS = {  # (chunk size in words, overlap in words)
    "small_100_no-overlap": (100, 0),
    "small_100_ov20": (100, 20),
    "large_400_ov50": (400, 50),
    "large_400_no-overlap": (400, 0),
}
KS = [1, 3, 5]


def norm(s):
    return re.sub(r"\s+", " ", s).strip().lower()


def chunk_words(text, size, overlap):
    words = text.split()
    step = size - overlap
    return [" ".join(words[i:i + size]) for i in range(0, max(len(words) - overlap, 1), step)]


def load_docs():
    return {p: open(p, encoding="utf-8").read() for p in sorted(glob.glob("docs/*.txt"))}


def main():
    docs = load_docs()
    questions = json.load(open("questions.json"))
    # sanity: every gold answer must exist in the corpus
    corpus_norm = norm(" ".join(docs.values()))
    for q in questions:
        assert norm(q["answer"]) in corpus_norm, f"Answer not in corpus: {q['answer'][:60]}"

    rows = []
    for m_name, (hf_id, q_prefix, d_prefix) in MODELS.items():
        model = SentenceTransformer(hf_id)
        q_emb = model.encode([q_prefix + q["question"] for q in questions],
                             normalize_embeddings=True)
        for c_name, (size, ov) in CHUNKINGS.items():
            chunks = [c for t in docs.values() for c in chunk_words(t, size, ov)]
            c_emb = model.encode([d_prefix + c for c in chunks],
                                 normalize_embeddings=True, batch_size=64)
            sims = q_emb @ c_emb.T
            ranking = np.argsort(-sims, axis=1)
            chunks_norm = [norm(c) for c in chunks]

            # is the answer fully intact in ANY chunk? (upper bound for this chunking)
            ceiling = np.mean([any(norm(q["answer"]) in c for c in chunks_norm)
                               for q in questions])
            hits = {k: [] for k in KS}
            rr = []
            for qi, q in enumerate(questions):
                ans = norm(q["answer"])
                rank = next((r + 1 for r, ci in enumerate(ranking[qi][:max(KS) * 4])
                             if ans in chunks_norm[ci]), None)
                for k in KS:
                    hits[k].append(rank is not None and rank <= k)
                rr.append(1 / rank if rank else 0)
            row = {"model": m_name, "chunking": c_name, "n_chunks": len(chunks),
                   "answer_intact_ceiling": round(ceiling, 3), "MRR": round(np.mean(rr), 3)}
            row.update({f"hit@{k}": round(np.mean(v), 3) for k, v in hits.items()})
            rows.append(row)
            print(row)

    df = pd.DataFrame(rows)
    df.to_csv("results.csv", index=False)
    print("\n", df.to_markdown(index=False) if hasattr(df, "to_markdown") else df)


if __name__ == "__main__":
    main()

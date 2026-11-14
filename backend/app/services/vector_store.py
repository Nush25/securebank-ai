
import json
from pathlib import Path

import faiss
import numpy as np

from backend.app.services.embedding_service import generate_embeddings


PROJECT_ROOT = Path(__file__).resolve().parents[3]
DATA_DIR = PROJECT_ROOT / "data"

INDEX_PATH = DATA_DIR / "faiss_index.bin"
METADATA_PATH = DATA_DIR / "chunks_metadata.json"


def create_vector_store(chunks: list[dict]):
    """Convert text chunks into vectors and save their metadata."""

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    texts = [item["text"] for item in chunks]

    embeddings = generate_embeddings(texts, task="document")
    vectors = np.asarray(embeddings, dtype="float32")

    # Normalize vectors for cosine similarity
    faiss.normalize_L2(vectors)

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    faiss.write_index(index, str(INDEX_PATH))

    metadata = [
        {
            "chunk_id": i,
            "text": item["text"],
            "source": item["source"]
        }
        for i, item in enumerate(chunks)
    ]

    with open(METADATA_PATH, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4, ensure_ascii=False)

    return index


def search_similar_chunks(question: str, top_k: int = 3):
    """Find relevant policy chunks and their source filenames."""

    if not INDEX_PATH.exists() or not METADATA_PATH.exists():
        raise FileNotFoundError(
            "Vector database has not been created yet."
        )

    query_embedding = generate_embeddings(
        [question],
        task="query"
    )

    query_vector = np.asarray(query_embedding, dtype="float32")
    faiss.normalize_L2(query_vector)

    index = faiss.read_index(str(INDEX_PATH))

    with open(METADATA_PATH, "r", encoding="utf-8") as file:
        metadata = json.load(file)

    scores, indices = index.search(
        query_vector,
        min(top_k, index.ntotal)
    )

    results = []

    for score, idx in zip(scores[0], indices[0]):
        if idx == -1:
            continue

        results.append({
            "text": metadata[idx]["text"],
            "source": metadata[idx]["source"],
            "score": float(score)
        })

    return results


from backend.app.services.document_loader import load_all_documents
from backend.app.services.text_chunker import chunk_text
from backend.app.services.vector_store import create_vector_store


def build_knowledge_base():
    """Load documents, split them into chunks and index them."""

    documents = load_all_documents()

    if not documents:
        raise ValueError("No banking documents found.")

    all_chunks = []

    for document in documents:
        chunks = chunk_text(document["content"])

        for chunk in chunks:
            all_chunks.append({
                "text": chunk,
                "source": document["filename"]
            })

    # Create the FAISS index
    create_vector_store(all_chunks)

    return {
        "documents_loaded": len(documents),
        "chunks_created": len(all_chunks),
        "sources": list({
            item["source"] for item in all_chunks
        })
    }

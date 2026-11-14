from backend.app.services.rag_pipeline import build_knowledge_base
from backend.app.services.vector_store import search_similar_chunks


if __name__ == "__main__":

    result = build_knowledge_base()

    print("\nKnowledge Base Created!")
    print("Documents:", result["documents_loaded"])
    print("Chunks:", result["chunks_created"])

    question = "What are the rules for keeping my bank account secure?"

    print("\nQuestion:", question)

    results = search_similar_chunks(question, top_k=3)

    print("\nRetrieved Results:")

    for item in results:
        print("\nSource:", item["source"])
        print("Score:", round(item["score"], 3))
        print("Content:", item["text"])
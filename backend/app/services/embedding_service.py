
import ollama


def generate_embeddings(
    texts: list[str],
    task: str = "document"
):
    """
    Generate local embeddings using Nomic Embed Text.
    """

    if task not in ("document", "query"):
        raise ValueError("task must be 'document' or 'query'")

    prefix = (
        "search_query: "
        if task == "query"
        else "search_document: "
    )

    formatted_texts = [
        prefix + text for text in texts
    ]

    response = ollama.embed(
        model="nomic-embed-text",
        input=formatted_texts
    )

    return response["embeddings"]

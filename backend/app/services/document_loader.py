
from pathlib import Path
from pypdf import PdfReader


# Locate the project's documents folder
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DOCUMENTS_DIR = PROJECT_ROOT / "data" / "documents"


def load_document(file_path: Path) -> str:
    """Extract text from a TXT or PDF document."""

    if file_path.suffix.lower() == ".txt":
        return file_path.read_text(encoding="utf-8")

    elif file_path.suffix.lower() == ".pdf":
        reader = PdfReader(str(file_path))

        pages = []
        for page in reader.pages:
            pages.append(page.extract_text() or "")

        return "\n".join(pages)

    else:
        raise ValueError(
            f"Unsupported file format: {file_path.suffix}"
        )


def load_all_documents() -> list[dict]:
    """Load all supported documents from the documents folder."""

    documents = []

    for file_path in DOCUMENTS_DIR.iterdir():

        if file_path.suffix.lower() not in [".txt", ".pdf"]:
            continue

        text = load_document(file_path)

        if text.strip():
            documents.append({
                "filename": file_path.name,
                "content": text
            })

    return documents

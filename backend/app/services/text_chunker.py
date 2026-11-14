
import re


def chunk_text(
    text: str,
    chunk_size: int = 500,
    overlap: int = 80
) -> list[str]:

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    # Split the document at level-two Markdown headings.
    sections = re.split(
    r"(?=^(?:##\s|\d+\.\s+[A-Z]))",
    text.strip(),
    flags=re.MULTILINE
    )

    chunks = []

    for section in sections:
        section = section.strip()

        if not section:
            continue

        # Keep each section's heading with its content.
        paragraphs = re.split(r"\n\s*\n", section)

        current_chunk = ""

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            candidate = (
                current_chunk + "\n\n" + paragraph
                if current_chunk else paragraph
            )

            if len(candidate) <= chunk_size:
                current_chunk = candidate
                continue

            if current_chunk:
                chunks.append(current_chunk)

            # Split unusually long paragraphs at word boundaries.
            words = paragraph.split()
            current_words = []

            for word in words:
                candidate = " ".join(current_words + [word])

                if len(candidate) <= chunk_size:
                    current_words.append(word)
                else:
                    if current_words:
                        previous_chunk = " ".join(current_words)
                        chunks.append(previous_chunk)

                        overlap_words = []
                        overlap_length = 0

                        for previous_word in reversed(current_words):
                            if (
                                overlap_length
                                + len(previous_word) + 1
                                > overlap
                            ):
                                break

                            overlap_words.insert(0, previous_word)
                            overlap_length += len(previous_word) + 1

                        current_words = overlap_words + [word]
                    else:
                        current_words = [word]

            current_chunk = " ".join(current_words)

        if current_chunk:
            chunks.append(current_chunk)

    return chunks

from typing import List

def process_extracted_text_for_llm(
    markdown_text: str, chunk_size: int = 12000
) -> List[str]:
    """Replaces legacy hard-slicing (raw_text[:8000]) with full semantic chunking."""
    if not markdown_text:
        return []

    # Chunk text cleanly by page markers or paragraph blocks without losing content
    pages = markdown_text.split("---")
    chunks = []
    current_chunk = ""

    for page in pages:
        if len(current_chunk) + len(page) <= chunk_size:
            current_chunk += page + "\n---"
        else:
            if current_chunk:
                chunks.append(current_chunk)
            current_chunk = page + "\n---"

    if current_chunk:
        chunks.append(current_chunk)

    return chunks

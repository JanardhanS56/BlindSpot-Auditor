from pathlib import Path
import re


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    """Splits arbitrary text into overlapping chunks respecting paragraph and sentence boundaries."""
    text = text.strip()
    if not text:
        return []

    if len(text) <= chunk_size:
        return [text]

    # Split by double newline (paragraphs)
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current_chunk: list[str] = []
    current_length = 0

    for para in paragraphs:
        para_len = len(para)

        # If a single paragraph is too big, split by sentences
        if para_len > chunk_size:
            sentences = re.split(r"(?<=[.!?])\s+", para)
            for sentence in sentences:
                sent_len = len(sentence)
                if current_length + sent_len + 1 > chunk_size and current_chunk:
                    chunk_str = " ".join(current_chunk)
                    chunks.append(chunk_str)
                    # Overlap handling
                    overlap_tokens = []
                    overlap_len = 0
                    for s in reversed(current_chunk):
                        if overlap_len + len(s) < overlap:
                            overlap_tokens.insert(0, s)
                            overlap_len += len(s)
                        else:
                            break
                    current_chunk = overlap_tokens
                    current_length = sum(len(s) for s in current_chunk)

                current_chunk.append(sentence)
                current_length += sent_len + 1
        else:
            if current_length + para_len + 2 > chunk_size and current_chunk:
                chunk_str = "\n\n".join(current_chunk)
                chunks.append(chunk_str)
                # Keep last paragraph for overlap if it fits
                if len(current_chunk[-1]) <= overlap:
                    current_chunk = [current_chunk[-1]]
                    current_length = len(current_chunk[0])
                else:
                    current_chunk = []
                    current_length = 0

            current_chunk.append(para)
            current_length += para_len + 2

    if current_chunk:
        chunk_str = "\n\n".join(current_chunk)
        chunks.append(chunk_str)

    return chunks


def chunk_markdown(filepath: str, chunk_size: int = 1000, overlap: int = 200) -> list[dict]:
    """Parses a markdown file, splits by headers (## ), and creates structured chunks."""
    path = Path(filepath)
    if not path.exists():
        raise FileNotFoundError(f"Markdown file not found: {filepath}")

    raw_text = path.read_text(encoding="utf-8")
    source_name = path.name

    # Regex to split on markdown ## headers
    header_pattern = re.compile(r"^(##\s+[^\n]+)", re.MULTILINE)
    splits = header_pattern.split(raw_text)

    chunks_data: list[dict] = []

    # If document has no ## headers
    if len(splits) == 1:
        text_chunks = chunk_text(raw_text, chunk_size=chunk_size, overlap=overlap)
        for idx, tc in enumerate(text_chunks):
            chunks_data.append({
                "content": tc,
                "section": "General",
                "source": source_name,
                "chunk_index": idx,
            })
        return chunks_data

    # First segment before any ## header
    preamble = splits[0].strip()
    if preamble:
        for tc in chunk_text(preamble, chunk_size=chunk_size, overlap=overlap):
            chunks_data.append({
                "content": tc,
                "section": "Overview",
                "source": source_name,
                "chunk_index": len(chunks_data),
            })

    # Pairs of (header, body)
    for i in range(1, len(splits), 2):
        header_raw = splits[i].strip()
        section_title = re.sub(r"^##\s*", "", header_raw)
        body = splits[i + 1].strip() if i + 1 < len(splits) else ""

        full_section_text = f"{header_raw}\n\n{body}".strip()
        sub_chunks = chunk_text(full_section_text, chunk_size=chunk_size, overlap=overlap)

        for sc in sub_chunks:
            chunks_data.append({
                "content": sc,
                "section": section_title,
                "source": source_name,
                "chunk_index": len(chunks_data),
            })

    return chunks_data

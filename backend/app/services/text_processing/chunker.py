import re
import uuid
import logging
from typing import List, Dict, Optional, Tuple

from app.core.config import settings

logger = logging.getLogger(__name__)

TARGET_CHUNK_TOKENS = 360
OVERLAP_TOKENS = 70

MIN_CHUNK_CHARS      = settings.MIN_CHUNK_LENGTH
MIN_ALPHA_RATIO      = 0.10

_HEADING_RE: List[tuple] = [
    (re.compile(r"^#{1}\s+(.+)$",   re.MULTILINE), 1),
    (re.compile(r"^#{2}\s+(.+)$",   re.MULTILINE), 2),
    (re.compile(r"^#{3}\s+(.+)$",   re.MULTILINE), 3),
    (re.compile(r"^#{4}\s+(.+)$",   re.MULTILINE), 4),
]

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')


def _get_tokenizer():
    try:
        import tiktoken
        return tiktoken.get_encoding("cl100k_base")
    except Exception:
        return None


_TOKENIZER = _get_tokenizer()


def _token_len(text: str) -> int:
    if _TOKENIZER is None:
        return max(1, int(len(text) / 4))
    try:
        return len(_TOKENIZER.encode(text))
    except Exception:
        return max(1, int(len(text) / 4))


def _offset_in_parent(parent: str, part: str, start_hint: int) -> int:
    if not part:
        return start_hint
    pos = parent.find(part, start_hint)
    if pos >= 0:
        return pos
    pos = parent.find(part)
    return pos if pos >= 0 else start_hint

def chunk_text(
    text: str,
    use_semantic_chunking: bool = False,
    source_type: str = "prose",
) -> List[Dict]:
    if not text or not text.strip():
        return []

    text = text.strip()

    if source_type in ("csv", "excel", "xlsx", "xls", "ods"):
        return _chunk_structured(text)

    if _has_markdown_headings(text):
        logger.info("Detected Markdown structure, using heading-aware chunking")
        sections = _split_on_headings(text)
    else:
        logger.info("No structure detected, using paragraph-based chunking")
        sections = [{"title": None, "level": 0, "content": text}]

    raw_chunks: List[Dict] = []
    for section in sections:
        raw_chunks.extend(
            _process_section(
                section["content"],
                section["title"],
                use_semantic_chunking=use_semantic_chunking,
                full_text=text,
            )
        )

    filtered = _filter_quality(raw_chunks)

    total = len(filtered)
    for i, chunk in enumerate(filtered):
        chunk["chunk_index"] = i
        chunk["total_chunks"] = total

    logger.info(
        "Created %d chunks from %d sections (target=%d tokens, overlap=%d, filtered=%d)",
        total, len(sections), TARGET_CHUNK_TOKENS, OVERLAP_TOKENS, len(raw_chunks) - total,
    )
    return filtered

def _chunk_structured(text: str) -> List[Dict]:
    sections = re.split(r"={3,}", text)

    schema_header = ""
    for sec in sections:
        stripped = sec.strip()
        if stripped and ("Columns:" in stripped or "Shape:" in stripped):
            schema_header = stripped.split("\n")[0]
            break

    chunks: List[Dict] = []
    cursor = 0
    for sec in sections:
        sec = sec.strip()
        if not sec or len(sec) < 30:
            continue
        body = (
            f"{schema_header}\n\n{sec}"
            if schema_header and schema_header not in sec
            else sec
        )
        start = _offset_in_parent(text, sec, cursor)
        end = start + len(sec)
        cursor = end
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "text": body,
                "section_title": sec.split("\n")[0].strip()[:80],
                "chunk_type": "structured",
                "char_start": start,
                "char_end": end,
            }
        )

    if not chunks and text.strip():
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "section_title": "Structured Data",
                "chunk_type": "structured",
                "char_start": 0,
                "char_end": len(text),
            }
        )

    total = len(chunks)
    for i, c in enumerate(chunks):
        c["chunk_index"] = i
        c["total_chunks"] = total

    logger.info("Structured chunking produced %d chunks", total)
    return chunks

def _has_markdown_headings(text: str) -> bool:
    return any(pat.search(text) for pat, _ in _HEADING_RE)

def _split_on_headings(text: str) -> List[Dict]:
    heading_matches: List[tuple] = []
    for pat, level in _HEADING_RE:
        for m in pat.finditer(text):
            heading_matches.append((m.start(), m.end(), level, m.group(1).strip()))

    if not heading_matches:
        return [{"title": None, "level": 0, "content": text}]

    heading_matches.sort(key=lambda x: (x[0], x[2]))

    sections: List[Dict] = []
    positions: List[tuple] = []

    prev_end = 0
    for start, end, level, title in heading_matches:
        positions.append((prev_end, start, end, level, title))
        prev_end = end

    first_start = heading_matches[0][0]
    preamble = text[:first_start].strip()
    if preamble:
        sections.append({"title": None, "level": 0, "content": preamble})

    for i, (_, hstart, hend, level, title) in enumerate(positions):
        next_hstart = (
            heading_matches[i + 1][0]
            if i + 1 < len(heading_matches)
            else len(text)
        )
        content = text[hend:next_hstart].strip()
        sections.append({"title": title, "level": level, "content": content})

    return sections or [{"title": None, "level": 0, "content": text}]

def _process_section(
    content: str,
    section_title: Optional[str],
    use_semantic_chunking: bool = False,
    full_text: Optional[str] = None,
) -> List[Dict]:
    if not content.strip():
        return []

    blocks: List[str] = [p.strip() for p in content.split("\n\n") if p.strip()]
    if not blocks:
        return []

    source_text = full_text if full_text is not None else content
    content_anchor = source_text.find(content)
    if content_anchor < 0:
        content_anchor = 0

    block_offsets: List[Tuple[str, int, int]] = []
    cursor = content_anchor
    for block in blocks:
        bstart = _offset_in_parent(source_text, block, cursor)
        bend = bstart + len(block)
        cursor = bend
        block_offsets.append((block, bstart, bend))

    output: List[Dict] = []
    current_parts: List[Tuple[str, int, int]] = []
    current_tokens = 0

    def _flush() -> None:
        nonlocal current_parts, current_tokens
        if not current_parts:
            return
        chunk_text_value = "\n\n".join(part for part, _, _ in current_parts).strip()
        if not chunk_text_value:
            current_parts = []
            current_tokens = 0
            return
        start = current_parts[0][1]
        end = current_parts[-1][2]
        output.append(_make_chunk(chunk_text_value, section_title, start, end))

        overlap_parts: List[Tuple[str, int, int]] = []
        overlap_tokens = 0
        for part in reversed(current_parts):
            ptok = _token_len(part[0])
            if overlap_parts and overlap_tokens + ptok > OVERLAP_TOKENS:
                break
            overlap_parts.insert(0, part)
            overlap_tokens += ptok

        current_parts = overlap_parts
        current_tokens = overlap_tokens

    for block, bstart, bend in block_offsets:
        block_parts = _split_semantic(block) if use_semantic_chunking else [block]
        for piece in block_parts:
            piece = piece.strip()
            if not piece:
                continue
            ptokens = _token_len(piece)

            if ptokens > TARGET_CHUNK_TOKENS:
                # Oversized piece: sentence-level fallback with token windows.
                sentence_splits = _split_sentences(piece, TARGET_CHUNK_TOKENS, OVERLAP_TOKENS)
                piece_cursor = _offset_in_parent(block, piece, 0)
                for split_part in sentence_splits:
                    split_part = split_part.strip()
                    if not split_part:
                        continue
                    sstart_local = _offset_in_parent(piece, split_part, piece_cursor)
                    send_local = sstart_local + len(split_part)
                    piece_cursor = send_local
                    sstart = bstart + max(0, sstart_local)
                    send = bstart + min(len(block), send_local)
                    split_tokens = _token_len(split_part)
                    if current_tokens + split_tokens > TARGET_CHUNK_TOKENS and current_parts:
                        _flush()
                    current_parts.append((split_part, sstart, send))
                    current_tokens += split_tokens
                continue

            if current_tokens + ptokens > TARGET_CHUNK_TOKENS and current_parts:
                _flush()

            pstart_local = _offset_in_parent(block, piece, 0)
            pend_local = pstart_local + len(piece)
            pstart = bstart + max(0, pstart_local)
            pend = bstart + min(len(block), pend_local)
            current_parts.append((piece, pstart, pend))
            current_tokens += ptokens

    _flush()
    return output


def _make_chunk(
    text: str,
    section_title: Optional[str],
    char_start: Optional[int] = None,
    char_end: Optional[int] = None,
) -> Dict:
    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "section_title": section_title,
        "char_start": char_start,
        "char_end": char_end,
    }


def _split_sentences(text: str, chunk_size_tokens: int, overlap_tokens: int) -> List[str]:
    sentences = _SENTENCE_SPLIT_RE.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    current_size = 0

    for sent in sentences:
        sent_size = _token_len(sent)

        if current_size + sent_size > chunk_size_tokens and current:
            chunks.append(" ".join(current))

            carry: List[str] = []
            carry_size = 0
            for s in reversed(current):
                stoks = _token_len(s)
                if carry and carry_size + stoks > overlap_tokens:
                    break
                carry.insert(0, s)
                carry_size += stoks

            current = carry
            current_size = carry_size

        current.append(sent)
        current_size += sent_size

    if current:
        chunks.append(" ".join(current))

    return chunks or [text]

def _split_semantic(text: str) -> List[str]:
    sentences = _SENTENCE_SPLIT_RE.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if len(sentences) <= 3:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    current_tokens = 0
    for sent in sentences:
        stoks = _token_len(sent)
        if current and current_tokens + stoks > max(120, TARGET_CHUNK_TOKENS // 2):
            chunks.append(" ".join(current).strip())
            current = []
            current_tokens = 0
        current.append(sent)
        current_tokens += stoks

    if current:
        chunks.append(" ".join(current).strip())

    return chunks or [text]

def _filter_quality(chunks: List[Dict]) -> List[Dict]:
    kept: List[Dict] = []

    for chunk in chunks:
        text = chunk["text"]

        if len(text) < MIN_CHUNK_CHARS:
            continue
        if len(text.strip()) < MIN_CHUNK_CHARS:
            continue

        alpha = sum(c.isalpha() for c in text)
        if alpha / len(text) < MIN_ALPHA_RATIO:
            continue

        kept.append(chunk)

    if chunks and not kept:
        logger.warning(
            "All %d chunks failed quality filter — keeping top 3 by alpha ratio",
            len(chunks),
        )
        candidates = [c for c in chunks if len(c["text"]) > 50]
        if candidates:
            candidates.sort(
                key=lambda c: sum(ch.isalpha() for ch in c["text"]) / max(len(c["text"]), 1),
                reverse=True,
            )
            kept = candidates[:3]

    logger.info("Filtered %d low-quality chunks", len(chunks) - len(kept))
    return kept

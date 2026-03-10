import re
import uuid
import logging
from typing import List, Dict, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

CHARS_PER_TOKEN = 4

TARGET_CHUNK_TOKENS  = 500
OVERLAP_TOKENS       = settings.CHUNK_OVERLAP_TOKENS

TARGET_CHUNK_CHARS   = TARGET_CHUNK_TOKENS * CHARS_PER_TOKEN
OVERLAP_CHARS        = OVERLAP_TOKENS * CHARS_PER_TOKEN
MAX_PARAGRAPH_CHARS  = 800 * CHARS_PER_TOKEN

MIN_CHUNK_CHARS      = settings.MIN_CHUNK_LENGTH
MIN_ALPHA_RATIO      = 0.10

_HEADING_RE: List[tuple] = [
    (re.compile(r"^#{1}\s+(.+)$",   re.MULTILINE), 1),
    (re.compile(r"^#{2}\s+(.+)$",   re.MULTILINE), 2),
    (re.compile(r"^#{3}\s+(.+)$",   re.MULTILINE), 3),
    (re.compile(r"^#{4}\s+(.+)$",   re.MULTILINE), 4),
]

_SENTENCE_SPLIT_RE = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')

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
            )
        )

    filtered = _filter_quality(raw_chunks)

    total = len(filtered)
    for i, chunk in enumerate(filtered):
        chunk["chunk_index"] = i
        chunk["total_chunks"] = total

    logger.info(
        "Created %d chunks from %d sections (filtered %d low-quality)",
        total, len(sections), len(raw_chunks) - total,
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
    for sec in sections:
        sec = sec.strip()
        if not sec or len(sec) < 30:
            continue
        body = (
            f"{schema_header}\n\n{sec}"
            if schema_header and schema_header not in sec
            else sec
        )
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "text": body,
                "section_title": sec.split("\n")[0].strip()[:80],
                "chunk_type": "structured",
            }
        )

    if not chunks and text.strip():
        chunks.append(
            {
                "id": str(uuid.uuid4()),
                "text": text,
                "section_title": "Structured Data",
                "chunk_type": "structured",
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
) -> List[Dict]:
    if not content.strip():
        return []

    paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
    chunks: List[Dict] = []

    for para in paragraphs:
        para_chars = len(para)

        if para_chars <= TARGET_CHUNK_CHARS:
            chunks.append(_make_chunk(para, section_title))

        elif para_chars <= MAX_PARAGRAPH_CHARS:
            if use_semantic_chunking:
                for part in _split_semantic(para):
                    chunks.append(_make_chunk(part, section_title))
            else:
                chunks.append(_make_chunk(para, section_title))

        else:
            for part in _split_sentences(para, TARGET_CHUNK_CHARS, OVERLAP_CHARS):
                chunks.append(_make_chunk(part, section_title))

    return chunks

def _make_chunk(text: str, section_title: Optional[str]) -> Dict:
    return {
        "id": str(uuid.uuid4()),
        "text": text,
        "section_title": section_title,
    }

def _split_sentences(text: str, chunk_size: int, overlap: int) -> List[str]:
    sentences = _SENTENCE_SPLIT_RE.split(text)
    sentences = [s.strip() for s in sentences if s.strip()]

    if not sentences:
        return [text]

    chunks: List[str] = []
    current: List[str] = []
    current_size = 0

    for sent in sentences:
        sent_size = len(sent)

        if current_size + sent_size > chunk_size and current:
            chunks.append(" ".join(current))

            carry: List[str] = []
            carry_size = 0
            for s in reversed(current):
                if carry_size + len(s) > overlap:
                    break
                carry.insert(0, s)
                carry_size += len(s)

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
    window, step = 3, 2
    for start in range(0, len(sentences), step):
        group = sentences[start : start + window]
        part = " ".join(group).strip()
        if part:
            chunks.append(part)

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

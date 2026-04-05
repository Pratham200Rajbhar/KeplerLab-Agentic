"""Lightweight BM25-like lexical scoring for hybrid retrieval."""
from __future__ import annotations

import math
import re
import logging
from collections import Counter, defaultdict
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

# Stop words for English (minimal set)
_STOP_WORDS = frozenset({
    "a", "an", "the", "is", "it", "in", "of", "to", "and", "or", "for",
    "on", "at", "by", "with", "from", "that", "this", "be", "are", "was",
    "were", "been", "being", "have", "has", "had", "do", "does", "did",
    "will", "would", "could", "should", "may", "might", "shall", "can",
    "not", "no", "but", "if", "so", "as", "its",
})

_TOKENIZE_RE = re.compile(r"[a-zA-Z0-9]+")


def tokenize(text: str) -> List[str]:
    """Tokenize text into lowercase terms, removing stop words."""
    tokens = _TOKENIZE_RE.findall(text.lower())
    return [t for t in tokens if t not in _STOP_WORDS and len(t) > 1]


class LexicalIndex:
    """
    Simple inverted index for BM25-like scoring.
    Built in-memory from chunks; cheap to construct per notebook.
    """

    def __init__(self):
        self._doc_count = 0
        self._avg_doc_len = 0.0
        self._doc_lens: Dict[str, int] = {}
        self._doc_texts: Dict[str, str] = {}
        self._inverted: Dict[str, set[str]] = defaultdict(set)
        self._term_freqs: Dict[str, Counter] = {}

    def add_document(self, doc_id: str, text: str) -> None:
        """Add a document to the index."""
        tokens = tokenize(text)
        if not tokens:
            return

        self._doc_count += 1
        self._doc_lens[doc_id] = len(tokens)
        self._doc_texts[doc_id] = text
        self._term_freqs[doc_id] = Counter(tokens)

        for token in set(tokens):
            self._inverted[token].add(doc_id)

        # Recompute avg doc length
        total = sum(self._doc_lens.values())
        self._avg_doc_len = total / max(self._doc_count, 1)

    def search(self, query: str, top_k: int = 10) -> List[Tuple[str, float, str]]:
        """
        Search the index.
        Returns list of (doc_id, score, text) tuples sorted by score descending.
        """
        query_tokens = tokenize(query)
        if not query_tokens or self._doc_count == 0:
            return []

        scores: Dict[str, float] = defaultdict(float)

        k1 = 1.5
        b = 0.75

        for term in query_tokens:
            if term not in self._inverted:
                continue

            df = len(self._inverted[term])
            idf = math.log((self._doc_count - df + 0.5) / (df + 0.5) + 1.0)

            for doc_id in self._inverted[term]:
                tf = self._term_freqs[doc_id].get(term, 0)
                doc_len = self._doc_lens[doc_id]
                numerator = tf * (k1 + 1)
                denominator = tf + k1 * (1 - b + b * doc_len / self._avg_doc_len)
                scores[doc_id] += idf * (numerator / denominator)

        sorted_docs = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:top_k]

        return [
            (doc_id, score, self._doc_texts.get(doc_id, ""))
            for doc_id, score in sorted_docs
        ]

    @property
    def doc_count(self) -> int:
        return self._doc_count

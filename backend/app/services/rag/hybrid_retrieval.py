from __future__ import annotations

import math
import re
from typing import Dict, List, Tuple


def rewrite_query_variants(query: str, max_variants: int = 2) -> List[str]:
    """Generate lightweight lexical variants for robust hybrid retrieval."""
    base = query.strip()
    if not base:
        return []

    variants: List[str] = [base]
    lowered = base.lower()

    replacements: List[Tuple[str, str]] = [
        ("difference", "compare"),
        ("compare", "difference"),
        ("summarize", "summary"),
        ("explain", "explanation"),
        ("analyze", "analysis"),
        ("analyse", "analysis"),
    ]

    for src, dst in replacements:
        if src in lowered and len(variants) < max_variants + 1:
            variants.append(re.sub(src, dst, base, flags=re.IGNORECASE))

    token_terms = [t for t in re.findall(r"[a-zA-Z0-9_]{3,}", base) if t]
    if token_terms and len(variants) < max_variants + 1:
        variants.append(" ".join(token_terms[:8]))

    deduped: List[str] = []
    seen = set()
    for q in variants:
        key = q.strip().lower()
        if key and key not in seen:
            deduped.append(q.strip())
            seen.add(key)
        if len(deduped) >= max_variants + 1:
            break
    return deduped


def adaptive_retrieval_k(query: str, total_in_collection: int, base_k: int) -> int:
    """Scale retrieval depth for more complex queries."""
    tokens = [t for t in re.findall(r"[a-zA-Z0-9_]+", query) if t]
    token_count = len(tokens)
    complexity_terms = {
        "compare", "contrast", "difference", "versus", "tradeoff",
        "analyze", "analysis", "why", "how", "multi", "across",
    }
    complexity_hits = sum(1 for t in tokens if t.lower() in complexity_terms)

    multiplier = 1.0
    if token_count >= 18:
        multiplier += 0.25
    if token_count >= 28:
        multiplier += 0.25
    if complexity_hits >= 2:
        multiplier += 0.25

    target = int(round(base_k * multiplier))
    return max(1, min(target, total_in_collection))


def tokenize_lexical(text: str) -> List[str]:
    return [t for t in re.findall(r"[a-z0-9_]{2,}", text.lower()) if t]


def bm25_like_scores(query: str, docs: List[str]) -> List[float]:
    if not docs:
        return []
    q_terms = tokenize_lexical(query)
    if not q_terms:
        return [0.0 for _ in docs]

    docs_terms = [tokenize_lexical(d) for d in docs]
    doc_lens = [len(toks) for toks in docs_terms]
    avgdl = sum(doc_lens) / max(1, len(doc_lens))

    df: Dict[str, int] = {}
    for toks in docs_terms:
        for tok in set(toks):
            df[tok] = df.get(tok, 0) + 1

    n_docs = len(docs)
    k1 = 1.2
    b = 0.75
    scores: List[float] = []

    for toks in docs_terms:
        tf: Dict[str, int] = {}
        for tok in toks:
            tf[tok] = tf.get(tok, 0) + 1
        dl = len(toks)
        score = 0.0
        for term in q_terms:
            freq = tf.get(term, 0)
            if freq <= 0:
                continue
            term_df = df.get(term, 0)
            idf = math.log(1.0 + ((n_docs - term_df + 0.5) / (term_df + 0.5)))
            denom = freq + k1 * (1 - b + b * (dl / max(1.0, avgdl)))
            score += idf * ((freq * (k1 + 1)) / max(1e-9, denom))
        scores.append(float(score))
    return scores


def reciprocal_rank_fusion(ranks: Dict[str, List[int]], k: int = 60) -> Dict[str, float]:
    fused: Dict[str, float] = {}
    for item_id, rank_list in ranks.items():
        fused[item_id] = sum(1.0 / (k + r) for r in rank_list)
    return fused

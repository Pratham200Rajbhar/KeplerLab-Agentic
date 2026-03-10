from __future__ import annotations

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

MIN_CITATION_DENSITY = 100

MIN_CITATIONS_REQUIRED = 1

def validate_citations(
    response: str,
    num_sources: int,
    strict: bool = True,
) -> Dict:
    result = {
        "is_valid": False,
        "cited_sources": [],
        "missing_citations": False,
        "invalid_sources": [],
        "citation_density": 0.0,
        "error_message": None,
    }
    
    if _is_not_found_response(response):
        result["is_valid"] = True
        logger.info("Response is a valid 'not found' answer")
        return result
    
    citation_pattern = r'\[SOURCE\s+(\d+)\]'
    matches = re.findall(citation_pattern, response)
    
    if not matches:
        result["missing_citations"] = True
        result["error_message"] = "No source citations found in response"
        logger.warning("Response has no citations")
        return result
    
    cited_sources = []
    invalid_sources = []
    
    for match in matches:
        source_num = int(match)
        if source_num < 1 or source_num > num_sources:
            invalid_sources.append(source_num)
        elif source_num not in cited_sources:
            cited_sources.append(source_num)
    
    result["cited_sources"] = sorted(cited_sources)
    result["invalid_sources"] = invalid_sources
    
    if invalid_sources:
        result["error_message"] = (
            f"Response cites invalid sources: {invalid_sources}. "
            f"Valid range: 1-{num_sources}"
        )
        logger.error(f"Invalid source citations: {invalid_sources}")
        return result
    
    word_count = len(response.split())
    result["citation_density"] = (len(matches) / max(word_count, 1)) * 100
    
    if strict:
        if word_count > 20 and len(cited_sources) < MIN_CITATIONS_REQUIRED:
            result["missing_citations"] = True
            result["error_message"] = (
                f"Insufficient citations: found {len(cited_sources)}, "
                f"required at least {MIN_CITATIONS_REQUIRED}"
            )
            logger.warning(
                f"Insufficient citations: {len(cited_sources)}/{MIN_CITATIONS_REQUIRED}"
            )
            return result
        
        if word_count > 50 and result["citation_density"] < (100 / MIN_CITATION_DENSITY):
            result["error_message"] = (
                f"Low citation density: {result['citation_density']:.2f} "
                f"citations per 100 words (minimum: {100/MIN_CITATION_DENSITY:.2f})"
            )
            logger.warning(
                f"Low citation density: {result['citation_density']:.2f}"
            )
            return result
    
    result["is_valid"] = True
    logger.info(
        f"Citations validated: {len(cited_sources)} sources, "
        f"density={result['citation_density']:.2f}"
    )
    
    return result

def _is_not_found_response(response: str) -> bool:
    response_lower = response.lower().strip()
    
    not_found_patterns = [
        "i could not find",
        "i couldn't find",
        "not found in the provided",
        "not available in the sources",
        "the sources do not contain",
        "there is no information",
        "the provided materials do not",
    ]
    
    return any(pattern in response_lower for pattern in not_found_patterns)

def extract_uncited_text(response: str) -> List[str]:
    citation_pattern = r'\[SOURCE\s+\d+\]'
    segments = re.split(citation_pattern, response)
    
    uncited = [seg.strip() for seg in segments if len(seg.strip()) > 50]
    
    logger.debug(f"Found {len(uncited)} potentially uncited text segments")
    return uncited

def suggest_citation_placement(response: str, num_sources: int) -> str:
    sentences = re.split(r'(?<=[.!?])\s+', response)
    
    annotated = []
    for sentence in sentences:
        if not re.search(r'\[SOURCE\s+\d+\]', sentence):
            annotated.append(f"{sentence} [CITATION NEEDED?]")
        else:
            annotated.append(sentence)
    
    return " ".join(annotated)

def check_citation_coverage(
    cited_sources: List[int],
    num_sources: int,
    min_coverage: float = 0.5,
) -> Tuple[bool, float]:
    unique_cited = len(set(cited_sources))
    coverage = unique_cited / max(num_sources, 1)
    
    is_sufficient = coverage >= min_coverage or num_sources < 3
    
    logger.debug(
        f"Citation coverage: {unique_cited}/{num_sources} "
        f"({coverage:.1%}) - sufficient={is_sufficient}"
    )
    
    return is_sufficient, coverage

def build_validation_error_message(validation_result: Dict) -> str:
    if validation_result["is_valid"]:
        return "Citations are valid"
    
    error = validation_result.get("error_message", "Unknown validation error")
    
    suggestions = []
    
    if validation_result["missing_citations"]:
        suggestions.append(
            "Please cite sources using [SOURCE 1], [SOURCE 2], etc."
        )
    
    if validation_result["invalid_sources"]:
        suggestions.append(
            "Ensure all citations reference valid source numbers"
        )
    
    if validation_result["citation_density"] < 1.0:
        suggestions.append(
            "Add more citations to support your claims"
        )
    
    if suggestions:
        error += "\n\nSuggestions:\n- " + "\n- ".join(suggestions)
    
    return error

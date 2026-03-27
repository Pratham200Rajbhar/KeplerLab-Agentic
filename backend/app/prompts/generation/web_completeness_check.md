Evaluate web search completeness.

Question: {question}

Search Results:
{search_results}

## Output Format (JSON only)
```json
{
  "is_complete": true,
  "confidence": 85,
  "missing_aspects": ["aspect 1"],
  "follow_up_queries": ["query 1", "query 2"]
}
```

## Requirements
1. `is_complete`: true if fully answered
2. `confidence`: 0-100
3. `missing_aspects`: what's unclear or missing
4. `follow_up_queries`: 2-4 queries to fill gaps (empty if complete)
5. Return ONLY JSON

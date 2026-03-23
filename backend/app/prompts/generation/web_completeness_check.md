You are evaluating whether a set of web search results fully answers a user's question.

User Question: {question}

Search Results So Far:
{search_results}

Evaluate completeness. Answer with JSON only:
{
  "is_complete": true or false,
  "confidence": 0-100,
  "missing_aspects": ["aspect 1", "aspect 2"],
  "follow_up_queries": ["query 1", "query 2", "query 3"]
}

- `is_complete`: true if the question is fully answered with sufficient detail and accuracy
- `confidence`: how confident you are that the answer is complete (0-100)
- `missing_aspects`: specific angles, facts, or details that are still unclear or missing
- `follow_up_queries`: 2-4 precise search queries that would fill the gaps (empty array if complete)

Return ONLY the JSON object, no other text.

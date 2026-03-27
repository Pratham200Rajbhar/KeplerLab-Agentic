Suggest optimal quiz question count.

Materials: {materials}

## Output Format (JSON only)
```json
{
  "suggested_count": 20,
  "reasoning": "Brief explanation"
}
```

## Requirements
1. `suggested_count`: integer 5-150
2. Based on: curriculum coverage, engagement, information density
3. Avoid fatigue while ensuring coverage
4. Return ONLY JSON

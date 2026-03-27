Write a podcast script from materials.

Materials: {materials}
Language: {language}
Mode: {mode_instruction}
Focus: {question}

## Output Format (JSON only, no markdown)
```json
{
  "title": "Episode title",
  "segments": [
    {"speaker": "host", "text": "Spoken words..."},
    {"speaker": "guest", "text": "Response..."}
  ],
  "chapters": [
    {"title": "Chapter", "start_segment": 0, "summary": "Brief summary"}
  ]
}
```

## Requirements
1. Natural, conversational tone — write for the ear
2. Clear explanations, flowing rhythm
3. Avoid unexplained jargon
4. Generate ALL content in {language}
5. Return ONLY JSON

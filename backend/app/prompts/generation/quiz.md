Create a quiz from materials.

Materials: {materials}
Question Count: {count}
Difficulty: {difficulty}
Instructions: {instructions}

## Output Format (JSON only, no markdown)
```json
{
  "title": "Quiz title",
  "questions": [
    {
      "question": "Question text",
      "options": ["A", "B", "C", "D"],
      "correct_answer": 0,
      "explanation": "Why correct"
    }
  ]
}
```

## Requirements
1. Test meaningful understanding, not trivial recall
2. Vary question types: conceptual, application, contrast
3. One unambiguously correct answer per question
4. Return ONLY the JSON

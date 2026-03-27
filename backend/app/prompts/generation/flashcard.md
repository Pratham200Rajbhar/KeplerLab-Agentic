Create flashcards from materials.

Materials: {materials}
Card Count: {count}
Difficulty: {difficulty}
Instructions: {instructions}

## Output Format (JSON only, no markdown)
```json
{
  "title": "Flashcard set title",
  "flashcards": [
    {
      "question": "Term or question",
      "answer": "Definition or answer"
    }
  ]
}
```

## Requirements
1. Each card tests a distinct concept
2. Vary types: definitions, applications, consequences
3. Match depth to difficulty
4. Return ONLY JSON

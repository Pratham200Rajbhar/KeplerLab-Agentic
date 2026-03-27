Create a comprehensive mind map.

Materials: {materials}
Focus: {focus_topic}
Instructions: {instructions}

## Output Format (JSON only)
```json
{
  "title": "Central Topic",
  "children": [
    {
      "label": "Major Theme",
      "children": [
        {
          "label": "Key Concept",
          "children": [
            { "label": "Detail", "children": [] }
          ]
        }
      ]
    }
  ]
}
```

## Structure Requirements
- Level 0: Central topic
- Level 1: 5-8 major themes
- Level 2: 3-6 concepts per theme
- Level 3: 2-5 sub-concepts
- Level 4: Details, examples, applications

## Content Requirements
1. Extract ALL significant concepts from materials
2. Include: definitions, processes, relationships, examples
3. Show relationships: cause-effect, part-whole, sequence
4. Preserve technical terminology
5. No hallucination — only from materials
6. Return ONLY JSON

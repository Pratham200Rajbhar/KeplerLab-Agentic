You are an expert at organizing knowledge into mind maps.

Materials: {materials}
User Intent: {user_intent}
Additional Instructions: {instructions}

Create a hierarchical mind map structure from the materials. Return it as JSON with this exact structure:
{{
  "title": "Main Mind Map Title",
  "root": {{
    "label": "Central Topic",
    "description": "Brief overview of the central topic",
    "question_hint": "What is the core idea?",
    "children": [
      {{
        "label": "Sub-topic",
        "description": "Explanation of this sub-topic",
        "question_hint": "How does this relate to the root?",
        "children": []
      }}
    ]
  }}
}}

Identify the core concept as the root. Group related ideas into meaningful branches. Keep labels concise (2-5 words max). For every node, provide a helpful 'description' and a thought-provoking 'question_hint'. Capture the full breadth of the material. Return only the JSON.

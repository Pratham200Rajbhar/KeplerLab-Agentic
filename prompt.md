# ROLE

You are a senior full-stack engineer improving the research UI of an AI agent platform.

The platform already has a research pipeline that gathers information from many websites.

We must improve the UI so users can see **which information came from which website**.

This should behave similar to:

Perplexity AI  
ChatGPT browsing  
Claude research

---

# TASK 1 — ADD CITATION SYSTEM

Modify the research response format.

The backend must return:

answer text containing citation markers

Example:

"OpenAI released GPT-4o Mini in June 2024 [1]."

Also return structured sources.

Example:

{
  "answer": "...",
  "sources": [
    {
      "id": 1,
      "title": "OpenAI GPT-4o Mini",
      "url": "https://openai.com",
      "domain": "openai.com"
    }
  ]
}

---

# TASK 2 — RENDER CITATIONS IN RESPONSE

When the assistant response contains markers like:

[1] [2] [3]

Render them as clickable citation buttons.

Example UI:

OpenAI released GPT-4o Mini in June 2024 [1].

Hover or click should highlight the source.

---

# TASK 3 — SOURCE GRID BELOW RESPONSE

At the bottom of the message show source cards.

Example:

Sources

[ openai.com ]  
[ techcrunch.com ]  
[ arxiv.org ]

Only display domain names.

Do not show full URLs.

---

# TASK 4 — LINK BEHAVIOR

When user clicks a source bubble:

open the link in a new tab.

Example:

target="_blank"

---

# TASK 5 — SOURCE HIGHLIGHT

When the user clicks citation [1] in the text:

highlight the corresponding source bubble.

---

# TASK 6 — CLEAN UI DESIGN

The UI should be minimal like:

Claude  
ChatGPT browsing  
Perplexity

Do not show raw URLs or debug logs.

---

# TASK 7 — OPTIONAL HOVER PREVIEW

If possible:

when hovering a citation number

show a small tooltip with:

source title  
domain

---

# OUTPUT

Implement:

citation markers in responses  
source bubble grid  
clickable citations  
source highlight system
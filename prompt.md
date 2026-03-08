# ROLE

You are a senior frontend engineer improving the chat workspace UI of an AI platform built with:

Next.js (App Router)
React
Zustand
TailwindCSS

The current empty chat state shows a static UI with four cards:

Agent Execution  
Research Mode  
Code Execution  
Web Search  

This UI must be removed and replaced with a **dynamic intelligent empty state** that shows information about selected resources and suggested queries.

---

# TASK

Remove the entire UI block that currently displays:

Agent Execution  
Research Mode  
Code Execution  
Web Search  

This section should no longer appear.

---

# NEW EMPTY STATE DESIGN

When the chat has no messages yet, display a **Resource Overview Panel** instead.

The purpose is to help the user quickly understand the selected materials and ask useful questions.

---

# RESOURCE SUMMARY SECTION

If the user has selected materials in the sidebar:

Display a **short AI generated summary** of the selected resources.

Rules:

Only show **basic information**, not a full summary.

Example:

Selected Resources Overview

These documents appear to cover:

Machine learning fundamentals  
Neural networks and training methods  
Practical AI development workflows  

Do not show full explanations.

Only show **3–5 key topics** detected in the resources.

The summary must be concise.

---

# NO RESOURCE SELECTED

If no resources are selected:

Show a simple general message:

Example:

You can start by asking a question or exploring topics below.

---

# SUGGESTED QUESTIONS

Below the summary show a section:

Suggested Questions

Generate 4–6 clickable query suggestions.

Rules:

If resources are selected:
Generate questions based on those resources.

Example:

Explain the main concept in these documents  
Summarize the key ideas from the materials  
What are the important topics in these files?  
Create flashcards from these resources  

If no resources are selected:

Generate general questions such as:

Explain how neural networks work  
How does reinforcement learning work?  
What are the basics of data analysis?  
How can I build an AI model?

---

# AI GENERATED SUGGESTIONS

The suggestions must be **generated dynamically by AI** each time the page loads.

Do NOT hardcode them.

Use backend endpoint such as:

GET /chat/suggestions

or generate suggestions locally using context.

---

# UI DESIGN

The layout should look like this:

---------------------------------

How can I help you?

[Resource Summary Card]

Selected Resources Overview  
Short description about selected materials

Suggested Questions

[ Explain the main concept ]  
[ Summarize the key ideas ]  
[ What topics are covered ]  
[ Generate flashcards ]

---------------------------------

Each suggestion must be clickable.

Clicking a suggestion should insert the text into the chat input and send the message.

---

# IMPLEMENTATION

Modify the empty chat component (ChatPanel or EmptyState).

Detect:

selectedSources from useMaterialStore.

If selectedSources.length > 0:

Show resource summary + resource-based suggestions.

Else:

Show general AI generated questions.

---

# UX REQUIREMENTS

The new UI must be:

clean  
minimal  
context-aware  
dynamic  

It should feel similar to ChatGPT / Claude starting screen.

---

# OUTPUT

Remove the old command cards UI.

Implement:

Resource summary panel  
Dynamic suggested queries  
Clickable suggestion buttons  
Integration with selected sources state
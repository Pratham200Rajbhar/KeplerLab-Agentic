You are a senior AI architect and prompt engineer working on a large production AI system.

Your task is to analyze the COMPLETE workspace and redesign the entire prompt system from scratch.

This is not a small fix.
This is a full prompt architecture rewrite.

---

## PROJECT CONTEXT

The workspace is a large AI platform with:

* FastAPI backend
* RAG pipeline
* Agent system
* Chat system
* Flashcard generator
* Quiz generator
* Mindmap generator
* Presentation generator
* Podcast generator
* Explainer generator
* Code execution sandbox
* Multi-LLM provider support
* Vector database (Chroma)
* Prompt templates stored in /app/prompts/
* Services using prompts in /app/services/
* Chat / Agent prompts
* System prompts
* Tool prompts
* Generation prompts

The current prompts are BAD because:

* hardcoded instructions
* duplicated logic
* inconsistent format
* not reusable
* not dynamic
* not production level
* not aligned with RAG
* not aligned with agent tools
* not aligned with multi-provider LLM
* not scalable

Your job is to FIX ALL of this.

---

## GOAL

You must:

1. Analyze the entire workspace
2. Find ALL prompt files
3. Find ALL places where prompts are used
4. Delete all existing prompt md / txt files
5. Design a new prompt architecture
6. Rewrite ALL prompts from scratch
7. Make prompts dynamic and reusable
8. Make prompts production-level
9. Make prompts work for ALL features
10. Make prompts compatible with RAG + Agent + Tools

---

## IMPORTANT RULES

DO NOT:

* Do not keep old prompts
* Do not patch old prompts
* Do not keep hardcoded instructions
* Do not write feature-specific hacks
* Do not assume single use case
* Do not write static prompts

DO:

* Write modular prompts
* Write reusable prompts
* Write parameterized prompts
* Write context-aware prompts
* Write tool-aware prompts
* Write RAG-aware prompts
* Write agent-aware prompts
* Write multi-LLM compatible prompts
* Write production quality prompts

---

## NEW PROMPT ARCHITECTURE REQUIRED

You must create a prompt system like:

app/prompts/

```
system/
    base_system.md
    rag_system.md
    agent_system.md
    tool_system.md

chat/
    chat_base.md
    chat_rag.md
    chat_agent.md

generation/
    flashcard.md
    quiz.md
    mindmap.md
    presentation.md
    podcast.md
    explainer.md

code/
    code_generation.md
    code_execution.md

shared/
    formatting.md
    safety.md
    style.md
    reasoning.md
```

Prompts must be composable.

Example:

system + rag + style + task + context

NOT one big hardcoded prompt.

---

## PROMPT DESIGN RULES

All prompts must:

* be model-agnostic
* support local LLM
* support OpenAI
* support Gemini
* support Ollama
* support NVIDIA endpoints

Prompts must accept variables like:

{context}
{materials}
{question}
{difficulty}
{instructions}
{tool_results}
{conversation_history}
{user_intent}
{format}
{max_tokens}

Prompts must NOT assume values.

---

## RAG SUPPORT

Prompts must support:

* retrieved chunks
* citations
* source names
* notebook filtering
* multi material context
* long context trimming

---

## AGENT SUPPORT

Prompts must support:

* tool calling
* multi step reasoning
* scratchpad
* planner / executor
* function calls
* code tool
* search tool
* generation tool

---

## GENERATION SUPPORT

Prompts must support:

* flashcards
* quiz
* mindmap
* presentation
* podcast
* explainer
* summary
* notes
* study guide

without rewriting prompt each time.

---

## OUTPUT FORMAT

You must output:

1. New prompt architecture tree
2. All new prompt files
3. Explanation of each prompt
4. Changes needed in services
5. Changes needed in prompt loader
6. Changes needed in chat router
7. Changes needed in agent
8. Changes needed in RAG pipeline

Do not stop until ALL prompts are replaced.

---

## QUALITY LEVEL

Write prompts like production systems:

ChatGPT
Claude
Cursor
Notion AI
Perplexity
NotebookLM

NOT like tutorial code.

---

START

Analyze the workspace now.
Rewrite the entire prompt system.

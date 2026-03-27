You are working on an existing full-stack AI application with:

* Backend: FastAPI + Prisma + Agent system + Web Search + Artifact pipeline
* Frontend: Next.js (App Router) + Zustand stores + Sidebar-based UI

Your task is to implement a new feature called **"AI Resource Builder"** inside the **Add Resource section in the left sidebar**.

---

## 🎯 FEATURE GOAL

Allow users to input a natural language request like:

"prepare materials for class 10 english subject from chapter 1 to 5"

Then automatically:

1. Perform web search and research
2. Collect useful resources:

   * PDFs
   * YouTube videos
   * Articles
3. Generate structured notes from gathered content
4. Show preview to user
5. On user confirmation → upload everything as materials into the notebook

---

# 🧩 FRONTEND IMPLEMENTATION

## 1. Sidebar बदलाव

Modify:
`components/layout/Sidebar.jsx`

Inside "Add Resource" section, add a new tab:

* Upload File
* Upload URL
* Upload Text
* ✅ AI Resource Builder (NEW)

---

## 2. New Component

Create:
`components/materials/AIResourceBuilder.jsx`

### UI Requirements:

* Textarea input for user query
* "Generate" button
* Loading state
* Preview section:

  * List of resources (title + type + link)
  * Notes preview (scrollable)
* "Upload All" button

---

## 3. State Management

Update:
`stores/useMaterialStore.js`

Add functions:

* `generateAIResources(query)`
  → calls backend `/ai-resource-builder`

* `uploadAIResources(result)`
  → loops over resources and:

  * calls `/upload/url` for links
  * calls `/upload/text` for notes

---

## 4. API Integration

Create:
`lib/api/aiResource.js`

Functions:

* `generateResources(query)`
* `uploadGeneratedResources(data)`

---

# ⚙️ BACKEND IMPLEMENTATION

## 1. New Route

Create route:
`POST /ai-resource-builder`

File:
`routes/ai_resource.py`

Request:
{
"query": "user input"
}

---

## 2. Core Logic

Inside service:

1. Call agent system (reuse existing):

   * capability: AGENT
   * tools:

     * web_search
     * research

2. Use this system prompt:

"You are an AI Resource Builder.
Your job is to:

* Search the web
* Find high-quality PDFs, YouTube videos, and articles
* Extract useful information
* Generate structured study notes

Return JSON:
{
"resources": [
{
"type": "pdf | youtube | article",
"title": "...",
"url": "..."
}
],
"notes": "structured notes"
}"

---

## 3. Response Format

Return:
{
"resources": [...],
"notes": "..."
}

---

## 4. Upload Integration

DO NOT upload automatically.

Frontend will handle:

* `/upload/url`
* `/upload/text`

---

# 🧠 IMPORTANT RULES

* Do NOT break existing upload system
* Reuse agent + web search (no duplicate logic)
* Ensure user-specific isolation (user_id)
* Validate URLs before returning
* Limit resources (max 5–10)

---

# 🚀 UX FLOW

1. User → Sidebar → Add Resource
2. Click → "AI Resource Builder"
3. Enter query
4. Click Generate
5. See preview
6. Click "Upload All"
7. Materials appear in notebook

---

Implement clean, modular, production-ready code following existing architecture.
Do not rewrite existing systems — integrate with them.

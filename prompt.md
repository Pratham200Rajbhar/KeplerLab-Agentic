You are working on an existing AI platform with:

* Backend: FastAPI + Chat SSE + Agent system + Artifact storage
* Frontend: Next.js + Zustand + streaming chat UI

Your task is to implement a **slash command `/image`** for generating images using Gemini API.

---

# 🎯 FEATURE GOAL

When user types:

/image futuristic classroom with AI students

The system should:

1. Detect `/image` command
2. Extract prompt text
3. Generate image using Gemini
4. Save image as artifact
5. Stream image to chat UI
6. Display image message

---

# ⚙️ BACKEND IMPLEMENTATION

## 1. Command Parsing

File:
`services/chat_v2/router_logic.py`

Add logic:

IF message starts with "/image":

* Extract prompt:
  message.replace("/image", "").strip()

* Return:
  capability = "IMAGE_GENERATION"
  with extracted prompt

---

## 2. Modify Capability Routing

Ensure `/image` overrides ALL other routing:

* Ignore RAG
* Ignore agent
* Ignore web search

---

## 3. Image Generation Service

Use:
Gemini model → "gemini-3.1-flash-lite-preview"

Create:
`services/image_generation/gemini_service.py`

Function:
generate_image(prompt: str)

Steps:

### Step 1: Enhance Prompt

* Add style (cinematic, realistic, 3D, illustration)
* Add lighting
* Add environment
* Add camera angle

### Step 2: Generate Image

* Use Gemini API
* response_modalities = ["TEXT", "IMAGE"]

### Step 3: Extract Image

* Get base64 image data
* Convert to bytes

---

## 4. Save as Artifact

Store file:
data/artifacts/{artifact_id}.png

Create DB entry (Artifact model)

Return:
{
"artifact_id": "...",
"url": "/artifacts/{id}",
"prompt": "enhanced prompt"
}

---

## 5. Chat Orchestrator Integration

File:
`services/chat_v2/orchestrator.py`

Add:

IF capability == "IMAGE_GENERATION":

* call generate_image()
* save artifact
* stream SSE event:

{
"event": "image",
"data": {
"url": "...",
"prompt": "...",
"original_prompt": "..."
}
}

---

## 6. Streaming Behavior

Before image:

* send status event:
  "🎨 Generating image..."

After generation:

* send image event

---

## 7. Error Handling

If:

* empty prompt → return error message
* Gemini fails → fallback message

DO NOT crash chat stream

---

# 🧩 FRONTEND IMPLEMENTATION

## 1. Input Handling

User types:

/image something

NO special UI needed — reuse chat input

---

## 2. Stream Handler Update

File:
`hooks/useChat.js`

Handle:

event.type === "image"

---

## 3. Message Format

{
type: "image",
url: "...",
prompt: "...",
original_prompt: "..."
}

---

## 4. Render Image

File:
`components/chat/ChatPanel.jsx`

Render:

* Image preview
* Prompt (small text)
* Optional:

  * Download button
  * Regenerate button

---

## 5. UX Enhancements

While generating:

* show loading message

After:

* replace with image

---

# 🧠 RULES

* `/image` MUST override all logic
* Only 1 image per request (initially)
* Do NOT create new API endpoint
* Reuse artifact system
* Keep streaming consistent with chat

---

# 🚀 OPTIONAL EXTENSIONS

* `/image 3 futuristic cars` → multiple images
* `/image --style anime cat`
* `/image --hd mountain sunset`

---

# ✅ FINAL FLOW

User:
→ "/image cyberpunk city at night"

Backend:
→ detect command
→ extract prompt
→ enhance prompt
→ generate image (Gemini)
→ save artifact

Frontend:
→ receive SSE
→ render image

---

Implement clean, modular, production-ready code following existing architecture.
Do not rewrite existing systems — extend them.



this is api key = AIzaSyBF7oCyPXrbnOAHjMk_bWPRBRdFaB2zIl0
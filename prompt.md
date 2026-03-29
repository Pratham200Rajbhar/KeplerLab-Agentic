You are a senior AI systems engineer working on an advanced AI platform (KeplerLab).

Your task is to implement TWO production-grade features:

---

## FEATURE 1: AI PRESENTATION GENERATOR (IMAGE-BASED)

Goal:
Generate high-quality presentation slides as 16:9 images using Gemini image generation.

STRICT REQUIREMENTS:

* DO NOT use HTML rendering or PPTX generation
* Slides must be generated as images directly using Gemini
* Each slide must look like a real presentation slide (clean, minimal, readable)
* Maintain consistent style across all slides

---

## FEATURE 2: AI EXPLAINER VIDEO

Goal:
Generate a teacher-style explanation video using:

* slide images
* AI-generated script
* TTS audio
* ffmpeg video stitching

---

## SYSTEM CONTEXT (IMPORTANT)

Backend:

* FastAPI
* BackgroundJob system already exists
* SSE streaming system exists
* Artifact storage system exists
* RAG pipeline exists
* Podcast/TTS system exists

Frontend:

* Next.js App Router
* Zustand stores
* StudioPanel (right sidebar) is the correct place for this feature
* SSE stream parser already implemented

---

## IMPLEMENTATION REQUIREMENTS

### 1. BACKEND ARCHITECTURE

Create new module:

backend/app/services/presentation/

Files:

* slide_planner.py
* prompt_builder.py
* image_generator.py
* video_generator.py
* presentation_service.py

---

### 2. SLIDE GENERATION PIPELINE

Step 1: Slide Planning (MANDATORY)

Use RAG to generate structured slide plan.

Output format:
[
{
"title": "string",
"bullets": ["point1", "point2"],
"visual_style": "diagram | minimal | modern",
"tone": "educational"
}
]

Rules:

* 5–10 slides max
* Each slide must have max 5 bullets
* Content must be concise

---

Step 2: Prompt Builder

For each slide, generate Gemini image prompt:

Template:

"Generate a clean, modern educational presentation slide in 16:9 ratio.

Title: {title}

Content:

* {bullet1}
* {bullet2}

Design rules:

* minimal text
* large readable fonts
* high contrast
* no watermark
* include relevant diagram or visual
* professional presentation style
* balanced layout

Style: {visual_style}
Tone: {tone}

Output: single slide image"

---

Step 3: Image Generation

* Use Gemini image API
* Generate slides in parallel
* Retry up to 2 times on failure
* Ensure resolution is 16:9 (e.g., 1280x720 or higher)

---

Step 4: Store Slides

* Save each slide as artifact
* Link to GeneratedContent
* Maintain order index

---

Step 5: Streaming Events (SSE)

Emit:

* slide_plan_ready
* slide_generation_started
* slide_generated (per slide)
* presentation_done

---

### 3. VIDEO GENERATION PIPELINE

Step 1: Script Generation

For each slide:

Prompt:

"Explain this slide like a friendly teacher.

Slide title: {title}
Points: {bullets}

Rules:

* simple explanation
* 20–40 seconds
* include example if possible
* conversational tone"

---

Step 2: Audio Generation

* Use existing TTS system
* Generate audio per slide

---

Step 3: Video Creation

For each slide:

ffmpeg:

* combine slide image + audio
* duration = audio length

---

Step 4: Merge Slides

* concatenate all slide videos into final video

---

Step 5: Store Output

* Save final video as artifact
* Link to presentation

---

Step 6: Streaming Events

Emit:

* script_generated
* audio_generated
* video_rendering
* video_done

---

### 4. API DESIGN

Create endpoints:

POST /presentation/generate
POST /presentation/{id}/generate-video
GET /presentation/{id}
GET /presentation/{id}/slides
GET /presentation/{id}/video

---

### 5. BACKGROUND JOBS

Use existing BackgroundJob system:

Job types:

* presentation_generation
* video_generation

---

### 6. FRONTEND IMPLEMENTATION

Location:

* StudioPanel (right sidebar)

Create component:

* PresentationGenerator.jsx

Features:

* select materials
* generate slides button
* live streaming UI
* show slides grid (2-column or horizontal scroll)
* regenerate individual slide
* button: "Generate Video"

---

### 7. UI DESIGN REQUIREMENTS

* clean modern UI (like Notion / Gamma / Canva)
* rounded cards for slides
* loading skeletons while generating
* progress indicators
* smooth transitions
* hover actions (regenerate slide, download)

---

### 8. PERFORMANCE REQUIREMENTS

* parallel slide generation
* async processing
* caching for same inputs
* retry failed slides
* limit max slides to avoid cost explosion

---

### 9. ERROR HANDLING

* if slide fails → retry
* if still fails → show placeholder + retry button
* if video fails → allow regenerate

---

### 10. OUTPUT EXPECTATION

Your implementation must:

* be modular
* production-ready
* follow existing project structure
* reuse existing systems (RAG, artifacts, SSE, TTS)

Do NOT:

* create redundant systems
* break existing architecture

---

FINAL GOAL

User clicks "Presentation Generator" in Studio →
Slides are generated as images →
User clicks "Generate Video" →
AI explains slides like a teacher in a video.

---

Now implement the full system step-by-step with clean, scalable code.

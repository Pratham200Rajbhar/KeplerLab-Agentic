from __future__ import annotations

import json
import logging
from typing import Optional

from app.db.prisma_client import prisma
from app.services.chat_v2.context_builder import build_messages
from app.services.llm_service.llm import get_llm_structured
from app.services.llm_service.structured_invoker import parse_json_robust
from app.services.material_service import filter_completed_material_ids
from app.services.notebook_service import get_notebook_by_id
from app.services.presentation.html_renderer import render_presentation_html
from app.services.presentation.ppt_exporter import export_pptx
from app.services.presentation.schemas import GeneratePresentationRequest, PresentationPayload
from app.services.rag.secure_retriever import secure_similarity_search_enhanced

logger = logging.getLogger(__name__)


def suggest_slide_count_from_context(rag_context: str) -> dict:
    text = rag_context or ""
    words = len(text.split())
    if words < 1200:
        return {"suggested_count": 10, "reasoning": "Material is compact but still requires detailed coverage, so 10 slides are recommended."}
    if words < 2500:
        return {"suggested_count": 14, "reasoning": "Moderate source depth benefits from 14 detailed slides."}
    if words < 4500:
        return {"suggested_count": 18, "reasoning": "Rich source material should be expanded to around 18 information-dense slides."}
    return {"suggested_count": 24, "reasoning": "Extensive material set detected; 24 slides provide better depth and completeness."}


def _build_generation_prompt(
    material_ids: list[str],
    instruction: Optional[str],
    full_context: str,
    *,
    max_slides: Optional[int],
) -> str:
    instruction_block = instruction.strip() if instruction else "No additional instruction"
    slide_count_req = (
        f"CRITICAL REQUIREMENT: You MUST generate EXACTLY {max_slides} items in the 'slides' array. "
        f"If the source material is short, you MUST split the concepts across multiple slides to reach exactly {max_slides}. "
        f"Do NOT output fewer than {max_slides} slides under ANY circumstances."
    ) if max_slides else "- Generate as many slides as needed for full depth."
    
    return (
        "You are generating a professional, highly-structured presentation strictly based on the provided study materials.\n"
        "You MUST extract all relevant facts, statistics, definitions, and conclusions directly from the context below.\n"
        "Do not invent new facts. If it is not in the material, do not include it.\n"
        "Output must be strict JSON only. No introductory or conversational text.\n\n"
        "DESIGN PRINCIPLES:\n"
        "- 16:9 Aspect Ratio: Content must fit comfortably on a wide slide (1920x1080).\n"
        "- NO TEXT DUMPS: Never fill a slide with long paragraphs. Keep it visual and structured.\n"
        "- STRUCTURED ORGANIZATION: Every slide must be logically organized. Use tables for comparisons and bullet points for lists.\n"
        "- SLIDE ECONOMY: Each slide should teach ONE specific concept with 3-6 high-quality, substantive bullet points.\n"
        "- DEPTH OVER VOLUME: Use substantial, meaningful points directly extracted from the study material.\n"
        "- IMAGERY: Provide highly descriptive prompts for images that would explain the concept better.\n"
        "- DYNAMIC THEME: Invent a custom 6-color hex palette and select appropriate Google Fonts that conceptually match the topic.\n\n"
        "Output Shape:\n"
        "{\n"
        "  \"theme_tokens\": {\n"
        "    \"bg\": \"#...\",\n"
        "    \"card\": \"#...\",\n"
        "    \"text\": \"#...\",\n"
        "    \"muted\": \"#...\",\n"
        "    \"accent\": \"#...\",\n"
        "    \"border\": \"#...\",\n"
        "    \"header_font\": \"'Font Name', sans-serif\",\n"
        "    \"body_font\": \"'Font Name', sans-serif\"\n"
        "  },\n"
        "  \"slides\": [\n"
        "    {\n"
        "      \"layout\": \"title_content\",\n"
        "      \"title\": \"\",\n"
        "      \"elements\": [\n"
        "        {\"type\": \"subtitle\", \"text\": \"Optional subtitle\"},\n"
        "        {\"type\": \"bullet\", \"items\": [\"Insight extracted straight from text\", \"Insight extracted straight from text\"]},\n"
        "        {\"type\": \"paragraph\", \"text\": \"Short explanatory text (max 40 words)\"},\n"
        "        {\"type\": \"table\", \"rows\": [[\"Header1\", \"Header2\"], [\"Value1\", \"Value2\"]]},\n"
        "        {\"type\": \"image\", \"prompt\": \"Highly descriptive prompt for an AI image generator\", \"source\": \"Optional URL or file path\", \"caption\": \"Optional image caption\"},\n"
        "        {\"type\": \"numbered_list\", \"items\": [\"Step 1\", \"Step 2\"]},\n"
        "        {\"type\": \"quote\", \"text\": \"Key quote from source material\"},\n"
        "        {\"type\": \"callout\", \"text\": \"Important takeaway\"},\n"
        "        {\"type\": \"code\", \"text\": \"Optional pseudo-code or command snippet\"}\n"
        "      ]\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        "Quality requirements:\n"
        "- Do not produce summary-only content. Avoid generic high-level statements.\n"
        "- Every slide must be content-rich and heavily dependent on the study material provided.\n"
        f"{slide_count_req}\n"
        "- Never output markdown, code fences, or prose outside JSON.\n\n"
        f"Selected material IDs: {', '.join(material_ids)}\n"
        f"User instruction: {instruction_block}\n\n"
        "Retrieved context:\n"
        f"{full_context}"
    )


async def generate_presentation_content(request: GeneratePresentationRequest, user_id: str) -> dict:
    notebook = await get_notebook_by_id(request.notebook_id, user_id)
    if not notebook:
        raise ValueError("Notebook not found")

    valid_material_ids = await filter_completed_material_ids(request.material_ids, user_id)
    if not valid_material_ids:
        raise ValueError("No valid/completed materials selected")

    from app.services.rag.secure_retriever import secure_similarity_search
    
    # Calculate how many chunks we need to feed the LLM based on slide count.
    # We want a very dense context, so about 2-3 chunks per slide requested.
    target_k = max(15, (request.max_slides * 3) if request.max_slides else 20)
    
    search_query = request.instruction or "comprehensive overview key concepts definitions structure analysis"
    
    retrieved_chunks = secure_similarity_search(
        user_id=user_id,
        query=search_query,
        k=target_k,
        material_ids=valid_material_ids,
        notebook_id=request.notebook_id,
    )
    
    if not retrieved_chunks:
        raise ValueError("Could not retrieve any content from the selected materials using RAG.")
        
    contexts = []
    for i, chunk in enumerate(retrieved_chunks, 1):
        contexts.append(f"--- Excerpt {i} ---\n{chunk}\n")
    
    full_context = "\n".join(contexts)

    user_prompt = _build_generation_prompt(
        valid_material_ids,
        request.instruction,
        full_context,
        max_slides=request.max_slides,
    )
    messages = build_messages(
        user_message=user_prompt,
        history=[],
        rag_context=None,
        system_prompt="You are an assistant that only returns valid JSON.",
    )

    llm = get_llm_structured(mode="structured")
    response = llm.invoke(messages)
    raw_text = getattr(response, "content", str(response))

    parsed = parse_json_robust(raw_text)
    payload = PresentationPayload.model_validate(parsed)

    create_data = {
        "notebook": {"connect": {"id": request.notebook_id}},
        "user": {"connect": {"id": user_id}},
        "contentType": "presentation",
        "title": request.title or (payload.slides[0].title if payload.slides else "Presentation"),
        "data": json.dumps(payload.model_dump()),
        "materialIds": valid_material_ids,
    }
    if len(valid_material_ids) == 1:
        create_data["material"] = {"connect": {"id": valid_material_ids[0]}}

    record = await prisma.generatedcontent.create(data=create_data)

    html_path = render_presentation_html(str(record.id), payload)
    ppt_path = export_pptx(str(record.id), payload)

    updated = await prisma.generatedcontent.update(
        where={"id": str(record.id)},
        data={
            "htmlPath": html_path,
            "pptPath": ppt_path,
            "data": json.dumps(payload.model_dump()),
        },
    )

    return {
        "id": str(updated.id),
        "notebook_id": str(updated.notebookId),
        "user_id": str(updated.userId),
        "content_type": updated.contentType,
        "title": updated.title,
        "data": updated.data if isinstance(updated.data, dict) else json.loads(updated.data or "{}"),
        "html_path": updated.htmlPath,
        "ppt_path": updated.pptPath,
        "material_ids": updated.materialIds or valid_material_ids,
        "created_at": updated.createdAt.isoformat() if updated.createdAt else None,
    }

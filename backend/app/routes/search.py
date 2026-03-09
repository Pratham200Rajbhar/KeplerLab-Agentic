from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import logging
from app.services.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/search", tags=["search"])

class WebSearchRequest(BaseModel):
    query: str
    file_type: Optional[str] = None
    engine: str = "duckduckgo"

class SearchResult(BaseModel):
    title: str
    link: str
    snippet: str

@router.post("/web", response_model=List[SearchResult])
async def search_web(
    request: WebSearchRequest,
    current_user=Depends(get_current_user),
):
    """Web search via DuckDuckGo."""
    query = request.query
    if request.file_type:
        query = f"{query} filetype:{request.file_type}"

    logger.info(f"[SEARCH] Query='{query}' user={current_user.id}")

    try:
        from app.core.web_search import ddg_search

        results = await ddg_search(query, max_results=5)
        
        return [
            SearchResult(
                title=r.get("title", "No Title"),
                link=r.get("url", ""),
                snippet=r.get("snippet", "No description available.")
            )
            for r in results
        ]
    except Exception as e:
        logger.exception("Web search failed")
        raise HTTPException(status_code=500, detail="Search failed")

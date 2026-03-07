"""SSE (Server-Sent Events) formatting utilities.

Provides consistent, type-safe SSE event formatting for all streaming responses.
"""

import json
from typing import Any, Dict, Optional, List


def format_sse(event_type: str, data: Any) -> str:
    """Format data as SSE event.
    
    Args:
        event_type: SSE event type (token, step, meta, etc.)
        data: Data payload (will be JSON-serialized)
        
    Returns:
        Formatted SSE string ready to yield
    """
    if isinstance(data, str):
        json_data = json.dumps({"content": data})
    else:
        json_data = json.dumps(data, default=str)
    
    return f"event: {event_type}\ndata: {json_data}\n\n"


def format_token(content: str) -> str:
    """Format a token (text chunk) event.
    
    Args:
        content: Text content to stream
        
    Returns:
        SSE formatted token event
    """
    return format_sse("token", {"content": content})


def format_step(
    tool: str,
    status: str = "running",
    label: Optional[str] = None,
    step_index: Optional[int] = None,
) -> str:
    """Format a step update event.
    
    Args:
        tool: Tool/step name
        status: Step status (running, done, error)
        label: Human-readable step description
        step_index: Step number in sequence
        
    Returns:
        SSE formatted step event
    """
    data = {
        "tool": tool,
        "status": status,
    }
    if label:
        data["label"] = label
    if step_index is not None:
        data["step_index"] = step_index
        
    return format_sse("step", data)


def format_error(error: Exception, details: Optional[Dict[str, Any]] = None) -> str:
    """Format an error event.
    
    Args:
        error: Exception that occurred
        details: Additional error context
        
    Returns:
        SSE formatted error event
    """
    data = {
        "error": str(error),
        "type": type(error).__name__,
    }
    if details:
        data.update(details)
        
    return format_sse("error", data)


def format_done(
    elapsed: float,
    metadata: Optional[Dict[str, Any]] = None,
) -> str:
    """Format a stream completion event.
    
    Args:
        elapsed: Total time elapsed in seconds
        metadata: Final metadata about the response
        
    Returns:
        SSE formatted done event
    """
    data = {"elapsed": round(elapsed, 2)}
    if metadata:
        data.update(metadata)
        
    return format_sse("done", data)


def format_metadata(metadata: Dict[str, Any]) -> str:
    """Format a metadata event.
    
    Args:
        metadata: Metadata dictionary
        
    Returns:
        SSE formatted meta event
    """
    return format_sse("meta", metadata)


def format_artifact(
    artifact_id: str,
    filename: str,
    url: str,
    mime_type: Optional[str] = None,
    size: Optional[int] = None,
    display_type: str = "file_card",
) -> str:
    """Format an artifact (generated file) event.
    
    Args:
        artifact_id: Unique artifact ID
        filename: File name
        url: Download URL
        mime_type: MIME type
        size: File size in bytes
        display_type: How to display (file_card, image, code, etc.)
        
    Returns:
        SSE formatted artifact event
    """
    data = {
        "artifact_id": artifact_id,
        "filename": filename,
        "url": url,
        "display_type": display_type,
    }
    if mime_type:
        data["mime"] = mime_type
    if size is not None:
        data["size"] = size
        
    return format_sse("artifact", data)


def format_code_block(
    code: str,
    language: str = "python",
    packages: Optional[List[str]] = None,
) -> str:
    """Format a code block event.
    
    Args:
        code: Code content
        language: Programming language
        packages: Required packages
        
    Returns:
        SSE formatted code_block event
    """
    data = {
        "code": code,
        "language": language,
    }
    if packages:
        data["packages"] = packages
        
    return format_sse("code_block", data)


def format_summary(
    title: str,
    description: Optional[str] = None,
    key_results: Optional[List[str]] = None,
    metrics: Optional[Dict[str, Any]] = None,
) -> str:
    """Format a summary event.
    
    Args:
        title: Summary title
        description: Detailed description
        key_results: List of key findings
        metrics: Performance/usage metrics
        
    Returns:
        SSE formatted summary event
    """
    data = {"title": title}
    if description:
        data["description"] = description
    if key_results:
        data["key_results"] = key_results
    if metrics:
        data["metrics"] = metrics
        
    return format_sse("summary", data)


def format_progress(
    current: int,
    total: int,
    message: Optional[str] = None,
) -> str:
    """Format a progress update event.
    
    Args:
        current: Current progress value
        total: Total/target value
        message: Progress message
        
    Returns:
        SSE formatted progress event
    """
    data = {
        "current": current,
        "total": total,
        "percentage": round((current / total) * 100, 1) if total > 0 else 0,
    }
    if message:
        data["message"] = message
        
    return format_sse("progress", data)

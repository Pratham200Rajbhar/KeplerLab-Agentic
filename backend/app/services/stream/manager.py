"""Stream manager - orchestrates chat response streaming.

Provides a unified interface for all chat intents (RAG, Agent, Web Search, etc.)
with clean state management, error handling, and persistence.
"""

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, AsyncIterator, Dict, List, Optional, Callable
from uuid import uuid4

from .sse import (
    format_token,
    format_step,
    format_error,
    format_done,
    format_metadata,
    format_artifact,
    format_code_block,
    format_summary,
    format_sse,
)
from .storage import ChatStorage

logger = logging.getLogger(__name__)


class StreamState(str, Enum):
    """Stream lifecycle states."""
    INITIALIZING = "initializing"
    ACTIVE = "active"
    PAUSED = "paused"
    FINALIZING = "finalizing"
    COMPLETED = "completed"
    ERROR = "error"
    ABORTED = "aborted"


@dataclass
class StreamContext:
    """Container for streaming session state."""
    
    stream_id: str
    user_id: str
    notebook_id: str
    session_id: str
    user_message: str
    intent: str
    
    state: StreamState = StreamState.INITIALIZING
    start_time: float = field(default_factory=time.time)
    
    # Accumulated content
    content_buffer: List[str] = field(default_factory=list)
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Step tracking
    steps: List[Dict[str, Any]] = field(default_factory=list)
    
    # Artifacts
    artifacts: List[Dict[str, Any]] = field(default_factory=list)
    
    # Message IDs
    user_message_id: Optional[str] = None
    assistant_message_id: Optional[str] = None
    
    # Error tracking
    error: Optional[Exception] = None
    
    @property
    def elapsed(self) -> float:
        """Get elapsed time in seconds."""
        return time.time() - self.start_time
    
    @property
    def full_content(self) -> str:
        """Get accumulated content as string."""
        return "".join(self.content_buffer)
    
    def add_content(self, content: str) -> None:
        """Add content chunk to buffer."""
        self.content_buffer.append(content)
    
    def add_step(self, step: Dict[str, Any]) -> None:
        """Add step to tracking."""
        self.steps.append(step)
    
    def add_artifact(self, artifact: Dict[str, Any]) -> None:
        """Add artifact to tracking."""
        self.artifacts.append(artifact)
    
    def set_error(self, error: Exception) -> None:
        """Set error state."""
        self.error = error
        self.state = StreamState.ERROR


class StreamManager:
    """Orchestrates streaming responses with clean persistence."""
    
    def __init__(
        self,
        user_id: str,
        notebook_id: str,
        session_id: str,
        user_message: str,
        intent: str = "RAG",
    ):
        """Initialize stream manager.
        
        Args:
            user_id: User ID
            notebook_id: Notebook ID
            session_id: Chat session ID
            user_message: User's message
            intent: Chat intent (RAG, AGENT, WEB_SEARCH, etc.)
        """
        self.context = StreamContext(
            stream_id=str(uuid4()),
            user_id=user_id,
            notebook_id=notebook_id,
            session_id=session_id,
            user_message=user_message,
            intent=intent,
        )
        self.storage = ChatStorage()
    
    async def initialize(self) -> None:
        """Initialize streaming session - save user message."""
        try:
            self.context.user_message_id = await self.storage.save_user_message(
                notebook_id=self.context.notebook_id,
                user_id=self.context.user_id,
                session_id=self.context.session_id,
                content=self.context.user_message,
            )
            self.context.state = StreamState.ACTIVE
            logger.info(f"Stream {self.context.stream_id} initialized")
        except Exception as e:
            logger.error(f"Failed to initialize stream: {e}")
            self.context.set_error(e)
            raise
    
    async def emit_token(self, content: str) -> str:
        """Emit a token event and accumulate content.
        
        Args:
            content: Text content chunk
            
        Returns:
            SSE formatted event
        """
        if self.context.state != StreamState.ACTIVE:
            logger.warning(f"Cannot emit token - stream in state {self.context.state}")
            return ""
        
        self.context.add_content(content)
        return format_token(content)
    
    async def emit_step(
        self,
        tool: str,
        status: str = "running",
        label: Optional[str] = None,
        step_index: Optional[int] = None,
    ) -> str:
        """Emit a step update event.
        
        Args:
            tool: Tool/step name
            status: Step status (running, done, error)
            label: Human-readable description
            step_index: Step number
            
        Returns:
            SSE formatted event
        """
        step = {
            "tool": tool,
            "status": status,
            "timestamp": time.time(),
        }
        if label:
            step["label"] = label
        if step_index is not None:
            step["step_index"] = step_index
        
        self.context.add_step(step)
        return format_step(tool, status, label, step_index)
    
    async def emit_artifact(
        self,
        artifact_id: str,
        filename: str,
        url: str,
        mime_type: Optional[str] = None,
        size: Optional[int] = None,
        display_type: str = "file_card",
    ) -> str:
        """Emit an artifact event.
        
        Args:
            artifact_id: Unique artifact ID
            filename: File name
            url: Download URL
            mime_type: MIME type
            size: File size
            display_type: Display type
            
        Returns:
            SSE formatted event
        """
        artifact = {
            "artifact_id": artifact_id,
            "filename": filename,
            "url": url,
            "display_type": display_type,
        }
        if mime_type:
            artifact["mime_type"] = mime_type
        if size:
            artifact["size"] = size
        
        self.context.add_artifact(artifact)
        return format_artifact(artifact_id, filename, url, mime_type, size, display_type)
    
    async def emit_metadata(self, metadata: Dict[str, Any]) -> str:
        """Emit metadata event.
        
        Args:
            metadata: Metadata dictionary
            
        Returns:
            SSE formatted event
        """
        self.context.metadata.update(metadata)
        return format_metadata(metadata)
    
    async def emit_code_block(
        self,
        code: str,
        language: str = "python",
        packages: Optional[List[str]] = None,
    ) -> str:
        """Emit code block event.
        
        Args:
            code: Code content
            language: Programming language
            packages: Required packages
            
        Returns:
            SSE formatted event
        """
        return format_code_block(code, language, packages)
    
    async def emit_summary(
        self,
        title: str,
        description: Optional[str] = None,
        key_results: Optional[List[str]] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Emit summary event.
        
        Args:
            title: Summary title
            description: Description
            key_results: Key findings
            metrics: Metrics
            
        Returns:
            SSE formatted event
        """
        return format_summary(title, description, key_results, metrics)
    
    async def emit_event(self, event_type: str, data: Any) -> str:
        """Emit custom event.
        
        Args:
            event_type: Event type name
            data: Event data
            
        Returns:
            SSE formatted event
        """
        return format_sse(event_type, data)
    
    async def finalize(
        self,
        additional_metadata: Optional[Dict[str, Any]] = None,
    ) -> AsyncIterator[str]:
        """Finalize stream - persist message and emit done event.
        
        Args:
            additional_metadata: Additional metadata to include
            
        Yields:
            SSE formatted done event
        """
        try:
            self.context.state = StreamState.FINALIZING
            
            # Merge metadata
            final_metadata = {
                "intent": self.context.intent,
                "elapsed": round(self.context.elapsed, 2),
                "steps_count": len(self.context.steps),
                "artifacts_count": len(self.context.artifacts),
                **self.context.metadata,
            }
            
            if additional_metadata:
                final_metadata.update(additional_metadata)
            
            # Save assistant message
            content = self.context.full_content
            if content.strip():
                self.context.assistant_message_id = await self.storage.save_assistant_message(
                    notebook_id=self.context.notebook_id,
                    user_id=self.context.user_id,
                    session_id=self.context.session_id,
                    content=content,
                    agent_meta=final_metadata,
                )
                
                # Save blocks
                if self.context.assistant_message_id:
                    blocks = await self.storage.save_blocks(
                        message_id=self.context.assistant_message_id,
                        content=content,
                    )
                    
                    # Emit blocks if created
                    if blocks:
                        yield format_sse("blocks", {"blocks": blocks})
            
            self.context.state = StreamState.COMPLETED
            logger.info(
                f"Stream {self.context.stream_id} completed in {self.context.elapsed:.2f}s"
            )
            
            yield format_done(self.context.elapsed, final_metadata)
            
        except Exception as e:
            logger.error(f"Failed to finalize stream: {e}")
            self.context.set_error(e)
            yield format_error(e)
    
    async def handle_error(self, error: Exception) -> str:
        """Handle and emit error.
        
        Args:
            error: Exception that occurred
            
        Returns:
            SSE formatted error event
        """
        self.context.set_error(error)
        logger.error(f"Stream {self.context.stream_id} error: {error}")
        return format_error(error)
    
    async def stream_from_llm(
        self,
        llm_stream: AsyncIterator[Any],
        extract_content: Optional[Callable[[Any], str]] = None,
    ) -> AsyncIterator[str]:
        """Stream from LLM response chunks.
        
        Args:
            llm_stream: Async iterator of LLM chunks
            extract_content: Function to extract content from chunk
            
        Yields:
            SSE formatted events
        """
        try:
            async for chunk in llm_stream:
                # Extract content
                if extract_content:
                    content = extract_content(chunk)
                else:
                    from app.services.llm_service.llm import extract_chunk_content
                    content = extract_chunk_content(chunk)
                
                if content:
                    yield await self.emit_token(content)
        
        except Exception as e:
            yield await self.handle_error(e)
    
    async def stream_with_pipeline(
        self,
        pipeline_func: Callable[..., AsyncIterator[str]],
        **kwargs,
    ) -> AsyncIterator[str]:
        """Execute a pipeline function and stream its events.
        
        This is a convenience wrapper for existing pipeline functions
        that already emit SSE events.
        
        Args:
            pipeline_func: Async function that yields SSE events
            **kwargs: Arguments to pass to pipeline function
            
        Yields:
            SSE formatted events
        """
        try:
            # Initialize stream
            await self.initialize()
            
            # Run pipeline and forward events
            async for event in pipeline_func(**kwargs):
                # Parse event to extract content for accumulation
                if event.startswith("event: token\n"):
                    lines = event.split("\n")
                    for line in lines:
                        if line.startswith("data: "):
                            try:
                                import json
                                data = json.loads(line[6:])
                                if "content" in data:
                                    self.context.add_content(data["content"])
                            except:
                                pass
                
                yield event
            
            # Finalize
            async for final_event in self.finalize():
                yield final_event
        
        except Exception as e:
            yield await self.handle_error(e)

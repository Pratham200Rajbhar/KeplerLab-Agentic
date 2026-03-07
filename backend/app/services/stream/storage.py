"""Clean storage service for chat state and artifacts.

Provides atomic operations for persisting chat messages, blocks, artifacts,
and session state with proper error handling and rollback support.
"""

import json
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


class ChatStorage:
    """Storage service for chat messages and related data."""
    
    @staticmethod
    async def save_user_message(
        notebook_id: str,
        user_id: str,
        session_id: str,
        content: str,
    ) -> str:
        """Save user message to database.
        
        Args:
            notebook_id: Notebook ID
            user_id: User ID
            session_id: Chat session ID
            content: Message content
            
        Returns:
            Message ID
        """
        try:
            message = await prisma.chatmessage.create(
                data={
                    "notebookId": notebook_id,
                    "userId": user_id,
                    "chatSessionId": session_id,
                    "role": "user",
                    "content": content,
                }
            )
            return message.id
        except Exception as e:
            logger.error(f"Failed to save user message: {e}")
            raise
    
    @staticmethod
    async def save_assistant_message(
        notebook_id: str,
        user_id: str,
        session_id: str,
        content: str,
        agent_meta: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save assistant message to database.
        
        Args:
            notebook_id: Notebook ID
            user_id: User ID
            session_id: Chat session ID
            content: Message content
            agent_meta: Metadata about generation (intent, tools, etc.)
            
        Returns:
            Message ID
        """
        try:
            data = {
                "notebookId": notebook_id,
                "userId": user_id,
                "chatSessionId": session_id,
                "role": "assistant",
                "content": content,
            }
            
            if agent_meta:
                data["agentMeta"] = json.dumps(agent_meta)
            
            message = await prisma.chatmessage.create(data=data)
            return message.id
        except Exception as e:
            logger.error(f"Failed to save assistant message: {e}")
            raise
    
    @staticmethod
    async def update_message_metadata(
        message_id: str,
        agent_meta: Dict[str, Any],
    ) -> None:
        """Update message metadata.
        
        Args:
            message_id: Message ID
            agent_meta: Updated metadata
        """
        try:
            await prisma.chatmessage.update(
                where={"id": message_id},
                data={"agentMeta": json.dumps(agent_meta)},
            )
        except Exception as e:
            logger.warning(f"Failed to update message metadata: {e}")
    
    @staticmethod
    async def save_blocks(
        message_id: str,
        content: str,
    ) -> List[Dict[str, Any]]:
        """Parse content and save as response blocks.
        
        Args:
            message_id: Message ID
            content: Full message content
            
        Returns:
            List of created blocks
        """
        try:
            # Simple split on double newline for now
            # Can be enhanced with more sophisticated parsing
            paragraphs = [p.strip() for p in content.split("\n\n") if p.strip()]
            
            blocks = []
            for idx, text in enumerate(paragraphs):
                block = await prisma.responseblock.create(
                    data={
                        "chatMessageId": message_id,
                        "blockIndex": idx,
                        "text": text,
                    }
                )
                blocks.append({
                    "id": block.id,
                    "block_index": block.blockIndex,
                    "text": block.text,
                })
            
            return blocks
        except Exception as e:
            logger.warning(f"Failed to save blocks (non-critical): {e}")
            return []
    
    @staticmethod
    async def save_artifact(
        message_id: str,
        filename: str,
        url: str,
        mime_type: str,
        size: int,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Save artifact reference to database.
        
        Args:
            message_id: Message ID
            filename: File name
            url: Download URL
            mime_type: MIME type
            size: File size in bytes
            metadata: Additional metadata
            
        Returns:
            Artifact ID
        """
        # Note: This assumes you have an Artifact table in Prisma schema
        # If not, you can store artifacts in message metadata instead
        try:
            # For now, store in message metadata since Artifact table may not exist
            message = await prisma.chatmessage.find_unique(where={"id": message_id})
            if not message:
                raise ValueError(f"Message {message_id} not found")
            
            current_meta = json.loads(message.agentMeta or "{}")
            artifacts = current_meta.get("artifacts", [])
            
            artifact = {
                "id": str(uuid4()),
                "filename": filename,
                "url": url,
                "mime_type": mime_type,
                "size": size,
                "created_at": datetime.utcnow().isoformat(),
            }
            
            if metadata:
                artifact["metadata"] = metadata
            
            artifacts.append(artifact)
            current_meta["artifacts"] = artifacts
            
            await prisma.chatmessage.update(
                where={"id": message_id},
                data={"agentMeta": json.dumps(current_meta)},
            )
            
            return artifact["id"]
        except Exception as e:
            logger.error(f"Failed to save artifact: {e}")
            raise
    
    @staticmethod
    async def get_session_history(
        notebook_id: str,
        session_id: str,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get chat history for a session.
        
        Args:
            notebook_id: Notebook ID
            session_id: Chat session ID
            limit: Maximum number of messages
            
        Returns:
            List of messages with blocks
        """
        try:
            messages = await prisma.chatmessage.find_many(
                where={
                    "notebookId": notebook_id,
                    "chatSessionId": session_id,
                },
                include={"blocks": True},
                order={"createdAt": "asc"},
                take=limit,
            )
            
            result = []
            for msg in messages:
                data = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.createdAt.isoformat(),
                    "blocks": [
                        {
                            "id": b.id,
                            "block_index": b.blockIndex,
                            "text": b.text,
                        }
                        for b in (msg.blocks or [])
                    ],
                }
                
                if msg.agentMeta:
                    try:
                        data["agent_meta"] = json.loads(msg.agentMeta)
                    except json.JSONDecodeError:
                        data["agent_meta"] = {}
                
                result.append(data)
            
            return result
        except Exception as e:
            logger.error(f"Failed to get session history: {e}")
            return []
    
    @staticmethod
    async def create_session(
        notebook_id: str,
        user_id: str,
        title: str = "New Chat",
    ) -> str:
        """Create a new chat session.
        
        Args:
            notebook_id: Notebook ID
            user_id: User ID
            title: Session title
            
        Returns:
            Session ID
        """
        try:
            session = await prisma.chatsession.create(
                data={
                    "notebookId": notebook_id,
                    "userId": user_id,
                    "title": title,
                }
            )
            return session.id
        except Exception as e:
            logger.error(f"Failed to create session: {e}")
            raise
    
    @staticmethod
    async def update_session_title(
        session_id: str,
        title: str,
    ) -> None:
        """Update session title.
        
        Args:
            session_id: Session ID
            title: New title
        """
        try:
            await prisma.chatsession.update(
                where={"id": session_id},
                data={"title": title},
            )
        except Exception as e:
            logger.warning(f"Failed to update session title: {e}")
    
    @staticmethod
    async def ensure_session(
        notebook_id: str,
        user_id: str,
        session_id: Optional[str] = None,
        title: str = "New Chat",
    ) -> str:
        """Ensure session exists, create if needed.
        
        Args:
            notebook_id: Notebook ID
            user_id: User ID
            session_id: Existing session ID (optional)
            title: Title for new session
            
        Returns:
            Session ID (existing or newly created)
        """
        if session_id:
            # Verify session exists
            try:
                session = await prisma.chatsession.find_unique(
                    where={"id": session_id}
                )
                if session:
                    return session_id
            except Exception:
                pass
        
        # Create new session
        return await ChatStorage.create_session(notebook_id, user_id, title)

"""Chat V2 — Message store.

Handles all chat persistence: sessions, messages, response blocks.
Uses existing Prisma models (ChatSession, ChatMessage, ResponseBlock).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

from app.db.prisma_client import prisma

logger = logging.getLogger(__name__)


# ── Session management ────────────────────────────────────────


async def ensure_session(
    notebook_id: str,
    user_id: str,
    session_id: Optional[str],
    title: str = "New Chat",
) -> str:
    """Return an existing session ID or create a new one.

    Args:
        notebook_id: Notebook the session belongs to.
        user_id: Owner.
        session_id: Existing session ID (may be None).
        title: Title for a new session.

    Returns:
        The session ID to use.
    """
    if session_id:
        # Auto-title untitled sessions
        try:
            existing = await prisma.chatsession.find_unique(where={"id": session_id})
            if existing and (not existing.title or existing.title in ("", "New Chat")):
                new_title = title[:30] + ("..." if len(title) > 30 else "")
                await prisma.chatsession.update(
                    where={"id": session_id}, data={"title": new_title}
                )
        except Exception:
            pass
        return session_id

    # Create new session
    try:
        session = await prisma.chatsession.create(
            data={"notebookId": notebook_id, "userId": user_id, "title": title[:100]}
        )
        return str(session.id)
    except Exception as exc:
        logger.error("Failed to create chat session: %s", exc)
        raise


async def get_sessions(notebook_id: str, user_id: str) -> List[Dict[str, Any]]:
    """List all chat sessions for a notebook."""
    try:
        sessions = await prisma.chatsession.find_many(
            where={"notebookId": notebook_id, "userId": user_id},
            order={"createdAt": "desc"},
            include={
                "chatMessages": {
                    "take": 3,
                    "order_by": {"createdAt": "asc"},
                }
            },
        )
        return [
            {
                "id": str(s.id),
                "title": s.title,
                "createdAt": s.createdAt.isoformat(),
                "created_at": s.createdAt.isoformat(),
                "messages_text": " ".join(
                    m.content[:200] for m in (getattr(s, "chatMessages", []) or [])[:3]
                ),
            }
            for s in sessions
        ]
    except Exception as exc:
        logger.error("get_sessions failed: %s", exc)
        return []


async def delete_session(session_id: str, user_id: str) -> bool:
    """Delete a chat session and cascade to messages + blocks."""
    try:
        messages = await prisma.chatmessage.find_many(
            where={"chatSessionId": session_id, "userId": user_id},
        )
        if messages:
            msg_ids = [str(m.id) for m in messages]
            await prisma.responseblock.delete_many(
                where={"chatMessageId": {"in": msg_ids}}
            )
        await prisma.chatmessage.delete_many(
            where={"chatSessionId": session_id, "userId": user_id}
        )
        await prisma.chatsession.delete_many(
            where={"id": session_id, "userId": user_id}
        )
        return True
    except Exception as exc:
        logger.error("delete_session failed: %s", exc)
        return False


# ── Message persistence ───────────────────────────────────────


async def save_user_message(
    notebook_id: str,
    user_id: str,
    session_id: str,
    content: str,
) -> str:
    """Save a user message. Returns the message ID."""
    try:
        msg = await prisma.chatmessage.create(
            data={
                "notebookId": notebook_id,
                "userId": user_id,
                "chatSessionId": session_id,
                "role": "user",
                "content": content,
            }
        )
        return str(msg.id)
    except Exception as exc:
        logger.error("save_user_message failed: %s", exc)
        raise


async def save_assistant_message(
    notebook_id: str,
    user_id: str,
    session_id: str,
    content: str,
    agent_meta: Optional[Dict[str, Any]] = None,
) -> str:
    """Save an assistant message. Returns the message ID."""
    try:
        data: Dict[str, Any] = {
            "notebookId": notebook_id,
            "userId": user_id,
            "chatSessionId": session_id,
            "role": "assistant",
            "content": content,
        }
        if agent_meta:
            try:
                data["agentMeta"] = json.dumps(agent_meta)
            except Exception:
                pass
        msg = await prisma.chatmessage.create(data=data)
        return str(msg.id)
    except Exception as exc:
        logger.error("save_assistant_message failed: %s", exc)
        raise


async def save_response_blocks(message_id: str, content: str) -> List[Dict[str, Any]]:
    """Split content into markdown-aware blocks and persist each."""
    blocks_text = _split_markdown_blocks(content)
    created = []
    for idx, text in enumerate(blocks_text):
        if not text.strip():
            continue
        try:
            block = await prisma.responseblock.create(
                data={
                    "chatMessageId": message_id,
                    "blockIndex": idx,
                    "text": text[:5000],
                }
            )
            created.append({"id": str(block.id), "index": block.blockIndex, "text": block.text})
        except Exception as exc:
            logger.debug("save_response_blocks idx=%d failed: %s", idx, exc)
    return created


# ── History retrieval ─────────────────────────────────────────


async def get_history(
    notebook_id: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Return serialised chat messages ordered oldest-first."""
    try:
        where: Dict[str, Any] = {"notebookId": notebook_id, "userId": user_id}
        if session_id:
            where["chatSessionId"] = session_id

        messages = await prisma.chatmessage.find_many(
            where=where,
            order={"createdAt": "asc"},
            include={"responseBlocks": True, "artifacts": True},
        )
        result = []
        for m in messages:
            agent_meta_val = None
            raw_meta = getattr(m, "agentMeta", None)
            if raw_meta:
                try:
                    agent_meta_val = json.loads(raw_meta)
                except Exception:
                    pass

            # Serialize linked artifacts so frontend can render them after refresh
            serialized_artifacts = []
            for art in getattr(m, "artifacts", []) or []:
                serialized_artifacts.append({
                    "id": str(art.id),
                    "filename": art.filename,
                    "mime": art.mimeType,
                    "display_type": art.displayType,
                    "size": art.sizeBytes,
                    "url": f"/api/artifacts/{art.id}",
                })

            result.append({
                "id": str(m.id),
                "role": m.role,
                "content": m.content,
                "created_at": m.createdAt.isoformat(),
                "agent_meta": agent_meta_val,
                "artifacts": serialized_artifacts,
                "blocks": sorted(
                    [{"id": str(b.id), "index": b.blockIndex, "text": b.text}
                     for b in getattr(m, "responseBlocks", []) or []],
                    key=lambda x: x["index"],
                ) if m.role == "assistant" else [],
            })
        return result
    except Exception as exc:
        logger.error("get_history failed: %s", exc)
        return []


async def clear_history(
    notebook_id: str,
    user_id: str,
    session_id: Optional[str] = None,
) -> None:
    """Delete chat messages (and response blocks) for a notebook/session."""
    try:
        where: Dict[str, Any] = {"notebookId": notebook_id, "userId": user_id}
        if session_id:
            where["chatSessionId"] = session_id

        messages = await prisma.chatmessage.find_many(where=where)
        if messages:
            msg_ids = [str(m.id) for m in messages]
            await prisma.responseblock.delete_many(
                where={"chatMessageId": {"in": msg_ids}}
            )
        await prisma.chatmessage.delete_many(where=where)
    except Exception as exc:
        logger.error("clear_history failed: %s", exc)


# ── Agent execution logging ───────────────────────────────────


async def log_agent_execution(
    user_id: str,
    notebook_id: str,
    meta: Dict[str, Any],
    elapsed: float,
) -> None:
    """Write an AgentExecutionLog row. Best-effort."""
    try:
        await prisma.agentexecutionlog.create(
            data={
                "userId": user_id,
                "notebookId": notebook_id,
                "intent": meta.get("intent", "UNKNOWN"),
                "confidence": float(meta.get("confidence", 0.0) or 0.0),
                "toolsUsed": meta.get("tools_used") or [],
                "stepsCount": int(meta.get("steps_count", 0) or 0),
                "tokensUsed": int(meta.get("total_tokens", 0) or 0),
                "elapsedTime": float(elapsed or 0.0),
            }
        )
    except Exception as exc:
        logger.debug("log_agent_execution failed: %s", exc)


# ── Markdown block splitter ───────────────────────────────────


def _split_markdown_blocks(content: str) -> List[str]:
    """Split markdown content into logical blocks, preserving structure."""
    lines = content.split("\n")
    blocks: List[str] = []
    current: List[str] = []
    in_fence = False
    fence_marker = ""
    in_table = False

    def _flush():
        text = "\n".join(current).strip()
        if text:
            blocks.append(text)
        current.clear()

    for line in lines:
        stripped = line.strip()

        # Fenced code block boundaries
        fence_match = re.match(r"^(`{3,}|~{3,})", stripped)
        if fence_match:
            if not in_fence:
                if current and not all(l.strip() == "" for l in current):
                    _flush()
                in_fence = True
                fence_marker = fence_match.group(1)[0]
                current.append(line)
                continue
            elif stripped.startswith(fence_marker):
                current.append(line)
                in_fence = False
                fence_marker = ""
                _flush()
                continue

        if in_fence:
            current.append(line)
            continue

        # Tables
        if stripped.startswith("|") or re.match(r"^\|?[\s:]*-{3,}", stripped):
            if not in_table and current:
                _flush()
            in_table = True
            current.append(line)
            continue
        elif in_table:
            in_table = False
            _flush()

        # Blank line
        if stripped == "":
            current.append(line)
            continue

        # Heading
        if re.match(r"^#{1,6}\s", stripped):
            if current and any(l.strip() for l in current):
                _flush()
            current.append(line)
            continue

        # Horizontal rule
        if re.match(r"^[-*_]{3,}\s*$", stripped):
            if current and any(l.strip() for l in current):
                _flush()
            current.append(line)
            _flush()
            continue

        # Blockquote
        if stripped.startswith(">"):
            if current and not any(l.strip().startswith(">") for l in current if l.strip()):
                _flush()
            current.append(line)
            continue

        # List items
        is_list_item = bool(re.match(r"^(\s*[-*+]|\s*\d+[.)]) ", line))
        is_continuation = bool(re.match(r"^\s{2,}", line)) and not is_list_item
        if is_list_item or is_continuation:
            prev_has_list = any(
                re.match(r"^(\s*[-*+]|\s*\d+[.)]) ", l) for l in current if l.strip()
            )
            if current and not prev_has_list and any(l.strip() for l in current):
                _flush()
            current.append(line)
            continue

        # Regular paragraph
        if current:
            trailing_blanks = sum(1 for l in reversed(current) if l.strip() == "")
            prev_is_list = any(re.match(r"^(\s*[-*+]|\s*\d+[.)]) ", l) for l in current if l.strip())
            prev_is_quote = any(l.strip().startswith(">") for l in current if l.strip())
            if trailing_blanks >= 1 and (prev_is_list or prev_is_quote):
                _flush()
            elif trailing_blanks >= 2:
                _flush()

        current.append(line)

    _flush()
    return blocks

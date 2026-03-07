'use client';

import { useCallback, useRef, useEffect } from 'react';
import useChatStore from '@/stores/useChatStore';
import { streamChat, getChatHistory, getChatSessions, createChatSession, deleteChatSession, clearChatHistory } from '@/lib/api/chat';
import { streamSSE } from '@/lib/stream/streamClient';
import { generateId } from '@/lib/utils/helpers';

/**
 * useChat — clean hook for chat operations.
 *
 * Flow:
 *   user submits message
 *   → add user message to store
 *   → create assistant placeholder
 *   → open SSE stream
 *   → append tokens to assistant message
 *   → finish message on done
 */
export default function useChat({ notebookId, materialIds = [] }) {
  const {
    messages,
    sessionId,
    isStreaming,
    error,
    addMessage,
    updateLastMessage,
    setStreaming,
    setError,
    setSessionId,
    setMessages,
    clearMessages,
  } = useChatStore();

  const abortRef = useRef(null);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  /**
   * Send a message and stream the response.
   * @param {string} content - The message text (already stripped of slash command prefix)
   * @param {string} [notebookIdOverride] - Optional notebook ID (use when closure may be stale)
   * @param {string} [intentOverride] - Optional intent e.g. 'AGENT', 'WEB_RESEARCH', 'CODE_EXECUTION', 'WEB_SEARCH'
   */
  const sendMessage = useCallback(
    async (content, notebookIdOverride, intentOverride = null) => {
      if (!content?.trim() || isStreaming) return;

      const effectiveNotebookId = notebookIdOverride || notebookId;
      if (!effectiveNotebookId) return;

      setError(null);

      // Ensure we have a session
      let activeSessionId = useChatStore.getState().sessionId;
      if (!activeSessionId) {
        try {
          const title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
          const res = await createChatSession(effectiveNotebookId, title);
          activeSessionId = res.session_id;
          setSessionId(activeSessionId);
        } catch (err) {
          setError(err.message || 'Failed to create chat session');
          return;
        }
      }

      // Add user message — store the displayed text (with command label prefix if any)
      const userMsg = {
        id: generateId(),
        role: 'user',
        content: content.trim(),
        createdAt: Date.now(),
        intentOverride: intentOverride || undefined,
      };
      addMessage(userMsg);

      // Add assistant placeholder
      const assistantMsg = {
        id: generateId(),
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
      };
      addMessage(assistantMsg);

      // Start streaming
      setStreaming(true);
      const ac = new AbortController();
      abortRef.current = ac;

      try {
        const response = await streamChat(
          null,
          content.trim(),
          effectiveNotebookId,
          materialIds,
          activeSessionId,
          ac.signal,
          intentOverride,
        );

        await streamSSE(
          response,
          {
            token: (data) => {
              const text = data.content || data.text || '';
              if (text) {
                useChatStore.getState().updateLastMessage((prev) => ({
                  ...prev,
                  content: prev.content + text,
                }));
              }
            },
            done: () => {
              setStreaming(false);
            },
            error: (data) => {
              setError(data.error || 'Stream error');
              setStreaming(false);
            },
            // Agent pipeline progress events
            step: (data) => {
              const text = data.text || data.phase || '';
              if (!text) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentSteps: [...(prev.agentSteps || []), text],
              }));
            },
            agent_start: (data) => {
              const text = data.message || 'Starting agent…';
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentSteps: [...(prev.agentSteps || []), text],
              }));
            },
            tool_result: () => {},
            code_generated: () => {},
            artifact: () => {},
            validation: () => {},
            summary: () => {},
            intent: () => {},
            dataset_profile: () => {},
            meta: () => {},
            blocks: () => {},
          },
          ac.signal,
        );

        // If stream ended without done event
        setStreaming(false);
      } catch (err) {
        if (err.name === 'AbortError') {
          // User aborted — keep whatever was accumulated
          setStreaming(false);
          return;
        }
        setError(err.message || 'Failed to send message');
        setStreaming(false);
      } finally {
        abortRef.current = null;
      }
    },
    [notebookId, materialIds, isStreaming, addMessage, setStreaming, setError, setSessionId, updateLastMessage],
  );

  /**
   * Abort the current stream.
   */
  const abort = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, [setStreaming]);

  /**
   * Retry the last failed message.
   */
  const retry = useCallback(() => {
    const msgs = useChatStore.getState().messages;
    if (msgs.length < 2) return;

    // Find the last user message
    let lastUserMsg = null;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        lastUserMsg = msgs[i];
        break;
      }
    }
    if (!lastUserMsg) return;

    // Remove the last assistant message (failed/empty one)
    const lastMsg = msgs[msgs.length - 1];
    if (lastMsg.role === 'assistant') {
      setMessages(msgs.slice(0, -1));
    }

    setError(null);
    sendMessage(lastUserMsg.content);
  }, [sendMessage, setMessages, setError]);

  /**
   * Load chat history from backend.
   */
  const loadHistory = useCallback(
    async (sid) => {
      if (!notebookId) return;
      try {
        const history = await getChatHistory(notebookId, sid || sessionId);
        if (history && history.length > 0) {
          setMessages(
            history.map((msg) => ({
              id: msg.id,
              role: msg.role,
              content: msg.content,
              createdAt: new Date(msg.created_at).getTime(),
            })),
          );
        } else {
          setMessages([]);
        }
      } catch {
        setMessages([]);
      }
    },
    [notebookId, sessionId, setMessages],
  );

  /**
   * Load sessions for the notebook.
   */
  const loadSessions = useCallback(async () => {
    if (!notebookId) return [];
    try {
      const data = await getChatSessions(notebookId);
      return data.sessions || [];
    } catch {
      return [];
    }
  }, [notebookId]);

  /**
   * Create a new session.
   */
  const createSession = useCallback(
    async (title = 'New Chat') => {
      if (!notebookId) return null;
      try {
        const res = await createChatSession(notebookId, title);
        setSessionId(res.session_id);
        setMessages([]);
        setError(null);
        return res.session_id;
      } catch {
        setError('Failed to create session');
        return null;
      }
    },
    [notebookId, setSessionId, setMessages, setError],
  );

  /**
   * Delete a session.
   */
  const deleteSession = useCallback(
    async (sid) => {
      try {
        await deleteChatSession(sid);
        if (sessionId === sid) {
          setSessionId(null);
          setMessages([]);
        }
      } catch {
        setError('Failed to delete session');
      }
    },
    [sessionId, setSessionId, setMessages, setError],
  );

  /**
   * Clear history for current session.
   */
  const clearHistory = useCallback(async () => {
    if (!notebookId) return;
    try {
      await clearChatHistory(notebookId, sessionId);
      setMessages([]);
    } catch {
      setError('Failed to clear history');
    }
  }, [notebookId, sessionId, setMessages, setError]);

  return {
    // State
    messages,
    sessionId,
    isStreaming,
    error,

    // Actions
    sendMessage,
    abort,
    retry,
    loadHistory,
    loadSessions,
    createSession,
    deleteSession,
    clearHistory,
    clearMessages,
    setSessionId,
    setMessages,
    setError,
  };
}

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

      setStreaming(true); // Lock out empty history fetches immediately
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
          setStreaming(false); // Revert lock on failure
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

      // Start streaming (already locked above)
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
            done: (data) => {
              // Propagate the backend intent to the assistant message so
              // MessageItem can reliably distinguish agent vs code mode.
              if (data?.intent) {
                useChatStore.getState().updateLastMessage((prev) => ({
                  ...prev,
                  intentOverride: data.intent,
                }));
              }
              setStreaming(false);
            },
            error: (data) => {
              setError(data.error || 'Stream error');
              setStreaming(false);
            },
            // ── Agent pipeline events ──────────────────────────
            step: (data) => {
              // Each step event appends a structured step object
              const status = data.status || data.phase || '';
              if (!status) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentSteps: [
                  ...(prev.agentSteps || []),
                  {
                    status,
                    phase: data.phase,
                    step: data.step ?? null,
                    tool: data.tool ?? null,
                  },
                ],
              }));
            },
            agent_start: (data) => {
              // Stores the planned steps for display in header
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentPlan: data.plan || [],
              }));
            },
            code_generated: (data) => {
              // Agent mode: code generated for a specific step.
              // Stored in agentCodeBlocks (NOT codeBlocks) so it never
              // triggers the /code CodeWorkspace UI.
              if (!data.code) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentCodeBlocks: [
                  ...(prev.agentCodeBlocks || []),
                  {
                    step_index: data.step_index ?? null,
                    code: data.code,
                    language: data.language || 'python',
                  },
                ],
              }));
            },
            // /code mode: code_block is emitted by python_tool via orchestrator
            code_block: (data) => {
              if (!data.code) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                codeBlocks: [
                  ...(prev.codeBlocks || []),
                  {
                    step_index: null,
                    code: data.code,
                    language: data.language || 'python',
                  },
                ],
              }));
            },
            tool_result: (data) => {
              // Attach result data to the last matching step by step index
              useChatStore.getState().updateLastMessage((prev) => {
                const steps = [...(prev.agentSteps || [])];
                // Find last step with matching index, or just the last step
                let target = -1;
                if (data.step != null) {
                  for (let i = steps.length - 1; i >= 0; i--) {
                    if (steps[i].step === data.step) { target = i; break; }
                  }
                }
                if (target === -1) target = steps.length - 1;
                if (target >= 0) {
                  steps[target] = { ...steps[target], toolResult: data };
                }
                return { ...prev, agentSteps: steps };
              });
            },
            artifact: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                artifacts: [...(prev.artifacts || []), data],
              }));
            },
            summary: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentSummary: data,
              }));
            },
            tool_start: () => {},
            validation: () => {},
            intent: () => {},
            dataset_profile: () => {},
            web_sources: () => {},
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
            history.map((msg) => {
              const meta = msg.agent_meta || {};
              // Restore intentOverride so agent/code messages re-render correctly
              const intentOverride = meta.intent || undefined;
              // Restore code blocks for /code messages (stored in agent_meta)
              const codeBlocks = meta.code_block
                ? [{ code: meta.code_block.code, language: meta.code_block.language || 'python', step_index: null }]
                : undefined;
              return {
                id: msg.id,
                role: msg.role,
                content: msg.content,
                createdAt: new Date(msg.created_at).getTime(),
                intentOverride,
                // Artifacts come from DB — persistent across refreshes
                artifacts: msg.artifacts?.length ? msg.artifacts : undefined,
                codeBlocks,
              };
            }),
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

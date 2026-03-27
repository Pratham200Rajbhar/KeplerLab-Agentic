'use client';

import { useCallback, useRef, useEffect } from 'react';
import useChatStore from '@/stores/useChatStore';
import { streamChat, getChatHistory, getChatSessions, createChatSession, deleteChatSession, clearChatHistory, deleteChatMessage, updateChatMessage } from '@/lib/api/chat';
import { streamSSE } from '@/lib/stream/streamClient';
import { generateId } from '@/lib/utils/helpers';


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


  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);


  const sendMessage = useCallback(
    async (content, notebookIdOverride, intentOverride = null) => {
            const trimmedContent = content.trim();
            const inferredIntent = (() => {
              if (intentOverride) return intentOverride;
              if (trimmedContent.startsWith('/image')) return 'IMAGE_GENERATION';
              if (trimmedContent.startsWith('/agent')) return 'AGENT';
              if (trimmedContent.startsWith('/web')) return 'WEB_SEARCH';
              if (trimmedContent.startsWith('/research')) return 'WEB_RESEARCH';
              if (trimmedContent.startsWith('/code')) return 'CODE_EXECUTION';
              return null;
            })();

      if (!content?.trim() || isStreaming) return;

      const effectiveNotebookId = notebookIdOverride || notebookId;
      if (!effectiveNotebookId) return;

      setStreaming(true);
      setError(null);


      let activeSessionId = useChatStore.getState().sessionId;
      if (!activeSessionId) {
        try {
          const title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
          const res = await createChatSession(effectiveNotebookId, title);
          activeSessionId = res.session_id;
          setSessionId(activeSessionId);
        } catch (err) {
          setError(err.message || 'Failed to create chat session');
          setStreaming(false);
          return;
        }
      }


      const userMsg = {
        id: generateId(),
        role: 'user',
        content: trimmedContent,
        createdAt: Date.now(),
        intentOverride: inferredIntent || undefined,
      };
      addMessage(userMsg);


      const assistantMsg = {
        id: generateId(),
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
        intentOverride: inferredIntent || undefined,
      };
      addMessage(assistantMsg);


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


              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                ...(data?.intent ? { intentOverride: data.intent } : {}),
                ...(prev.webSearchState
                  ? { webSearchState: { ...prev.webSearchState, status: 'done' } }
                  : {}),
              }));
              setStreaming(false);
            },
            error: (data) => {
              setError(data.error || 'Stream error');
              setStreaming(false);
            },

            step: () => { },
            agent_start: () => { },
            code_generated: () => { },
            tool_result: () => { },
            summary: () => { },

            code_block: (data) => {
              if (!data.code) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                codeBlocks: [
                  ...(prev.codeBlocks || []),
                  {
                    step_index: data.step_index !== undefined ? data.step_index : null,
                    code: data.code,
                    language: data.language || 'python',
                  },
                ],
              }));
            },
            artifact: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                artifacts: [...(prev.artifacts || []), data],
              }));
            },
            tool_start: () => { },
            validation: () => { },
            intent: (data) => {
              if (!data?.intent) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                intentOverride: data.intent,
              }));
            },
            dataset_profile: () => { },
            web_search_update: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                webSearchState: {
                  status: data.status || 'searching',
                  queries: data.queries || prev.webSearchState?.queries || [],
                  scrapingUrls: data.scrapingUrls || prev.webSearchState?.scrapingUrls || [],
                },
              }));
            },
            web_sources: (data) => {
              if (!data?.sources) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                webSources: data.sources,
                webSearchState: prev.webSearchState ? { ...prev.webSearchState, status: 'done' } : undefined,
              }));
            },

            research_start: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                intentOverride: "WEB_RESEARCH",
                researchState: {
                  status: 'researching',
                  phase: 'searching',
                  label: 'Initializing research...',
                  queries: [],
                  sources: [],
                },
              }));
            },
            research_phase: (data) => {
              useChatStore.getState().updateLastMessage((prev) => {
                const existing = prev.researchState || {};
                const newQueries = data.queries
                  ? [...new Set([...(existing.queries || []), ...data.queries])]
                  : existing.queries || [];
                return {
                  ...prev,
                  researchState: {
                    ...existing,
                    status: data.phase === 'writing' ? 'synthesizing' : 'researching',
                    iteration: data.iteration ?? existing.iteration ?? 0,
                    phase: data.phase || existing.phase,
                    phaseNum: data.phase_num || existing.phaseNum || 1,
                    phaseLabel: data.label || '',
                    queries: newQueries,
                    sourcesFetched: data.sources_fetched ?? existing.sourcesFetched,
                    totalQueued: data.total_queued ?? existing.totalQueued,
                  },
                };
              });
            },
            research_source: (data) => {
              useChatStore.getState().updateLastMessage((prev) => {
                const existing = prev.researchState || {};
                return {
                  ...prev,
                  researchState: {
                    ...existing,
                    sources: [...(existing.sources || []), data],
                  },
                };
              });
            },
            research_pdf: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                artifacts: [...(prev.artifacts || []), data],
              }));
            },
            citations: (data) => {

              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                citations: data.citations || [],
                researchState: {
                  ...(prev.researchState || {}),
                  status: 'done',
                },
              }));
            },
            meta: () => { },
            blocks: (data) => {
              if (!data?.blocks) return;
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                blocks: data.blocks,
              }));
            },
            image: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                images: [...(prev.images || []), data],
              }));
            },

            // Agent events
            agent_status: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentState: {
                  ...(prev.agentState || {}),
                  status: data.phase || 'working',
                  message: data.message || '',
                },
              }));
            },
            agent_plan: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentState: {
                  ...(prev.agentState || {}),
                  status: 'executing',
                  plan: data.steps || [],
                  currentStep: 0,
                },
              }));
            },
            agent_step: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentState: {
                  ...(prev.agentState || {}),
                  status: 'executing',
                  currentStep: data.step_number || 0,
                  totalSteps: data.total_steps || 0,
                  stepDescription: data.description || '',
                },
              }));
            },
            agent_tool: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentState: {
                  ...(prev.agentState || {}),
                  activeTool: data.tool || '',
                  toolStep: data.step || '',
                },
              }));
            },
            agent_result: (data) => {
              useChatStore.getState().updateLastMessage((prev) => {
                const existing = prev.agentState || {};
                const results = [...(existing.results || [])];
                const resObj = { 
                  tool: data.tool, 
                  success: data.success, 
                  summary: data.summary,
                  step_index: data.step_index
                };
                
                if (data.step_index !== undefined && data.step_index !== null) {
                  results[data.step_index] = resObj;
                } else {
                  results.push(resObj);
                }

                return {
                  ...prev,
                  agentState: {
                    ...existing,
                    activeTool: null,
                    results,
                  },
                };
              });
            },
            agent_reflection: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentState: {
                  ...(prev.agentState || {}),
                  reflection: {
                    stepSucceeded: data.step_succeeded,
                    goalAchieved: data.goal_achieved,
                    action: data.action,
                    reason: data.reason,
                  },
                },
              }));
            },
            agent_done: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                agentState: {
                  ...(prev.agentState || {}),
                  status: 'done',
                  finishReason: data.finish_reason,
                  stepsExecuted: data.steps_executed,
                  toolCalls: data.tool_calls,
                },
              }));
            },
            agent_artifact: (data) => {
              useChatStore.getState().updateLastMessage((prev) => ({
                ...prev,
                artifacts: [...(prev.artifacts || []), data],
                agentState: {
                  ...(prev.agentState || {}),
                  hasArtifacts: true,
                },
              }));
            },
          },
          ac.signal,
        );


        setStreaming(false);
      } catch (err) {
        if (err.name === 'AbortError') {

          setStreaming(false);
          return;
        }
        setError(err.message || 'Failed to send message');
        setStreaming(false);
      } finally {
        abortRef.current = null;
      }
    },
    [notebookId, materialIds, isStreaming, addMessage, setStreaming, setError, setSessionId],
  );


  const abort = useCallback(() => {
    abortRef.current?.abort();
    setStreaming(false);
  }, [setStreaming]);


  const retry = useCallback(() => {
    const msgs = useChatStore.getState().messages;
    if (msgs.length < 2) return;


    let lastUserMsg = null;
    for (let i = msgs.length - 1; i >= 0; i--) {
      if (msgs[i].role === 'user') {
        lastUserMsg = msgs[i];
        break;
      }
    }
    if (!lastUserMsg) return;


    const lastMsg = msgs[msgs.length - 1];
    if (lastMsg.role === 'assistant') {
      setMessages(msgs.slice(0, -1));
    }

    setError(null);
    sendMessage(lastUserMsg.content);
  }, [sendMessage, setMessages, setError]);


  const loadHistory = useCallback(
    async (sid) => {
      if (!notebookId) return;
      try {
        const history = await getChatHistory(notebookId, sid || sessionId);
        if (history && history.length > 0) {
          setMessages(
            history.map((msg) => {
              const meta = msg.agent_meta || {};
              let intentOverride = meta.intent || undefined;

              // Fallback: If metadata is missing but content has slash command, use it
              if (!intentOverride && msg.role === 'user' && msg.content) {
                const trimmed = msg.content.trim();
                if (trimmed.startsWith('/agent')) intentOverride = 'AGENT';
                else if (trimmed.startsWith('/web')) intentOverride = 'WEB_SEARCH';
                else if (trimmed.startsWith('/research')) intentOverride = 'WEB_RESEARCH';
                else if (trimmed.startsWith('/code')) intentOverride = 'CODE_EXECUTION';
                else if (trimmed.startsWith('/image')) intentOverride = 'IMAGE_GENERATION';
              }

              const codeBlockFromMeta = meta.code_block?.code
                ? { code: meta.code_block.code, language: meta.code_block.language || 'python', step_index: null }
                : null;

              const codeBlockFromLegacyMeta = (!codeBlockFromMeta && meta.original_code)
                ? {
                    code: meta.original_code,
                    language: meta.language || 'python',
                    step_index: null,
                  }
                : null;

              const codeBlocks = codeBlockFromMeta || codeBlockFromLegacyMeta
                ? [codeBlockFromMeta || codeBlockFromLegacyMeta]
                : undefined;

              // Reconstruct minimal agentState so AgentProgressPanel renders in
              // the "done" state when this message is loaded from history.
              const agentState = (intentOverride === 'AGENT') ? {
                status: 'done',
                finishReason: meta.finish_reason,
                stepsExecuted: meta.steps_executed,
                toolCalls: meta.tool_calls,
                hasArtifacts: !!(msg.artifacts?.length),
                plan: [],
                results: [],
              } : undefined;

              return {
                id: msg.id,
                role: msg.role,
                content: msg.content,
                createdAt: new Date(msg.created_at).getTime(),
                intentOverride,
                agentState,
                blocks: msg.blocks,
                artifacts: msg.artifacts?.length ? msg.artifacts : undefined,
                codeBlocks,
                images: meta.images || undefined,
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


  const loadSessions = useCallback(async () => {
    if (!notebookId) return [];
    try {
      const data = await getChatSessions(notebookId);
      return data.sessions || [];
    } catch {
      return [];
    }
  }, [notebookId]);


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


  const clearHistory = useCallback(async () => {
    if (!notebookId) return;
    try {
      await clearChatHistory(notebookId, sessionId);
      setMessages([]);
    } catch {
      setError('Failed to clear history');
    }
  }, [notebookId, sessionId, setMessages, setError]);
  
  const deleteMessage = useCallback(async (messageId) => {
    try {
      await deleteChatMessage(messageId);
      const msgs = useChatStore.getState().messages;
      const idx = msgs.findIndex(m => m.id === messageId);
      if (idx !== -1) {
        const newMsgs = [...msgs];
        if (msgs[idx].role === 'user' && msgs[idx+1]?.role === 'assistant') {
          newMsgs.splice(idx, 2);
        } else {
          newMsgs.splice(idx, 1);
        }
        setMessages(newMsgs);
      }
    } catch {
      setError('Failed to delete message');
    }
  }, [setMessages, setError]);

  const editMessage = useCallback(async (messageId, content) => {
    try {
      await updateChatMessage(messageId, content);
      const msgs = useChatStore.getState().messages;
      const idx = msgs.findIndex(m => m.id === messageId);
      if (idx !== -1) {
        const newMsgs = [...msgs];
        if (msgs[idx].role === 'user' && msgs[idx+1]?.role === 'assistant') {
          newMsgs.splice(idx + 1, 1);
        }
        newMsgs[idx] = { ...newMsgs[idx], content };
        setMessages(newMsgs);
        sendMessage(content);
      }
    } catch {
      setError('Failed to update message');
    }
  }, [setMessages, setError, sendMessage]);

  return {
    messages,
    sessionId,
    isStreaming,
    error,

    sendMessage,
    abort,
    retry,
    loadHistory,
    loadSessions,
    createSession,
    deleteSession,
    clearHistory,
    deleteMessage,
    editMessage,
    clearMessages,
    setSessionId,
    setMessages,
    setError,
  };
}

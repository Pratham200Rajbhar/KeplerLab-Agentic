'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Clock, Plus } from 'lucide-react';

import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import {
  streamChat,
  getChatHistory,
  streamResearch,
  getChatSessions,
  createChatSession,
  deleteChatSession,
} from '@/lib/api/chat';
import { createNotebook } from '@/lib/api/notebooks';
import { readSSEStream } from '@/lib/utils/helpers';
import { apiConfig } from '@/lib/api/config';
import { RESEARCH_STEPS_TEMPLATE } from '@/lib/utils/constants';

import ChatMessageList from './ChatMessageList';
import ChatInputArea from './ChatInputArea';
import ChatHistoryModal from './ChatHistoryModal';
import ChatEmptyState from './ChatEmptyState';

/**
 * Thin wrapper that isolates useSearchParams so URL changes
 * don't trigger a full ChatPanel re-render (PERF 3).
 */
export default function ChatPanelWithParams() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const pathname = usePathname();

  const currentSessionId = searchParams.get('session') || null;
  const setCurrentSessionId = useCallback(
    (id) => {
      const params = new URLSearchParams(searchParams.toString());
      if (id) params.set('session', id);
      else params.delete('session');
      router.replace(`${pathname}?${params.toString()}`, { scroll: false });
    },
    [searchParams, router, pathname],
  );

  return (
    <ChatPanel
      currentSessionId={currentSessionId}
      setCurrentSessionId={setCurrentSessionId}
    />
  );
}

function ChatPanel({ currentSessionId, setCurrentSessionId }) {
  const router = useRouter();

  /* ── Store selectors ── */
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const messages = useAppStore((s) => s.messages);
  const setMessages = useAppStore((s) => s.setMessages);
  const addMessage = useAppStore((s) => s.addMessage);
  const loading = useAppStore((s) => s.loading);
  const setLoadingState = useAppStore((s) => s.setLoadingState);
  const draftMode = useAppStore((s) => s.draftMode);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);
  const pendingChatMessage = useAppStore((s) => s.pendingChatMessage);
  const setPendingChatMessage = useAppStore((s) => s.setPendingChatMessage);

  const toast = useToast();

  /* ── Derived state ── */
  const effectiveIds = useMemo(
    () =>
      selectedSources.filter((id) => {
        const mat = materials.find((m) => m.id === id);
        return mat && mat.status === 'completed';
      }),
    [selectedSources, materials],
  );
  const hasSource = effectiveIds.length > 0;
  const isSourceProcessing = !hasSource && selectedSources.length > 0;

  /* ── Local state ── */
  const [streamingContent, setStreamingContent] = useState('');
  const [mindMapBanner, setMindMapBanner] = useState(null);

  // Agent thinking state
  const [isThinking, setIsThinking] = useState(false);
  const [stepLog, setStepLog] = useState([]);
  const [pendingFiles, setPendingFiles] = useState([]);

  // Streaming step log
  const [liveStepLog, setLiveStepLog] = useState([]);

  // Sessions
  const [sessions, setSessions] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historySearchTerm, setHistorySearchTerm] = useState('');

  // Research
  const [researchMode, setResearchMode] = useState(false);
  const [researchSteps, setResearchSteps] = useState([]);

  // ── Mode-specific live state (used during streaming, saved to agentMeta on done) ──
  // Agent mode
  const [agentPlan, setAgentPlan] = useState(null);        // { steps[], total_steps }
  const [agentStepResults, setAgentStepResults] = useState([]); // StepResult[]
  const [agentActiveStep, setAgentActiveStep] = useState(null); // { step_index, tool, description }
  // New agent execution view state
  const [liveAgentSteps, setLiveAgentSteps] = useState([]);  // [{ label, status }] for AgentExecutionView
  const [liveAgentArtifacts, setLiveAgentArtifacts] = useState([]);  // Artifacts during streaming
  const [liveAgentSummary, setLiveAgentSummary] = useState(null);  // Summary text during streaming
  // Code mode
  const [codeBlock, setCodeBlock] = useState(null);         // { code, language, packages }
  const [codeExecResult, setCodeExecResult] = useState(null); // { stdout, stderr, exit_code }
  // Web search mode
  const [webSearchStatus, setWebSearchStatus] = useState('idle'); // idle | searching | scraping | synthesizing | done
  const [webSources, setWebSources] = useState([]);
  const [webQueries, setWebQueries] = useState([]);
  // Research (deep) mode — enhanced
  const [researchIteration, setResearchIteration] = useState(0);
  const [researchTotalIterations, setResearchTotalIterations] = useState(5);
  const [researchPhase, setResearchPhase] = useState('searching');
  const [researchPhaseLabel, setResearchPhaseLabel] = useState('');
  const [researchQueriesUsed, setResearchQueriesUsed] = useState([]);
  const [researchSources, setResearchSources] = useState([]);
  const [researchStatus, setResearchStatus] = useState('idle'); // idle | researching | synthesizing | done
  const [researchQuery, setResearchQuery] = useState('');

  /* ── Refs ── */
  const isChattingRef = useRef(false);
  const abortControllerRef = useRef(null);

  /* ── Effects ── */

  // Abort on unmount
  useEffect(() => () => abortControllerRef.current?.abort(), []);

  // Mind map → chat bridge
  useEffect(() => {
    if (pendingChatMessage?.source === 'mindmap') {
      setMindMapBanner(pendingChatMessage.nodeLabel);
      setPendingChatMessage(null);
    }
  }, [pendingChatMessage, setPendingChatMessage]);

  useEffect(() => {
    isChattingRef.current = loading.chat || researchMode;
  }, [loading.chat, researchMode]);

  // Load sessions on notebook change
  useEffect(() => {
    const loadHistory = async () => {
      if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
        try {
          const sessionsData = await getChatSessions(currentNotebook.id);
          const newSessions = sessionsData.sessions || [];
          setSessions(newSessions);
          const isValid = currentSessionId && newSessions.some((s) => s.id === currentSessionId);
          if (!isValid && newSessions.length > 0) setCurrentSessionId(newSessions[0].id);
          else if (!isValid) setCurrentSessionId(null);
        } catch (error) {
          console.error('Failed to load initial sessions:', error);
        }
      } else {
        setSessions([]);
      }
    };
    loadHistory();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentNotebook?.id, draftMode]);

  // Load messages when session / notebook changes
  useEffect(() => {
    let cancelled = false;
    const loadMessages = async () => {
      // Don't overwrite the message list while a stream is in progress
      if (useAppStore.getState().loading?.chat) return;
      if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
        try {
          const history = await getChatHistory(currentNotebook.id, currentSessionId);
          if (cancelled || useAppStore.getState().loading?.chat) return;
          setMessages(
            history && history.length > 0
              ? history.map((msg) => ({
                  id: msg.id,
                  role: msg.role,
                  content: msg.content,
                  timestamp: new Date(msg.created_at),
                  blocks: msg.blocks || [],
                  agentMeta: msg.agent_meta || null,
                }))
              : [],
          );
        } catch (error) {
          console.error('Failed to load chat history:', error);
          if (!cancelled) setMessages([]);
        }
      } else if (currentNotebook?.id) {
        setMessages([]);
      }
    };
    loadMessages();
    return () => { cancelled = true; };
  }, [currentNotebook?.id, currentNotebook?.isDraft, currentSessionId, draftMode, setMessages]);

  /* ── Session handlers ── */
  const handleCreateSession = useCallback(async () => {
    if (!currentNotebook?.id) return;
    try {
      const res = await createChatSession(currentNotebook.id, 'New Chat');
      if (res.session_id) {
        setCurrentSessionId(res.session_id);
        setMessages([]);
        const sessionsData = await getChatSessions(currentNotebook.id);
        setSessions(sessionsData.sessions || []);
      }
    } catch (e) {
      console.error('Failed to create session', e);
      toast.error('Failed to create chat session');
    }
  }, [currentNotebook?.id, setCurrentSessionId, setMessages, toast]);

  const handleDeleteSession = useCallback(async (e, sessionId) => {
    e.stopPropagation();
    try {
      await deleteChatSession(sessionId);
      const sessionsData = await getChatSessions(currentNotebook?.id);
      const newSessions = sessionsData.sessions || [];
      setSessions(newSessions);
      if (currentSessionId === sessionId) {
        setCurrentSessionId(newSessions.length > 0 ? newSessions[0].id : null);
      }
    } catch (err) {
      console.error('Failed to delete', err);
      toast.error('Failed to delete session');
    }
  }, [currentNotebook?.id, currentSessionId, setCurrentSessionId, toast]);

  const handleSelectSession = useCallback((sessionId) => {
    setCurrentSessionId(sessionId);
    setIsHistoryModalOpen(false);
  }, [setCurrentSessionId]);

  const handleCreateChatClick = useCallback(() => {
    handleCreateSession();
    setIsHistoryModalOpen(false);
  }, [handleCreateSession]);

  const handleStop = useCallback(() => abortControllerRef.current?.abort(), []);

  /* ── Reset mode-specific state ── */
  const resetModeState = useCallback(() => {
    setAgentPlan(null); setAgentStepResults([]); setAgentActiveStep(null);
    setLiveAgentSteps([]); setLiveAgentArtifacts([]); setLiveAgentSummary(null);
    setCodeBlock(null); setCodeExecResult(null);
    setWebSearchStatus('idle'); setWebSources([]); setWebQueries([]);
    setResearchStatus('idle'); setResearchIteration(0); setResearchPhase('searching');
    setResearchPhaseLabel(''); setResearchQueriesUsed([]); setResearchSources([]);
  }, []);

  /* ── Main send handler ── */
  const handleSend = useCallback(async (userMessage, intentOverride, commandForMessage) => {
    if (!userMessage?.trim()) return;

    let activeNotebookId = currentNotebook?.id;

    if (!activeNotebookId || currentNotebook?.isDraft) {
      setLoadingState('chat', true);
      try {
        const title = userMessage.slice(0, 30) + (userMessage.length > 30 ? '...' : '');
        const newNb = await createNotebook(title, 'Created from chat');
        const store = useAppStore.getState();
        store.setCurrentNotebook(newNb);
        store.setNewlyCreatedNotebookId(newNb.id);
        store.setDraftMode(false);
        activeNotebookId = newNb.id;
        router.replace(`/notebook/${newNb.id}`);
      } catch (e) {
        console.error('Failed to auto-create notebook:', e);
        toast.error('Failed to start chat in new notebook');
        setLoadingState('chat', false);
        return;
      }
    }

    addMessage('user', userMessage, { slashCommand: commandForMessage || undefined });
    setLoadingState('chat', true);
    setStreamingContent('');
    setIsThinking(true);
    setStepLog([]);
    setLiveStepLog([]);
    setPendingFiles([]);
    resetModeState();

    const ac = new AbortController();
    abortControllerRef.current = ac;

    let accumulated = '';
    let agentMeta = null;
    let messageBlocks = [];
    let committedMsgId = null;
    let localStepLog = [];
    let localPendingFiles = [];
    let localArtifacts = [];
    // Mode-specific accumulators
    let localAgentPlan = null;
    let localAgentStepResults = [];
    let localAgentSteps = [];  // New: for AgentExecutionView
    let localAgentSummary = null;  // New: summary text
    let localCodeBlock = null;
    let localCodeExecResult = null;
    let localWebSources = [];
    let localWebQueries = [];
    let localResearchSources = [];
    let localResearchQueriesUsed = [];
    let detectedIntent = intentOverride || null;

    try {
      let sessionIdToUse = currentSessionId;
      if (!sessionIdToUse) {
        const title = userMessage.slice(0, 30) + (userMessage.length > 30 ? '...' : '');
        const res = await createChatSession(activeNotebookId, title);
        sessionIdToUse = res.session_id;
        setCurrentSessionId(sessionIdToUse);
        const sessionsData = await getChatSessions(activeNotebookId);
        setSessions(sessionsData.sessions || []);
      }

      const response = await streamChat(
        null, userMessage, activeNotebookId, effectiveIds, sessionIdToUse, ac.signal, intentOverride,
      );

      await readSSEStream(response.body, {
        // ── Common events ──
        token: (p) => { accumulated += p.content || ''; setStreamingContent(accumulated); },
        step: (p) => {
          // Backend uses 'status' key for the step description text
          const stepLabel = p.label || p.status || p.tool || '';
          const stepEntry = { tool: p.tool || p.label || '', status: 'running', label: stepLabel };
          localStepLog.push(stepEntry);
          setLiveStepLog([...localStepLog]);
          // Also update AgentExecutionView steps
          const agentStep = { label: stepLabel, status: 'running' };
          localAgentSteps.push(agentStep);
          setLiveAgentSteps([...localAgentSteps]);
        },
        step_done: (p) => {
          const stepEntry = p.step || { tool: p.tool, status: p.status };
          localStepLog.push(stepEntry);
          setStepLog((prev) => [...prev, stepEntry]);
        },
        // New: intent detection event — backend sends {task_type, confidence, ...}
        intent: (p) => {
          detectedIntent = p.intent || p.task_type || detectedIntent;
        },
        // New: summary event — backend sends {title, description, key_results, metrics}
        summary: (p) => {
          const summaryText = p.text || p.summary || p.description || p.title || '';
          localAgentSummary = {
            text: summaryText,
            key_results: p.key_results || [],
            metrics: p.metrics || null,
            title: p.title || '',
          };
          setLiveAgentSummary(localAgentSummary);
        },
        file_ready: (p) => { localPendingFiles.push(p); setPendingFiles((prev) => [...prev, p]); },
        artifact: (p) => {
          // Make the artifact URL absolute — backend returns relative path like /agent/file/{id}?token=...
          const rawUrl = p.url || p.download_url || p.downloadUrl || '';
          const absoluteUrl = rawUrl && rawUrl.startsWith('/') ? `${apiConfig.baseUrl}${rawUrl}` : rawUrl;
          const artifact = {
            artifact_id: p.artifact_id || p.id || null,
            filename: p.filename || p.name || 'file',
            mime: p.mime || p.mimeType || '',
            display_type: p.display_type || 'file_card',
            url: absoluteUrl,
            size: p.size_bytes || p.sizeBytes || p.size || 0,
            category: p.category || null,
          };
          localArtifacts = [...localArtifacts, artifact];
          setLiveAgentArtifacts([...localArtifacts]);
        },
        meta: (p) => { agentMeta = p; if (p.intent) detectedIntent = p.intent; },
        blocks: (p) => { messageBlocks = p.blocks || []; },

        // ── Agent mode events ──
        agent_start: (p) => {
          detectedIntent = 'AGENT';
          localAgentPlan = { steps: p.plan || [], total_steps: p.total_steps || 0 };
          setAgentPlan(localAgentPlan);
        },
        tool_start: (p) => {
          const step = { step_index: p.step_index, tool: p.tool, description: p.description, status: 'running' };
          setAgentActiveStep(step);
          // Also add to AgentExecutionView steps
          const agentStep = { label: p.description || p.tool || '', status: 'running' };
          localAgentSteps.push(agentStep);
          setLiveAgentSteps([...localAgentSteps]);
        },
        tool_result: (p) => {
          const result = {
            step_index: p.step_index, tool: p.tool, description: p.description,
            summary: p.summary, duration_ms: p.duration_ms,
            artifacts: p.artifacts || [], code: p.code || null,
            status: p.error ? 'error' : 'done', error: p.error || null,
          };
          localAgentStepResults = [...localAgentStepResults, result];
          setAgentStepResults([...localAgentStepResults]);
          setAgentActiveStep(null);
          // Update step status in AgentExecutionView
          if (localAgentSteps.length > 0) {
            localAgentSteps[localAgentSteps.length - 1].status = p.error ? 'error' : 'completed';
            setLiveAgentSteps([...localAgentSteps]);
          }
        },
        code_generated: (p) => {
          // Agent mode: code generated by python_tool
          localCodeBlock = { code: p.code, language: p.language || 'python', step_index: p.step_index };
        },

        // ── Code mode events ──
        code_block: (p) => {
          detectedIntent = detectedIntent || 'CODE_EXECUTION';
          localCodeBlock = { code: p.code, language: p.language || 'python', packages: p.packages || [] };
          setCodeBlock(localCodeBlock);
        },
        done_generation: (p) => {
          // Code generation complete (Phase 1), user can now review + run
          localCodeBlock = { code: p.code, language: p.language || 'python', packages: p.packages || [] };
          setCodeBlock(localCodeBlock);
        },

        // ── Web search mode events ──
        web_start: (p) => {
          detectedIntent = detectedIntent || 'WEB_SEARCH';
          localWebQueries = p.queries || [];
          setWebQueries(localWebQueries);
          setWebSearchStatus('searching');
        },
        web_scraping: (p) => {
          setWebSearchStatus('scraping');
        },
        web_sources: (p) => {
          localWebSources = p.sources || [];
          setWebSources(localWebSources);
          setWebSearchStatus('done');
        },

        // ── Research mode events ──
        research_start: (p) => {
          detectedIntent = detectedIntent || 'WEB_RESEARCH';
          setResearchStatus('researching');
          setResearchTotalIterations(p.max_iterations || 5);
        },
        research_phase: (p) => {
          if (p.iteration !== undefined) setResearchIteration(p.iteration);
          if (p.phase) setResearchPhase(p.phase);
          if (p.label) setResearchPhaseLabel(p.label);
          if (p.queries) {
            localResearchQueriesUsed = [...localResearchQueriesUsed, ...p.queries];
            setResearchQueriesUsed([...localResearchQueriesUsed]);
          }
          if (p.status === 'synthesizing') setResearchStatus('synthesizing');
        },
        research_source: (p) => {
          localResearchSources = [...localResearchSources, p];
          setResearchSources([...localResearchSources]);
        },
        citations: (p) => {
          // Store citations to attach to the message
          if (p.citations) {
            agentMeta = { ...(agentMeta || {}), citations: p.citations };
          }
        },

        // ── Lifecycle ──
        done: (p) => {
          const finalContent = accumulated || agentMeta?.response || p.response || '';
          if (finalContent || localCodeBlock || localArtifacts.length > 0) {
            const newMsg = {
              id: `ai-${Date.now()}`, role: 'assistant', content: finalContent,
              agentMeta: {
                ...(agentMeta || {}),
                intent: detectedIntent,
                step_log: localStepLog.length > 0 ? localStepLog : agentMeta?.step_log || [],
                generated_files: localPendingFiles.length > 0 ? localPendingFiles : agentMeta?.generated_files || [],
                total_time: p.elapsed || p.duration_ms || 0,
                // Agent mode
                plan: localAgentPlan,
                step_results: localAgentStepResults.length > 0 ? localAgentStepResults : undefined,
                tools_used: p.tools_used || agentMeta?.tools_used || [],
                // New agent execution data
                steps: localAgentSteps.length > 0 ? localAgentSteps : undefined,
                summary: localAgentSummary || p.summary || undefined,
                generated_code: localCodeBlock,
                logs: p.logs || undefined,
                tool_outputs: p.tool_outputs || undefined,
                // Code mode
                code_block: localCodeBlock,
                // Web search mode
                web_sources: localWebSources.length > 0 ? localWebSources : undefined,
                web_queries: localWebQueries.length > 0 ? localWebQueries : undefined,
                // Research mode
                research_sources: localResearchSources.length > 0 ? localResearchSources : undefined,
                research_queries: localResearchQueriesUsed.length > 0 ? localResearchQueriesUsed : undefined,
              },
              blocks: messageBlocks,
              artifacts: localArtifacts,
            };
            setMessages((prev) => [...prev, newMsg]);
            committedMsgId = newMsg.id;
          }
          setStreamingContent(''); setIsThinking(false); setLiveStepLog([]);
          resetModeState(); accumulated = '';
        },
        error: (p) => {
          addMessage('assistant', `I encountered an error: ${p.error || 'Streaming error'}`);
          setStreamingContent(''); setIsThinking(false); setLiveStepLog([]);
          resetModeState(); accumulated = '';
        },
      });

      if (accumulated && !committedMsgId) {
        setMessages((prev) => [...prev, { id: `ai-${Date.now()}`, role: 'assistant', content: accumulated, agentMeta: { ...(agentMeta || {}), intent: detectedIntent }, blocks: messageBlocks }]);
        setStreamingContent('');
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        if (accumulated && !committedMsgId) {
          setMessages((prev) => [...prev, { id: `ai-${Date.now()}`, role: 'assistant', content: accumulated, agentMeta, blocks: messageBlocks }]);
        }
      } else {
        addMessage('assistant', `I encountered an error: ${error.message}`);
      }
      setStreamingContent(''); setLiveStepLog([]); resetModeState();
    } finally {
      setLoadingState('chat', false); setIsThinking(false);
      abortControllerRef.current = null;
    }
  }, [currentNotebook, currentSessionId, effectiveIds, addMessage, setLoadingState, setMessages, setCurrentSessionId, resetModeState, router, toast]);

  /* ── Message actions ── */
  const handleDeleteMessage = useCallback((messageId) => {
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
  }, [setMessages]);

  const handleRetryMessage = useCallback((message) => {
    const idx = messages.findIndex((m) => m.id === message.id);
    if (idx === -1) return;
    let userMsg = null;
    for (let i = idx - 1; i >= 0; i--) {
      if (messages[i].role === 'user') { userMsg = messages[i]; break; }
    }
    if (!userMsg) return;
    setMessages((prev) => prev.slice(0, idx));
    handleSend(userMsg.content, null, null);
  }, [messages, setMessages, handleSend]);

  const handleEditMessage = useCallback((messageId, newContent) => {
    const idx = messages.findIndex((m) => m.id === messageId);
    if (idx === -1) return;
    setMessages((prev) => prev.slice(0, idx));
    handleSend(newContent, null, null);
  }, [messages, setMessages, handleSend]);

  /* ── Research handler ── */
  const handleResearch = useCallback(async (query) => {
    if (!query || loading.chat) return;

    let activeNotebookId = currentNotebook?.id;
    if (!activeNotebookId || currentNotebook?.isDraft) {
      setLoadingState('chat', true);
      try {
        const title = query.slice(0, 30) + (query.length > 30 ? '...' : '');
        const newNb = await createNotebook(title, 'Created from research');
        const store = useAppStore.getState();
        store.setCurrentNotebook(newNb);
        store.setNewlyCreatedNotebookId(newNb.id);
        store.setDraftMode(false);
        activeNotebookId = newNb.id;
        router.replace(`/notebook/${newNb.id}`);
      } catch (e) {
        console.error('Failed to auto-create notebook:', e);
        toast.error('Failed to start research in new notebook');
        setLoadingState('chat', false);
        return;
      }
    }

    addMessage('user', query);
    setLoadingState('chat', true);
    setResearchMode(true);
    setResearchQuery(query);
    setResearchSteps(RESEARCH_STEPS_TEMPLATE.map((s) => ({ ...s })));

    const stepMap = { research_planner: 0, search_executor: 1, content_extractor: 2, theme_clusterer: 3, synthesis_engine: 4 };
    const ac = new AbortController();
    abortControllerRef.current = ac;
    let accumulated = '';
    let agentMeta = null;

    const advanceStep = (toolName) => {
      const idx = stepMap[toolName] ?? -1;
      if (idx < 0) return;
      setResearchSteps((prev) => prev.map((s, i) => ({ ...s, status: i < idx ? 'done' : i === idx ? 'active' : s.status })));
    };

    try {
      const response = await streamResearch(query, activeNotebookId, effectiveIds, ac.signal);
      await readSSEStream(response.body, {
        step: (p) => advanceStep(p.tool || ''),
        token: (p) => { accumulated += p.content || ''; },
        meta: (p) => { agentMeta = p; setResearchSteps((prev) => prev.map((s) => ({ ...s, status: 'done' }))); },
        done: () => {
          setResearchMode(false);
          if (accumulated) {
            setMessages((prev) => [...prev, { id: `ai-research-${Date.now()}`, role: 'assistant', content: accumulated, agentMeta, blocks: [] }]);
          }
        },
        error: (p) => { setResearchMode(false); addMessage('assistant', `Research failed: ${p.error || 'Unknown error'}`); },
      });
    } catch (err) {
      setResearchMode(false);
      if (err.name === 'AbortError') {
        if (accumulated) {
          setMessages((prev) => [...prev, { id: `ai-research-${Date.now()}`, role: 'assistant', content: accumulated, agentMeta, blocks: [] }]);
        }
      } else {
        addMessage('assistant', `Research failed: ${err.message}`);
      }
    } finally {
      setLoadingState('chat', false); setResearchMode(false); abortControllerRef.current = null;
    }
  }, [currentNotebook?.id, loading.chat, effectiveIds, addMessage, setLoadingState, setMessages, router, toast, currentNotebook?.isDraft]);

  /* ── Quick actions ── */
  const handleQuickAction = useCallback((action) => {
    const prompts = {
      summarize: 'Summarize the main points from this document',
      explain: 'Explain the key concepts in simple terms',
      keypoints: 'What are the most important takeaways?',
      studyguide: 'Create a study guide from this content',
    };
    handleSend(prompts[action.id] || action.label, null, null);
  }, [handleSend]);

  const isLoading = loading.chat;

  /* ── Render ── */
  return (
    <main className="flex-1 bg-surface-50 flex flex-col overflow-hidden relative">
      {/* History Modal */}
      <ChatHistoryModal
        isOpen={isHistoryModalOpen}
        onClose={() => setIsHistoryModalOpen(false)}
        sessions={sessions}
        currentSessionId={currentSessionId}
        onSelectSession={handleSelectSession}
        onCreateChat={handleCreateChatClick}
        onDeleteSession={handleDeleteSession}
        historySearchTerm={historySearchTerm}
        setHistorySearchTerm={setHistorySearchTerm}
      />

      {/* Header */}
      <div className="panel-header flex justify-between items-center px-4 py-2.5 shrink-0 gap-3" style={{ background: 'var(--surface-raised)', borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
        <div className="flex items-center gap-2.5 min-w-0">
          <span className="font-semibold text-text-primary text-sm">Chat</span>
          {sessions.find((s) => s.id === currentSessionId)?.title && (
            <span className="text-xs text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full truncate max-w-[140px]">
              {sessions.find((s) => s.id === currentSessionId)?.title}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5 shrink-0">
          {hasSource && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-full bg-success/10 text-success">
              <span className="w-1.5 h-1.5 rounded-full bg-success" />
              {selectedSources.length > 1 ? `${selectedSources.length} sources` : '1 source'}
            </div>
          )}
          {isSourceProcessing && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-full bg-accent/10 text-accent animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              Indexing…
            </div>
          )}
          <button onClick={() => setIsHistoryModalOpen(true)} className="btn-secondary py-1.5 px-2.5 flex items-center gap-1.5 text-xs" title="Chat history" aria-label="Open chat history">
            <Clock className="w-3.5 h-3.5 text-text-muted" />
            History
          </button>
          <button onClick={handleCreateChatClick} className="btn-icon p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted transition-all" title="New Chat" aria-label="Start new chat">
            <Plus className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Chat Content */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 && !researchMode ? (
          <ChatEmptyState
            hasSource={hasSource}
            isSourceProcessing={isSourceProcessing}
            selectedSources={selectedSources}
            materials={materials}
            onQuickAction={handleQuickAction}
          />
        ) : (
          <>
            <ChatMessageList
              messages={messages}
              notebookId={currentNotebook?.id}
              currentSessionId={currentSessionId}
              onRetry={handleRetryMessage}
              onEdit={handleEditMessage}
              onDelete={handleDeleteMessage}
              streamingContent={streamingContent}
              liveStepLog={liveStepLog}
              isThinking={isThinking}
              researchMode={researchMode}
              researchSteps={researchSteps}
              researchQuery={researchQuery}
              isLoading={isLoading}
              /* ── Mode-specific live state ── */
              agentPlan={agentPlan}
              agentStepResults={agentStepResults}
              agentActiveStep={agentActiveStep}
              liveAgentSteps={liveAgentSteps}
              liveAgentArtifacts={liveAgentArtifacts}
              liveAgentSummary={liveAgentSummary}
              codeBlock={codeBlock}
              codeExecResult={codeExecResult}
              webSearchStatus={webSearchStatus}
              webSources={webSources}
              researchStatus={researchStatus}
              researchIteration={researchIteration}
              researchTotalIterations={researchTotalIterations}
              researchPhase={researchPhase}
              researchPhaseLabel={researchPhaseLabel}
              researchQueriesUsed={researchQueriesUsed}
              researchSources={researchSources}
            />
          </>
        )}
      </div>

      {/* Input Area */}
      <ChatInputArea
        onSend={handleSend}
        onResearch={handleResearch}
        disabled={false}
        isStreaming={isLoading}
        onStop={handleStop}
        hasSource={hasSource}
        isSourceProcessing={isSourceProcessing}
        notebookId={currentNotebook?.id}
        mindMapBanner={mindMapBanner}
        onDismissBanner={() => setMindMapBanner(null)}
      />
    </main>
  );
}

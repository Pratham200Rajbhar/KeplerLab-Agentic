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
import { readSSEStream } from '@/lib/utils/helpers';
import { RESEARCH_STEPS_TEMPLATE } from '@/lib/utils/constants';

import ChatMessageList from './ChatMessageList';
import ChatInputArea from './ChatInputArea';
import ChatHistoryModal from './ChatHistoryModal';
import ChatEmptyState from './ChatEmptyState';
import ArtifactPanel from './ArtifactPanel';

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
  const [agentStepLabel, setAgentStepLabel] = useState('');
  const [mindMapBanner, setMindMapBanner] = useState(null);

  // Agent thinking state
  const [isThinking, setIsThinking] = useState(false);
  const [thinkingStep, setThinkingStep] = useState('');
  const [stepLog, setStepLog] = useState([]);
  const [currentStepNum, setCurrentStepNum] = useState(0);
  const [pendingFiles, setPendingFiles] = useState([]);
  const [isRepair, setIsRepair] = useState(false);
  const [repairCount, setRepairCount] = useState(0);

  // Streaming step log
  const [liveStepLog, setLiveStepLog] = useState([]);

  // Per-command state
  const [codeForReview, setCodeForReview] = useState(null);
  const [agentTaskSteps, setAgentTaskSteps] = useState([]);
  const [webResearchPhase, setWebResearchPhase] = useState(null);

  // Artifact panel state
  const [artifacts, setArtifacts] = useState({});
  const [artifactPanelOpen, setArtifactPanelOpen] = useState(false);

  // Sessions
  const [sessions, setSessions] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historySearchTerm, setHistorySearchTerm] = useState('');

  // Research
  const [researchMode, setResearchMode] = useState(false);
  const [researchSteps, setResearchSteps] = useState([]);
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
    const loadMessages = async (attempt = 0) => {
      if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
        try {
          const history = await getChatHistory(currentNotebook.id, currentSessionId);
          if (cancelled || isChattingRef.current) return;
          if (history && history.length > 0) {
            setMessages(
              history.map((msg) => ({
                id: msg.id,
                role: msg.role,
                content: msg.content,
                timestamp: new Date(msg.created_at),
                blocks: msg.blocks || [],
                agentMeta: msg.agent_meta || null,
              })),
            );
          } else {
            setMessages([]);
          }
        } catch (error) {
          console.error('Failed to load chat history:', error);
          if (attempt < 1 && !cancelled) {
            setTimeout(() => !cancelled && loadMessages(attempt + 1), 800);
            return;
          }
          if (!isChattingRef.current && !cancelled) setMessages([]);
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

  /* ── Main send handler ── */
  const handleSend = useCallback(async (userMessage, intentOverride, commandForMessage) => {
    if (!userMessage?.trim() || !hasSource || !currentNotebook?.id || currentNotebook.isDraft) return;

    addMessage('user', userMessage, { slashCommand: commandForMessage || undefined });
    setLoadingState('chat', true);
    setStreamingContent('');
    setAgentStepLabel('');
    setIsThinking(true);
    setThinkingStep('');
    setStepLog([]);
    setLiveStepLog([]);
    setCurrentStepNum(0);
    setPendingFiles([]);
    setIsRepair(false);
    setRepairCount(0);
    setCodeForReview(null);
    setAgentTaskSteps([]);
    setWebResearchPhase(null);

    const ac = new AbortController();
    abortControllerRef.current = ac;

    let accumulated = '';
    let agentMeta = null;
    let messageBlocks = [];
    let committedMsgId = null;
    let localStepLog = [];
    let localPendingFiles = [];

    const TOOL_STEP_LABELS = {
      rag_tool:             'Searching materials…',
      research_tool:        'Researching online…',
      python_tool:          'Running Python…',
      data_profiler:        'Profiling dataset…',
      quiz_tool:            'Generating quiz…',
      flashcard_tool:       'Creating flashcards…',
      ppt_tool:             'Building slides…',
      file_generator:       'Generating file…',
      agent_task_tool:      'Executing task…',
      web_research_tool:    'Deep-searching…',
      code_generation_tool: 'Generating code…',
    };

    try {
      let sessionIdToUse = currentSessionId;
      if (!sessionIdToUse) {
        const title = userMessage.slice(0, 30) + (userMessage.length > 30 ? '...' : '');
        const res = await createChatSession(currentNotebook.id, title);
        sessionIdToUse = res.session_id;
        setCurrentSessionId(sessionIdToUse);
        const sessionsData = await getChatSessions(currentNotebook.id);
        setSessions(sessionsData.sessions || []);
      }

      const response = await streamChat(
        null, userMessage, currentNotebook.id, effectiveIds, sessionIdToUse, ac.signal, intentOverride,
      );

      await readSSEStream(response.body, {
        token: (p) => { accumulated += p.content || ''; setStreamingContent(accumulated); },
        step: (p) => {
          const raw = p.tool || p.label || '';
          const label = TOOL_STEP_LABELS[raw] || p.label || raw || 'Thinking…';
          setAgentStepLabel(label);
          setThinkingStep(label);
          setCurrentStepNum((prev) => prev + 1);
          setLiveStepLog((prev) => {
            const updated = prev.map((s) => s.status === 'running' ? { ...s, status: 'success' } : s);
            return [...updated, { tool: raw, label: TOOL_STEP_LABELS[raw] || raw, status: 'running' }];
          });
        },
        step_done: (p) => {
          const stepEntry = p.step || { tool: p.tool, status: p.status };
          localStepLog.push(stepEntry);
          setStepLog((prev) => [...prev, stepEntry]);
          setLiveStepLog((prev) => {
            const lastRunningIdx = prev.findLastIndex((s) => s.status === 'running');
            if (lastRunningIdx === -1) return [...prev, stepEntry];
            const updated = [...prev];
            const liveStep = updated[lastRunningIdx];
            updated[lastRunningIdx] = { ...stepEntry, code: stepEntry.code || liveStep.code || '', stdout: stepEntry.stdout || liveStep.stdout || '' };
            return updated;
          });
        },
        code_written: (p) => {
          setLiveStepLog((prev) => {
            if (!prev.length) return prev;
            const updated = [...prev];
            const idx = updated.findLastIndex((s) => s.status === 'running');
            const ti = idx !== -1 ? idx : updated.length - 1;
            updated[ti] = { ...updated[ti], code: p.code };
            return updated;
          });
        },
        code_generating: () => {
          setThinkingStep('Generating code…');
          setLiveStepLog((prev) => {
            if (!prev.length) return prev;
            const updated = [...prev];
            const idx = updated.findLastIndex((s) => s.status === 'running');
            if (idx !== -1) updated[idx] = { ...updated[idx], label: 'Generating code…' };
            return updated;
          });
        },
        code_stdout: (p) => {
          const line = p.line || '';
          setLiveStepLog((prev) => {
            if (!prev.length) return prev;
            const updated = [...prev];
            const idx = updated.findLastIndex((s) => s.status === 'running');
            const ti = idx !== -1 ? idx : updated.length - 1;
            const existing = updated[ti].stdout || '';
            updated[ti] = { ...updated[ti], stdout: existing ? existing + '\n' + line : line, label: 'Running Python…' };
            return updated;
          });
        },
        stdout: (p) => {
          const output = p.output || '';
          if (output) {
            setLiveStepLog((prev) => {
              if (!prev.length) return prev;
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (!updated[lastIdx].stdout) updated[lastIdx] = { ...updated[lastIdx], stdout: output };
              return updated;
            });
          }
        },
        agent_step: (p) => {
          setAgentTaskSteps((prev) => [...prev, p]);
          const labels = { plan: 'Planning task…', act: p.action ? `Acting: ${p.action.slice(0, 50)}` : 'Executing step…', observe: 'Observing result…' };
          setThinkingStep(labels[p.phase] || 'Thinking…');
        },
        web_research_phase: (p) => { setWebResearchPhase(p); setThinkingStep(p.label || `Research phase ${p.phase}/5`); },
        code_for_review: (p) => {
          setCodeForReview({ code: p.code || '', language: p.language || 'python', explanation: p.explanation || '', dependencies: p.dependencies || [] });
          setThinkingStep('Code ready — review below');
        },
        repair_attempt: (p) => { setIsRepair(true); setRepairCount(p.attempt || 1); setThinkingStep(`Fixing error — attempt ${p.attempt || 1}`); },
        repair_success: () => { setIsRepair(false); setThinkingStep('Fix applied, re-running…'); },
        file_ready: (p) => { localPendingFiles.push(p); setPendingFiles((prev) => [...prev, p]); },
        artifact: (p) => {
          const type = p.type || 'files'; // charts | files | tables | code
          setArtifacts((prev) => ({
            ...prev,
            [type]: [...(prev[type] || []), p],
          }));
          setArtifactPanelOpen(true);
        },
        meta: (p) => { agentMeta = p; },
        blocks: (p) => { messageBlocks = p.blocks || []; },
        done: (p) => {
          const finalContent = accumulated || agentMeta?.response || '';
          if (finalContent) {
            const newMsg = {
              id: `ai-${Date.now()}`, role: 'assistant', content: finalContent,
              agentMeta: { ...(agentMeta || {}), step_log: localStepLog.length > 0 ? localStepLog : agentMeta?.step_log || [], generated_files: localPendingFiles.length > 0 ? localPendingFiles : agentMeta?.generated_files || [], total_time: p.elapsed || 0 },
              blocks: messageBlocks,
            };
            setMessages((prev) => [...prev, newMsg]);
            committedMsgId = newMsg.id;
          }
          setStreamingContent(''); setIsThinking(false); setLiveStepLog([]); accumulated = '';
        },
        error: (p) => {
          addMessage('assistant', `I encountered an error: ${p.error || 'Streaming error'}`);
          setStreamingContent(''); setIsThinking(false); setLiveStepLog([]); accumulated = '';
        },
      });

      if (accumulated && !committedMsgId) {
        setMessages((prev) => [...prev, { id: `ai-${Date.now()}`, role: 'assistant', content: accumulated, agentMeta, blocks: messageBlocks }]);
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
      setStreamingContent(''); setLiveStepLog([]);
    } finally {
      setLoadingState('chat', false); setAgentStepLabel(''); setIsThinking(false);
      setIsRepair(false); setRepairCount(0); abortControllerRef.current = null;
    }
  }, [hasSource, currentNotebook, currentSessionId, effectiveIds, addMessage, setLoadingState, setMessages, setCurrentSessionId]);

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
    if (!query || !hasSource || !currentNotebook?.id || loading.chat) return;

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
      const response = await streamResearch(query, currentNotebook.id, effectiveIds, ac.signal);
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
  }, [hasSource, currentNotebook?.id, loading.chat, effectiveIds, addMessage, setLoadingState, setMessages]);

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
            codeForReview={codeForReview}
            agentTaskSteps={agentTaskSteps}
            webResearchPhase={webResearchPhase}
            agentStepLabel={agentStepLabel}
            isLoading={isLoading}
          />
        )}
      </div>

      {/* Input Area */}
      <ChatInputArea
        onSend={handleSend}
        onResearch={handleResearch}
        disabled={!currentNotebook?.id || !!currentNotebook?.isDraft}
        isStreaming={isLoading}
        onStop={handleStop}
        hasSource={hasSource}
        isSourceProcessing={isSourceProcessing}
        notebookId={currentNotebook?.id}
        isThinking={isThinking}
        thinkingStep={thinkingStep}
        currentStepNum={currentStepNum}
        isRepair={isRepair}
        repairCount={repairCount}
        mindMapBanner={mindMapBanner}
        onDismissBanner={() => setMindMapBanner(null)}
      />

      {/* Artifact Panel */}
      <ArtifactPanel
        isOpen={artifactPanelOpen}
        onClose={() => setArtifactPanelOpen(false)}
        artifacts={artifacts}
      />
    </main>
  );
}

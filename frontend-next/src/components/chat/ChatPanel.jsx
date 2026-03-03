'use client';

import { useState, useRef, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import {
  Clock,
  Plus,
  Square,
  Send,
  X,
  Lightbulb,
  Sparkles,
  FlaskConical,
} from 'lucide-react';

import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import {
  streamChat,
  getChatHistory,
  streamResearch,
  getSuggestions,
  getChatSessions,
  createChatSession,
  deleteChatSession,
} from '@/lib/api/chat';
import { readSSEStream } from '@/lib/utils/helpers';
import { RESEARCH_STEPS_TEMPLATE, TIMERS } from '@/lib/utils/constants';

import ChatMessage from './ChatMessage';
import MarkdownRenderer, { sanitizeStreamingMarkdown } from './MarkdownRenderer';
import SuggestionDropdown from './SuggestionDropdown';
import ResearchProgress from './ResearchProgress';
import AgentThinkingBar from './AgentThinkingBar';
import AgentActionBlock from './AgentActionBlock';
import SlashCommandPills from './SlashCommandPills';
import SlashCommandDropdown from './SlashCommandDropdown';
import CommandBadge from './CommandBadge';
import { parseSlashCommand } from './slashCommands';
import ChatHistoryModal from './ChatHistoryModal';
import ChatEmptyState from './ChatEmptyState';

const LIVE_TOOL_LABELS = {
  rag_tool:       'Searching your materials',
  research_tool:  'Researching the web',
  python_tool:    'Running code',
  data_profiler:  'Analyzing data',
  quiz_tool:      'Generating quiz',
  flashcard_tool: 'Creating flashcards',
  ppt_tool:       'Building slides',
  code_repair:    'Fixing error',
};

function getLiveLabel(tool = '') {
  const key = Object.keys(LIVE_TOOL_LABELS).find(k => tool.toLowerCase().includes(k));
  return key ? LIVE_TOOL_LABELS[key] : (tool || 'Processing');
}

function LiveStepText({ steps }) {
  const latest = steps[steps.length - 1];
  const label = getLiveLabel(latest?.tool || '');
  return (
    <div className="flex items-center gap-1.5 mb-2 animate-fade-in">
      <span className="flex gap-0.5 items-end h-3 shrink-0">
        <span className="w-0.5 h-1.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '0ms' }} />
        <span className="w-0.5 h-2.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '150ms' }} />
        <span className="w-0.5 h-1.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '300ms' }} />
      </span>
      <span className="text-xs text-text-muted">{label}…</span>
    </div>
  );
}

export default function ChatPanel() {
  /* ── Store selectors ── */
  const currentMaterial = useAppStore((s) => s.currentMaterial);
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

  /* ── Next.js routing ── */
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

  /* ── Derived state ── */
  const effectiveIds = useMemo(
    () =>
      Array.from(selectedSources).filter((id) => {
        const mat = materials.find((m) => m.id === id);
        return mat && mat.status === 'completed';
      }),
    [selectedSources, materials],
  );
  const hasSource = effectiveIds.length > 0;
  const isSourceProcessing = !hasSource && selectedSources.size > 0;

  /* ── Local state ── */
  const [inputValue, setInputValue] = useState('');
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

  // Suggestions
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

  // Slash commands
  const [activeCommand, setActiveCommand] = useState(null);
  const [showSlashDropdown, setShowSlashDropdown] = useState(false);
  const [slashFilter, setSlashFilter] = useState('');
  const [isInputFocused, setIsInputFocused] = useState(false);

  // Streaming step log
  const [liveStepLog, setLiveStepLog] = useState([]);

  // Sessions
  const [sessions, setSessions] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historySearchTerm, setHistorySearchTerm] = useState('');

  // Research
  const [researchMode, setResearchMode] = useState(false);
  const [researchSteps, setResearchSteps] = useState([]);
  const [researchQuery, setResearchQuery] = useState('');

  /* ── Refs ── */
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);
  const isChattingRef = useRef(false);
  const abortControllerRef = useRef(null);

  /* ── Effects ── */

  // Abort on unmount
  useEffect(() => () => abortControllerRef.current?.abort(), []);

  // Mind map → chat bridge
  useEffect(() => {
    if (pendingChatMessage?.source === 'mindmap') {
      setInputValue(pendingChatMessage.text);
      setMindMapBanner(pendingChatMessage.nodeLabel);
      textareaRef.current?.focus();
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
          const urlSession = searchParams.get('session');
          const isValid = urlSession && newSessions.some((s) => s.id === urlSession);
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
    return () => {
      cancelled = true;
    };
  }, [currentNotebook?.id, currentSessionId, draftMode, setMessages]);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  // Reset suggestions on input change
  useEffect(() => {
    setShowSuggestions(false);
    setSuggestions([]);
  }, [inputValue]);

  /* ── Session handlers ── */
  const handleCreateSession = async () => {
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
  };

  const handleDeleteSession = async (e, sessionId) => {
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
  };

  const handleSelectSession = (sessionId) => {
    setCurrentSessionId(sessionId);
    setIsHistoryModalOpen(false);
  };

  const handleCreateChatClick = () => {
    handleCreateSession();
    setIsHistoryModalOpen(false);
  };

  const handleStop = useCallback(() => abortControllerRef.current?.abort(), []);

  /* ── Main send handler ── */
  const handleSend = async (message = inputValue) => {
    if (!message.trim() || !hasSource || !currentNotebook?.id || currentNotebook.isDraft) return;

    let userMessage = message.trim();
    let intentOverride = null;
    let commandForMessage = activeCommand;

    if (!commandForMessage) {
      const parsed = parseSlashCommand(userMessage);
      if (parsed) {
        commandForMessage = parsed.command;
        intentOverride = parsed.command.intent;
        userMessage = parsed.remainingMessage || commandForMessage.label;
      }
    } else {
      intentOverride = commandForMessage.intent;
    }

    setActiveCommand(null);
    setShowSlashDropdown(false);
    setSlashFilter('');
    setInputValue('');

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

    const ac = new AbortController();
    abortControllerRef.current = ac;

    let accumulated = '';
    let agentMeta = null;
    let messageBlocks = [];
    let committedMsgId = null;
    let localStepLog = [];
    let localPendingFiles = [];

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
        null,
        userMessage,
        currentNotebook.id,
        effectiveIds,
        sessionIdToUse,
        ac.signal,
        intentOverride,
      );

      await readSSEStream(response.body, {
        token: (payload) => {
          accumulated += payload.content || '';
          setStreamingContent(accumulated);
        },
        step: (payload) => {
          const TOOL_STEP_LABELS = {
            rag_tool: 'Searching materials…',
            research_tool: 'Researching online…',
            python_tool: 'Running Python…',
            data_profiler: 'Profiling dataset…',
            quiz_tool: 'Generating quiz…',
            flashcard_tool: 'Creating flashcards…',
            ppt_tool: 'Building slides…',
            file_generator: 'Generating file…',
          };
          const raw = payload.tool || payload.label || '';
          const label = TOOL_STEP_LABELS[raw] || payload.label || raw || 'Thinking…';
          setAgentStepLabel(label);
          setThinkingStep(label);
          setCurrentStepNum((prev) => prev + 1);
          setLiveStepLog((prev) => {
            const updated = prev.map((s) =>
              s.status === 'running' ? { ...s, status: 'success' } : s,
            );
            return [
              ...updated,
              { tool: raw, label: TOOL_STEP_LABELS[raw] || raw, status: 'running' },
            ];
          });
        },
        step_done: (payload) => {
          const stepEntry = payload.step || { tool: payload.tool, status: payload.status };
          localStepLog.push(stepEntry);
          setStepLog((prev) => [...prev, stepEntry]);
          setLiveStepLog((prev) => {
            const lastRunningIdx = prev.findLastIndex((s) => s.status === 'running');
            if (lastRunningIdx === -1) return [...prev, stepEntry];
            const updated = [...prev];
            const liveStep = updated[lastRunningIdx];
            updated[lastRunningIdx] = {
              ...stepEntry,
              code: stepEntry.code || liveStep.code || '',
              stdout: stepEntry.stdout || liveStep.stdout || '',
            };
            return updated;
          });
          setLiveStepLog((prev) => {
            const last = prev[prev.length - 1];
            if (last && last.code && localStepLog.length > 0) {
              localStepLog[localStepLog.length - 1].code = last.code;
            }
            if (
              last &&
              last.stdout &&
              localStepLog.length > 0 &&
              !localStepLog[localStepLog.length - 1].stdout
            ) {
              localStepLog[localStepLog.length - 1].stdout = last.stdout;
            }
            return prev;
          });
        },
        code_written: (payload) => {
          setLiveStepLog((prev) => {
            if (prev.length === 0) return prev;
            const updated = [...prev];
            const runningIdx = updated.findLastIndex((s) => s.status === 'running');
            const targetIdx = runningIdx !== -1 ? runningIdx : updated.length - 1;
            updated[targetIdx] = { ...updated[targetIdx], code: payload.code };
            return updated;
          });
        },
        code_generating: () => {
          setThinkingStep('Generating code…');
          setLiveStepLog((prev) => {
            if (prev.length === 0) return prev;
            const updated = [...prev];
            const runningIdx = updated.findLastIndex((s) => s.status === 'running');
            if (runningIdx !== -1) {
              updated[runningIdx] = { ...updated[runningIdx], label: 'Generating code…' };
            }
            return updated;
          });
        },
        code_stdout: (payload) => {
          const line = payload.line || '';
          setLiveStepLog((prev) => {
            if (prev.length === 0) return prev;
            const updated = [...prev];
            const runningIdx = updated.findLastIndex((s) => s.status === 'running');
            const targetIdx = runningIdx !== -1 ? runningIdx : updated.length - 1;
            const existing = updated[targetIdx].stdout || '';
            updated[targetIdx] = {
              ...updated[targetIdx],
              stdout: existing ? existing + '\n' + line : line,
              label: 'Running Python…',
            };
            return updated;
          });
        },
        stdout: (payload) => {
          const output = payload.output || '';
          if (output) {
            setLiveStepLog((prev) => {
              if (prev.length === 0) return prev;
              const updated = [...prev];
              const lastIdx = updated.length - 1;
              if (!updated[lastIdx].stdout) {
                updated[lastIdx] = { ...updated[lastIdx], stdout: output };
              }
              return updated;
            });
          }
        },
        repair_attempt: (payload) => {
          const count = payload.attempt || 1;
          setIsRepair(true);
          setRepairCount(count);
          setThinkingStep(`Fixing error — attempt ${count}`);
        },
        repair_success: () => {
          setIsRepair(false);
          setThinkingStep('Fix applied, re-running…');
        },
        file_ready: (payload) => {
          localPendingFiles.push(payload);
          setPendingFiles((prev) => [...prev, payload]);
        },
        meta: (payload) => {
          agentMeta = payload;
        },
        blocks: (payload) => {
          messageBlocks = payload.blocks || [];
        },
        done: (payload) => {
          const finalContent = accumulated || (agentMeta && agentMeta.response) || '';
          const elapsedTime = payload.elapsed || 0;
          if (finalContent) {
            const newMsg = {
              id: `ai-${Date.now()}`,
              role: 'assistant',
              content: finalContent,
              agentMeta: {
                ...(agentMeta || {}),
                step_log:
                  localStepLog.length > 0 ? localStepLog : agentMeta?.step_log || [],
                generated_files:
                  localPendingFiles.length > 0
                    ? localPendingFiles
                    : agentMeta?.generated_files || [],
                total_time: elapsedTime,
              },
              blocks: messageBlocks,
            };
            setMessages((prev) => [...prev, newMsg]);
            committedMsgId = newMsg.id;
          }
          setStreamingContent('');
          setIsThinking(false);
          setLiveStepLog([]);
          accumulated = '';
        },
        error: (payload) => {
          addMessage(
            'assistant',
            `I encountered an error: ${payload.error || 'Streaming error'}`,
          );
          setStreamingContent('');
          setIsThinking(false);
          setLiveStepLog([]);
          accumulated = '';
        },
      });

      if (accumulated && !committedMsgId) {
        setMessages((prev) => [
          ...prev,
          {
            id: `ai-${Date.now()}`,
            role: 'assistant',
            content: accumulated,
            agentMeta,
            blocks: messageBlocks,
          },
        ]);
        setStreamingContent('');
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        if (accumulated && !committedMsgId) {
          setMessages((prev) => [
            ...prev,
            {
              id: `ai-${Date.now()}`,
              role: 'assistant',
              content: accumulated,
              agentMeta,
              blocks: messageBlocks,
            },
          ]);
        }
      } else {
        addMessage('assistant', `I encountered an error: ${error.message}`);
      }
      setStreamingContent('');
      setLiveStepLog([]);
    } finally {
      setLoadingState('chat', false);
      setAgentStepLabel('');
      setIsThinking(false);
      setIsRepair(false);
      setRepairCount(0);
      abortControllerRef.current = null;
    }
  };

  /* ── Message actions (delete / retry / edit) ── */
  const handleDeleteMessage = useCallback((messageId) => {
    setMessages((prev) => prev.filter((m) => m.id !== messageId));
  }, [setMessages]);

  const handleRetryMessage = useCallback((message) => {
    const msgList = messages;
    const idx = msgList.findIndex((m) => m.id === message.id);
    if (idx === -1) return;
    let userMsg = null;
    for (let i = idx - 1; i >= 0; i--) {
      if (msgList[i].role === 'user') { userMsg = msgList[i]; break; }
    }
    if (!userMsg) return;
    setMessages((prev) => prev.slice(0, idx));
    handleSend(userMsg.content);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, setMessages]);

  const handleEditMessage = useCallback((messageId, newContent) => {
    const idx = messages.findIndex((m) => m.id === messageId);
    if (idx === -1) return;
    setMessages((prev) => prev.slice(0, idx));
    handleSend(newContent);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [messages, setMessages]);

  /* ── Research handler ── */
  const handleResearch = async () => {
    const query = inputValue.trim();
    if (!query || !hasSource || !currentNotebook?.id || loading.chat) return;

    setInputValue('');
    addMessage('user', query);
    setLoadingState('chat', true);
    setResearchMode(true);
    setResearchQuery(query);
    setResearchSteps(RESEARCH_STEPS_TEMPLATE.map((s) => ({ ...s })));

    const stepMap = {
      research_planner: 0,
      search_executor: 1,
      content_extractor: 2,
      theme_clusterer: 3,
      synthesis_engine: 4,
    };

    const ac = new AbortController();
    abortControllerRef.current = ac;
    let accumulated = '';
    let agentMeta = null;

    const advanceStep = (toolName) => {
      const idx = stepMap[toolName] ?? -1;
      if (idx < 0) return;
      setResearchSteps((prev) =>
        prev.map((s, i) => ({
          ...s,
          status: i < idx ? 'done' : i === idx ? 'active' : s.status,
        })),
      );
    };

    try {
      const response = await streamResearch(
        query,
        currentNotebook.id,
        effectiveIds,
        ac.signal,
      );

      await readSSEStream(response.body, {
        step: (payload) => advanceStep(payload.tool || ''),
        token: (payload) => {
          accumulated += payload.content || '';
        },
        meta: (payload) => {
          agentMeta = payload;
          setResearchSteps((prev) => prev.map((s) => ({ ...s, status: 'done' })));
        },
        done: () => {
          setResearchMode(false);
          if (accumulated) {
            setMessages((prev) => [
              ...prev,
              {
                id: `ai-research-${Date.now()}`,
                role: 'assistant',
                content: accumulated,
                agentMeta,
                blocks: [],
              },
            ]);
          }
        },
        error: (payload) => {
          setResearchMode(false);
          addMessage('assistant', `Research failed: ${payload.error || 'Unknown error'}`);
        },
      });
    } catch (err) {
      setResearchMode(false);
      if (err.name === 'AbortError') {
        if (accumulated) {
          setMessages((prev) => [
            ...prev,
            {
              id: `ai-research-${Date.now()}`,
              role: 'assistant',
              content: accumulated,
              agentMeta,
              blocks: [],
            },
          ]);
        }
      } else {
        addMessage('assistant', `Research failed: ${err.message}`);
      }
    } finally {
      setLoadingState('chat', false);
      setResearchMode(false);
      abortControllerRef.current = null;
    }
  };

  /* ── Input handlers ── */
  const handleKeyDown = (e) => {
    if (showSlashDropdown) return;
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInputChange = useCallback(
    (e) => {
      const val = e.target.value;
      setInputValue(val);
      if (!activeCommand) {
        if (val === '/') {
          setShowSlashDropdown(true);
          setSlashFilter('');
        } else if (val.startsWith('/') && !val.includes(' ')) {
          setShowSlashDropdown(true);
          setSlashFilter(val.slice(1));
        } else {
          setShowSlashDropdown(false);
          setSlashFilter('');
        }
      } else {
        setShowSlashDropdown(false);
      }
    },
    [activeCommand],
  );

  const handleSlashSelect = useCallback((cmd) => {
    setActiveCommand(cmd);
    setShowSlashDropdown(false);
    setSlashFilter('');
    setInputValue('');
    textareaRef.current?.focus();
  }, []);

  const handleRemoveCommand = useCallback(() => {
    setActiveCommand(null);
    textareaRef.current?.focus();
  }, []);

  const handleQuickAction = (action) => {
    const prompts = {
      summarize: 'Summarize the main points from this document',
      explain: 'Explain the key concepts in simple terms',
      keypoints: 'What are the most important takeaways?',
      studyguide: 'Create a study guide from this content',
    };
    handleSend(prompts[action.id] || action.label);
  };

  const handleGetSuggestions = async () => {
    if (!inputValue.trim() || !hasSource || !currentNotebook?.id) return;
    setIsFetchingSuggestions(true);
    setShowSuggestions(true);
    try {
      const data = await getSuggestions(inputValue, currentNotebook.id);
      setSuggestions(data?.suggestions || []);
    } catch (err) {
      console.error(err);
      setSuggestions([]);
    } finally {
      setIsFetchingSuggestions(false);
    }
  };

  const handleSuggestionSelect = (suggestion) => {
    setShowSuggestions(false);
    setSuggestions([]);
    setInputValue(suggestion);
    handleSend(suggestion);
  };

  const isLoading = loading.chat;
  const showTypingIndicator =
    isLoading && !streamingContent && !researchMode && liveStepLog.length === 0;

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
              {selectedSources.size > 1
                ? `${selectedSources.size} sources`
                : '1 source'}
            </div>
          )}
          {isSourceProcessing && (
            <div className="hidden sm:flex items-center gap-1.5 text-xs px-2 py-1 rounded-full bg-accent/10 text-accent animate-pulse">
              <span className="w-1.5 h-1.5 rounded-full bg-accent" />
              Indexing…
            </div>
          )}
          <button
            onClick={() => setIsHistoryModalOpen(true)}
            className="btn-secondary py-1.5 px-2.5 flex items-center gap-1.5 text-xs"
            title="Chat history"
            aria-label="Open chat history"
          >
            <Clock className="w-3.5 h-3.5 text-text-muted" />
            History
          </button>
          <button
            onClick={handleCreateChatClick}
            className="btn-icon p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted transition-all"
            title="New Chat"
            aria-label="Start new chat"
          >
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
          <div className="max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 md:px-8">
            {messages.map((msg) => (
              <ChatMessage
                key={msg.id}
                message={msg}
                notebookId={currentNotebook?.id}
                onRetry={msg.role === 'assistant' ? handleRetryMessage : undefined}
                onEdit={msg.role === 'user' ? handleEditMessage : undefined}
                onDelete={handleDeleteMessage}
              />
            ))}

            {/* Research progress */}
            {researchMode && (
              <div className="message flex w-full justify-start message-ai">
                <div className="message-content w-full">
                  <ResearchProgress steps={researchSteps} query={researchQuery} />
                </div>
              </div>
            )}

            {/* Live streaming bubble */}
            {(streamingContent || (isThinking && liveStepLog.length > 0)) && (
              <div className="chat-msg chat-msg-ai group py-5">
                <div className="flex gap-3 w-full">
                  <div className="ai-avatar shrink-0 mt-0.5 streaming-pulse">
                    <Lightbulb className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    {liveStepLog.length > 0 && !streamingContent && (
                      <LiveStepText steps={liveStepLog} />
                    )}
                    {streamingContent && (
                      <div className="markdown-content">
                        <MarkdownRenderer
                          content={sanitizeStreamingMarkdown(streamingContent)}
                        />
                        <span className="streaming-cursor" />
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Typing indicator */}
            {showTypingIndicator && (
              <div className="chat-msg chat-msg-ai py-5 animate-fade-in">
                <div className="flex gap-3 w-full">
                  <div className="ai-avatar shrink-0 mt-0.5 streaming-pulse">
                    <Lightbulb className="w-4 h-4" />
                  </div>
                  <div className="flex items-center gap-2 py-1">
                    <div className="typing-indicator">
                      <span />
                      <span />
                      <span />
                    </div>
                    {agentStepLabel && (
                      <span className="text-xs text-text-muted">{agentStepLabel}</span>
                    )}
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 sm:p-6 flex justify-center w-full z-10 sticky bottom-0 bg-linear-to-t from-surface-100 via-surface-100 to-transparent pt-12">
        <div className="max-w-4xl w-full relative">
          {/* Agent Thinking Bar */}
          {isThinking && (
            <AgentThinkingBar
              isActive={isThinking}
              currentStep={thinkingStep}
              stepNumber={currentStepNum}
              totalSteps={0}
              isRepair={isRepair}
              repairCount={repairCount}
            />
          )}

          {/* Suggestion Dropdown */}
          {hasSource &&
            currentNotebook?.id &&
            !currentNotebook.isDraft &&
            showSuggestions && (
              <SuggestionDropdown
                suggestions={suggestions}
                loading={isFetchingSuggestions}
                onSelect={handleSuggestionSelect}
                onClose={() => setShowSuggestions(false)}
              />
            )}

          {/* Mind Map banner */}
          {mindMapBanner && (
            <div className="border-l-[3px] border-accent-light bg-surface-raised px-3 py-1.5 mb-2 rounded-r-md flex items-center justify-between">
              <span className="text-xs text-text-secondary">
                Asking about:{' '}
                <strong className="text-text-primary">{mindMapBanner}</strong>
              </span>
              <button
                onClick={() => setMindMapBanner(null)}
                className="text-text-secondary hover:text-text-primary transition-colors p-0.5"
                aria-label="Dismiss mind map context"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}

          {/* Slash Command Suggestion Pills */}
          <SlashCommandPills
            visible={
              isInputFocused && !activeCommand && !inputValue && hasSource && !isLoading
            }
            onSelect={handleSlashSelect}
          />

          {/* Slash Command Dropdown */}
          <SlashCommandDropdown
            visible={showSlashDropdown && !activeCommand}
            filter={slashFilter}
            onSelect={handleSlashSelect}
            onClose={() => {
              setShowSlashDropdown(false);
              setSlashFilter('');
            }}
          />

          <div className="chat-input-container rounded-2xl shadow-lg transition-all transform-gpu">
            <div className="flex items-center flex-1 min-w-0">
              {activeCommand && (
                <div className="pl-3 shrink-0">
                  <CommandBadge command={activeCommand} onRemove={handleRemoveCommand} />
                </div>
              )}
              <textarea
                ref={textareaRef}
                value={inputValue}
                onChange={handleInputChange}
                onKeyDown={handleKeyDown}
                onFocus={() => setIsInputFocused(true)}
                onBlur={() => setTimeout(() => setIsInputFocused(false), 150)}
                placeholder={
                  activeCommand
                    ? `Type your ${activeCommand.label.toLowerCase()} prompt…`
                    : hasSource
                      ? isLoading
                        ? 'AI is thinking…'
                        : selectedSources.size > 1
                          ? `Ask about ${selectedSources.size} sources…`
                          : 'Ask anything about your source… (type / for commands)'
                      : isSourceProcessing
                        ? 'Processing source, please wait…'
                        : 'Select a source to start…'
                }
                disabled={!hasSource || isLoading}
                className="flex-1 bg-transparent text-[15px] sm:text-base text-text-primary placeholder-text-muted resize-none outline-none min-h-[48px] max-h-[200px] py-3.5 px-4 leading-relaxed"
                rows={1}
                aria-label="Chat message input"
              />
            </div>
            <div className="flex items-end pb-2.5 pr-2.5 gap-1">
              {/* Suggest button */}
              {inputValue.trim().length > 0 && (
                <button
                  onClick={handleGetSuggestions}
                  disabled={!hasSource || isLoading || isFetchingSuggestions}
                  className="btn-icon text-accent hover:bg-accent/10 disabled:opacity-30 rounded-[10px] w-9 h-9 flex items-center justify-center transition-all"
                  title="Get prompt suggestions"
                  aria-label="Get prompt suggestions"
                >
                  {isFetchingSuggestions ? (
                    <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <Sparkles className="w-4 h-4" />
                  )}
                </button>
              )}

              {/* Research button */}
              {!isLoading && (
                <button
                  onClick={handleResearch}
                  disabled={!inputValue.trim() || !hasSource || isLoading}
                  className="btn-icon text-text-muted disabled:opacity-30 rounded-[10px] w-9 h-9 flex items-center justify-center transition-all research-btn"
                  title="Deep Research — searches the web and synthesizes a report"
                  aria-label="Deep Research"
                >
                  <FlaskConical className="w-4 h-4" />
                </button>
              )}

              {/* Stop / Send button */}
              {isLoading ? (
                <button
                  onClick={handleStop}
                  className="btn-icon bg-danger-subtle text-danger hover:bg-danger-subtle rounded-[10px] w-9 h-9 flex items-center justify-center transition-all ml-1"
                  title="Stop generation"
                  aria-label="Stop generation"
                >
                  <Square className="w-4 h-4" fill="currentColor" />
                </button>
              ) : (
                <button
                  onClick={() => handleSend()}
                  disabled={
                    !inputValue.trim() ||
                    !hasSource ||
                    isLoading ||
                    !currentNotebook?.id ||
                    !!currentNotebook?.isDraft
                  }
                  className="btn-icon bg-accent text-white disabled:opacity-40 disabled:bg-surface-overlay disabled:text-text-muted rounded-[10px] w-9 h-9 flex items-center justify-center transition-all ml-1"
                  aria-label="Send message"
                >
                  <Send className="w-4 h-4" />
                </button>
              )}
            </div>
          </div>

          {/* Footer hint */}
          <div className="flex items-center justify-center gap-3 mt-2">
            <p className="text-xs text-text-muted">
              <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay/60 font-mono text-[10px]">
                Enter
              </kbd>{' '}
              send &nbsp;·&nbsp;
              <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay/60 font-mono text-[10px]">
                ⇧ Enter
              </kbd>{' '}
              new line &nbsp;·&nbsp;
              <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay/60 font-mono text-[10px]">
                /
              </kbd>{' '}
              commands
            </p>
            {inputValue.length > 0 && (
              <span
                className={`text-xs tabular-nums ${inputValue.length > TIMERS.INPUT_LENGTH_WARNING
                  ? 'text-status-error'
                  : 'text-text-muted'
                  }`}
              >
                {inputValue.length}
              </span>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

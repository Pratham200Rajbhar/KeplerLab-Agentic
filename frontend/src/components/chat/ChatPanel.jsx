'use client';

import { useState, useEffect, useCallback, useMemo } from 'react';
import { useSearchParams, useRouter, usePathname } from 'next/navigation';
import { Clock, Plus, AlertCircle } from 'lucide-react';

import useAppStore from '@/stores/useAppStore';
import useChatStore from '@/stores/useChatStore';
import useChat from '@/hooks/useChat';
import { createNotebook } from '@/lib/api/notebooks';

import MessageList from './MessageList';
import ChatInput from './ChatInput';
import ChatHistorySidebar from './ChatHistorySidebar';
import EmptyState from './EmptyState';


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

  
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const draftMode = useAppStore((s) => s.draftMode);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);

  
  const effectiveIds = useMemo(
    () =>
      selectedSources.filter((id) => {
        const mat = materials.find((m) => m.id === id);
        return mat && mat.status === 'completed';
      }),
    [selectedSources, materials],
  );

  
  const {
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
    clearMessages,
    setSessionId,
    setError,
  } = useChat({
    notebookId: currentNotebook?.id,
    materialIds: effectiveIds,
  });

  
  const [sessions, setSessions] = useState([]);
  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [historySearchTerm, setHistorySearchTerm] = useState('');

  
  useEffect(() => {
    if (currentSessionId && currentSessionId !== sessionId) {
      setSessionId(currentSessionId);
    } else if (sessionId && !currentSessionId) {
      setCurrentSessionId(sessionId);
    }
  }, [currentSessionId, sessionId, setSessionId, setCurrentSessionId]);

  
  useEffect(() => {
    if (!currentNotebook?.id || currentNotebook.isDraft || draftMode) {
      setSessions([]);
      return;
    }

    let cancelled = false;
    (async () => {
      const data = await loadSessions();
      if (cancelled) return;
      setSessions(data);

      const isValid = currentSessionId && data.some((s) => s.id === currentSessionId);
      if (!isValid && data.length > 0) {
        setCurrentSessionId(data[0].id);
      } else if (!isValid) {
        setCurrentSessionId(null);
      }
    })();

    return () => { cancelled = true; };
    
  }, [currentNotebook?.id, draftMode]);

  
  useEffect(() => {
    if (!currentNotebook?.id || currentNotebook.isDraft || draftMode) {
      clearMessages();
      return;
    }
    if (isStreaming) return; 

    loadHistory(currentSessionId);
    
  }, [currentNotebook?.id, currentSessionId, draftMode]);

  
  const handleCreateSession = useCallback(async () => {
    if (!currentNotebook?.id) return;

    
    const emptySession = sessions.find((s) => !s.messages_text || s.messages_text.trim() === '');
    if (emptySession) {
      setCurrentSessionId(emptySession.id);
      setIsHistoryModalOpen(false);
      return;
    }

    const newId = await createSession('New Chat');
    if (newId) {
      setCurrentSessionId(newId);
      const data = await loadSessions();
      setSessions(data);
    }
  }, [currentNotebook?.id, createSession, setCurrentSessionId, loadSessions, sessions]);

  const handleDeleteSession = useCallback(
    async (e, sid) => {
      e.stopPropagation();
      await deleteSession(sid);
      const data = await loadSessions();
      setSessions(data);
      if (currentSessionId === sid) {
        setCurrentSessionId(data.length > 0 ? data[0].id : null);
      }
    },
    [currentSessionId, deleteSession, loadSessions, setCurrentSessionId],
  );

  const handleSelectSession = useCallback(
    (sid) => {
      setCurrentSessionId(sid);
      setIsHistoryModalOpen(false);
    },
    [setCurrentSessionId],
  );

  const handleCreateChatClick = useCallback(() => {
    handleCreateSession();
    setIsHistoryModalOpen(false);
  }, [handleCreateSession]);

  
  const handleSend = useCallback(
    async (content, intentOverride = null) => {
      if (!content?.trim()) return;

      let notebookId = currentNotebook?.id;

      
      if (!notebookId || currentNotebook?.isDraft) {
        try {
          const title = content.slice(0, 30) + (content.length > 30 ? '...' : '');
          const newNb = await createNotebook(title, 'Created from chat');
          const store = useAppStore.getState();
          store.setCurrentNotebook(newNb);
          store.setNewlyCreatedNotebookId(newNb.id);
          store.setDraftMode(false);
          notebookId = newNb.id;
          router.replace(`/notebook/${newNb.id}`);
        } catch {
          setError('Failed to start chat in new notebook');
          return;
        }
      }

      
      await sendMessage(content, notebookId, intentOverride);
    },
    [currentNotebook?.id, currentNotebook?.isDraft, sendMessage, router, setError],
  );

  
  const handleRetry = useCallback(
    (message) => {
      const msgs = useChatStore.getState().messages;
      const idx = msgs.findIndex((m) => m.id === message.id);
      if (idx === -1) return;

      
      let userMsg = null;
      for (let i = idx - 1; i >= 0; i--) {
        if (msgs[i].role === 'user') {
          userMsg = msgs[i];
          break;
        }
      }
      if (!userMsg) return;

      
      useChatStore.getState().setMessages(msgs.slice(0, idx));
      sendMessage(userMsg.content);
    },
    [sendMessage],
  );

  
  const currentSessionTitle = sessions.find((s) => s.id === currentSessionId)?.title;

  
  return (
    <main className="flex-1 bg-surface-50 flex flex-row overflow-hidden relative">
      {}
      {isHistoryModalOpen && (
        <div
          className="absolute inset-0 z-20 bg-black/20 backdrop-blur-sm transition-opacity opacity-100"
          onClick={() => setIsHistoryModalOpen(false)}
        />
      )}

      {}
      <ChatHistorySidebar
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

      {}
      <div className="flex-1 flex flex-col min-w-0">

        {}
        <div
          className="panel-header flex justify-between items-center px-4 py-2.5 shrink-0 gap-3"
          style={{
            background: 'var(--surface-raised)',
            borderBottom: '1px solid rgba(255,255,255,0.04)',
          }}
        >
          <div className="flex items-center gap-2.5 min-w-0">
            <span className="font-semibold text-text-primary text-sm">Chat</span>
            {currentSessionTitle && (
              <span className="text-xs text-text-muted bg-surface-overlay px-2 py-0.5 rounded-full truncate max-w-[140px]">
                {currentSessionTitle}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1.5 shrink-0">
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

        {}
        {error && (
          <div className="px-4 py-2 bg-error/10 border-b border-error/20 flex items-center gap-2 text-sm text-error">
            <AlertCircle size={14} />
            <span className="flex-1">{error}</span>
            <button
              onClick={retry}
              className="text-xs underline hover:no-underline"
            >
              Retry
            </button>
            <button
              onClick={() => setError(null)}
              className="text-xs opacity-60 hover:opacity-100"
            >
              Dismiss
            </button>
          </div>
        )}

        {}
        {messages.length === 0 && !isStreaming ? (
          <EmptyState onSend={handleSend} />
        ) : (
          <MessageList
            messages={messages}
            isStreaming={isStreaming}
            error={error}
            onRetry={handleRetry}
            notebookId={currentNotebook?.id}
            sessionId={sessionId}
          />
        )}

        <ChatInput
          onSend={handleSend}
          onStop={abort}
          isStreaming={isStreaming}
          disabled={false}
        />
      </div>
    </main>
  );
}

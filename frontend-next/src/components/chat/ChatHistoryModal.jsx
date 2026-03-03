'use client';

import { useMemo } from 'react';
import { Clock, Plus, Search, X, MessageCircle, Trash2 } from 'lucide-react';
import Modal from '@/components/ui/Modal';

export default function ChatHistoryModal({
  isOpen, onClose, sessions, currentSessionId, onSelectSession,
  onCreateChat, onDeleteSession, historySearchTerm, setHistorySearchTerm,
}) {
  const filteredSessions = useMemo(() =>
    sessions.filter(s => {
      const term = historySearchTerm.toLowerCase();
      return (s.title || 'New Conversation').toLowerCase().includes(term) ||
        (s.messages_text ? s.messages_text.toLowerCase().includes(term) : false);
    }),
    [sessions, historySearchTerm]
  );

  const groupedSessions = useMemo(() => {
    const groups = { today: [], yesterday: [], previous7Days: [], older: [] };
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today); yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today); sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    filteredSessions.forEach(session => {
      const d = new Date(session.createdAt ?? 0);
      if (d >= today) groups.today.push(session);
      else if (d >= yesterday) groups.yesterday.push(session);
      else if (d >= sevenDaysAgo) groups.previous7Days.push(session);
      else groups.older.push(session);
    });
    return groups;
  }, [filteredSessions]);

  const renderGroup = (title, items) => {
    if (items.length === 0) return null;
    return (
      <div className="mb-6 last:mb-0" key={title}>
        <h3 className="text-xs font-semibold text-text-muted uppercase tracking-wider mb-3 px-2">{title}</h3>
        <div className="space-y-2">
          {items.map(s => (
            <div key={s.id} onClick={() => onSelectSession(s.id)} role="button" tabIndex={0}
              onKeyDown={e => e.key === 'Enter' && onSelectSession(s.id)}
              className={`group relative p-3 rounded-xl transition-all cursor-pointer flex items-center justify-between ${currentSessionId === s.id ? 'bg-accent/5 shadow-sm' : 'bg-surface hover:bg-surface-raised hover:shadow-sm'}`}>
              <div className="flex items-center gap-4 min-w-0 pr-4">
                <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 transition-colors ${currentSessionId === s.id ? 'bg-accent/10 text-accent' : 'bg-surface-overlay text-text-muted group-hover:text-accent group-hover:bg-accent/5'}`}>
                  <MessageCircle className="w-5 h-5" />
                </div>
                <div className="flex flex-col min-w-0">
                  <h4 className={`font-medium text-[15px] truncate transition-colors ${currentSessionId === s.id ? 'text-accent' : 'text-text-primary group-hover:text-accent'}`}>
                    {s.title || 'New Conversation'}
                  </h4>
                  <div className="text-[11px] text-text-muted mt-0.5">
                    {new Date(s.createdAt || Date.now()).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </div>
                </div>
              </div>
              <button onClick={e => onDeleteSession(e, s.id)}
                className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-status-error transition-all p-2 rounded-lg hover:bg-danger-subtle shrink-0"
                title="Delete Chat"><Trash2 className="w-4 h-4" /></button>
            </div>
          ))}
        </div>
      </div>
    );
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Chat History" size="xl">
      <div className="flex flex-col md:flex-row h-[70vh] gap-6 -mx-2">
        <div className="w-full md:w-72 flex flex-col gap-5 shrink-0 pr-6 pl-2">
          <button onClick={onCreateChat}
            className="w-full py-3.5 px-4 rounded-xl bg-accent hover:bg-accent-dark text-white font-medium flex items-center justify-center gap-2.5 transition-all shadow-md hover:shadow-lg transform active:scale-[0.98]">
            <Plus className="w-5 h-5 shrink-0" />New Conversation
          </button>
          <div className="relative group">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted group-focus-within:text-accent transition-colors" />
            <input type="text" placeholder="Search conversations..." value={historySearchTerm}
              onChange={e => setHistorySearchTerm(e.target.value)}
              className="w-full pl-10 pr-4 py-2.5 bg-surface-overlay rounded-xl text-sm focus:outline-none focus:ring-1 focus:ring-accent/30 transition-all text-text-primary placeholder:text-text-muted" />
            {historySearchTerm && (
              <button onClick={() => setHistorySearchTerm('')} className="absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors">
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
          <div className="mt-auto p-4 rounded-xl bg-surface-overlay">
            <h3 className="text-xs font-bold text-text-muted uppercase tracking-wider mb-3">Overview</h3>
            <div className="flex items-center justify-between text-sm">
              <div className="flex items-center gap-2 text-text-secondary"><MessageCircle className="w-4 h-4 text-accent" />Total Chats</div>
              <span className="font-semibold text-text-primary px-2 py-0.5 rounded-md bg-surface-100">{sessions.length}</span>
            </div>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto pr-3 flex flex-col">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-16 h-16 rounded-2xl bg-accent-subtle text-accent flex items-center justify-center mb-4 shadow-sm"><MessageCircle className="w-8 h-8" /></div>
              <h3 className="text-lg text-text-primary font-semibold">No Conversations Yet</h3>
              <p className="text-sm text-text-secondary mt-2 max-w-sm">Start a new conversation to begin exploring topics.</p>
            </div>
          ) : filteredSessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full text-center">
              <div className="w-12 h-12 rounded-full bg-surface-overlay text-text-muted flex items-center justify-center mb-3"><Search className="w-6 h-6" /></div>
              <h3 className="text-text-primary font-medium">No results found</h3>
              <p className="text-sm text-text-muted mt-1">Try adjusting your search term.</p>
            </div>
          ) : (
            <div className="flex flex-col">
              {renderGroup('Today', groupedSessions.today)}
              {renderGroup('Yesterday', groupedSessions.yesterday)}
              {renderGroup('Previous 7 Days', groupedSessions.previous7Days)}
              {renderGroup('Older', groupedSessions.older)}
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

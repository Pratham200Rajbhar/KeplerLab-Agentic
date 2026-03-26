'use client';

import { useMemo } from 'react';
import { Plus, Search, X, MessageCircle, Trash2, ChevronLeft } from 'lucide-react';

export default function ChatHistorySidebar({
  isOpen,
  onClose,
  sessions,
  currentSessionId,
  onSelectSession,
  onCreateChat,
  onDeleteSession,
  historySearchTerm,
  setHistorySearchTerm,
}) {
  const filteredSessions = useMemo(
    () =>
      sessions.filter((s) => {
        const term = historySearchTerm.toLowerCase();
        return (
          (s.title || 'New Conversation').toLowerCase().includes(term) ||
          (s.messages_text ? s.messages_text.toLowerCase().includes(term) : false)
        );
      }),
    [sessions, historySearchTerm]
  );

  const groupedSessions = useMemo(() => {
    const groups = { today: [], yesterday: [], previous7Days: [], older: [] };
    const now = new Date();
    const today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
    filteredSessions.forEach((session) => {
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
        <h3 className="text-[10px] font-bold text-text-muted uppercase tracking-[0.15em] mb-3 px-2">
          {title}
        </h3>
        <div className="space-y-1">
          {items.map((s) => {
            const isActive = currentSessionId === s.id;
            return (
              <div
                key={s.id}
                onClick={() => onSelectSession(s.id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => e.key === 'Enter' && onSelectSession(s.id)}
                className={`workspace-history-item group relative p-3 rounded-xl transition-all duration-300 cursor-pointer flex items-center justify-between
                  ${
                    isActive
                      ? 'workspace-history-item-active border shadow-[0_0_15px_rgba(16,185,129,0.1)]'
                      : 'border border-transparent'
                  }`}
              >
                {isActive && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-1 h-8 bg-accent rounded-r-full shadow-[0_0_8px_var(--accent)]" />
                )}
                
                <div className="flex items-center gap-3 min-w-0 pr-2">
                  <div
                    className={`w-9 h-9 rounded-xl flex flex-shrink-0 items-center justify-center transition-all duration-300 ${
                      isActive
                        ? 'bg-accent/20 text-accent ring-1 ring-accent/30'
                        : 'bg-surface-overlay text-text-muted group-hover:bg-accent/10 group-hover:text-accent group-hover:ring-1 group-hover:ring-accent/20'
                    }`}
                  >
                    <MessageCircle className="w-4 h-4" />
                  </div>
                  <div className="flex flex-col min-w-0">
                    <h4
                      className={`font-medium text-sm truncate transition-colors duration-200 ${
                        isActive ? 'text-text-primary' : 'text-text-secondary group-hover:text-text-primary'
                      }`}
                    >
                      {s.title || 'New Conversation'}
                    </h4>
                    <div className="text-[10px] text-text-muted mt-0.5 font-medium tracking-wide">
                      {new Date(s.createdAt || Date.now()).toLocaleTimeString([], {
                        hour: '2-digit',
                        minute: '2-digit',
                      })}
                    </div>
                  </div>
                </div>
                
                <button
                  onClick={(e) => onDeleteSession(e, s.id)}
                  className="opacity-0 group-hover:opacity-100 text-text-muted hover:text-danger hover:bg-danger/10 transition-all p-2 rounded-lg shrink-0 translate-x-2 group-hover:translate-x-0"
                  title="Delete Chat"
                  aria-label="Delete chat"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div
      className={`workspace-history-sidebar absolute inset-y-0 right-0 z-30 transform transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)] flex flex-col w-80 ${
        isOpen ? 'translate-x-0 opacity-100' : 'translate-x-full opacity-0 pointer-events-none'
      }`}
    >
      {}
      <div className="workspace-history-header flex items-center justify-between p-5 shrink-0">
        <h2 className="text-sm font-semibold text-text-primary flex items-center gap-2">
          Chat History
          <span className="workspace-history-count text-[10px] py-0.5 px-2 rounded-full text-text-muted font-bold">
            {sessions.length}
          </span>
        </h2>
        <button
          onClick={onClose}
          className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-overlay transition-all"
          aria-label="Close history"
        >
          <ChevronLeft className="w-4 h-4" />
        </button>
      </div>

      {}
      <div className="p-5 flex flex-col gap-4 shrink-0 relative z-10">
        <button
          onClick={onCreateChat}
          className="workspace-history-cta group relative w-full py-3.5 px-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-all duration-300 overflow-hidden text-white"
        >
          {}
          <div className="absolute inset-0 bg-gradient-to-r from-accent to-accent-light opacity-90 group-hover:opacity-100 transition-opacity" />
          <div className="absolute inset-0 bg-gradient-to-r from-accent-light to-accent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
          
          <Plus className="w-5 h-5 relative z-10 shrink-0 transform group-hover:rotate-90 transition-transform duration-300" />
          <span className="relative z-10 tracking-wide text-[15px]">New Conversation</span>
        </button>

        <div className="workspace-history-search relative group/search">
          <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted group-focus-within/search:text-accent transition-colors duration-300" />
          <input
            type="text"
            placeholder="Search conversations..."
            value={historySearchTerm}
            onChange={(e) => setHistorySearchTerm(e.target.value)}
            className="workspace-history-search-input w-full pl-10 pr-10 py-3 border rounded-xl text-sm focus:outline-none transition-all duration-300 text-text-primary placeholder:text-text-muted"
          />
          {historySearchTerm && (
            <button
              onClick={() => setHistorySearchTerm('')}
              className="workspace-history-clear absolute right-3 top-1/2 -translate-y-1/2 text-text-muted hover:text-text-primary transition-colors p-1 rounded-md"
              aria-label="Clear search"
            >
              <X className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>

      {}
      <div className="workspace-history-list flex-1 overflow-y-auto custom-scrollbar px-3 pb-6 relative z-0">
        {}
        <div className="sticky top-0 h-4 bg-gradient-to-b from-surface/90 to-transparent z-10 pointer-events-none -mx-3 mb-2" />

        {sessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 -mt-10">
            <div className="w-16 h-16 rounded-3xl bg-surface-raised shadow-sm flex items-center justify-center mb-5 group-hover:scale-105 transition-transform">
              <MessageCircle className="w-6 h-6 text-text-muted" />
            </div>
            <h3 className="text-[15px] text-text-primary font-medium mb-1">It&apos;s quiet here</h3>
            <p className="text-[13px] text-text-secondary leading-relaxed max-w-[200px]">
              Start a new conversation to begin exploring topics.
            </p>
          </div>
        ) : filteredSessions.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full text-center px-4 -mt-10 animate-fade-in">
            <div className="w-14 h-14 rounded-full bg-surface-overlay flex items-center justify-center mb-4">
              <Search className="w-5 h-5 text-text-muted" />
            </div>
            <h3 className="text-[14px] text-text-primary font-medium">No results found</h3>
            <p className="text-[12px] text-text-muted mt-1.5">Try adjusting your search term.</p>
          </div>
        ) : (
          <div className="flex flex-col px-2">
            {renderGroup('Today', groupedSessions.today)}
            {renderGroup('Yesterday', groupedSessions.yesterday)}
            {renderGroup('Previous 7 Days', groupedSessions.previous7Days)}
            {renderGroup('Older', groupedSessions.older)}
          </div>
        )}
      </div>
    </div>
  );
}

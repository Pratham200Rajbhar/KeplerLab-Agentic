'use client';

import { useState, useEffect, useCallback, useRef, memo } from 'react';
import { SLASH_COMMANDS } from './slashCommands';

export default memo(function SlashCommandDropdown({ filter, onSelect, onClose, visible }) {
  // Derived-state pattern: tie the active index to the specific filter value it was
  // set for. When `filter` changes, activeIndex auto-resets to 0 during render
  // without needing a separate useEffect setState call.
  const [{ index, forFilter }, setActive] = useState({ index: 0, forFilter: filter });
  const activeIndex = forFilter === filter ? index : 0;
  const listRef = useRef(null);

  const filtered = SLASH_COMMANDS.filter(cmd => {
    if (!filter) return true;
    const search = filter.toLowerCase();
    return cmd.command.slice(1).startsWith(search) || cmd.label.toLowerCase().startsWith(search);
  });

  useEffect(() => {
    if (listRef.current) listRef.current.children[activeIndex]?.scrollIntoView({ block: 'nearest' });
  }, [activeIndex]);

  const handleKeyDown = useCallback(e => {
    if (!visible || filtered.length === 0) return;
    if (e.key === 'ArrowDown') {
      e.preventDefault();
      // setActive is a stable setState setter — no need to add it to deps
      setActive(prev => ({ index: (prev.index + 1) % filtered.length, forFilter: filter }));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setActive(prev => ({ index: (prev.index - 1 + filtered.length) % filtered.length, forFilter: filter }));
    } else if (e.key === 'Enter' || e.key === 'Tab') {
      e.preventDefault();
      onSelect(filtered[activeIndex]);
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  }, [visible, filtered, filter, activeIndex, onSelect, onClose]);

  useEffect(() => {
    if (!visible) return;
    const handler = e => handleKeyDown(e);
    window.addEventListener('keydown', handler, true);
    return () => window.removeEventListener('keydown', handler, true);
  }, [visible, handleKeyDown]);

  if (!visible || filtered.length === 0) return null;

  return (
    <div className="slash-dropdown absolute bottom-full left-0 right-0 mb-2 z-50 animate-fade-in">
      <div className="bg-surface-raised border border-border rounded-xl shadow-elevated overflow-hidden max-h-[320px] overflow-y-auto">
        <div className="px-3 py-2 border-b border-border/50">
          <span className="text-xs font-medium text-text-muted">Slash Commands</span>
        </div>
        <div ref={listRef} className="py-1">
          {filtered.map((cmd, idx) => (
            <button key={cmd.command} onClick={() => onSelect(cmd)} onMouseEnter={() => setActiveIndex(idx)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors duration-75 ${idx === activeIndex ? 'bg-accent/10' : 'hover:bg-surface-overlay/50'}`}>
              <span className="inline-flex items-center justify-center w-16 text-xs font-mono font-semibold rounded-md px-1.5 py-0.5 border"
                style={{ borderColor: `${cmd.color}40`, backgroundColor: `${cmd.color}15`, color: cmd.color }}>{cmd.command}</span>
              <span className="flex-1 min-w-0">
                <span className="text-sm text-text-primary">{cmd.label}</span>
                <span className="block text-xs text-text-muted truncate">{cmd.description}</span>
              </span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
});

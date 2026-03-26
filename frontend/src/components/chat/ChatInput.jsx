'use client';

import { useState, useRef, useEffect, useCallback, memo, useMemo } from 'react';
import { Send, Square, X, Globe, Code2, Search, Bot, Sparkles } from 'lucide-react';
import { parseSlashCommand } from '@/lib/utils/parseSlashCommand';
import useAppStore from '@/stores/useAppStore';
import PromptOptimizerDialog from './PromptOptimizerDialog';

const COMMAND_META = {
  research: { icon: Globe,  title: 'Research Mode',    desc: 'Deep web research and summarization',     color: 'text-blue-400',   bg: 'bg-blue-500/10' },
  code:     { icon: Code2,  title: 'Code Execution',   desc: 'Run Python analysis and generate charts', color: 'text-green-400',  bg: 'bg-green-500/10' },
  web:      { icon: Search, title: 'Web Search',       desc: 'Search latest information online',        color: 'text-orange-400', bg: 'bg-orange-500/10' },
  agent:    { icon: Bot,    title: 'Agent Mode',       desc: 'Autonomous multi-step reasoning agent',   color: 'text-purple-400', bg: 'bg-purple-500/10' },
};

const BADGE_COLORS = {
  WEB_RESEARCH:   'bg-blue-500/15 text-blue-300 border-blue-500/30',
  CODE_EXECUTION: 'bg-green-500/15 text-green-300 border-green-500/30',
  WEB_SEARCH:     'bg-orange-500/15 text-orange-300 border-orange-500/30',
  AGENT:          'bg-purple-500/15 text-purple-300 border-purple-500/30',
};

const ChatInput = memo(function ChatInput({ onSend, onStop, isStreaming, disabled, materialIds = [] }) {
  const [value, setValue] = useState('');
  const [dropdownIndex, setDropdownIndex] = useState(0);
  const [showOptimizer, setShowOptimizer] = useState(false);
  const textareaRef = useRef(null);

  
  // Sync with global chat input value from store
  const chatInputValue = useAppStore(s => s.chatInputValue);
  const setChatInputValue = useAppStore(s => s.setChatInputValue);

  const syncedValue = chatInputValue && chatInputValue.trim() !== '' ? chatInputValue : value;

  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = 'auto';
    el.style.height = `${Math.min(el.scrollHeight, 160)}px`;
  }, [syncedValue]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  useEffect(() => {
    if (chatInputValue && chatInputValue.trim() !== '') {
      // Focus and adjust height when an external source injects text.
      setTimeout(() => {
        if (textareaRef.current) {
          textareaRef.current.focus();
          textareaRef.current.style.height = 'auto';
          textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 160)}px`;
        }
      }, 50);
    }
  }, [chatInputValue]);

  
  // Derived state to avoid synchronous setStates in useEffect
  const { activeCommand, showDropdown } = useMemo(() => {
    const trimmed = syncedValue.trim();
    const parsed = parseSlashCommand(trimmed);
    const isTypingCmd = trimmed.startsWith('/') && !trimmed.includes(' ');
    
    return {
      activeCommand: parsed.command ? { label: parsed.label, intent: parsed.intent, command: parsed.command } : null,
      showDropdown: isTypingCmd
    };
  }, [syncedValue]);

  const handleValueChange = useCallback((val) => {
    if (chatInputValue) setChatInputValue('');
    setValue(val);
    setDropdownIndex(0);
  }, [chatInputValue, setChatInputValue]);

  
  const filteredCommands = useMemo(() => {
    if (!syncedValue.startsWith('/')) return [];
    const partial = syncedValue.slice(1).toLowerCase();
    return Object.entries(COMMAND_META).filter(([cmd]) => cmd.startsWith(partial));
  }, [syncedValue]);

  const selectCommand = useCallback((cmd) => {
    handleValueChange(`/${cmd} `);
    textareaRef.current?.focus();
  }, [handleValueChange]);
 
  const handleSend = useCallback(() => {
    const trimmed = syncedValue.trim();
    if (!trimmed || isStreaming) return;
    const parsed = parseSlashCommand(trimmed);
    const query = trimmed; // Keep full text including slash command
    const intentOverride = parsed.intent || null;
    if (!query) return;
    onSend(query, intentOverride);
    handleValueChange('');
    if (textareaRef.current) textareaRef.current.style.height = 'auto';
  }, [syncedValue, isStreaming, onSend, handleValueChange]);
 
  const handleKeyDown = useCallback(
    (e) => {
      
      if (showDropdown && filteredCommands.length > 0) {
        if (e.key === 'ArrowDown') {
          e.preventDefault();
          setDropdownIndex((i) => (i + 1) % filteredCommands.length);
          return;
        }
        if (e.key === 'ArrowUp') {
          e.preventDefault();
          setDropdownIndex((i) => (i - 1 + filteredCommands.length) % filteredCommands.length);
          return;
        }
        if (e.key === 'Tab' || e.key === 'Enter') {
          e.preventDefault();
          const [cmd] = filteredCommands[dropdownIndex] ?? filteredCommands[0];
          selectCommand(cmd);
          return;
        }
        if (e.key === 'Escape') {
          e.preventDefault();
          handleValueChange(syncedValue + ' '); // Hiding dropdown by adding space
          return;
        }
      }
 
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
      }
      if (e.key === 'Escape' && activeCommand) {
        const parsed = parseSlashCommand(syncedValue.trim());
        handleValueChange(parsed.query || '');
      }
    },
    [handleSend, activeCommand, syncedValue, showDropdown, filteredCommands, dropdownIndex, selectCommand, handleValueChange],
  );
 
  const dismissCommand = useCallback(() => {
    const parsed = parseSlashCommand(syncedValue.trim());
    handleValueChange(parsed.query || '');
    textareaRef.current?.focus();
  }, [syncedValue, handleValueChange]);

  return (
    <div className="px-4 sm:px-6 pb-5 pt-2 flex justify-center w-full sticky bottom-0 z-10 bg-gradient-to-t from-surface-50 via-surface-50/95 to-transparent">
      <div className="max-w-3xl w-full relative">

        {/* Optimize Prompt button — above the input panel, left-aligned, visible only when there's text */}
        {!isStreaming && syncedValue.trim().length > 0 && (() => {
          const parsed = parseSlashCommand(syncedValue.trim());
          const queryToOptimize = parsed.command ? parsed.query : syncedValue.trim();
          const slashPrefix = parsed.command ? `/${parsed.command} ` : '';
          return (
            <div className="flex justify-start mb-2 px-1">
              <button
                onClick={() => setShowOptimizer(true)}
                disabled={disabled || queryToOptimize.length <= 10}
                className="inline-flex items-center gap-2 h-8 px-4 rounded-lg border transition-all duration-150
                  bg-surface-overlay border-border text-text-secondary
                  hover:bg-accent-muted hover:border-accent-border hover:text-accent
                  disabled:opacity-40 disabled:cursor-not-allowed"
                title={queryToOptimize.length <= 10 ? 'Type more than 10 characters to optimize' : 'Optimize your prompt with AI'}
                aria-label="Optimize Prompt"
              >
                <Sparkles size={13} />
                <span className="text-[13px] font-medium">Optimize Prompt</span>
              </button>

              {showOptimizer && (
                <PromptOptimizerDialog
                  originalPrompt={queryToOptimize}
                  materialIds={materialIds}
                  onSelect={(text) => handleValueChange(slashPrefix + text)}
                  onClose={() => setShowOptimizer(false)}
                />
              )}
            </div>
          );
        })()}

        {}
        {showDropdown && filteredCommands.length > 0 && (
          <div
            className="absolute bottom-full mb-2 left-0 right-0 rounded-xl border overflow-hidden shadow-2xl"
            style={{ background: 'var(--surface-raised, #1e1e2e)', borderColor: 'rgba(255,255,255,0.1)' }}
          >
            <div className="px-3 py-1.5 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
              <span className="text-[11px] font-semibold text-text-muted tracking-widest uppercase">Commands</span>
            </div>
            {filteredCommands.map(([cmd, meta], idx) => {
              const Icon = meta.icon;
              const isActive = idx === dropdownIndex;
              return (
                <button
                  key={cmd}
                  onMouseDown={(e) => { e.preventDefault(); selectCommand(cmd); }}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                    isActive ? 'bg-white/5' : 'hover:bg-white/[0.03]'
                  }`}
                >
                  <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${meta.bg}`}>
                    <Icon size={15} className={meta.color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-text-primary leading-snug">{meta.title}</div>
                    <div className="text-xs text-text-muted mt-0.5">{meta.desc}</div>
                  </div>
                  <kbd className="shrink-0 text-[11px] text-text-muted/50 font-mono px-1.5 py-0.5 rounded bg-black/40">
                    /{cmd}
                  </kbd>
                </button>
              );
            })}
          </div>
        )}

        {}
        {activeCommand && !showDropdown && (
          <div className="flex items-center gap-2 mb-2 px-1">
            <span
              className={`inline-flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-full border ${
                BADGE_COLORS[activeCommand.intent] || 'bg-surface-overlay text-text-muted shadow-sm'
              }`}
            >
              {activeCommand.label}
            </span>
            <button
              onClick={dismissCommand}
              className="text-text-muted hover:text-text-secondary transition-colors"
              aria-label="Remove slash command"
            >
              <X size={12} />
            </button>
          </div>
        )}

        {}
        <div
          className="flex items-end gap-2 rounded-2xl border px-4 py-2.5 transition-all duration-150"
          style={{
            background: 'var(--surface-raised, #1e1e2e)',
            borderColor: activeCommand ? 'rgba(255,255,255,0.15)' : 'rgba(255,255,255,0.08)',
          }}
        >
          <textarea
            ref={textareaRef}
            value={syncedValue}
            onChange={(e) => handleValueChange(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={
              activeCommand
                ? `${activeCommand.label} — type your query…`
                : 'Message or type / for commands…'
            }
            disabled={disabled}
            rows={1}
            className="flex-1 bg-transparent text-sm text-text-primary placeholder:text-text-muted resize-none outline-none max-h-40 py-1"
            style={{ lineHeight: '1.6' }}
          />

          {isStreaming ? (
            <button
              onClick={onStop}
              className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-error/15 text-error hover:bg-error/25 transition-colors"
              title="Stop generating"
              aria-label="Stop generating"
            >
              <Square size={14} fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!syncedValue.trim() || disabled}
              className="shrink-0 w-8 h-8 rounded-lg flex items-center justify-center bg-accent text-white disabled:opacity-30 disabled:cursor-not-allowed hover:bg-accent/80 transition-colors"
              title="Send message"
              aria-label="Send message"
            >
              <Send size={14} />
            </button>
          )}
        </div>

      </div>
    </div>
  );
});

export default ChatInput;

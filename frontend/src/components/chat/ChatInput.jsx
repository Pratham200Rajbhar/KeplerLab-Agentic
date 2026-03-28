'use client';

import { useState, useRef, useEffect, useCallback, memo, useMemo } from 'react';
import { Send, Square, X, Globe, Code2, Search, Bot, Sparkles, CornerDownLeft } from 'lucide-react';
import { parseSlashCommand } from '@/lib/utils/parseSlashCommand';
import { SLASH_COMMANDS } from '@/lib/config/slashCommands';
import useAppStore from '@/stores/useAppStore';
import PromptOptimizerDialog from './PromptOptimizerDialog';

const ICON_BY_KEY = {
  globe: Globe,
  search: Search,
  code: Code2,
  bot: Bot,
};

const COLOR_TOKEN_CLASSES = {
  sky: { color: 'text-sky-300', bg: 'bg-sky-500/12', border: 'border-sky-400/25' },
  emerald: { color: 'text-emerald-300', bg: 'bg-emerald-500/12', border: 'border-emerald-400/25' },
  indigo: { color: 'text-indigo-300', bg: 'bg-indigo-500/12', border: 'border-indigo-400/25' },
  fuchsia: { color: 'text-fuchsia-300', bg: 'bg-fuchsia-500/12', border: 'border-fuchsia-400/25' },
};

const COMMAND_CATALOG = SLASH_COMMANDS.map((cmd) => ({
  ...cmd,
  icon: ICON_BY_KEY[cmd.iconKey] || Bot,
  ...(COLOR_TOKEN_CLASSES[cmd.colorToken] || COLOR_TOKEN_CLASSES.sky),
}));

const COMMAND_LOOKUP = COMMAND_CATALOG.reduce((acc, cmd) => {
  acc[cmd.command] = cmd;
  return acc;
}, {});

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
    el.style.height = `${Math.min(el.scrollHeight, 144)}px`;
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
          textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 144)}px`;
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
    if (!partial) return COMMAND_CATALOG;
    return COMMAND_CATALOG.filter((cmd) =>
      cmd.command.includes(partial) ||
      cmd.title.toLowerCase().includes(partial) ||
      cmd.desc.toLowerCase().includes(partial) ||
      cmd.tags.some((tag) => tag.includes(partial))
    );
  }, [syncedValue]);

  const safeDropdownIndex =
    filteredCommands.length === 0 ? 0 : Math.min(dropdownIndex, filteredCommands.length - 1);

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
          const selected = filteredCommands[safeDropdownIndex] ?? filteredCommands[0];
          if (selected) selectCommand(selected.command);
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
    [handleSend, activeCommand, syncedValue, showDropdown, filteredCommands, safeDropdownIndex, selectCommand, handleValueChange],
  );
 
  const dismissCommand = useCallback(() => {
    const parsed = parseSlashCommand(syncedValue.trim());
    handleValueChange(parsed.query || '');
    textareaRef.current?.focus();
  }, [syncedValue, handleValueChange]);

  return (
    <div className="workspace-chat-input-dock px-4 sm:px-6 pb-3 pt-1 flex justify-center w-full shrink-0 relative z-10">
      <div className="max-w-3xl w-full relative">

        {/* Optimize Prompt button — above the input panel, left-aligned, visible only when there's text */}
        {!isStreaming && syncedValue.trim().length > 0 && (() => {
          const parsed = parseSlashCommand(syncedValue.trim());
          const queryToOptimize = parsed.command ? parsed.query : syncedValue.trim();
          const slashPrefix = parsed.command ? `/${parsed.command} ` : '';
          return (
            <div className="flex justify-start mb-1.5 px-0.5">
              <button
                onClick={() => setShowOptimizer(true)}
                disabled={disabled || queryToOptimize.length <= 10}
                className="workspace-optimize-btn inline-flex items-center gap-1.5 h-7 px-3 rounded-md border transition-all duration-150
                  disabled:opacity-40 disabled:cursor-not-allowed"
                title={queryToOptimize.length <= 10 ? 'Type more than 10 characters to optimize' : 'Optimize your prompt with AI'}
                aria-label="Optimize Prompt"
              >
                <Sparkles size={12} />
                <span className="text-[12px] font-medium">Optimize Prompt</span>
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
          <div className="slash-cmd-palette absolute bottom-full mb-2 left-0 right-0 rounded-2xl overflow-hidden shadow-2xl">
            <div className="slash-cmd-header px-3 py-2 border-b flex items-center justify-between">
              <span className="text-[11px] font-semibold tracking-widest uppercase">Command Palette</span>
              <span className="text-[10px] text-text-muted">Use ↑ ↓ and Enter</span>
            </div>
            <div className="slash-cmd-list p-2">
            {filteredCommands.map((item, idx) => {
              const Icon = item.icon;
              const isActive = idx === safeDropdownIndex;
              return (
                <button
                  key={item.command}
                  onMouseDown={(e) => { e.preventDefault(); selectCommand(item.command); }}
                  className={`slash-cmd-item w-full flex items-center gap-3 px-3 py-2.5 text-left rounded-xl transition-colors ${
                    isActive ? 'slash-cmd-item-active' : ''
                  }`}
                >
                  <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center border ${item.bg} ${item.border}`}>
                    <Icon size={15} className={item.color} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-text-primary leading-snug">{item.title}</div>
                    <div className="text-xs text-text-muted mt-0.5">{item.desc}</div>
                  </div>
                  <div className="shrink-0 flex items-center gap-1.5">
                    <kbd className="slash-cmd-kbd text-[11px] font-mono px-1.5 py-0.5 rounded">
                      /{item.command}
                    </kbd>
                    <CornerDownLeft className="w-3.5 h-3.5 text-text-muted/60" />
                  </div>
                </button>
              );
            })}
            </div>
          </div>
        )}

        {}
        {activeCommand && !showDropdown && (
          <div className="flex items-center gap-2 mb-2 px-1">
            {(() => {
              const meta = COMMAND_LOOKUP[activeCommand.command];
              const Icon = meta?.icon;
              return Icon ? (
                <span
                  className={`inline-flex items-center gap-2 text-xs font-semibold px-3 py-1.5 rounded-full border transition-all ${
                    BADGE_COLORS[activeCommand.intent] || `${meta.bg} ${meta.border} text-text-primary`
                  }`}
                >
                  <Icon size={14} className={meta?.color} />
                  <span>{activeCommand.label}</span>
                </span>
              ) : null;
            })()}
            <button
              onClick={dismissCommand}
              className="text-text-muted hover:text-text-secondary transition-colors ml-auto"
              aria-label="Remove slash command"
            >
              <X size={14} />
            </button>
          </div>
        )}

        {}
        <div
          className="workspace-chat-input-shell flex items-end gap-2 rounded-xl border px-3 py-2 transition-all duration-150"
          style={{
            borderColor: activeCommand ? 'var(--accent-border)' : 'color-mix(in srgb, var(--border-strong) 78%, transparent)',
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
            className="flex-1 bg-transparent text-[14px] text-text-primary placeholder:text-text-muted/90 resize-none outline-none max-h-36 py-0.5"
            style={{ lineHeight: '1.6' }}
          />

          {isStreaming ? (
            <button
              onClick={onStop}
              className="workspace-stop-btn shrink-0 w-8 h-8 rounded-md flex items-center justify-center transition-colors"
              title="Stop generating"
              aria-label="Stop generating"
            >
              <Square size={13} fill="currentColor" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!syncedValue.trim() || disabled}
              className="workspace-send-btn shrink-0 w-8 h-8 rounded-md flex items-center justify-center text-white disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title="Send message"
              aria-label="Send message"
            >
              <Send size={13} />
            </button>
          )}
        </div>

      </div>
    </div>
  );
});

export default ChatInput;

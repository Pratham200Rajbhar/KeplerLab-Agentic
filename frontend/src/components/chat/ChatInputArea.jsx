'use client';

import { useState, useRef, useEffect, useCallback, memo } from 'react';
import {
  Send,
  Square,
  X,
  Sparkles,
  FlaskConical,
} from 'lucide-react';

import { TIMERS } from '@/lib/utils/constants';
import SlashCommandPills from './SlashCommandPills';
import SlashCommandDropdown from './SlashCommandDropdown';
import CommandBadge from './CommandBadge';
import SuggestionDropdown from './SuggestionDropdown';
import { parseSlashCommand } from './slashCommands';
import { getSuggestions } from '@/lib/api/chat';

/**
 * ChatInputArea — owns text input, slash command dropdown, active command pill,
 * send/stop/suggest/research buttons, quick action buttons.
 *
 * Props:
 *   onSend(message, intentOverride, command) — send callback
 *   onResearch(query) — deep research callback
 *   disabled — whether input is disabled
 *   isStreaming — whether AI is currently streaming
 *   onStop — stop generation callback
 *   hasSource — whether any source is selected
 *   isSourceProcessing — sources are indexing
 *   notebookId — current notebook id
 *   mindMapBanner / onDismissBanner — mind map context banner
 */
function ChatInputArea({
  onSend,
  onResearch,
  disabled,
  isStreaming,
  onStop,
  hasSource,
  isSourceProcessing,
  notebookId,
  mindMapBanner,
  onDismissBanner,
}) {
  const textareaRef = useRef(null);

  const [inputValue, setInputValue] = useState('');
  const [activeCommand, setActiveCommand] = useState(null);
  const [showSlashDropdown, setShowSlashDropdown] = useState(false);
  const [slashFilter, setSlashFilter] = useState('');
  const [isInputFocused, setIsInputFocused] = useState(false);

  // Suggestions
  const [isFetchingSuggestions, setIsFetchingSuggestions] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const [suggestions, setSuggestions] = useState([]);

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

  /* ── Handlers ── */
  const handleSend = useCallback(() => {
    if (!inputValue.trim()) return;

    let userMessage = inputValue.trim();
    let intentOverride = null;
    let commandForMessage = activeCommand;

    // Parse inline slash command if no active command is set
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

    onSend(userMessage, intentOverride, commandForMessage);
  }, [inputValue, activeCommand, onSend]);

  const handleKeyDown = useCallback((e) => {
    if (showSlashDropdown) return;
    if (e.key === 'Escape' && activeCommand) {
      e.preventDefault();
      setActiveCommand(null);
      return;
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }, [showSlashDropdown, activeCommand, handleSend]);

  const handleInputChange = useCallback((e) => {
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
  }, [activeCommand]);

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

  const handleResearch = useCallback(() => {
    const query = inputValue.trim();
    if (!query) return;
    setInputValue('');
    onResearch?.(query);
  }, [inputValue, onResearch]);

  const handleGetSuggestions = useCallback(async () => {
    if (!inputValue.trim() || !hasSource || !notebookId) return;
    setIsFetchingSuggestions(true);
    setShowSuggestions(true);
    try {
      const data = await getSuggestions(inputValue, notebookId);
      setSuggestions(data?.suggestions || []);
    } catch (err) {
      console.error(err);
      setSuggestions([]);
    } finally {
      setIsFetchingSuggestions(false);
    }
  }, [inputValue, hasSource, notebookId]);

  const handleSuggestionSelect = useCallback((suggestion) => {
    setShowSuggestions(false);
    setSuggestions([]);
    setInputValue('');
    // Parse and send the suggestion directly
    onSend(suggestion, null, null);
  }, [onSend]);

  const isLoading = isStreaming;

  return (
    <div className="p-4 sm:p-6 flex justify-center w-full z-10 sticky bottom-0 bg-linear-to-t from-surface-100 via-surface-100 to-transparent pt-12">
      <div className="max-w-4xl w-full relative">
        {/* Suggestion Dropdown */}
        {hasSource && notebookId && showSuggestions && (
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
              onClick={onDismissBanner}
              className="text-text-secondary hover:text-text-primary transition-colors p-0.5"
              aria-label="Dismiss mind map context"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          </div>
        )}

        {/* Slash Command Suggestion Pills */}
        <SlashCommandPills
          visible={isInputFocused && !activeCommand && !inputValue && hasSource && !isLoading}
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
                  ? activeCommand.placeholder
                  : hasSource
                    ? isLoading
                      ? 'AI is thinking…'
                      : 'Ask about your selected materials...'
                    : isSourceProcessing
                      ? 'Processing source, please wait…'
                      : 'Select a source to start…'
              }
              disabled={disabled || !hasSource || isLoading}
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
                onClick={onStop}
                className="btn-icon bg-danger-subtle text-danger hover:bg-danger-subtle rounded-[10px] w-9 h-9 flex items-center justify-center transition-all ml-1"
                title="Stop generation"
                aria-label="Stop generation"
              >
                <Square className="w-4 h-4" fill="currentColor" />
              </button>
            ) : (
              <button
                onClick={handleSend}
                disabled={!inputValue.trim() || !hasSource || isLoading || disabled}
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
              className={`text-xs tabular-nums ${
                inputValue.length > TIMERS.INPUT_LENGTH_WARNING
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
  );
}

export default memo(ChatInputArea);

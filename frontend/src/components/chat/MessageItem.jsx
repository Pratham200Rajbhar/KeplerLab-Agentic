'use client';

import { memo, useState, useCallback } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import { Bot, RotateCcw, Copy, Check } from 'lucide-react';

const INTENT_BADGES = {
  AGENT:          { label: 'Agent Mode',    color: 'bg-purple-500/15 text-purple-300 border border-purple-500/20' },
  WEB_RESEARCH:   { label: 'Deep Research', color: 'bg-blue-500/15 text-blue-300 border border-blue-500/20' },
  CODE_EXECUTION: { label: 'Code Mode',     color: 'bg-green-500/15 text-green-300 border border-green-500/20' },
  WEB_SEARCH:     { label: 'Web Search',    color: 'bg-orange-500/15 text-orange-300 border border-orange-500/20' },
};

/**
 * MessageItem — a single chat turn.
 *
 * User messages — right-aligned bubble.
 * Assistant messages — left-aligned with avatar, streaming cursor, hover actions.
 */
const MessageItem = memo(function MessageItem({ message, isStreaming, onRetry }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  /* ── User message ─────────────────────────────────────── */
  if (isUser) {
    const badge = message.intentOverride ? INTENT_BADGES[message.intentOverride] : null;
    return (
      <div className="flex justify-end px-4 sm:px-6 py-2 group">
        <div className="max-w-[78%] flex flex-col items-end gap-1.5">
          {badge && (
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full ${badge.color}`}>
              {badge.label}
            </span>
          )}
          <div
            className="px-4 py-2.5 rounded-2xl rounded-tr-md text-sm text-text-primary whitespace-pre-wrap break-words leading-relaxed"
            style={{ background: 'var(--surface-overlay, rgba(255,255,255,0.07))' }}
          >
            {message.content}
          </div>
        </div>
      </div>
    );
  }

  /* ── Assistant message ────────────────────────────────── */
  const hasSteps = message.agentSteps?.length > 0;
  const hasContent = !!message.content;

  return (
    <div className="group px-4 sm:px-6 py-5">
      <div className="max-w-3xl mx-auto flex gap-3.5">
        {/* Avatar */}
        <div className="shrink-0 mt-0.5">
          <div className="w-7 h-7 rounded-full flex items-center justify-center bg-accent/15 text-accent">
            <Bot size={14} />
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {/* Agent step progress (shown while agent is working, before content arrives) */}
          {hasSteps && !hasContent && (
            <div className="mb-3 space-y-1.5">
              {message.agentSteps.map((step, i) => {
                const isLatest = i === message.agentSteps.length - 1;
                return (
                  <div
                    key={i}
                    className={`flex items-center gap-2 text-xs transition-opacity ${
                      isLatest ? 'text-text-muted opacity-100' : 'text-text-muted/40 opacity-60'
                    }`}
                  >
                    <span
                      className={`shrink-0 w-1.5 h-1.5 rounded-full ${
                        isLatest ? 'bg-accent animate-pulse' : 'bg-text-muted/20'
                      }`}
                    />
                    {step}
                  </div>
                );
              })}
            </div>
          )}

          {/* Message body */}
          {hasContent ? (
            <div className="text-sm text-text-primary leading-relaxed prose-chat">
              <MarkdownRenderer content={message.content} />
              {isStreaming && (
                <span
                  className="inline-block w-[2px] h-[1em] bg-text-muted/50 ml-0.5 align-text-bottom animate-pulse"
                  aria-hidden="true"
                />
              )}
            </div>
          ) : !hasSteps && !isStreaming ? (
            <div className="text-sm text-text-muted italic">No response generated.</div>
          ) : null}

          {/* Hover actions */}
          {!isStreaming && hasContent && (
            <div className="flex items-center gap-1 mt-3 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
              <button
                onClick={handleCopy}
                className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary transition-colors px-2 py-1 rounded-lg hover:bg-surface-overlay"
                title="Copy response"
              >
                {copied ? <Check size={12} /> : <Copy size={12} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
              {onRetry && (
                <button
                  onClick={() => onRetry(message)}
                  className="flex items-center gap-1.5 text-xs text-text-muted hover:text-text-primary transition-colors px-2 py-1 rounded-lg hover:bg-surface-overlay"
                  title="Regenerate response"
                >
                  <RotateCcw size={12} />
                  Regenerate
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export default MessageItem;

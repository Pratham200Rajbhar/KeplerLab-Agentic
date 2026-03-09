'use client';

import { memo, useState, useCallback } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import AgentExecutionPanel from './AgentExecutionPanel';
import CodeWorkspace from './CodeWorkspace';
import ArtifactViewer from './ArtifactViewer';
import WebSearchProgressPanel from './WebSearchProgressPanel';
import ResearchReport from './ResearchReport';
import { Bot, RotateCcw, Copy, Check } from 'lucide-react';

const INTENT_BADGES = {
  AGENT:          { label: 'Agent Mode',    color: 'bg-purple-500/10 text-purple-300' },
  WEB_RESEARCH:   { label: 'Deep Research', color: 'bg-blue-500/10 text-blue-300' },
  CODE_EXECUTION: { label: 'Code Mode',     color: 'bg-green-500/10 text-green-300' },
  WEB_SEARCH:     { label: 'Web Search',    color: 'bg-orange-500/10 text-orange-300' },
};

/**
 * MessageItem — a single chat turn.
 *
 * User messages — right-aligned bubble.
 * Assistant messages — left-aligned with avatar.
 *   · /agent intent → AgentExecutionPanel (steps + artifacts) above markdown
 *   · /code intent  → CodeWorkspace (editor + console + AI edit) below markdown
 *   · standalone artifacts → ArtifactViewer
 */
const MessageItem = memo(function MessageItem({ message, isStreaming, onRetry, notebookId, sessionId }) {
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
  // Agent mode: driven by intentOverride propagated from the done event,
  // or by the presence of agentSteps / agentCodeBlocks emitted during execution.
  const isAgentMode =
    message.intentOverride === 'AGENT' ||
    message.agentSteps?.length > 0 ||
    message.agentCodeBlocks?.length > 0;
  // Research mode: active when research SSE events have arrived or intent is set.
  const isResearchMode =
    message.intentOverride === 'WEB_RESEARCH' ||
    !!(message.researchState && message.researchState.status !== 'idle');
  // Code mode: only when a /code code_block was generated AND NOT in agent/research mode.
  const isCodeMode  = !isAgentMode && !isResearchMode && message.codeBlocks?.length > 0;
  const hasContent  = !!message.content;
  const hasArtifactsOnly = message.artifacts?.length > 0 && !isAgentMode && !isCodeMode && !isResearchMode;

  // When agent is working but no content yet — if agentSteps exist, panel handles display
  const showTypingFallback = !hasContent && !message.agentSteps?.length && !isCodeMode && !isResearchMode && !isStreaming;

  return (
    <div className="group px-4 sm:px-6 py-4">
      <div className="max-w-3xl mx-auto flex gap-3.5">
        {/* Avatar */}
        <div className="shrink-0 mt-0.5">
          <div className="w-7 h-7 rounded-full flex items-center justify-center bg-accent/15 text-accent">
            <Bot size={14} />
          </div>
        </div>

        {/* Content column */}
        <div className="flex-1 min-w-0 overflow-hidden">
          {/* Agent execution panel (steps, summary, artifacts) */}
          {isAgentMode && (
            <AgentExecutionPanel message={message} isStreaming={isStreaming} />
          )}

          {/* Deep research — minimal loading indicator + collapsible panel + source bubbles */}
          {isResearchMode && (
            <ResearchReport
              sources={message.researchState?.sources || []}
              streamingContent={message.content}
              citations={message.citations || []}
              isDone={!isStreaming}
              isStreaming={isStreaming}
            />
          )}

          {/* Web search progress panel (live during streaming; collapses to sources when done) */}
          {message.webSearchState && (
            <WebSearchProgressPanel
              webSearchState={message.webSearchState}
              sources={message.webSources || []}
              isStreaming={isStreaming}
            />
          )}

          {/* Markdown response body — hidden in research mode (ResearchReport renders content) */}
          {hasContent && !isResearchMode && (
            <div className="text-sm text-text-primary leading-relaxed prose-chat">
              <MarkdownRenderer content={message.content} />
              {isStreaming && !isCodeMode && (
                <span
                  className="inline-block w-[2px] h-[1em] bg-text-muted/50 ml-0.5 align-text-bottom animate-pulse"
                  aria-hidden="true"
                />
              )}
            </div>
          )}

          {/* Code workspace (/code mode) */}
          {isCodeMode && (
            <CodeWorkspace
              codeBlocks={message.codeBlocks}
              notebookId={notebookId}
              sessionId={sessionId}
              isStreaming={isStreaming}
            />
          )}

          {/* Standalone artifacts (e.g., from web-search or research) */}
          {hasArtifactsOnly && (
            <div className="mt-2">
              <ArtifactViewer artifacts={message.artifacts} />
            </div>
          )}

          {/* Fallback empty state */}
          {showTypingFallback && (
            <div className="text-sm text-text-muted italic">No response generated.</div>
          )}

          {/* Hover actions (only for completed assistant messages with text) */}
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

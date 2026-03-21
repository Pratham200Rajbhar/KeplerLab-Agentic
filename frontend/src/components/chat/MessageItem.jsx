'use client';

import { memo, useState, useCallback, useMemo } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import CodeWorkspace from './CodeWorkspace';
import ArtifactViewer from './ArtifactViewer';
import WebSearchProgressPanel from './WebSearchProgressPanel';
import ResearchReport from './ResearchReport';
import AgentProgressPanel from './AgentProgressPanel';
import CollapsibleActionBlock from './CollapsibleActionBlock';
import AnnotatedText from './AnnotatedText';
import { Copy, Check, RotateCcw, Sparkles } from 'lucide-react';

const INTENT_BADGES = {
  WEB_RESEARCH:   { label: 'Deep Research', color: 'bg-blue-500/10 text-blue-300',   border: 'border-blue-500/20' },
  CODE_EXECUTION: { label: 'Code Mode',     color: 'bg-green-500/10 text-green-300', border: 'border-green-500/20' },
  WEB_SEARCH:     { label: 'Web Search',    color: 'bg-orange-500/10 text-orange-300', border: 'border-orange-500/20' },
  AGENT:          { label: 'Agent',         color: 'bg-purple-500/10 text-purple-300', border: 'border-purple-500/20' },
};


const MessageItem = memo(function MessageItem({ message, isStreaming, onRetry, notebookId, sessionId }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  
  if (isUser) {
    const badge = message.intentOverride ? INTENT_BADGES[message.intentOverride] : null;
    return (
      <div className="flex justify-end px-4 sm:px-6 py-2 group">
        <div className="max-w-[78%] flex flex-col items-end gap-1.5">
          {badge && (
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${badge.color} ${badge.border}`}>
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

  
  const isResearchMode =
    message.intentOverride === 'WEB_RESEARCH' ||
    !!(message.researchState && message.researchState.status !== 'idle');
  
  const isAgentMode =
    message.intentOverride === 'AGENT' ||
    !!(message.agentState && message.agentState.status);

  const isCodeMode  = !isResearchMode && !isAgentMode && message.codeBlocks?.length > 0;
  const hasContent  = !!message.content;
  const hasArtifactsOnly = message.artifacts?.length > 0 && !isCodeMode && !isResearchMode && !isAgentMode;
  const hasAgentArtifacts = isAgentMode && message.artifacts?.length > 0;

  
  const showTypingFallback = !hasContent && !isCodeMode && !isResearchMode && !isAgentMode && !isStreaming;

  return (
    <div className="group px-4 sm:px-6 py-4">
      <div className="max-w-3xl mx-auto flex gap-3.5">
        {}
        <div className="shrink-0 mt-0.5">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-gradient-to-br from-accent/20 to-accent/5 text-accent border border-accent/10 shadow-sm shadow-accent/5">
            <Sparkles size={14} className="animate-pulse-glow" style={{ animationDuration: '3s' }} />
          </div>
        </div>

        {}
        <div className="flex-1 min-w-0 message-selection-container overflow-hidden">
          {}
          {isResearchMode && (
            <ResearchReport
              sources={message.researchState?.sources || []}
              streamingContent={message.content}
              citations={message.citations || []}
              isDone={!isStreaming}
              isStreaming={isStreaming}
              researchState={message.researchState || null}
              messageBlocks={message.blocks || []}
            />
          )}

          {}
          {message.webSearchState && (
            <WebSearchProgressPanel
              webSearchState={message.webSearchState}
              sources={message.webSources || []}
              isStreaming={isStreaming}
            />
          )}

          {/* Agent progress panel */}
          {isAgentMode && message.agentState && (
            <AgentProgressPanel
              agentState={message.agentState}
              isStreaming={isStreaming}
            />
          )}

          {/* Agent artifacts */}
          {hasAgentArtifacts && (
            <div className="mt-2">
              <ArtifactViewer artifacts={message.artifacts} />
            </div>
          )}

          {hasContent && !isResearchMode && (
            <div className="text-sm text-text-primary leading-relaxed prose-chat">
              {message.blocks?.length > 0 && !isStreaming ? (
                (() => {
                  const parents = [];
                  const annotationsByParent = {};
                  const orphanedAnnotations = [];
                  const seenAnnotations = new Set();

                  message.blocks.forEach(block => {
                    const match = block.text.match(/^\[(translate|ask|simplify|explain):([^:]+):?([^\]]*)\]\s*(.*)/s);
                    if (match) {
                      const [, action, parentId, selection, body] = match;
                      const uniqueKey = `${action}:${parentId}:${selection}:${body.trim()}`;
                      
                      if (!seenAnnotations.has(uniqueKey)) {
                        seenAnnotations.add(uniqueKey);
                        if (!annotationsByParent[parentId]) annotationsByParent[parentId] = [];
                        annotationsByParent[parentId].push(block);
                      }
                    } else {
                      parents.push(block);
                    }
                  });

                  // Check if annotations belong to parents in this message
                  // If not, they are orphans
                  const parentIds = new Set(parents.map(p => p.id));
                  Object.keys(annotationsByParent).forEach(pid => {
                    if (!parentIds.has(pid)) {
                      orphanedAnnotations.push(...annotationsByParent[pid]);
                      delete annotationsByParent[pid];
                    }
                  });

                  return (
                    <>
                      {parents.map((block) => (
                        <div key={block.id} data-block-id={block.id} className="mb-6 last:mb-0">
                          <AnnotatedText 
                            content={block.text} 
                            annotations={annotationsByParent[block.id] || []} 
                          />
                        </div>
                      ))}
                      {orphanedAnnotations.map((block) => (
                        <div key={block.id} data-block-id={block.id} className="mb-4 last:mb-0">
                          <CollapsibleActionBlock content={block.text} />
                        </div>
                      ))}
                    </>
                  );
                })()
              ) : (
                <MarkdownRenderer content={message.content} />
              )}
              {isStreaming && !isCodeMode && (
                <span
                  className="inline-block w-[2px] h-[1em] bg-text-muted/50 ml-0.5 align-text-bottom animate-pulse"
                  aria-hidden="true"
                />
              )}
            </div>
          )}

          {}
          {isCodeMode && (
            <CodeWorkspace
              codeBlocks={message.codeBlocks}
              notebookId={notebookId}
              sessionId={sessionId}
              isStreaming={isStreaming}
            />
          )}

          {}
          {hasArtifactsOnly && (
            <div className="mt-2">
              <ArtifactViewer artifacts={message.artifacts} />
            </div>
          )}

          {}
          {showTypingFallback && (
            <div className="text-sm text-text-muted italic">No response generated.</div>
          )}

          {}
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

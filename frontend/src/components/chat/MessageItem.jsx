'use client';

import { memo, useState, useCallback, useMemo, useEffect } from 'react';
import MarkdownRenderer from './MarkdownRenderer';
import CodeWorkspace from './CodeWorkspace';
import ArtifactViewer from './ArtifactViewer';
import WebSearchProgressPanel from './WebSearchProgressPanel';
import ResearchReport from './ResearchReport';
import AgentProgressPanel from './AgentProgressPanel';
import CollapsibleActionBlock from './CollapsibleActionBlock';
import AnnotatedText from './AnnotatedText';
import { Copy, Check, RotateCcw, Sparkles, Pencil, Trash2, X, SendHorizonal } from 'lucide-react';

const INTENT_BADGES = {
  WEB_RESEARCH:   { label: 'Deep Research', color: 'bg-blue-500/10 text-blue-300',   border: 'border-blue-500/20' },
  CODE_EXECUTION: { label: 'Code Mode',     color: 'bg-green-500/10 text-green-300', border: 'border-green-500/20' },
  WEB_SEARCH:     { label: 'Web Search',    color: 'bg-orange-500/10 text-orange-300', border: 'border-orange-500/20' },
  AGENT:          { label: 'Agent',         color: 'bg-purple-500/10 text-purple-300', border: 'border-purple-500/20' },
};


const MessageItem = memo(function MessageItem({ message, isStreaming, onRetry, onEdit, onDelete, notebookId, sessionId }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [editText, setEditText] = useState(message.content || '');
  const [fullscreenImage, setFullscreenImage] = useState(null);
  const [loadedImages, setLoadedImages] = useState(new Set());

  useEffect(() => {
    setLoadedImages(new Set());
  }, [message.images?.length]);

  useEffect(() => {
    if (!fullscreenImage) return;

    const handleEscape = (event) => {
      if (event.key === 'Escape') setFullscreenImage(null);
    };

    window.addEventListener('keydown', handleEscape);
    return () => window.removeEventListener('keydown', handleEscape);
  }, [fullscreenImage]);

  const handleImageLoad = useCallback((index) => {
    setLoadedImages(prev => {
      const next = new Set(prev);
      next.add(index);
      return next;
    });
  }, []);

  const handleCopy = useCallback(() => {
    if (!message.content) return;
    navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  const handleEditSave = useCallback(() => {
    if (editText.trim() && editText.trim() !== message.content) {
      onEdit?.(message.id, editText.trim());
    }
    setIsEditing(false);
  }, [editText, message.content, message.id, onEdit]);

  const handleEditCancel = useCallback(() => {
    setEditText(message.content || '');
    setIsEditing(false);
  }, [message.content]);

  
  if (isUser) {
    const badge = message.intentOverride ? INTENT_BADGES[message.intentOverride] : null;
    return (
      <div className="flex justify-end px-4 sm:px-6 py-2 group">
        <div className={`max-w-[85%] sm:max-w-[78%] flex flex-col items-end gap-1.5 ${isEditing ? 'w-full' : ''}`}>
          {badge && (
            <span className={`text-[11px] font-medium px-2 py-0.5 rounded-full border ${badge.color} ${badge.border}`}>
              {badge.label}
            </span>
          )}
          
          {isEditing ? (
            <div className="w-full space-y-2">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEditSave(); }
                  if (e.key === 'Escape') handleEditCancel();
                }}
                rows={Math.min(10, editText.split('\n').length + 1)}
                autoFocus
                className="w-full px-4 py-3 text-sm rounded-2xl rounded-tr-md bg-surface-overlay text-text-primary border border-accent/40 focus:outline-none focus:ring-1 focus:ring-accent resize-none leading-relaxed transition-all"
                placeholder="Edit your message..."
              />
              <div className="flex items-center justify-end gap-2">
                <button onClick={handleEditCancel} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-overlay transition-colors">
                  <X className="w-3.5 h-3.5" /> Cancel
                </button>
                <button onClick={handleEditSave} disabled={!editText.trim()} className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-40">
                  <SendHorizonal className="w-3.5 h-3.5" /> Save
                </button>
              </div>
            </div>
          ) : isDeleting ? (
            <div className="px-4 py-3 rounded-2xl rounded-tr-md bg-danger/10 border border-danger/20 flex flex-col gap-2 items-center animate-in fade-in zoom-in duration-200">
              <span className="text-xs font-medium text-danger text-center">Delete this message and its response?</span>
              <div className="flex items-center gap-2">
                <button 
                  onClick={() => setIsDeleting(false)}
                  className="px-3 py-1 text-[11px] font-semibold rounded-md bg-surface-overlay text-text-primary hover:bg-surface-raised transition-colors"
                >
                  No, keep it
                </button>
                <button 
                  onClick={() => { onDelete?.(message.id); setIsDeleting(false); }}
                  className="px-3 py-1 text-[11px] font-semibold rounded-md bg-danger text-white hover:bg-danger/90 transition-colors shadow-sm shadow-danger/20"
                >
                  Yes, delete
                </button>
              </div>
            </div>
          ) : (
            <>
              <div
                className="px-4 py-2.5 rounded-2xl rounded-tr-md text-sm text-text-primary whitespace-pre-wrap break-words leading-relaxed transition-all"
                style={{ background: 'var(--surface-overlay, rgba(255,255,255,0.07))' }}
              >
                {message.content}
              </div>
              <div className="flex items-center gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                {onEdit && (
                  <button 
                    onClick={() => { setIsEditing(true); setIsDeleting(false); setEditText(message.content || ''); }} 
                    title="Edit message" 
                    className="flex items-center justify-center w-6 h-6 rounded-lg text-text-muted hover:text-text-secondary hover:bg-surface-overlay transition-colors"
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                )}
                {onDelete && (
                  <button 
                    onClick={() => { setIsDeleting(true); setIsEditing(false); }} 
                    title="Delete message" 
                    className="flex items-center justify-center w-6 h-6 rounded-lg text-text-muted hover:text-danger hover:bg-danger/10 transition-colors"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            </>
          )}
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
  const hasGeneratedImages = message.images?.length > 0;
  const imageCount = message.images?.length || 0;
  const isImageGenerationMessage = message.intentOverride === 'IMAGE_GENERATION' || hasGeneratedImages;

  
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
              artifacts={message.artifacts || []}
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
              codeBlocks={message.codeBlocks}
              artifacts={message.artifacts}
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

          {isStreaming && isImageGenerationMessage && !hasGeneratedImages && (
            <div
              className="mt-4 max-w-3xl w-full rounded-2xl border overflow-hidden shadow-md bg-surface-raised"
              style={{
                borderColor: 'var(--border, #cbd5e1)',
              }}
            >
              <div className="p-4 sm:p-5 space-y-3">
                <div className="h-3.5 w-36 rounded-md animate-pulse bg-surface-overlay" />
                <div className="h-3 w-28 rounded-md animate-pulse bg-surface-overlay" />
                <div className="h-56 sm:h-72 w-full rounded-xl animate-pulse bg-surface-overlay" />
              </div>
            </div>
          )}

          {hasGeneratedImages && (
            <div className="mt-4 flex flex-col gap-4 max-w-5xl">
              <div className={`grid gap-4 ${imageCount === 1 ? 'grid-cols-1' : 'grid-cols-1 xl:grid-cols-2'}`}>
              {message.images.map((img, i) => {
                const isLoaded = loadedImages.has(i);

                return (
                <article
                  key={i}
                  className="relative inline-flex w-fit max-w-full flex-col rounded-2xl overflow-hidden border shadow-md transition-transform duration-300 hover:-translate-y-0.5 bg-surface"
                  style={{
                    borderColor: 'var(--border, #cbd5e1)',
                  }}
                >
                  <button
                    type="button"
                    className="relative cursor-zoom-in text-left bg-surface"
                    onClick={() => setFullscreenImage({ ...img, index: i })}
                    aria-label={`Open generated image ${i + 1}`}
                  >
                    {!isLoaded && (
                      <div className="absolute inset-0 bg-surface-raised flex items-center justify-center min-h-[280px]">
                        <div className="w-full h-full p-4 sm:p-5 space-y-3">
                          <div className="h-3.5 w-28 rounded-md animate-pulse bg-surface-overlay" />
                          <div className="h-3 w-20 rounded-md animate-pulse bg-surface-overlay" />
                          <div className="h-[calc(100%-2.5rem)] min-h-[220px] rounded-xl animate-pulse bg-surface-overlay" />
                        </div>
                      </div>
                    )}
                    <img
                      src={img.url}
                      alt={img.prompt || `Generated image ${i + 1}`}
                      onLoad={() => handleImageLoad(i)}
                      className={`block h-auto w-auto max-w-full max-h-[620px] object-contain transition-opacity duration-500 ${isLoaded ? 'opacity-100' : 'opacity-0'}`}
                    />
                  </button>
                </article>
                );
              })}
              </div>
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

      {fullscreenImage && (
        <div
          className="fixed inset-0 z-[200] bg-black/85 backdrop-blur-sm flex flex-col items-center justify-center p-4 sm:p-8 cursor-zoom-out animate-in fade-in zoom-in-95 duration-200"
          onClick={() => setFullscreenImage(null)}
        >
          <img
            src={fullscreenImage.url}
            alt={fullscreenImage.prompt}
            className="max-w-full max-h-[78vh] object-contain rounded-xl shadow-2xl"
          />
          <button
            className="absolute top-6 right-6 p-2 rounded-full bg-white/10 text-white hover:bg-white/20 transition-colors"
            onClick={(e) => { e.stopPropagation(); setFullscreenImage(null); }}
            aria-label="Close image preview"
          >
            <X size={20} />
          </button>
        </div>
      )}
    </div>
  );
});

export default MessageItem;

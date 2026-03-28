'use client';

import { useState, useCallback, useMemo, useContext, createContext, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import { ChevronDown, ChevronRight, ExternalLink, Loader2, Search, Globe, CheckCircle2 } from 'lucide-react';
import { sanitizeStreamingMarkdown } from './MarkdownRenderer';
import MarkdownRenderer from './MarkdownRenderer';
import CollapsibleActionBlock from './CollapsibleActionBlock';
import AnnotatedText from './AnnotatedText';
import ArtifactViewer from './ArtifactViewer';



const CitationCtx = createContext({ citations: [], activeCite: null, onCite: () => {} });

function tryHostname(url) {
  if (!url) return '';
  try { return new URL(url).hostname.replace(/^www\./, ''); } catch { return ''; }
}

function injectCiteTags(text) {
  if (!text) return '';
  return text.replace(/\[(\d+)\]/g, '<cite class="cite-ref" data-n="$1">[$1]</cite>');
}

const REMARK_PLUGINS = [remarkGfm, remarkMath];
const REHYPE_PLUGINS = [rehypeRaw, rehypeKatex];


/* ── Single source card for the batch grid ── */
function SourceCard({ source }) {
  const domain = source.domain || tryHostname(source.url);
  const title = source.title || domain || 'Source';
  return (
    <a
      href={source.url || '#'}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center gap-1.5 text-[11px] text-text-muted hover:text-text-secondary transition-colors"
    >
      <Globe className="w-3 h-3 shrink-0" />
      <span className="truncate">{title}</span>
    </a>
  );
}


/* ── Live research progress panel (shown while streaming, no content yet) ── */
function ResearchProgressPanel({ researchState }) {
  const [expanded, setExpanded] = useState(false);

  if (!researchState) return null;

  const { phase = 'searching', label: phaseLabel = 'Starting deep research…', queries = [], sources = [] } = researchState;

  const lowerPhase = String(phase).toLowerCase();
  const isSearchPhase = lowerPhase.includes('search');
  const isWritePhase = lowerPhase.includes('write') || lowerPhase.includes('synth');
  const activeStep = isSearchPhase ? 'search' : isWritePhase ? 'write' : 'read';

  const latestSources = sources.slice(-5);
  const steps = [
    { key: 'search', label: 'Search' },
    { key: 'read', label: 'Read' },
    { key: 'write', label: 'Write' },
  ];

  const activeIdx = steps.findIndex((step) => step.key === activeStep);

  return (
    <div className="mb-2.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-[14px] text-text-primary"
      >
        <Loader2 className="w-3.5 h-3.5 text-text-muted animate-spin" />
        <span className="truncate">{phaseLabel}</span>
        {sources.length > 0 && <span className="text-[11px] text-text-muted">({sources.length} sites)</span>}
        {expanded ? <ChevronDown className="w-3.5 h-3.5 text-text-muted rotate-180 transition-transform" /> : <ChevronDown className="w-3.5 h-3.5 text-text-muted" />}
      </button>

      {expanded && (
        <div className="mt-2 pl-0.5 space-y-1.5">
          <div className="text-[11px] uppercase tracking-wide text-text-muted/80">Functions</div>

          {steps.map((step, idx) => {
            const done = idx < activeIdx;
            const active = step.key === activeStep;
            const stateLabel = done ? 'done' : active ? 'running' : 'pending';
            const stateClass = done ? 'text-success' : active ? 'text-accent' : 'text-text-muted';

            return (
              <div key={step.key} className="text-[12px] text-text-secondary">
                {step.label} <span className={stateClass}>({stateLabel})</span>
              </div>
            );
          })}

          {queries.length > 0 && isSearchPhase && (
            <div className="space-y-0.5 pt-0.5">
              {queries.slice(0, 6).map((q, i) => (
                <div key={i} className="text-[11px] text-text-muted truncate">- {q}</div>
              ))}
              {queries.length > 6 && <div className="text-[11px] text-text-muted">+{queries.length - 6} more queries</div>}
            </div>
          )}

          {latestSources.length > 0 && (
            <div className="space-y-0.5 pt-0.5">
              {latestSources.map((src, i) => (
                <SourceCard key={src.url || i} source={src} />
              ))}
              {sources.length > 5 && <div className="text-[11px] text-text-muted">+{sources.length - 5} more sources</div>}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


// function CiteChip({ 'data-n': rawN }) { ... } removed


const MD_COMPONENTS = {
  // cite: CiteChip,
  h1: ({ children }) => <h1 className="md-heading md-h1">{children}</h1>,
  h2: ({ children }) => <h2 className="md-heading md-h2">{children}</h2>,
  h3: ({ children }) => <h3 className="md-heading md-h3">{children}</h3>,
  h4: ({ children }) => <h4 className="md-heading md-h4">{children}</h4>,
  h5: ({ children }) => <h5 className="md-heading md-h5">{children}</h5>,
  h6: ({ children }) => <h6 className="md-heading md-h6">{children}</h6>,
  p: ({ children, node }) => {
    const hasBlock = node?.children?.some(c =>
      c.tagName === 'img' || c.tagName === 'div' || c.tagName === 'pre' || c.tagName === 'table'
    );
    if (hasBlock) return <div className="md-paragraph">{children}</div>;
    return <p className="md-paragraph">{children}</p>;
  },
  ul: ({ children, className }) => {
    const isTaskList = className?.includes('contains-task-list');
    return <ul className={`md-list md-ul ${isTaskList ? 'md-task-list' : ''}`}>{children}</ul>;
  },
  ol: ({ children, start }) => <ol className="md-list md-ol" start={start}>{children}</ol>,
  li: ({ children, className }) => {
    const isTask = className?.includes('task-list-item');
    return <li className={`md-list-item ${isTask ? 'md-task-item' : ''}`}>{children}</li>;
  },
  blockquote: ({ children }) => (
    <blockquote className="md-blockquote"><div className="md-blockquote-content">{children}</div></blockquote>
  ),
  strong: ({ children }) => <strong className="md-strong">{children}</strong>,
  em: ({ children }) => <em className="md-em">{children}</em>,
  hr: () => <hr className="md-hr" />,
  table: ({ children }) => <div className="md-table-wrapper"><table className="md-table">{children}</table></div>,
  thead: ({ children }) => <thead className="md-thead">{children}</thead>,
  tbody: ({ children }) => <tbody className="md-tbody">{children}</tbody>,
  tr: ({ children }) => <tr className="md-tr">{children}</tr>,
  th: ({ children, style }) => <th className="md-th" style={style}>{children}</th>,
  td: ({ children, style }) => <td className="md-td" style={style}>{children}</td>,
  a: ({ children }) => <span className="md-strong">{children}</span>,
};


/* ── Markdown renderer ── */
function ResearchMarkdown({ content, isDone }) {
  const text = isDone ? content : sanitizeStreamingMarkdown(content);
  // const withCites = injectCiteTags(text);
  return (
    <div className="text-sm text-text-primary leading-relaxed">
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} rehypePlugins={REHYPE_PLUGINS} components={MD_COMPONENTS}>
        {text}
      </ReactMarkdown>
      {!isDone && (
        <span className="inline-block w-[2px] h-[1em] bg-text-muted/50 ml-0.5 align-text-bottom animate-pulse" aria-hidden="true" />
      )}
    </div>
  );
}


/* ── Collapsible sources summary (collapsed after done) ── */
function ResearchSummaryPanel({ sources, citations }) {
  const [open, setOpen] = useState(false);

  const items = useMemo(() => {
    const src = citations.length ? citations : sources;
    const seen = new Set();
    const out = [];
    for (const item of src) {
      const domain = item.domain || tryHostname(item.url);
      if (!domain || seen.has(domain)) continue;
      seen.add(domain);
      out.push({ ...item, domain });
    }
    return out;
  }, [citations, sources]);

  if (!items.length) return null;

  return (
    <div className="mb-3 rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <button
        className="flex items-center gap-2 w-full px-3.5 py-2.5 text-left hover:bg-white/[0.03] transition-colors"
        onClick={() => setOpen(v => !v)}
      >
        <CheckCircle2 className="w-3.5 h-3.5 text-green-400 shrink-0" />
        <span className="text-xs text-text-secondary font-medium flex-1">
          {items.length} source{items.length !== 1 ? 's' : ''} researched
        </span>
        {open ? <ChevronDown className="w-3 h-3 text-text-muted/50" /> : <ChevronRight className="w-3 h-3 text-text-muted/50" />}
      </button>
      {open && (
        <div className="px-3.5 pb-3 pt-0.5 border-t border-white/[0.04]">
          <div className="grid grid-cols-2 gap-1.5 sm:grid-cols-3">
            {items.slice(0, 18).map((item, idx) => {
              const n = item.index ?? idx + 1;
              return (
                <a
                  key={item.domain}
                  href={item.url || '#'}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg border border-white/[0.05] bg-white/[0.02] hover:border-white/[0.1] hover:bg-white/[0.05] transition-colors group"
                >
                  <span className="flex items-center justify-center w-4 h-4 rounded bg-accent/10 text-accent text-[9px] font-bold shrink-0">{n}</span>
                  <span className="text-[10px] text-text-muted group-hover:text-text-secondary truncate transition-colors">{item.domain}</span>
                  <ExternalLink className="w-2.5 h-2.5 text-text-muted/20 group-hover:text-text-muted/60 shrink-0 ml-auto transition-colors" />
                </a>
              );
            })}
          </div>
          {items.length > 18 && (
            <div className="text-[10px] text-text-muted/40 mt-1.5 px-1">+{items.length - 18} more</div>
          )}
        </div>
      )}
    </div>
  );
}


/* ── Bottom citation source links ── */
function SourceBubbles({ citations, sources, activeCite, onCite }) {
  const items = useMemo(() => {
    const src = citations.length ? citations : sources;
    const seen = new Set();
    const out = [];
    for (const item of src) {
      const domain = item.domain || tryHostname(item.url);
      if (!domain || seen.has(domain)) continue;
      seen.add(domain);
      out.push({ ...item, domain });
    }
    return out;
  }, [citations, sources]);

  if (!items.length) return null;

  return (
    <div className="mt-4 pt-3 border-t border-white/[0.06]">
      <div className="flex flex-wrap gap-1.5">
        {items.slice(0, 24).map((item, idx) => {
          const n = item.index ?? idx + 1;
          const isActive = activeCite === n;
          return (
            <a
              key={item.domain}
              id={`cite-src-${n}`}
              href={item.url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              onClick={() => onCite(n)}
              className={`inline-flex items-center gap-1.5 text-[11px] pl-1.5 pr-2 py-1 rounded-md border transition-colors ${
                isActive
                  ? 'bg-accent/15 text-accent border-accent/25'
                  : 'text-text-muted border-white/[0.06] bg-white/[0.03] hover:bg-white/[0.06] hover:text-text-secondary hover:border-white/[0.1]'
              }`}
            >
              <span className={`text-[10px] font-mono ${isActive ? 'text-accent' : 'text-text-muted/60'}`}>{n}</span>
              {item.domain}
            </a>
          );
        })}
        {items.length > 24 && (
          <span className="text-[10px] text-text-muted/50 px-1.5 py-1">+{items.length - 24}</span>
        )}
      </div>
    </div>
  );
}


/* ── Main component ── */
function ResearchReport({
  sources = [],
  streamingContent = '',
  citations = [],
  isDone = false,
  isStreaming = false,
  researchState = null,
  messageBlocks = [],
  artifacts = [],
}) {
  const [activeCite, setActiveCite] = useState(null);

  const handleCite = useCallback((n) => {
    setActiveCite(prev => (prev === n ? null : n));
    setTimeout(() => {
      document.getElementById(`cite-src-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }, []);

  const ctxValue = useMemo(
    () => ({ citations, activeCite, onCite: handleCite }),
    [citations, activeCite, handleCite],
  );

  const showProgress = isStreaming && !streamingContent;
  const hasContent = !!streamingContent;

  return (
    <CitationCtx.Provider value={ctxValue}>
      <div className="w-full">
        {/* Live progress (while no content yet) */}
        {showProgress && (
          <ResearchProgressPanel researchState={researchState} />
        )}

        {/* Done sources summary removed */}

        {/* Markdown report */}
        {hasContent && (
          isDone && messageBlocks.length > 0 ? (
            <div className="space-y-6">
              {(() => {
                const parents = [];
                const annotationsByParent = {};
                const orphanedAnnotations = [];
                const seenAnnotations = new Set();

                messageBlocks.forEach(block => {
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
                      <div key={block.id} data-block-id={block.id}>
                        <AnnotatedText 
                          content={block.text} 
                          annotations={annotationsByParent[block.id] || []} 
                        />
                      </div>
                    ))}
                    {orphanedAnnotations.map((block) => (
                      <div key={block.id} data-block-id={block.id}>
                        <CollapsibleActionBlock content={block.text} />
                      </div>
                    ))}
                  </>
                );
              })()}
            </div>
          ) : (
            <ResearchMarkdown content={streamingContent} isDone={isDone} />
          )
        )}

        {/* Citation source bubbles removed */}
        
        {/* Research Artifacts (PDF Export, etc.) */}
        {artifacts.length > 0 && isDone && (
          <div className="mt-6 pt-4 border-t border-white/[0.06]">
            <div className="text-[10px] uppercase tracking-wider text-text-muted/60 mb-2.5 font-bold">
              Research Deliverables
            </div>
            <ArtifactViewer artifacts={artifacts} />
          </div>
        )}
      </div>
    </CitationCtx.Provider>
  );
}


export default memo(ResearchReport);

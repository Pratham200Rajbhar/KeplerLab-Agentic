'use client';

import { useState, useCallback, useMemo, useContext, createContext, memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import { ChevronDown, ChevronRight, Globe } from 'lucide-react';
import { sanitizeStreamingMarkdown } from './MarkdownRenderer';

/**
 * ResearchReport — minimal, citation-aware research UI.
 *
 * While streaming (no content yet): pulsing "Researching the web..."
 * While streaming (content arriving): inline markdown with live citation chips + cursor
 * When done:
 *   - Collapsible "Research Process" panel (source count + domains)
 *   - Clean markdown with interactive [N] citation chips
 *   - Source bubble grid — click citation ↔ highlights matching bubble
 */

// ── Citation context ───────────────────────────────────────────────────────
const CitationCtx = createContext({ citations: [], activeCite: null, onCite: () => {} });

// ── Helpers ────────────────────────────────────────────────────────────────
function tryHostname(url) {
  if (!url) return '';
  try { return new URL(url).hostname; } catch { return ''; }
}

/** Replace [N] in text with <cite data-n="N"> so rehype-raw renders them. */
function injectCiteTags(text) {
  if (!text) return '';
  return text.replace(/\[(\d+)\]/g, '<cite class="cite-ref" data-n="$1">[$1]</cite>');
}

const REMARK_PLUGINS = [remarkGfm, remarkMath];
const REHYPE_PLUGINS = [rehypeRaw, rehypeKatex];

// ── Inline citation chip ────────────────────────────────────────────────────
// Reads citation data + active state from CitationCtx.
// Defined outside render to prevent remounts.
function CiteChip({ 'data-n': rawN }) {
  const { citations, activeCite, onCite } = useContext(CitationCtx);
  const [hovered, setHovered] = useState(false);
  const num = parseInt(rawN, 10);
  if (!num) return <span>[{rawN}]</span>;

  const src = citations[num - 1];
  const domain = src?.domain || tryHostname(src?.url) || `Source ${num}`;
  const title = src?.title || domain;
  const isActive = activeCite === num;

  return (
    <span className="relative inline-flex items-center align-middle mx-0.5">
      <button
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => onCite(num)}
        className={`inline-flex items-center text-[11px] font-mono px-1.5 py-0.5 rounded border transition-all leading-none ${
          isActive
            ? 'bg-blue-500/30 text-blue-300 border-blue-500/50'
            : 'bg-blue-500/10 text-blue-400 border-blue-500/20 hover:bg-blue-500/20 hover:text-blue-300 hover:border-blue-500/40'
        }`}
      >
        {num}
      </button>
      {/* Hover tooltip */}
      {hovered && src && (
        <span className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-50 w-max max-w-[200px] bg-surface-raised border border-border/30 rounded-lg shadow-xl px-3 py-2 pointer-events-none">
          <span className="block text-[11px] font-medium text-text-secondary truncate leading-snug">{title}</span>
          <span className="block text-[10px] text-text-muted mt-0.5">{domain}</span>
        </span>
      )}
    </span>
  );
}

/** ReactMarkdown component map — stable reference, reads from CitationCtx. */
const MD_COMPONENTS = {
  cite: CiteChip,
  a: ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
      {children}
    </a>
  ),
};

// ── Citation-aware markdown renderer ───────────────────────────────────────
function ResearchMarkdown({ content, isDone }) {
  const text = isDone ? content : sanitizeStreamingMarkdown(content);
  const withCites = injectCiteTags(text);

  return (
    <div className="text-sm text-text-primary leading-relaxed prose-chat">
      <ReactMarkdown remarkPlugins={REMARK_PLUGINS} rehypePlugins={REHYPE_PLUGINS} components={MD_COMPONENTS}>
        {withCites}
      </ReactMarkdown>
      {!isDone && (
        <span
          className="inline-block w-[2px] h-[1em] bg-text-muted/50 ml-0.5 align-text-bottom animate-pulse"
          aria-hidden="true"
        />
      )}
    </div>
  );
}

// ── Loading indicator ──────────────────────────────────────────────────────
function ResearchingIndicator() {
  return (
    <div className="flex items-center gap-2.5 py-1 mb-3">
      <span className="relative flex h-2 w-2">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-blue-400 opacity-60" />
        <span className="relative inline-flex rounded-full h-2 w-2 bg-blue-500" />
      </span>
      <span className="text-sm text-text-muted">Researching the web...</span>
    </div>
  );
}

// ── Collapsible research process panel ────────────────────────────────────
function ResearchProcessPanel({ sources, citations }) {
  const [open, setOpen] = useState(false);

  const domains = useMemo(() => {
    const items = citations.length ? citations : sources;
    const seen = new Set();
    const out = [];
    for (const item of items) {
      const d = item.domain || tryHostname(item.url);
      if (d && !seen.has(d)) { seen.add(d); out.push(d); }
    }
    return out;
  }, [citations, sources]);

  if (!domains.length) return null;

  return (
    <div className="mb-4 rounded-lg border border-border/20 bg-surface-overlay/20 overflow-hidden">
      <button
        className="flex items-center gap-2 w-full px-3 py-2.5 text-left hover:bg-surface-overlay/30 transition-colors"
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
      >
        {open
          ? <ChevronDown className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />
          : <ChevronRight className="w-3.5 h-3.5 text-text-muted flex-shrink-0" />}
        <span className="text-xs text-text-secondary font-medium">Research Process</span>
        <span className="ml-auto text-xs text-text-muted">Visited {domains.length} sources</span>
      </button>
      {open && (
        <div className="px-4 pb-3 pt-1 border-t border-border/10">
          <div className="flex flex-wrap gap-1.5">
            {domains.slice(0, 30).map((d) => (
              <span key={d} className="text-[11px] text-text-secondary bg-surface-raised px-2 py-0.5 rounded-md border border-border/20">
                {d}
              </span>
            ))}
            {domains.length > 30 && (
              <span className="text-[11px] text-text-muted px-2 py-0.5">+{domains.length - 30} more</span>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Source bubble grid ───────────────────────────────────────────────────
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
    <div className="mt-4 pt-3 border-t border-border/15">
      <div className="flex items-center gap-1.5 mb-2.5">
        <Globe className="w-3.5 h-3.5 text-text-muted" />
        <span className="text-xs font-medium text-text-muted">Sources</span>
      </div>
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
              className={`inline-flex items-center gap-1.5 text-[11px] px-2.5 py-1 rounded-full border transition-all ${
                isActive
                  ? 'bg-blue-500/20 text-blue-300 border-blue-500/40 ring-1 ring-blue-500/25'
                  : 'text-text-secondary border-border/25 bg-surface-overlay/30 hover:bg-surface-overlay/60 hover:border-border/50 hover:text-text-primary'
              }`}
            >
              <span className={`text-[10px] font-mono ${isActive ? 'text-blue-400' : 'text-text-muted'}`}>{n}</span>
              {item.domain}
            </a>
          );
        })}
        {items.length > 24 && (
          <span className="text-[11px] text-text-muted px-2 py-1">+{items.length - 24} more</span>
        )}
      </div>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────────
function ResearchReport({
  sources = [],
  streamingContent = '',
  citations = [],
  isDone = false,
  isStreaming = false,
}) {
  const [activeCite, setActiveCite] = useState(null);

  const handleCite = useCallback((n) => {
    setActiveCite((prev) => (prev === n ? null : n));
    setTimeout(() => {
      document.getElementById(`cite-src-${n}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }, 50);
  }, []);

  const ctxValue = useMemo(
    () => ({ citations, activeCite, onCite: handleCite }),
    [citations, activeCite, handleCite],
  );

  const showLoading = isStreaming && !streamingContent;
  const hasContent = !!streamingContent;

  return (
    <CitationCtx.Provider value={ctxValue}>
      <div className="w-full">
        {showLoading && <ResearchingIndicator />}

        {isDone && (
          <ResearchProcessPanel sources={sources} citations={citations} />
        )}

        {hasContent && (
          <ResearchMarkdown content={streamingContent} isDone={isDone} />
        )}

        {isDone && hasContent && (
          <SourceBubbles
            citations={citations}
            sources={sources}
            activeCite={activeCite}
            onCite={handleCite}
          />
        )}
      </div>
    </CitationCtx.Provider>
  );
}

export default memo(ResearchReport);

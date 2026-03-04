'use client';

import { useState, memo } from 'react';
import { Check, ExternalLink, Download } from 'lucide-react';
import MarkdownRenderer, { sanitizeStreamingMarkdown } from './MarkdownRenderer';

/**
 * ResearchReport — replaces ResearchProgress with a full research report UI.
 *
 * Features:
 *   - 5-phase progress bar: Decomposing → Searching → Fetching → Synthesizing → Formatting
 *   - Source cards as horizontal scroll row
 *   - Streaming markdown report body with citation chips
 *   - Export button after completion
 */

const PHASES = [
  { id: 1, label: 'Decomposing' },
  { id: 2, label: 'Searching' },
  { id: 3, label: 'Fetching' },
  { id: 4, label: 'Synthesizing' },
  { id: 5, label: 'Formatting' },
];

const RATING_STYLES = {
  high:   'bg-green-500/20 text-green-400',
  medium: 'bg-yellow-500/20 text-yellow-400',
  low:    'bg-red-500/20 text-red-400',
};

/* ── Phase Progress Bar ── */
function PhaseProgressBar({ currentPhase, detail }) {
  return (
    <div className="mb-4">
      <div className="flex items-center justify-between gap-1 mb-2">
        {PHASES.map((phase, idx) => {
          const isCompleted = phase.id < currentPhase;
          const isActive = phase.id === currentPhase;
          const isPending = phase.id > currentPhase;

          return (
            <div key={phase.id} className="flex items-center gap-1 flex-1">
              {/* Node */}
              <div className="flex flex-col items-center">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-medium transition-all duration-300 ${
                    isCompleted
                      ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                      : isActive
                        ? 'bg-accent/20 text-accent border border-accent/40 ring-2 ring-accent/20 animate-pulse'
                        : 'bg-surface-overlay text-text-muted border border-border/30'
                  }`}
                >
                  {isCompleted ? <Check className="w-3 h-3" /> : phase.id}
                </div>
                <span
                  className={`text-[10px] mt-1 text-center whitespace-nowrap ${
                    isActive ? 'text-accent font-medium' : isCompleted ? 'text-green-400' : 'text-text-muted'
                  }`}
                >
                  {phase.label}
                </span>
              </div>

              {/* Connector line */}
              {idx < PHASES.length - 1 && (
                <div
                  className={`flex-1 h-0.5 mx-0.5 rounded transition-colors duration-300 ${
                    isCompleted ? 'bg-green-500/40' : 'bg-border/20'
                  }`}
                />
              )}
            </div>
          );
        })}
      </div>

      {/* Status detail */}
      {detail && (
        <p className="text-xs text-text-muted text-center">{detail}</p>
      )}
    </div>
  );
}

/* ── Source Card ── */
function SourceCard({ source }) {
  const rating = source.rating || 'medium';
  const ratingStyle = RATING_STYLES[rating] || RATING_STYLES.medium;
  const domain = source.domain || (source.url ? new URL(source.url).hostname : '');

  return (
    <a
      href={source.url}
      target="_blank"
      rel="noopener noreferrer"
      className="flex-shrink-0 w-44 rounded-lg border border-border/20 bg-surface-overlay/30 p-3 hover:bg-surface-overlay/50 transition-all cursor-pointer"
      style={{ animation: 'sourceSlideIn 0.3s ease-out forwards' }}
    >
      <span className={`inline-block text-[10px] px-1.5 py-0.5 rounded font-medium mb-1.5 ${ratingStyle}`}>
        {rating}
      </span>
      <p className="text-xs text-text-secondary font-medium truncate" title={source.title}>
        {source.title}
      </p>
      <p className="text-[10px] text-text-muted truncate">{domain}</p>
      {source.relevance != null && (
        <p className="text-[10px] text-text-muted mt-1">
          relevance: {typeof source.relevance === 'number' ? source.relevance.toFixed(2) : source.relevance}
        </p>
      )}
    </a>
  );
}

/* ── Source Cards Panel (horizontal scroll) ── */
function SourceCardsPanel({ sources }) {
  if (!sources.length) return null;

  return (
    <div className="mb-4">
      <p className="text-xs font-medium text-text-muted mb-2">Sources Found ({sources.length})</p>
      <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-thin">
        {sources.map((source, idx) => (
          <SourceCard key={source.url || idx} source={source} />
        ))}
      </div>
    </div>
  );
}

/* ── Citation Chip ── */
function CitationChip({ index, citation, onHover }) {
  const [showPopover, setShowPopover] = useState(false);

  return (
    <span className="relative inline-block">
      <span
        className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-blue-500/20 text-blue-400 cursor-pointer font-mono hover:bg-blue-500/30 transition-colors"
        onMouseEnter={() => setShowPopover(true)}
        onMouseLeave={() => setShowPopover(false)}
      >
        [{index}]
      </span>
      {showPopover && citation && (
        <div className="absolute bottom-full left-0 mb-1 w-64 p-3 rounded-lg border border-border/30 bg-surface-raised shadow-lg z-50 text-left">
          <p className="text-xs font-medium text-text-secondary truncate">{citation.title}</p>
          {citation.domain && (
            <div className="flex items-center gap-1 mt-1">
              <span className="text-[10px] text-text-muted">{citation.domain}</span>
              {citation.rating && (
                <span className={`text-[10px] px-1 py-0 rounded ${RATING_STYLES[citation.rating] || ''}`}>
                  {citation.rating}
                </span>
              )}
            </div>
          )}
          {citation.snippet && (
            <p className="text-[11px] text-text-muted mt-1 line-clamp-3">{citation.snippet}</p>
          )}
          {citation.url && (
            <a
              href={citation.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-[11px] text-accent mt-1.5 hover:underline"
            >
              Open source <ExternalLink className="w-3 h-3" />
            </a>
          )}
        </div>
      )}
    </span>
  );
}

/* ── Main Component ── */
function ResearchReport({
  query = '',
  currentPhase = 0,
  phaseDetail = '',
  sources = [],
  streamingContent = '',
  citations = [],
  isDone = false,
  // Legacy props for backward compatibility
  steps = [],
}) {
  // If we have legacy steps but no currentPhase, derive from steps
  const resolvedPhase = currentPhase || (() => {
    if (!steps.length) return 0;
    const activeIdx = steps.findIndex((s) => s.status === 'active');
    const allDone = steps.every((s) => s.status === 'done');
    if (allDone) return 6; // past final phase
    if (activeIdx >= 0) return activeIdx + 1;
    return 0;
  })();

  const showPhaseBar = resolvedPhase > 0 && resolvedPhase <= 5;

  return (
    <div className="research-report w-full">
      {/* Query header */}
      {query && (
        <div className="flex items-center gap-2 mb-4">
          <span className="text-base">🔬</span>
          <div>
            <p className="text-sm font-medium text-text-primary">Deep Research</p>
            <p className="text-xs text-text-muted italic">&ldquo;{query}&rdquo;</p>
          </div>
        </div>
      )}

      {/* Phase progress bar */}
      {showPhaseBar && (
        <PhaseProgressBar currentPhase={resolvedPhase} detail={phaseDetail} />
      )}

      {/* Source cards — show during Searching/Fetching phases (2-3) or after */}
      {sources.length > 0 && (
        <SourceCardsPanel sources={sources} />
      )}

      {/* Report body — streaming markdown */}
      {streamingContent && (
        <div className="markdown-content prose prose-sm max-w-none">
          <MarkdownRenderer
            content={isDone ? streamingContent : sanitizeStreamingMarkdown(streamingContent)}
          />
          {!isDone && <span className="streaming-cursor" />}
        </div>
      )}

      {/* Export button — after done */}
      {isDone && streamingContent && (
        <div className="flex items-center gap-2 mt-4 pt-3 border-t border-border/20">
          <button
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-accent/10 text-accent border border-accent/20 hover:bg-accent/20 transition-colors"
            aria-label="Export research report"
            onClick={() => {
              // Export as text file (PDF generation requires jspdf which may not be installed)
              const blob = new Blob([streamingContent], { type: 'text/markdown' });
              const url = URL.createObjectURL(blob);
              const link = document.createElement('a');
              link.href = url;
              link.download = `research-report-${Date.now()}.md`;
              link.click();
              URL.revokeObjectURL(url);
            }}
          >
            <Download className="w-3.5 h-3.5" />
            Export Report
          </button>
        </div>
      )}

      <style jsx>{`
        @keyframes sourceSlideIn {
          from { opacity: 0; transform: translateX(12px); }
          to   { opacity: 1; transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}

export default memo(ResearchReport);

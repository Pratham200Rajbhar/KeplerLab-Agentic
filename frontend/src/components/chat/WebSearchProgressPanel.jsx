'use client';

import { memo, useState } from 'react';
import {
  Globe,
  BookOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  CheckCircle2,
  Loader2,
  Search,
  XCircle,
} from 'lucide-react';

function safeDomain(url) {
  if (!url) return '';
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return '';
  }
}

function WebSearchProgressPanel({ webSearchState, sources = [], isStreaming }) {
  const [expanded, setExpanded] = useState(false);

  const { status = '', queries = [], scrapingUrls = [] } = webSearchState || {};
  if (!webSearchState) return null;

  const isDone = status === 'done' && !isStreaming;
  const effectiveStatus = (status === 'done' || sources.length > 0) && isStreaming
    ? 'generating'
    : status;

  const phases = [
    { key: 'searching', label: 'Search', icon: Search, active: effectiveStatus === 'searching' },
    { key: 'reading', label: 'Read', icon: BookOpen, active: effectiveStatus === 'reading' },
    { key: 'generating', label: 'Write', icon: Sparkles, active: effectiveStatus === 'generating' },
  ];

  const currentIdx = phases.findIndex((phase) => phase.active);
  const doneCount = scrapingUrls.filter((u) => u.status === 'done').length;
  const failCount = scrapingUrls.filter((u) => u.status === 'failed').length;

  const statusLabel = (() => {
    if (isDone && sources.length > 0) return `${sources.length} source${sources.length === 1 ? '' : 's'} collected`;
    if (effectiveStatus === 'searching') return 'Searching the web';
    if (effectiveStatus === 'reading') return 'Reading relevant pages';
    if (effectiveStatus === 'generating') return 'Preparing answer';
    if (effectiveStatus === 'done') return 'Search complete';
    return 'Running web search';
  })();

  return (
    <div className="mb-2.5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="inline-flex items-center gap-1.5 text-[14px] text-text-primary"
      >
        {isDone ? (
          <CheckCircle2 className="w-3.5 h-3.5 text-success" />
        ) : effectiveStatus === 'generating' ? (
          <Sparkles className="w-3.5 h-3.5 text-accent" />
        ) : (
          <Globe className="w-3.5 h-3.5 text-text-muted" />
        )}
        <span>{statusLabel}</span>
        {!isDone && <Loader2 className="w-3.5 h-3.5 text-text-muted animate-spin" />}
        {expanded ? <ChevronUp className="w-3.5 h-3.5 text-text-muted" /> : <ChevronDown className="w-3.5 h-3.5 text-text-muted" />}
      </button>

      {expanded && (
        <div className="mt-2 pl-0.5 space-y-1.5">
          <div className="text-[11px] uppercase tracking-wide text-text-muted/80">Functions</div>

          {phases.map((phase, idx) => {
            const done = currentIdx > -1 && idx < currentIdx;
            const active = phase.active;
            const Icon = phase.icon;
            const stateLabel = done ? 'done' : active ? 'running' : 'pending';
            const stateClass = done ? 'text-success' : active ? 'text-accent' : 'text-text-muted';

            return (
              <div key={phase.key} className="flex items-center gap-2 text-[12px] text-text-secondary">
                <Icon className="w-3 h-3" />
                <span>{phase.label}</span>
                <span className={stateClass}>({stateLabel})</span>
              </div>
            );
          })}

          {effectiveStatus === 'searching' && queries.length > 0 && (
            <div className="space-y-0.5 pt-0.5">
              {queries.slice(0, 6).map((q, i) => (
                <div key={i} className="text-[11px] text-text-muted truncate">- {q}</div>
              ))}
              {queries.length > 6 && <div className="text-[11px] text-text-muted">+{queries.length - 6} more queries</div>}
            </div>
          )}

          {effectiveStatus === 'reading' && scrapingUrls.length > 0 && (
            <div className="space-y-0.5 pt-0.5">
              {scrapingUrls.slice(0, 4).map((item, idx) => {
                const domain = safeDomain(item.url) || item.url;
                const rowState = item.status === 'done' ? 'done' : item.status === 'failed' ? 'failed' : 'running';
                const rowClass = rowState === 'done' ? 'text-success' : rowState === 'failed' ? 'text-danger' : 'text-accent';
                return (
                  <div key={idx} className="text-[11px] text-text-muted truncate">
                    {domain} <span className={rowClass}>({rowState})</span>
                  </div>
                );
              })}
              <div className="text-[11px] text-text-muted">
                {doneCount > 0 ? `${doneCount} read` : ''}
                {doneCount > 0 && failCount > 0 ? ', ' : ''}
                {failCount > 0 ? `${failCount} failed` : ''}
                {scrapingUrls.length > 4 ? `, +${scrapingUrls.length - 4} more` : ''}
              </div>
            </div>
          )}

          {sources.length > 0 && (
            <div className="space-y-0.5 pt-0.5">
              {sources.slice(0, 6).map((src, idx) => {
                const domain = safeDomain(src.url) || src.url;
                return (
                  <a
                    key={src.url || idx}
                    href={src.url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1.5 text-[11px] text-text-muted hover:text-text-secondary transition-colors"
                  >
                    <ExternalLink className="w-3 h-3 shrink-0" />
                    <span className="truncate">{src.title || domain}</span>
                  </a>
                );
              })}
              {sources.length > 6 && <div className="text-[11px] text-text-muted">+{sources.length - 6} more sources</div>}
            </div>
          )}

          {effectiveStatus === 'generating' && (
            <div className="text-[11px] text-text-muted">Composing answer from extracted sources.</div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(WebSearchProgressPanel);

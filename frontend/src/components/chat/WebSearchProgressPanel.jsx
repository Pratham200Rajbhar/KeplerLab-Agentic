'use client';

import { memo, useState, useMemo } from 'react';
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


function WebSearchProgressPanel({ webSearchState, sources = [], isStreaming }) {
  const [expanded, setExpanded] = useState(false);

  const { status = '', queries = [], scrapingUrls = [] } = webSearchState || {};
  const isDone = status === 'done' && !isStreaming;
  const effectiveStatus = (status === 'done' || sources.length > 0) && isStreaming
    ? 'generating'
    : status;

  const phases = useMemo(() => [
    { key: 'searching',  label: 'Searching',    icon: Search,      active: effectiveStatus === 'searching' },
    { key: 'reading',    label: 'Reading',       icon: BookOpen,    active: effectiveStatus === 'reading' },
    { key: 'generating', label: 'Synthesizing',  icon: Sparkles,    active: effectiveStatus === 'generating' },
  ], [effectiveStatus]);

  if (!webSearchState) return null;

  const currentIdx = phases.findIndex(p => p.active);
  const doneCount = scrapingUrls.filter(u => u.status === 'done').length;
  const failCount = scrapingUrls.filter(u => u.status === 'failed').length;

  /* ── Done state: compact summary ── */
  if (isDone && sources.length > 0) {
    return (
      <div className="mb-3 rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
        <button
          onClick={() => setExpanded(!expanded)}
          className="w-full flex items-center gap-3 px-3.5 py-2.5 hover:bg-white/[0.03] transition-colors group"
        >
          <div className="flex items-center justify-center w-6 h-6 rounded-lg bg-green-500/10">
            <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />
          </div>
          <span className="text-xs font-medium text-text-primary flex-1 text-left">
            {sources.length} source{sources.length !== 1 ? 's' : ''} found
          </span>
          <div className="text-text-muted/50 group-hover:text-text-muted transition-colors">
            {expanded
              ? <ChevronUp className="w-3.5 h-3.5" />
              : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
        </button>

        {expanded && (
          <div className="px-3.5 pb-3 pt-0.5 space-y-1 border-t border-white/[0.04]">
            {sources.map((src, idx) => {
              let domain = '';
              try { domain = new URL(src.url).hostname.replace(/^www\./, ''); } catch {}
              return (
                <a
                  key={src.url || idx}
                  href={src.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center gap-2.5 py-1.5 px-2 rounded-lg hover:bg-white/[0.04] transition-colors group/src"
                >
                  <span className="flex items-center justify-center w-5 h-5 rounded-md bg-accent/10 text-accent text-[10px] font-bold shrink-0">
                    {idx + 1}
                  </span>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-text-secondary group-hover/src:text-accent truncate transition-colors">
                      {src.title || domain}
                    </div>
                    <div className="text-[10px] text-text-muted/50 truncate">{domain}</div>
                  </div>
                  <ExternalLink className="w-3 h-3 text-text-muted/30 group-hover/src:text-accent/60 shrink-0 transition-colors" />
                </a>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  /* ── In-progress state ── */
  return (
    <div className="mb-3 rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      <div className="px-3.5 py-3 space-y-3">
        {/* Phase dots */}
        <div className="flex items-center gap-1">
          {phases.map((phase, idx) => {
            const done = idx < currentIdx || isDone;
            const active = phase.active;
            const Icon = phase.icon;
            return (
              <div key={phase.key} className="flex items-center gap-1">
                {idx > 0 && (
                  <div className={`w-6 h-px mx-0.5 transition-colors duration-500 ${done ? 'bg-accent/40' : 'bg-white/[0.06]'}`} />
                )}
                <div className="flex items-center gap-1.5">
                  <div className={`flex items-center justify-center w-5 h-5 rounded-md transition-all duration-300 ${
                    done ? 'bg-accent/15' : active ? 'bg-white/[0.06]' : 'bg-white/[0.03]'
                  }`}>
                    {done ? (
                      <CheckCircle2 className="w-3 h-3 text-accent" />
                    ) : active ? (
                      <Icon className="w-3 h-3 text-text-primary animate-pulse" />
                    ) : (
                      <Icon className="w-3 h-3 text-text-muted/30" />
                    )}
                  </div>
                  <span className={`text-[11px] transition-colors duration-300 ${
                    done ? 'text-accent/70' : active ? 'text-text-primary font-medium' : 'text-text-muted/30'
                  }`}>
                    {phase.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Search queries */}
        {effectiveStatus === 'searching' && queries.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {queries.map((q, i) => (
              <span key={i} className="inline-flex items-center gap-1 px-2 py-1 rounded-md bg-white/[0.04] text-[11px] text-text-secondary">
                <Search className="w-2.5 h-2.5 text-text-muted/50" />
                {q}
              </span>
            ))}
          </div>
        )}

        {/* Scraping URLs */}
        {effectiveStatus === 'reading' && scrapingUrls.length > 0 && (
          <div className="space-y-1">
            {scrapingUrls.map((item, idx) => {
              let domain = item.url;
              try { domain = new URL(item.url).hostname.replace(/^www\./, ''); } catch {}
              return (
                <div key={idx} className="flex items-center gap-2 text-[11px]">
                  {item.status === 'done'
                    ? <CheckCircle2 className="w-3 h-3 text-green-400/70 shrink-0" />
                    : item.status === 'failed'
                      ? <XCircle className="w-3 h-3 text-red-400/60 shrink-0" />
                      : <Loader2 className="w-3 h-3 text-text-muted/50 animate-spin shrink-0" />
                  }
                  <span className="text-text-muted truncate">{domain}</span>
                </div>
              );
            })}
            {(doneCount > 0 || failCount > 0) && (
              <div className="flex gap-2 pt-0.5">
                {doneCount > 0 && <span className="text-[10px] text-green-400/60">{doneCount} read</span>}
                {failCount > 0 && <span className="text-[10px] text-red-400/50">{failCount} failed</span>}
              </div>
            )}
          </div>
        )}

        {/* Generating */}
        {effectiveStatus === 'generating' && (
          <div className="flex items-center gap-2 text-[11px] text-text-muted">
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Writing response…</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(WebSearchProgressPanel);

'use client';

import { memo, useState, useEffect, useRef } from 'react';
import { ChevronDown, ChevronUp, Search, FileText, BrainCircuit, Pencil } from 'lucide-react';

/**
 * ResearchProgressPanel — rich progress UI for deep research mode.
 *
 * Props:
 *   status: "idle" | "researching" | "synthesizing" | "done"
 *   iteration: number
 *   totalIterations: number
 *   currentPhase: "searching" | "reading" | "analyzing" | "writing"
 *   phaseLabel: string
 *   queriesUsed: string[]
 *   sources: [{ index, title, url, domain, iteration_found }]
 */
function ResearchProgressPanel({
  status,
  iteration = 0,
  totalIterations = 5,
  currentPhase = 'searching',
  phaseLabel = '',
  queriesUsed = [],
  sources = [],
}) {
  const [queriesOpen, setQueriesOpen] = useState(false);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);

  // Elapsed timer
  useEffect(() => {
    if (status === 'researching' || status === 'synthesizing') {
      timerRef.current = setInterval(() => {
        setElapsed((prev) => prev + 1);
      }, 1000);
    } else {
      if (timerRef.current) clearInterval(timerRef.current);
      if (status === 'idle') setElapsed(0);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [status]);

  if (status === 'idle' || status === 'done') return null;

  const formatTime = (secs) => {
    const m = Math.floor(secs / 60);
    const s = secs % 60;
    return `${m}:${s.toString().padStart(2, '0')}`;
  };

  const progressPct = totalIterations > 0
    ? Math.round((iteration / totalIterations) * 100)
    : 0;

  const phaseIcons = {
    searching: <Search className="w-3.5 h-3.5" />,
    reading: <FileText className="w-3.5 h-3.5" />,
    analyzing: <BrainCircuit className="w-3.5 h-3.5" />,
    writing: <Pencil className="w-3.5 h-3.5" />,
  };

  const phaseLabels = {
    searching: 'Searching...',
    reading: 'Reading pages...',
    analyzing: 'Analyzing findings...',
    writing: 'Writing research report...',
  };

  const isSynthesizing = status === 'synthesizing';

  return (
    <div className="mb-3 rounded-lg border border-blue-500/20 bg-blue-500/5 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2">
        <div className="flex items-center gap-2">
          <span className="text-sm">🔬</span>
          <span className="text-sm font-medium text-text-primary">Deep Research</span>
        </div>
        <span className="text-xs text-text-muted font-mono">
          {formatTime(elapsed)} elapsed
        </span>
      </div>

      {/* Progress */}
      {!isSynthesizing && (
        <div className="px-3 pb-2 space-y-2">
          {/* Iteration counter */}
          <div className="flex items-center justify-between text-xs text-text-secondary">
            <span>Iteration {iteration} of {totalIterations}</span>
            <span>{progressPct}%</span>
          </div>

          {/* Progress bar */}
          <div className="w-full h-1.5 rounded-full bg-surface-raised overflow-hidden">
            <div
              className="h-full rounded-full bg-blue-500 transition-all duration-500"
              style={{ width: `${progressPct}%` }}
            />
          </div>

          {/* Phase status */}
          <div className="flex items-center gap-2 text-xs text-text-secondary">
            <span className="animate-spin-slow text-blue-400">
              {phaseIcons[currentPhase] || phaseIcons.searching}
            </span>
            <span>{phaseLabel || phaseLabels[currentPhase] || 'Working...'}</span>
          </div>
        </div>
      )}

      {/* Synthesizing state */}
      {isSynthesizing && (
        <div className="px-3 pb-2">
          <div className="flex items-center gap-2 text-xs text-blue-400">
            <Pencil className="w-3.5 h-3.5 animate-pulse" />
            <span>Writing research report...</span>
          </div>
        </div>
      )}

      {/* Queries used (collapsible) */}
      {queriesUsed.length > 0 && (
        <div className="border-t border-blue-500/10">
          <button
            className="flex items-center gap-1.5 w-full px-3 py-1.5 text-xs text-text-muted hover:text-text-secondary transition-colors"
            onClick={() => setQueriesOpen(!queriesOpen)}
          >
            {queriesOpen ? (
              <ChevronUp className="w-3 h-3" />
            ) : (
              <ChevronDown className="w-3 h-3" />
            )}
            <span>Queries used so far ({queriesUsed.length})</span>
          </button>

          {queriesOpen && (
            <div className="px-3 pb-2 space-y-1">
              {queriesUsed.map((q, i) => (
                <div key={i} className="text-[11px] text-text-muted pl-4">
                  {i + 1}. {q}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default memo(ResearchProgressPanel);

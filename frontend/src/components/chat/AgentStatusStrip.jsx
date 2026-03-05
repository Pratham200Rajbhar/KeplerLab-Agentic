'use client';

import { memo, useState, useCallback } from 'react';
import {
  ChevronDown, ChevronUp, Search, Globe, Code2,
  Brain, Wrench, CheckCircle2, Loader2, AlertCircle,
} from 'lucide-react';

/**
 * AgentStatusStrip — shows the agent's current execution status
 * and expandable details panel with step timeline.
 *
 * Props:
 *   status: "idle" | "executing" | "done"
 *   currentLabel: string — current step label
 *   steps: [{ tool, label, status, elapsed_ms, code }]
 *   stepCodes: { [step_index]: { code, language } }
 *   dotColor: "blue" | "amber" | "green"
 */

const TOOL_ICONS = {
  rag_tool: Search,
  python_tool: Code2,
  web_search_tool: Globe,
  research_tool: Brain,
};

function AgentStatusStrip({ status, currentLabel, steps = [], stepCodes = {}, dotColor = 'blue' }) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [openCodeSteps, setOpenCodeSteps] = useState({});

  const toggleCode = useCallback((idx) => {
    setOpenCodeSteps((prev) => ({ ...prev, [idx]: !prev[idx] }));
  }, []);

  if (status === 'idle') return null;

  const dotColorClass = {
    blue: 'bg-blue-500',
    amber: 'bg-amber-500',
    green: 'bg-emerald-500',
  }[dotColor] || 'bg-blue-500';

  const pulseClass = status === 'executing' ? 'animate-pulse' : '';

  return (
    <div className="mb-3 rounded-lg border border-border/30 bg-surface-overlay/50 overflow-hidden">
      {/* Main strip */}
      <div
        className="flex items-center gap-2.5 px-3 py-2 cursor-pointer select-none"
        onClick={() => setDetailsOpen(!detailsOpen)}
      >
        <span className={`w-2 h-2 rounded-full ${dotColorClass} ${pulseClass} shrink-0`} />
        <span className="text-sm text-text-primary flex-1 truncate">
          {currentLabel || 'Agent working...'}
        </span>
        <button className="text-text-muted hover:text-text-primary transition-colors p-0.5">
          {detailsOpen ? (
            <ChevronUp className="w-3.5 h-3.5" />
          ) : (
            <ChevronDown className="w-3.5 h-3.5" />
          )}
        </button>
        <span className="text-[10px] text-text-muted">
          {detailsOpen ? 'Hide' : 'Details'}
        </span>
      </div>

      {/* Details panel */}
      {detailsOpen && steps.length > 0 && (
        <div className="border-t border-border/20 px-3 py-2 space-y-1.5">
          {steps.map((step, idx) => {
            const Icon = TOOL_ICONS[step.tool] || Wrench;
            const isRunning = step.status === 'running';
            const isDone = step.status === 'done' || step.status === 'completed';
            const hasError = step.status === 'error';
            const hasCode = stepCodes[idx]?.code;

            return (
              <div key={idx} className="space-y-1">
                <div className="flex items-center gap-2 text-xs">
                  <div className="flex items-center justify-center w-5 h-5 rounded-md bg-surface-raised">
                    {isRunning ? (
                      <Loader2 className="w-3 h-3 text-blue-400 animate-spin" />
                    ) : hasError ? (
                      <AlertCircle className="w-3 h-3 text-red-400" />
                    ) : isDone ? (
                      <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <Icon className="w-3 h-3 text-text-muted" />
                    )}
                  </div>
                  <span className="text-text-secondary font-medium capitalize">
                    {step.tool?.replace(/_/g, ' ') || 'Tool'}
                  </span>
                  <span className="text-text-muted flex-1 truncate">
                    {step.label || step.description || ''}
                  </span>
                  {step.elapsed_ms > 0 && (
                    <span className="text-text-muted shrink-0">
                      {(step.elapsed_ms / 1000).toFixed(1)}s
                    </span>
                  )}
                  {hasCode && (
                    <button
                      className="text-text-muted hover:text-text-primary text-[10px] underline"
                      onClick={(e) => { e.stopPropagation(); toggleCode(idx); }}
                    >
                      {openCodeSteps[idx] ? 'Hide Code' : 'View Code'}
                    </button>
                  )}
                </div>

                {/* Code viewer */}
                {hasCode && openCodeSteps[idx] && (
                  <pre className="text-[11px] font-mono bg-surface-raised rounded-md p-2 overflow-x-auto max-h-[200px] text-text-secondary ml-7">
                    {stepCodes[idx].code}
                  </pre>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

export default memo(AgentStatusStrip);

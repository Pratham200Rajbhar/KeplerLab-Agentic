'use client';

import { useState } from 'react';
import { ChevronRight, Loader2, Check, X, Terminal, Zap } from 'lucide-react';
import ArtifactViewer from './ArtifactViewer';

/**
 * AgentExecutionPanel — shows collapsible step-by-step agent execution.
 *
 * Renders:
 *   - Plan header (step count + intent)
 *   - Step cards: collapsed by default, expandable to see code + tool output
 *   - Summary section (key results)
 *   - Artifacts grid
 */
export default function AgentExecutionPanel({ message, isStreaming }) {
  const [expandedSteps, setExpandedSteps] = useState(new Set());

  const {
    agentPlan = [],
    agentSteps = [],
    artifacts = [],
    agentSummary,
    // agentCodeBlocks is stored in the message but intentionally NOT rendered
    // (per /agent spec: hide generated Python scripts from the chat UI).
  } = message;

  const toggle = (i) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(i)) next.delete(i);
      else next.add(i);
      return next;
    });
  };

  if (!agentSteps.length && !agentPlan.length) return null;

  return (
    <div className="mt-1 mb-2">
      {/* ── Header ── */}
      <div className="flex items-center gap-2 mb-2.5 text-xs">
        <Zap size={12} className="text-purple-400 shrink-0" />
        <span className="font-semibold text-purple-400">Agent Execution</span>
        {agentPlan.length > 0 ? (
          <>
            <span className="text-text-muted/40">·</span>
            <span className="text-text-muted">{agentPlan.length} steps</span>
          </>
        ) : null}
        {isStreaming && (
          <Loader2 size={11} className="text-accent animate-spin ml-auto" />
        )}
      </div>

      {/* ── Step cards ── */}
      <div className="space-y-1">
        {agentSteps.map((step, i) => {
          const isLatest = isStreaming && i === agentSteps.length - 1;
          // Internal code blocks are stored but never shown in the UI.
          // Only show a step as expandable when it has a tool result to display.
          const hasDetail = !!step.toolResult;
          const isExpanded = expandedSteps.has(i);
          const succeeded = step.toolResult?.success !== false;

          return (
            <div
              key={i}
              className="rounded-lg border overflow-hidden"
              style={{
                borderColor: isExpanded
                  ? 'rgba(255,255,255,0.1)'
                  : 'rgba(255,255,255,0.05)',
                background: 'rgba(255,255,255,0.02)',
              }}
            >
              {/* Step row */}
              <button
                className="w-full flex items-center gap-2.5 px-3 py-2 text-left"
                onClick={() => hasDetail && toggle(i)}
                disabled={!hasDetail}
              >
                {/* Icon */}
                <span className="shrink-0 w-4 flex items-center justify-center">
                  {isLatest ? (
                    <Loader2 size={13} className="text-accent animate-spin" />
                  ) : !succeeded ? (
                    <X size={13} className="text-error/70" />
                  ) : (
                    <Check size={13} className="text-green-400/60" />
                  )}
                </span>

                {/* Label */}
                <span
                  className={`flex-1 text-xs leading-snug truncate ${
                    isLatest ? 'text-text-primary' : 'text-text-muted'
                  }`}
                >
                  {step.status}
                </span>

                {/* Tool tag */}
                {step.tool && step.tool !== 'python_tool' && (
                  <span className="text-[10px] text-text-muted/50 font-mono px-1.5 py-0.5 rounded bg-surface-overlay">
                    {step.tool}
                  </span>
                )}

                {/* Duration */}
                {step.toolResult?.duration_ms != null && (
                  <span className="text-[10px] text-text-muted/40 tabular-nums">
                    {(step.toolResult.duration_ms / 1000).toFixed(1)}s
                  </span>
                )}

                {/* Expand chevron */}
                {hasDetail && (
                  <ChevronRight
                    size={12}
                    className={`shrink-0 text-text-muted/40 transition-transform duration-150 ${
                      isExpanded ? 'rotate-90' : ''
                    }`}
                  />
                )}
              </button>

              {/* Expanded body — shows tool result only; generated code is intentionally hidden */}
              {isExpanded && hasDetail && (
                <div
                  className="border-t px-3 py-3 space-y-3"
                  style={{ borderColor: 'rgba(255,255,255,0.05)' }}
                >
                  {step.toolResult?.summary && (
                    <div>
                      <div className="flex items-center gap-1.5 mb-1.5 text-[10px] text-text-muted/60 uppercase tracking-wider font-semibold">
                        <Terminal size={10} />
                        Result
                      </div>
                      <p className="text-xs text-text-muted leading-relaxed">
                        {step.toolResult.summary}
                      </p>
                    </div>
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* ── Summary ── */}
      {agentSummary && !isStreaming && (
        <div
          className="mt-3 p-3 rounded-lg border"
          style={{
            background: 'rgba(139,92,246,0.04)',
            borderColor: 'rgba(139,92,246,0.15)',
          }}
        >
          {agentSummary.title && (
            <div className="text-xs font-semibold text-purple-300 mb-1.5">
              {agentSummary.title}
            </div>
          )}
          {agentSummary.key_results?.length > 0 && (
            <ul className="space-y-1">
              {agentSummary.key_results.slice(0, 5).map((r, i) => (
                <li key={i} className="flex items-start gap-2 text-xs text-text-muted leading-relaxed">
                  <span className="text-green-400 shrink-0 mt-0.5">✓</span>
                  {r}
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* ── Artifacts ── */}
      {artifacts.length > 0 && (
        <div className="mt-3">
          <ArtifactViewer artifacts={artifacts} />
        </div>
      )}
    </div>
  );
}

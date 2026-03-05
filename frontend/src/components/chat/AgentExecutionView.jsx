'use client';

import { memo } from 'react';
import { CheckCircle2, Loader2, Circle, AlertCircle, Bot } from 'lucide-react';

/**
 * AgentExecutionView — displays agent progress with animated steps.
 * 
 * Shows a clean step-by-step progress view:
 * - Completed steps have a checkmark
 * - Current step has a spinner
 * - Pending steps have a circle
 * - Error steps have an alert icon
 *
 * Props:
 *   steps: [{ id, label, status: 'pending'|'running'|'completed'|'error', error? }]
 *   isExecuting: boolean
 *   showHeader: boolean - whether to show "Agent Execution" header
 */
function AgentExecutionView({ steps = [], isExecuting = false, showHeader = true }) {
  if (steps.length === 0 && !isExecuting) {
    return null;
  }

  return (
    <div className="agent-execution-view mb-4">
      {/* Header */}
      {showHeader && (
        <div className="flex items-center gap-2 mb-3">
          <div className="flex items-center justify-center w-6 h-6 rounded-md bg-amber-500/15 text-amber-400">
            <Bot className="w-3.5 h-3.5" />
          </div>
          <span className="text-sm font-medium text-text-primary">Agent Execution</span>
          {isExecuting && (
            <span className="text-xs text-text-muted animate-pulse">Running...</span>
          )}
        </div>
      )}

      {/* Steps list */}
      <div className="space-y-1.5 pl-1">
        {steps.map((step, index) => (
          <StepItem key={step.id || index} step={step} isLast={index === steps.length - 1} />
        ))}
        
        {/* Show waiting indicator if executing but no steps yet */}
        {isExecuting && steps.length === 0 && (
          <div className="flex items-center gap-2.5 py-1">
            <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
            <span className="text-sm text-text-secondary">Starting agent...</span>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * Individual step item with status icon.
 */
function StepItem({ step, isLast }) {
  const { label, status, error } = step;
  // Ensure label is always a string to avoid "Objects are not valid as a React child"
  const displayLabel = typeof label === 'string' ? label : String(label ?? '');

  return (
    <div className="flex items-start gap-2.5 group">
      {/* Status icon */}
      <div className="flex items-center justify-center w-5 h-5 shrink-0 mt-0.5">
        {status === 'completed' && (
          <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        )}
        {status === 'running' && (
          <Loader2 className="w-4 h-4 text-amber-400 animate-spin" />
        )}
        {status === 'pending' && (
          <Circle className="w-4 h-4 text-text-muted/50" />
        )}
        {status === 'error' && (
          <AlertCircle className="w-4 h-4 text-red-400" />
        )}
      </div>

      {/* Step content */}
      <div className="flex-1 min-w-0">
        <span
          className={`text-sm leading-relaxed ${
            status === 'completed'
              ? 'text-text-secondary'
              : status === 'running'
                ? 'text-text-primary font-medium'
                : status === 'error'
                  ? 'text-red-400'
                  : 'text-text-muted'
          }`}
        >
          {displayLabel}
        </span>
        
        {/* Error message if any */}
        {status === 'error' && error && (
          <p className="text-xs text-red-400/80 mt-0.5">{error}</p>
        )}
      </div>

      {/* Connector line (hidden for last item) */}
      {!isLast && (
        <div className="absolute left-[9px] top-6 w-px h-[calc(100%-12px)] bg-border/30 hidden" />
      )}
    </div>
  );
}

/**
 * Compact version for inline use in messages.
 */
export function AgentExecutionCompact({ steps = [], isExecuting = false }) {
  if (steps.length === 0 && !isExecuting) {
    return null;
  }

  const completedCount = steps.filter((s) => s.status === 'completed').length;
  const hasError = steps.some((s) => s.status === 'error');
  const currentStep = steps.find((s) => s.status === 'running');

  return (
    <div className="flex items-center gap-2 text-xs text-text-muted">
      {isExecuting ? (
        <>
          <Loader2 className="w-3 h-3 text-amber-400 animate-spin" />
          <span>{currentStep?.label || 'Processing...'}</span>
        </>
      ) : hasError ? (
        <>
          <AlertCircle className="w-3 h-3 text-red-400" />
          <span className="text-red-400">Error in execution</span>
        </>
      ) : (
        <>
          <CheckCircle2 className="w-3 h-3 text-emerald-400" />
          <span className="text-emerald-400">{completedCount} steps completed</span>
        </>
      )}
    </div>
  );
}

/**
 * Streaming version that builds steps from SSE events.
 */
export function AgentExecutionStreaming({ liveSteps = [], isStreaming = false }) {
  // Convert live step events to step objects, handling both string and object entries
  const steps = liveSteps.map((step, index) => {
    const label =
      typeof step === 'string'
        ? step
        : step?.label || step?.tool || step?.description || '';
    const isLast = index === liveSteps.length - 1;
    return {
      id: `live-step-${index}`,
      label: String(label),
      status: isLast && isStreaming ? 'running' : 'completed',
    };
  });

  return <AgentExecutionView steps={steps} isExecuting={isStreaming} />;
}

export default memo(AgentExecutionView);

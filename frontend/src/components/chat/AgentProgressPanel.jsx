'use client';

import { memo, useMemo, useState } from 'react';
import {
  AlertCircle,
  CheckCircle2,
  ChevronDown,
  ChevronUp,
  Loader2,
} from 'lucide-react';

const TOOL_LABELS = {
  rag: 'Docs',
  web_search: 'Search',
  research: 'Research',
  python: 'Python',
  python_auto: 'Generate',
};

function getToolLabel(toolName) {
  return TOOL_LABELS[toolName] || 'Thinking';
}

function StepRow({ index, step, result, isActive, isPending, artifacts }) {
  const toolName = result?.tool || step?.tool_hint || '';
  const functionName = getToolLabel(toolName);
  const descText = step?.description || `Step ${index + 1}`;

  const status = result
    ? (result.success === false ? 'failed' : 'done')
    : isActive
      ? 'running'
      : isPending
        ? 'pending'
        : 'queued';

  const statusClass = status === 'done'
    ? 'text-success'
    : status === 'failed'
      ? 'text-danger'
      : status === 'running'
        ? 'text-accent'
        : 'text-text-muted';

  return (
    <div className="py-1.5">
      <div className="flex items-start gap-2">
        <span className="text-[11px] text-text-muted mt-0.5">{index + 1}.</span>
        <div className="min-w-0 flex-1">
          <div className="text-[12px] text-text-secondary leading-snug">
            {descText}
            <span className="text-text-muted"> - function </span>
            <span className="text-text-primary">{functionName}</span>
            <span className={`ml-1 ${statusClass}`}>({status})</span>
          </div>
          {result?.summary && (
            <div className="text-[11px] text-text-muted mt-0.5 leading-relaxed">
              {result.summary}
            </div>
          )}
        </div>
      </div>

      {artifacts && artifacts.length > 0 && (
        <div className="mt-1 ml-5 space-y-1">
          {artifacts.map((art, i) => (
            <div key={i} className="flex items-center gap-2 px-2 py-1 rounded-md border border-border/40 bg-surface-raised/55">
              <CheckCircle2 className="w-3 h-3 text-accent shrink-0" />
              <span className="text-[11px] text-text-primary truncate">{art.filename || art.name}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function ReflectionFeed({ reflection }) {
  if (!reflection) return null;

  const { action, reason } = reflection;

  return (
    <div className="mt-1 text-[11px] text-text-muted leading-relaxed">
      Reflection: {reason || 'Reviewing output quality and selecting the next best action.'}
      {action && (
        <span>
          {' '}Next action: <span className="text-text-secondary">{action.replace(/_/g, ' ')}</span>
        </span>
      )}
    </div>
  );
}

function WorkLog({ message }) {
  if (!message) return null;

  return (
    <div className="mt-1 text-[11px] text-text-muted truncate">
      System: {message}
    </div>
  );
}

function AgentProgressPanel({ agentState, isStreaming, artifacts = [] }) {
  const [expanded, setExpanded] = useState(false);

  const {
    status = 'planning',
    plan = [],
    currentStep = 0,
    totalSteps = 0,
    activeTool,
    results = [],
    finishReason,
    reflection,
    message,
    hasArtifacts = false,
  } = agentState || {};

  const isDone = status === 'done' && !isStreaming;
  const isSynthesizing = (status === 'done' && isStreaming) || status === 'synthesizing';
  const isPlanning = status === 'planning' || status === 'routing';
  const isExecuting = status === 'executing';

  const headerLabel = useMemo(() => {
    if (isDone) {
      if (finishReason === 'aborted') return 'Completed with issues';
      return 'Completed';
    }
    if (isSynthesizing) return 'Writing final response';
    if (isPlanning) return 'Analyzing';
    if (activeTool) return `${getToolLabel(activeTool)} in progress`;
    return 'Processing';
  }, [isDone, isSynthesizing, isPlanning, activeTool, finishReason]);

  const subLabel = useMemo(() => {
    if (isDone) {
      return hasArtifacts ? 'Artifacts are ready.' : 'All functions finished.';
    }
    if (isExecuting && totalSteps > 0) {
      return `Step ${Math.max(currentStep || 1, 1)} of ${totalSteps}`;
    }
    if (isSynthesizing) return 'Composing final output.';
    if (isPlanning) return 'Preparing function plan.';
    return 'Running functions.';
  }, [isDone, hasArtifacts, isExecuting, totalSteps, currentStep, isSynthesizing, isPlanning]);

  if (!agentState) return null;

  const hasPlan = plan.length > 0;

  return (
    <div className="mb-2.5">
      <div className="flex items-center gap-1.5 text-[14px] text-text-primary">
        {isDone ? (
          finishReason === 'aborted' ? <AlertCircle className="w-3.5 h-3.5 text-danger" /> : <CheckCircle2 className="w-3.5 h-3.5 text-success" />
        ) : (
          <Loader2 className="w-3.5 h-3.5 text-text-muted animate-spin" />
        )}

        <span>{headerLabel}</span>

        {hasPlan && (
          <button
            onClick={() => setExpanded((v) => !v)}
            className="inline-flex items-center text-text-muted hover:text-text-secondary transition-colors"
            aria-label={expanded ? 'Collapse functions' : 'Expand functions'}
          >
            {expanded ? <ChevronUp size={15} /> : <ChevronDown size={15} />}
          </button>
        )}
      </div>

      {subLabel && (
        <div className="text-[11px] text-text-muted mt-0.5">{subLabel}</div>
      )}

      {expanded && hasPlan && (
        <div className="mt-2 pl-0.5">
          <div className="text-[11px] uppercase tracking-wide text-text-muted/80 mb-1">Functions</div>

          {plan.map((step, idx) => {
            const stepResult = (results || []).find((r) => r.step_index === idx) || results[idx];
            const stepArtifacts = (artifacts || []).filter((a) => a.step_index === idx);

            return (
              <StepRow
                key={idx}
                index={idx}
                step={step}
                result={stepResult || null}
                isActive={isExecuting && (idx + 1) === currentStep}
                isPending={(idx + 1) > currentStep}
                artifacts={stepArtifacts}
              />
            );
          })}

          {isSynthesizing && (
            <div className="py-1.5 text-[12px] text-text-secondary">
              {plan.length + 1}. Finalizing response - function Generate (running)
            </div>
          )}

          {message && !isDone && <WorkLog message={message} />}
          {reflection && (isExecuting || !isDone) && <ReflectionFeed reflection={reflection} />}
        </div>
      )}
    </div>
  );
}

export default memo(AgentProgressPanel);

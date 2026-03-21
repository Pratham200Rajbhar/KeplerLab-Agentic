'use client';

import { memo, useState, useMemo } from 'react';
import {
  Bot,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Search,
  Globe,
  Code2,
  BookOpen,
  Zap,
  Wrench,
  XCircle,
  Sparkles,
  ListChecks,
  Circle,
} from 'lucide-react';

// ── Tool metadata ─────────────────────────────────────────────────────
const TOOL_META = {
  rag:         { icon: BookOpen, label: 'Reading documents', color: 'text-teal-400',    ring: 'ring-teal-400/30',    bg: 'bg-teal-400/10' },
  web_search:  { icon: Globe,    label: 'Web search',        color: 'text-blue-400',    ring: 'ring-blue-400/30',    bg: 'bg-blue-400/10' },
  research:    { icon: Search,   label: 'Deep research',     color: 'text-violet-400',  ring: 'ring-violet-400/30',  bg: 'bg-violet-400/10' },
  python:      { icon: Code2,    label: 'Running code',      color: 'text-green-400',   ring: 'ring-green-400/30',   bg: 'bg-green-400/10' },
  python_auto: { icon: Zap,      label: 'Generating output', color: 'text-emerald-400', ring: 'ring-emerald-400/30', bg: 'bg-emerald-400/10' },
};

const DEFAULT_TOOL = { icon: Wrench, label: 'Processing', color: 'text-slate-400', ring: 'ring-slate-400/30', bg: 'bg-slate-400/10' };

function getToolMeta(toolName) {
  return TOOL_META[toolName] || DEFAULT_TOOL;
}

// ── Step status icon ──────────────────────────────────────────────────
function StepStatusIcon({ state, tool, isActive }) {
  if (state === 'done-ok')   return <CheckCircle2 className="w-4 h-4 text-green-400 shrink-0" />;
  if (state === 'done-fail') return <XCircle      className="w-4 h-4 text-red-400   shrink-0" />;
  if (isActive)              return <Loader2      className="w-4 h-4 text-violet-400 animate-spin shrink-0" />;
  // Pending
  const meta = getToolMeta(tool);
  return <Circle className={`w-4 h-4 ${meta.color} opacity-30 shrink-0`} />;
}

// ── Single step row ───────────────────────────────────────────────────
function StepRow({ index, step, result, isActive, isPending }) {
  const toolName  = result?.tool || step?.tool_hint || '';
  const succeeded = result ? result.success !== false : null;
  const meta      = getToolMeta(toolName);
  const ToolIcon  = meta.icon;

  const rowState = result != null
    ? (succeeded ? 'done-ok' : 'done-fail')
    : (isActive ? 'active' : 'pending');

  const descText = step?.description || `Step ${index + 1}`;
  // Trim long descriptions
  const shortDesc = descText.length > 70 ? descText.slice(0, 67) + '…' : descText;

  return (
    <div
      className={`
        flex items-start gap-3 px-3.5 py-2.5 rounded-xl transition-all duration-300
        ${isActive  ? 'bg-white/[0.05] ring-1 ring-white/[0.08]' : ''}
        ${isPending ? 'opacity-50' : ''}
      `}
    >
      {/* Step number badge */}
      <div className={`
        flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold shrink-0 mt-0.5
        ${rowState === 'done-ok'   ? 'bg-green-400/15  text-green-400'   : ''}
        ${rowState === 'done-fail' ? 'bg-red-400/15    text-red-400'     : ''}
        ${isActive                 ? 'bg-violet-400/15 text-violet-400'  : ''}
        ${isPending                ? 'bg-white/5       text-text-muted'  : ''}
      `}>
        {index + 1}
      </div>

      {/* Description */}
      <div className="flex-1 min-w-0">
        <p className={`text-xs leading-relaxed ${isActive ? 'text-text-primary' : 'text-text-muted'}`}>
          {shortDesc}
        </p>
      </div>

      {/* Tool chip */}
      {toolName && (
        <div className={`flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] font-medium shrink-0 ${meta.bg} ${meta.color}`}>
          <ToolIcon className="w-2.5 h-2.5" />
          <span>{meta.label}</span>
        </div>
      )}

      {/* Status icon */}
      <StepStatusIcon state={rowState === 'done-ok' ? 'done-ok' : rowState === 'done-fail' ? 'done-fail' : null} isActive={isActive} tool={toolName} />
    </div>
  );
}

// ── Progress bar ─────────────────────────────────────────────────────
function ProgressBar({ pct }) {
  return (
    <div className="h-px w-full bg-white/[0.06] rounded-full overflow-hidden">
      <div
        className="h-full rounded-full transition-all duration-700 ease-out"
        style={{
          width: `${pct}%`,
          background: 'linear-gradient(90deg, rgba(139,92,246,0.6) 0%, rgba(192,132,252,0.9) 100%)',
        }}
      />
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────
function AgentProgressPanel({ agentState, isStreaming }) {
  const [expanded, setExpanded] = useState(false);

  const {
    status     = 'planning',
    plan       = [],
    currentStep = 0,
    totalSteps  = 0,
    activeTool,
    results    = [],
    finishReason,
    stepsExecuted,
    toolCalls,
    hasArtifacts,
  } = agentState || {};

  const isDone           = status === 'done' && !isStreaming;
  const isSynthesizing   = (status === 'done' && isStreaming) || status === 'synthesizing';
  const isPlanning       = status === 'planning' || status === 'routing';
  const isExecuting      = status === 'executing';

  const pct = useMemo(() => {
    if (!agentState)    return 0;
    if (isDone)         return 100;
    if (isSynthesizing) return 92;
    if (isPlanning)     return 8;
    if (totalSteps > 0) return Math.min(12 + ((currentStep - 1) / totalSteps) * 78, 88);
    return 25;
  }, [agentState, isDone, isSynthesizing, isPlanning, currentStep, totalSteps]);

  const headerLabel = useMemo(() => {
    if (!agentState)    return '';
    if (isDone) {
      if (finishReason === 'artifact_produced') return 'Files generated';
      if (finishReason === 'aborted')           return 'Could not complete';
      if (finishReason === 'direct_response')   return 'Response generated';
      if (hasArtifacts)                         return 'Analysis complete';
      return 'Task completed';
    }
    if (isSynthesizing) return 'Generating response…';
    if (isPlanning)     return 'Planning task…';
    if (activeTool) {
      const meta = getToolMeta(activeTool);
      return meta.label + '…';
    }
    return 'Working…';
  }, [agentState, isDone, isSynthesizing, isPlanning, activeTool, finishReason, hasArtifacts]);

  if (!agentState) return null;

  const completedCount   = results.filter(r => r?.success !== false).length;
  const failedCount      = results.filter(r => r?.success === false).length;

  const isError = isDone && (finishReason === 'aborted');
  const HeaderIcon = isDone
    ? (isError ? AlertCircle : CheckCircle2)
    : (isSynthesizing ? Sparkles : isPlanning ? ListChecks : Loader2);
  const headerIconColor = isDone
    ? (isError ? 'text-yellow-400' : 'text-green-400')
    : 'text-violet-400';
  const borderColor = isDone
    ? (isError ? 'border-yellow-400/20' : 'border-green-400/20')
    : 'border-white/[0.08]';

  const hasPlan = plan.length > 0;

  return (
    <div className={`relative mb-3 rounded-2xl border ${borderColor} bg-white/[0.025] backdrop-blur-xl overflow-hidden transition-all duration-500`}>

      {/* Progress bar — top edge */}
      {!isDone && (
        <div className="absolute top-0 left-0 right-0">
          <ProgressBar pct={pct} />
        </div>
      )}
      {isDone && !isError && (
        <div className="h-px w-full bg-green-400/20" />
      )}

      {/* Header row */}
      <button
        onClick={() => hasPlan && setExpanded(e => !e)}
        className={`w-full flex items-center justify-between px-4 py-3 transition-colors ${hasPlan ? 'hover:bg-white/[0.03] cursor-pointer' : 'cursor-default'}`}
      >
        <div className="flex items-center gap-2.5 min-w-0">
          <div className={`p-1.5 rounded-lg ${isDone ? (isError ? 'bg-yellow-400/10' : 'bg-green-400/10') : 'bg-violet-400/10'}`}>
            <HeaderIcon className={`w-4 h-4 ${headerIconColor} ${!isDone && !isSynthesizing && !isPlanning ? 'animate-spin' : ''}`} />
          </div>
          <span className="text-sm font-medium text-text-primary truncate">{headerLabel}</span>

          {/* Step counter badge */}
          {isExecuting && totalSteps > 0 && (
            <span className="text-[10px] tabular-nums bg-white/[0.06] text-text-muted px-2 py-0.5 rounded-full shrink-0">
              {currentStep}/{totalSteps}
            </span>
          )}

          {/* Done stats */}
          {isDone && (
            <div className="flex items-center gap-2 ml-1">
              {completedCount > 0 && (
                <span className="text-[10px] text-green-400/70 flex items-center gap-0.5">
                  <CheckCircle2 className="w-2.5 h-2.5" />{completedCount}
                </span>
              )}
              {failedCount > 0 && (
                <span className="text-[10px] text-red-400/70 flex items-center gap-0.5">
                  <XCircle className="w-2.5 h-2.5" />{failedCount}
                </span>
              )}
              {(toolCalls || 0) > 0 && (
                <span className="text-[10px] text-text-muted/60 flex items-center gap-0.5">
                  <Wrench className="w-2.5 h-2.5" />{toolCalls}
                </span>
              )}
            </div>
          )}
        </div>

        {hasPlan && (
          <div className="text-text-muted/50 shrink-0 ml-2">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
        )}
      </button>

      {/* Plan steps — always show when in-progress, collapsible when done */}
      {hasPlan && (isExecuting || isSynthesizing || (!isDone && !isPlanning) || (isDone && expanded)) && (
        <div className="px-2 pb-3 pt-1 space-y-0.5 border-t border-white/[0.04] animate-in fade-in slide-in-from-top-1 duration-200">
          {plan.map((step, idx) => {
            const stepNum   = idx + 1;
            const isActive  = isExecuting && stepNum === currentStep;
            const isDoneStep = idx < results.length;
            const isPending = !isDoneStep && !isActive;

            return (
              <StepRow
                key={idx}
                index={idx}
                step={step}
                result={results[idx] || null}
                isActive={isActive}
                isPending={isPending}
              />
            );
          })}

          {/* Synthesis step — shown after all plan steps when synthesizing */}
          {isSynthesizing && (
            <div className="flex items-center gap-3 px-3.5 py-2.5 rounded-xl bg-white/[0.05] ring-1 ring-white/[0.08] mt-0.5">
              <div className="flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold bg-violet-400/15 text-violet-400 shrink-0">
                {plan.length + 1}
              </div>
              <p className="text-xs text-text-primary flex-1">Generating response</p>
              <div className="flex items-center gap-1 px-1.5 py-0.5 rounded-md text-[10px] bg-violet-400/10 text-violet-400">
                <Sparkles className="w-2.5 h-2.5" />
                <span>Synthesis</span>
              </div>
              <Loader2 className="w-4 h-4 text-violet-400 animate-spin shrink-0" />
            </div>
          )}
        </div>
      )}

      {/* Collapsed hint when done and plan hidden */}
      {isDone && hasPlan && !expanded && (
        <div className="px-4 pb-2.5 -mt-1">
          <div className="flex gap-1.5">
            {plan.map((step, idx) => {
              const toolName = results[idx]?.tool || step?.tool_hint || '';
              const meta = getToolMeta(toolName);
              const ok = !results[idx] || results[idx].success !== false;
              return (
                <div
                  key={idx}
                  className={`h-1 flex-1 rounded-full transition-all ${ok ? 'bg-green-400/50' : 'bg-red-400/50'}`}
                />
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(AgentProgressPanel);

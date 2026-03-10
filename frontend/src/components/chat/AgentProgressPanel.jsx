'use client';

import { memo, useState, useMemo } from 'react';
import {
  Bot,
  ListChecks,
  Cog,
  Sparkles,
  CheckCircle2,
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Loader2,
  Search,
  Globe,
  Code2,
  BookOpen,
  FileText,
  Wrench,
  XCircle,
  Clock,
  Zap,
} from 'lucide-react';

const TOOL_META = {
  rag:         { icon: BookOpen,  label: 'Searching materials',  color: 'text-teal-400',    bg: 'bg-teal-400/10' },
  web_search:  { icon: Globe,     label: 'Searching the web',    color: 'text-orange-400',  bg: 'bg-orange-400/10' },
  research:    { icon: Search,    label: 'Deep research',        color: 'text-blue-400',    bg: 'bg-blue-400/10' },
  python:      { icon: Code2,     label: 'Running code',         color: 'text-green-400',   bg: 'bg-green-400/10' },
  python_auto: { icon: Zap,       label: 'Generating & running', color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
};

function simplifyStep(desc) {
  if (!desc) return '';
  return desc
    .replace(/\brag\b/gi, 'documents')
    .replace(/\bpython_auto\b/gi, 'code execution')
    .replace(/\bpython\b/gi, 'code');
}

const PHASE_CONFIG = {
  routing:      { label: 'Preparing',      icon: Bot,          color: 'text-blue-400',   bg: 'bg-blue-400/10' },
  planning:     { label: 'Planning',        icon: ListChecks,   color: 'text-blue-400',   bg: 'bg-blue-400/10' },
  executing:    { label: 'Working',         icon: Cog,          color: 'text-purple-400', bg: 'bg-purple-400/10' },
  synthesizing: { label: 'Finalizing',      icon: Sparkles,     color: 'text-violet-400', bg: 'bg-violet-400/10' },
  done:         { label: 'Complete',        icon: CheckCircle2, color: 'text-green-400',  bg: 'bg-green-400/10' },
  limit:        { label: 'Limit Reached',   icon: AlertCircle,  color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
  timeout:      { label: 'Timed Out',       icon: Clock,        color: 'text-yellow-400', bg: 'bg-yellow-400/10' },
};

function AgentProgressPanel({ agentState, isStreaming }) {
  const [showDetails, setShowDetails] = useState(false);

  const {
    status = 'planning',
    message = '',
    plan = [],
    currentStep = 0,
    totalSteps = 0,
    stepDescription = '',
    activeTool,
    results = [],
    finishReason,
    stepsExecuted,
    toolCalls,
    hasArtifacts,
  } = agentState || {};

  const isDone = status === 'done' && !isStreaming;
  const effectiveStatus = status === 'done' && isStreaming ? 'synthesizing' : status;
  const phase = PHASE_CONFIG[effectiveStatus] || PHASE_CONFIG.executing;
  const PhaseIcon = phase.icon;

  const progress = useMemo(() => {
    if (isDone) return 100;
    if (effectiveStatus === 'routing') return 5;
    if (effectiveStatus === 'planning') return 10;
    if (effectiveStatus === 'synthesizing') return 92;
    if (totalSteps > 0) return Math.min(15 + (currentStep / totalSteps) * 75, 88);
    return 30;
  }, [isDone, effectiveStatus, currentStep, totalSteps]);

  const statusMessage = useMemo(() => {
    if (isDone) {
      if (finishReason === 'artifact_produced') return 'Files generated successfully';
      if (finishReason === 'aborted') return 'Task could not be completed';
      if (finishReason === 'timeout') return 'Task timed out';
      if (finishReason === 'max_steps_reached') return 'Completed with step limit';
      if (hasArtifacts) return 'Analysis complete';
      return 'Task completed';
    }
    if (effectiveStatus === 'routing') return 'Analyzing request…';
    if (effectiveStatus === 'planning') return 'Creating execution plan…';
    if (effectiveStatus === 'synthesizing') return 'Generating response…';

    if (activeTool) {
      const meta = TOOL_META[activeTool];
      return meta ? `${meta.label}…` : 'Working…';
    }
    if (stepDescription) return simplifyStep(stepDescription);
    return 'Working…';
  }, [isDone, effectiveStatus, activeTool, stepDescription, hasArtifacts, finishReason]);

  if (!agentState) return null;

  // Success/failure stats
  const successCount = results.filter(r => r?.success !== false).length;
  const failCount = results.filter(r => r?.success === false).length;

  // Done state — compact pill with expandable detail
  if (isDone) {
    const isError = finishReason === 'aborted' || finishReason === 'timeout';
    const pillColor = isError ? 'border-yellow-400/20' : 'border-green-400/20';
    const StatusIcon = isError ? AlertCircle : CheckCircle2;
    const iconColor = isError ? 'text-yellow-400' : 'text-green-400';
    const iconBg = isError ? 'bg-yellow-400/10' : 'bg-green-400/10';

    return (
      <div className={`mb-3 rounded-xl border ${pillColor} bg-white/[0.02] backdrop-blur-xl overflow-hidden transition-all duration-500`}>
        <button
          onClick={() => setShowDetails(!showDetails)}
          className="w-full flex items-center justify-between px-4 py-2.5 hover:bg-white/[0.03] transition-colors group"
        >
          <div className="flex items-center gap-2.5">
            <div className={`p-1 rounded-md ${iconBg}`}>
              <StatusIcon className={`w-3.5 h-3.5 ${iconColor}`} />
            </div>
            <span className="text-xs font-medium text-text-primary">{statusMessage}</span>
            <div className="flex items-center gap-1.5">
              {successCount > 0 && (
                <span className="text-[10px] text-green-400/70 flex items-center gap-0.5">
                  <CheckCircle2 className="w-2.5 h-2.5" /> {successCount}
                </span>
              )}
              {failCount > 0 && (
                <span className="text-[10px] text-red-400/70 flex items-center gap-0.5">
                  <XCircle className="w-2.5 h-2.5" /> {failCount}
                </span>
              )}
              {toolCalls > 0 && (
                <span className="text-[10px] text-text-muted/50 flex items-center gap-0.5">
                  <Wrench className="w-2.5 h-2.5" /> {toolCalls} tool{toolCalls !== 1 ? 's' : ''}
                </span>
              )}
            </div>
          </div>
          <div className="text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
            {showDetails ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
        </button>

        {showDetails && plan.length > 0 && (
          <div className="px-4 pb-3 pt-0.5 space-y-1 animate-in fade-in slide-in-from-top-1 duration-200 border-t border-white/[0.04]">
            {plan.map((step, idx) => {
              const stepResult = results[idx];
              const succeeded = stepResult?.success !== false;
              const toolMeta = stepResult?.tool ? TOOL_META[stepResult.tool] : null;
              const ToolIcon = toolMeta?.icon;

              return (
                <div key={idx} className="flex items-center gap-2 text-[11px] py-0.5">
                  {succeeded
                    ? <CheckCircle2 className="w-3 h-3 text-green-400/70 shrink-0" />
                    : <XCircle className="w-3 h-3 text-red-400/70 shrink-0" />
                  }
                  <span className="text-text-muted truncate flex-1">{simplifyStep(step.description)}</span>
                  {ToolIcon && (
                    <div className={`flex items-center gap-1 shrink-0 ${toolMeta.color}`}>
                      <ToolIcon className="w-2.5 h-2.5" />
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    );
  }

  // In-progress state — animated card
  const activeToolMeta = activeTool ? TOOL_META[activeTool] : null;

  return (
    <div className="mb-3 rounded-xl border border-white/[0.08] bg-white/[0.03] backdrop-blur-xl overflow-hidden relative">
      {/* Animated accent line */}
      <div className="absolute top-0 left-0 w-full h-[2px] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${progress}%`,
            background: 'linear-gradient(90deg, rgba(139,92,246,0.5), rgba(192,132,252,0.8))',
          }}
        />
      </div>

      <div className="relative z-10 p-3.5 space-y-3">
        {/* Status row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className={`p-1.5 rounded-lg ${phase.bg}`}>
              <PhaseIcon className={`w-4 h-4 ${phase.color} animate-pulse`} />
            </div>
            <div className="flex flex-col">
              <span className="text-sm font-medium text-text-primary leading-tight">{statusMessage}</span>
              {/* Active tool badge */}
              {activeToolMeta && effectiveStatus === 'executing' && (
                <div className={`flex items-center gap-1 mt-0.5 ${activeToolMeta.color}`}>
                  <activeToolMeta.icon className="w-3 h-3" />
                  <span className="text-[10px] font-medium">{activeToolMeta.label}</span>
                </div>
              )}
            </div>
          </div>
          {totalSteps > 0 && effectiveStatus === 'executing' && (
            <span className="text-[10px] text-text-muted tabular-nums bg-white/5 px-1.5 py-0.5 rounded-md">
              {currentStep}/{totalSteps}
            </span>
          )}
        </div>

        {/* Step list — only during execution */}
        {plan.length > 0 && effectiveStatus === 'executing' && (
          <div className="space-y-0.5 pl-1">
            {plan.map((step, idx) => {
              const stepNum = idx + 1;
              const isCurrent = stepNum === currentStep;
              const isDoneStep = stepNum < currentStep;
              const stepResult = results[idx];
              const stepFailed = stepResult?.success === false;

              return (
                <div key={idx} className={`flex items-center gap-2 text-[11px] py-0.5 transition-all duration-300 ${
                  isCurrent ? 'opacity-100' : isDoneStep ? 'opacity-50' : 'opacity-20'
                }`}>
                  <div className="w-4 h-4 flex items-center justify-center shrink-0">
                    {isDoneStep ? (
                      stepFailed
                        ? <XCircle className="w-3 h-3 text-red-400" />
                        : <CheckCircle2 className="w-3 h-3 text-green-400" />
                    ) : isCurrent ? (
                      <Loader2 className="w-3 h-3 animate-spin text-purple-400" />
                    ) : (
                      <div className="w-1.5 h-1.5 rounded-full bg-white/15" />
                    )}
                  </div>
                  <span className={`truncate ${isCurrent ? 'text-text-primary font-medium' : 'text-text-muted'}`}>
                    {simplifyStep(step.description)}
                  </span>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(AgentProgressPanel);

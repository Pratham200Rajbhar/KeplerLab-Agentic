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
  BrainCircuit,
  Terminal,
  Activity,
  ArrowRight,
} from 'lucide-react';

// ── Tool metadata ─────────────────────────────────────────────────────
const TOOL_META = {
  rag:         { icon: BookOpen, label: 'Reading docs',     color: 'text-teal-400',    ring: 'ring-teal-400/30',    bg: 'bg-teal-400/10' },
  web_search:  { icon: Globe,    label: 'Search',           color: 'text-blue-400',    ring: 'ring-blue-400/30',    bg: 'bg-blue-400/10' },
  research:    { icon: Search,   label: 'Analyze',          color: 'text-violet-400',  ring: 'ring-violet-400/30',  bg: 'bg-violet-400/10' },
  python:      { icon: Code2,    label: 'Calculate',        color: 'text-green-400',   ring: 'ring-green-400/30',   bg: 'bg-green-400/10' },
  python_auto: { icon: Zap,      label: 'Generative',       color: 'text-emerald-400', ring: 'ring-emerald-400/30', bg: 'bg-emerald-400/10' },
};

const DEFAULT_TOOL = { icon: Wrench, label: 'Thinking', color: 'text-slate-400', ring: 'ring-slate-400/30', bg: 'bg-slate-400/10' };

function getToolMeta(toolName) {
  return TOOL_META[toolName] || DEFAULT_TOOL;
}

// ── Components ────────────────────────────────────────────────────────

function StepBadge({ index, state, isActive }) {
  const base = "flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold shrink-0 transition-all duration-300";
  if (state === 'done-ok')   return <div className={`${base} bg-green-500/20 text-green-400 border border-green-500/30 shadow-[0_0_8px_rgba(74,222,128,0.2)]`}>{index + 1}</div>;
  if (state === 'done-fail') return <div className={`${base} bg-red-500/20 text-red-400 border border-red-500/30`}>{index + 1}</div>;
  if (isActive)              return <div className={`${base} bg-violet-500/20 text-violet-400 border border-violet-500/40 animate-pulse`}>{index + 1}</div>;
  return <div className={`${base} bg-white/5 text-slate-500 border border-white/10`}>{index + 1}</div>;
}

function StepRow({ index, step, result, isActive, isPending, codeBlock, artifacts }) {
  const [isExpanded, setIsExpanded] = useState(false);
  const toolName  = result?.tool || step?.tool_hint || '';
  const succeeded = result ? result.success !== false : null;
  const meta      = getToolMeta(toolName);
  const ToolIcon  = meta.icon;

  const rowState = result != null
    ? (succeeded ? 'done-ok' : 'done-fail')
    : (isActive ? 'active' : 'pending');

  const descText = step?.description || `Task component ${index + 1}`;
  const hasDetails = !!(codeBlock || result?.summary || (artifacts && artifacts.length > 0));

  return (
    <div className="flex flex-col gap-1">
      <div 
        onClick={() => hasDetails && setIsExpanded(!isExpanded)}
        className={`
          flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-500 group
          ${isActive ? 'bg-white/[0.04] ring-1 ring-white/[0.08] shadow-inner' : 'hover:bg-white/[0.02]'}
          ${isPending ? 'opacity-40 grayscale-[0.5]' : ''}
          ${hasDetails ? 'cursor-pointer' : ''}
        `}
      >
        <StepBadge index={index} state={rowState} isActive={isActive} />
        
        <div className="flex-1 min-w-0">
          <p className={`text-[11px] leading-tight transition-colors ${isActive ? 'text-text-primary font-medium' : 'text-text-muted'}`}>
            {descText}
          </p>
        </div>

        {toolName && (
          <div className={`flex items-center gap-1.5 px-2 py-0.5 rounded-full text-[9px] font-semibold border ${meta.bg} ${meta.color} border-current/20 scale-95 opacity-80 group-hover:opacity-100 group-hover:scale-100 transition-all`}>
            <ToolIcon className="w-2.5 h-2.5" />
            <span className="uppercase tracking-wider">{meta.label}</span>
          </div>
        )}

        <div className="shrink-0 flex items-center gap-2">
          {rowState === 'done-ok' && <CheckCircle2 className="w-3.5 h-3.5 text-green-400" />}
          {rowState === 'done-fail' && <XCircle className="w-3.5 h-3.5 text-red-400" />}
          {isActive && <Loader2 className="w-3.5 h-3.5 text-violet-400 animate-spin" />}
          {hasDetails && (
            <div className={`transition-transform duration-300 ${isExpanded ? 'rotate-180' : ''}`}>
              <ChevronDown size={14} className="text-text-muted" />
            </div>
          )}
        </div>
      </div>

      {isExpanded && hasDetails && (
        <div className="ml-8 mr-2 mb-2 p-3 rounded-lg bg-black/20 border border-white/5 animate-in fade-in slide-in-from-top-1 duration-300">
          {result?.summary && (
            <div className="flex items-start gap-2 mb-2">
              <Activity className="w-3 h-3 text-violet-400 mt-0.5" />
              <p className="text-[10px] text-text-secondary leading-relaxed">{result.summary}</p>
            </div>
          )}
          
          {codeBlock && (
            <div className="mt-2 rounded-md overflow-hidden border border-white/10 bg-[#0d1117]">
              <div className="flex items-center justify-between px-2 py-1 bg-white/5 border-b border-white/5">
                <span className="text-[9px] font-mono text-text-muted uppercase">{codeBlock.language || 'python'}</span>
                <Terminal className="w-3 h-3 text-text-muted" />
              </div>
              <pre className="p-2 text-[10px] font-mono text-blue-300 overflow-x-auto">
                <code>{codeBlock.code}</code>
              </pre>
            </div>
          )}

          {artifacts && artifacts.length > 0 && (
            <div className="mt-2 space-y-1">
              <p className="text-[9px] font-bold text-text-muted uppercase tracking-wider mb-1">Generated Artifacts</p>
              {artifacts.map((art, i) => (
                <div key={i} className="flex items-center gap-2 px-2 py-1 rounded bg-white/5 border border-white/5">
                  <Sparkles className="w-2.5 h-2.5 text-emerald-400" />
                  <span className="text-[10px] text-text-primary truncate">{art.filename || art.name}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function ReflectionFeed({ reflection }) {
  if (!reflection) return null;
  
  const { action, reason, stepSucceeded } = reflection;
  const isHealing = action === 'retry_with_fix' || action === 'replan';

  return (
    <div className="mx-2 mt-1 mb-2 px-3 py-2.5 rounded-xl bg-violet-500/5 border border-violet-500/20 animate-in fade-in slide-in-from-bottom-2 duration-500">
      <div className="flex items-center gap-2 mb-1.5">
        <BrainCircuit className="w-3.5 h-3.5 text-violet-400" />
        <span className="text-[10px] font-bold text-violet-300 uppercase tracking-widest">Self-Reflection</span>
        {isHealing && (
          <span className="flex items-center gap-1 px-1.5 py-0.5 rounded-md bg-amber-500/10 text-amber-400 text-[9px] font-bold border border-amber-500/20">
            <Zap className="w-2 h-2 fill-current" /> HEALING
          </span>
        )}
      </div>
      <p className="text-[11px] text-text-secondary leading-relaxed font-italic border-l-2 border-violet-500/30 pl-3 py-0.5 italic">
        {reason || "Analyzing current state and optimizing next actions..."}
      </p>
      {action && (
        <div className="mt-2 flex items-center gap-2 text-[10px] text-violet-400/80 font-medium">
          <ArrowRight className="w-3 h-3" />
          <span>Decision: {action.replace(/_/g, ' ')}</span>
        </div>
      )}
    </div>
  );
}

function WorkLog({ message }) {
  if (!message) return null;
  return (
    <div className="mx-2 mt-1 mb-2 px-3 py-2 rounded-lg bg-black/40 border border-white/5 font-mono">
      <div className="flex items-center gap-2 mb-1">
        <Terminal className="w-3 h-3 text-emerald-400" />
        <span className="text-[9px] text-emerald-400/60 font-bold uppercase tracking-tight">System Log</span>
      </div>
      <p className="text-[10px] text-emerald-400/80 truncate">{message}</p>
    </div>
  );
}

// ── Main Component ────────────────────────────────────────────────────

function AgentProgressPanel({ agentState, isStreaming, codeBlocks = [], artifacts = [] }) {
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
    hasArtifacts,
  } = agentState || {};

  const isDone = status === 'done' && !isStreaming;
  const isSynthesizing = (status === 'done' && isStreaming) || status === 'synthesizing';
  const isPlanning = status === 'planning' || status === 'routing';
  const isExecuting = status === 'executing';

  const pct = useMemo(() => {
    if (!agentState) return 0;
    if (isDone) return 100;
    if (isSynthesizing) return 94;
    if (isPlanning) return 10;
    if (totalSteps > 0) return Math.min(15 + ((currentStep - 1) / totalSteps) * 75, 90);
    return 20;
  }, [agentState, isDone, isSynthesizing, isPlanning, currentStep, totalSteps]);

  const headerLabel = useMemo(() => {
    if (isDone) {
      if (finishReason === 'aborted') return 'Intelligence execution failed';
      return 'Task optimization complete';
    }
    if (isSynthesizing) return 'Synthesizing internal logic…';
    if (isPlanning)     return 'Architecting multi-step plan…';
    if (activeTool) {
      const meta = getToolMeta(activeTool);
      return `Autonomous: ${meta.label}…`;
    }
    return 'Processing intelligence feed…';
  }, [isDone, isSynthesizing, isPlanning, activeTool, finishReason]);

  if (!agentState) return null;

  const isError = isDone && finishReason === 'aborted';
  const hasPlan = plan.length > 0;

  return (
    <div className={`
      relative mb-4 rounded-2xl border transition-all duration-700 ease-in-out overflow-hidden
      ${isDone ? (isError ? 'border-amber-500/30 bg-amber-500/5' : 'border-emerald-500/30 bg-emerald-500/5') : 'border-white/10 bg-white/[0.03] shadow-2xl'}
      backdrop-blur-2xl
    `}>
      {/* Glossy Overlay */}
      <div className="absolute inset-0 bg-gradient-to-tr from-white/5 to-transparent pointer-events-none" />

      {/* Progress Line */}
      {!isDone && (
        <div className="absolute top-0 left-0 right-0 h-0.5 bg-white/5 overflow-hidden">
          <div 
            className="h-full bg-gradient-to-r from-violet-600 to-fuchsia-400 shadow-[0_0_10px_rgba(139,92,246,0.6)] transition-all duration-1000 ease-out"
            style={{ width: `${pct}%` }}
          />
        </div>
      )}

      <div className="p-3 sm:p-4">
        {/* Header Section */}
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-3 min-w-0">
            <div className={`
              flex items-center justify-center w-8 h-8 rounded-xl shrink-0 transition-colors
              ${isDone ? (isError ? 'bg-amber-400/10 text-amber-400' : 'bg-emerald-400/10 text-emerald-400') : 'bg-violet-400/10 text-violet-400'}
            `}>
              {isDone ? (isError ? <AlertCircle size={18} /> : <CheckCircle2 size={18} />) : 
               isSynthesizing ? <Activity size={18} className="animate-pulse" /> : 
               isPlanning ? <ListChecks size={18} /> : <Bot size={18} className={!isDone ? 'animate-pulse' : ''} />}
            </div>
            
            <div className="min-w-0">
              <h3 className="text-xs font-bold text-text-primary tracking-tight truncate uppercase opacity-90">
                {headerLabel}
              </h3>
              {isExecuting && (
                <div className="flex items-center gap-2 mt-0.5">
                  <div className="h-1 w-12 bg-white/10 rounded-full overflow-hidden">
                    <div className="h-full bg-violet-400" style={{ width: `${(currentStep/totalSteps)*100}%` }} />
                  </div>
                  <span className="text-[9px] font-mono text-text-muted">STAGE_{currentStep}/{totalSteps}</span>
                </div>
              )}
            </div>
          </div>

          {hasPlan && (
            <button 
              onClick={() => setExpanded(!expanded)}
              className="p-1.5 rounded-lg hover:bg-white/5 text-text-muted transition-colors"
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
        </div>

        {/* Action Feed / Message */}
        {message && !isDone && <WorkLog message={message} />}

        {/* Reflection Node */}
        {reflection && (isExecuting || !isDone) && <ReflectionFeed reflection={reflection} />}

        {/* Execution Steps */}
        {hasPlan && (isExecuting || expanded) && (
          <div className="mt-4 space-y-1.5 border-t border-white/5 pt-4 animate-in fade-in slide-in-from-top-2 duration-300">
            {plan.map((step, idx) => {
              const stepResult = (results || []).find(r => r.step_index === idx) || results[idx];
              const stepCode = (codeBlocks || []).find(c => c.step_index === idx);
              const stepArtifacts = (artifacts || []).filter(a => a.step_index === idx);

              return (
                <StepRow
                  key={idx}
                  index={idx}
                  step={step}
                  result={stepResult || null}
                  isActive={isExecuting && (idx + 1) === currentStep}
                  isPending={(idx + 1) > currentStep}
                  codeBlock={stepCode}
                  artifacts={stepArtifacts}
                />
              );
            })}
            
            {isSynthesizing && (
              <div className="flex items-center gap-3 px-3 py-2 rounded-xl bg-violet-400/5 ring-1 ring-violet-400/20 mt-2">
                <div className="flex items-center justify-center w-5 h-5 rounded-md text-[10px] font-bold bg-violet-400/20 text-violet-400 shrink-0">
                  {plan.length + 1}
                </div>
                <p className="text-[11px] text-text-primary font-medium flex-1">Finalizing synthesis</p>
                <Sparkles size={14} className="text-violet-400 animate-pulse" />
              </div>
            )}
          </div>
        )}
      </div>

      {isDone && hasPlan && !expanded && (
        <div className="px-4 pb-3 flex gap-1 justify-center">
          {plan.map((_, i) => (
            <div key={i} className={`h-0.5 flex-1 rounded-full ${results[i]?.success === false ? 'bg-red-400/40' : 'bg-emerald-400/40'}`} />
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(AgentProgressPanel);

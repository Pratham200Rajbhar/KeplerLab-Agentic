'use client';

import { memo, useState } from 'react';
import {
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock3,
  Loader2,
  Search,
  Globe2,
  Code2,
  Sparkles,
} from 'lucide-react';

const TOOL_META = {
  rag: { icon: Search, label: 'Docs' },
  web_search: { icon: Globe2, label: 'Web' },
  research: { icon: Globe2, label: 'Research' },
  python_auto: { icon: Code2, label: 'Python' },
  llm: { icon: Sparkles, label: 'LLM' },
};

function statusTone(status) {
  if (status === 'completed') return 'text-emerald-300';
  if (status === 'completed_with_errors' || status === 'failed') return 'text-rose-300';
  if (status === 'running' || status === 'compiling' || status === 'starting') return 'text-amber-300';
  return 'text-text-secondary';
}

function StepRow({ step }) {
  const [expanded, setExpanded] = useState(false);
  const Icon = (TOOL_META[step.tool] || TOOL_META.llm).icon;
  const toolLabel = (TOOL_META[step.tool] || TOOL_META.llm).label;
  const hasBody = Boolean(step.content || step.error || step.reason);

  const marker = step.status === 'completed'
    ? <CheckCircle2 className="w-3.5 h-3.5 text-emerald-300" />
    : step.status === 'failed'
      ? <AlertTriangle className="w-3.5 h-3.5 text-rose-300" />
      : step.status === 'running'
        ? <Loader2 className="w-3.5 h-3.5 text-amber-300 animate-spin" />
        : step.status === 'skipped'
          ? <Clock3 className="w-3.5 h-3.5 text-text-muted" />
          : <span className="text-[10px] text-text-muted">{step.index}</span>;

  return (
    <div className="rounded-xl border border-border/60 bg-surface-overlay/45 overflow-hidden">
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full px-3 py-2.5 text-left flex items-start gap-2"
      >
        <div className="mt-0.5 shrink-0">{marker}</div>
        <div className="flex-1 min-w-0">
          <p className="text-[12px] text-text-primary leading-snug">{step.instruction || `Step ${step.index}`}</p>
          <div className="mt-1 flex items-center gap-1.5 text-[10px] text-text-muted">
            <Icon className="w-3 h-3" />
            <span>{toolLabel}</span>
            {step.elapsed ? <span>· {Number(step.elapsed).toFixed(1)}s</span> : null}
          </div>
        </div>
        {hasBody ? (
          expanded
            ? <ChevronDown className="w-3.5 h-3.5 text-text-muted mt-0.5 shrink-0" />
            : <ChevronRight className="w-3.5 h-3.5 text-text-muted mt-0.5 shrink-0" />
        ) : null}
      </button>

      {expanded && hasBody && (
        <div className="px-3 pb-3 border-t border-border/60">
          {step.content ? (
            <div className="mt-2 rounded-lg border border-border/60 bg-surface px-2.5 py-2 text-[11px] text-text-secondary whitespace-pre-wrap leading-relaxed">
              {step.content}
            </div>
          ) : null}
          {step.error ? (
            <div className="mt-2 rounded-lg border border-rose-300/30 bg-rose-500/10 px-2.5 py-2 text-[11px] text-rose-200">
              {step.error}
            </div>
          ) : null}
          {step.reason ? (
            <div className="mt-2 rounded-lg border border-amber-300/30 bg-amber-500/10 px-2.5 py-2 text-[11px] text-amber-100">
              {step.reason}
            </div>
          ) : null}
        </div>
      )}
    </div>
  );
}

function SkillProgressPanel({ skillState, isStreaming }) {
  const {
    skillTitle = 'Skill Run',
    status = 'running',
    message = '',
    progress = 0,
    plan = [],
    steps = [],
    artifacts = [],
    elapsed,
  } = skillState || {};

  const normalizedProgress = Math.max(0, Math.min(100, Number(progress) || 0));
  const isLive = isStreaming || !['completed', 'completed_with_errors', 'failed'].includes(status);

  const completedCount = steps.filter((s) => s.status === 'completed').length;

  return (
    <div className="mb-2.5 rounded-2xl border border-border bg-surface-raised/70 p-3.5">
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="text-[12px] font-semibold text-text-primary truncate">{skillTitle}</p>
          <p className={`text-[11px] mt-0.5 ${statusTone(status)}`}>
            {message || status.replaceAll('_', ' ')}
          </p>
        </div>
        <span className="text-[10px] text-text-muted shrink-0">
          {elapsed ? `${Number(elapsed).toFixed(1)}s` : `${completedCount}/${Math.max(steps.length, plan.length || 0)} steps`}
        </span>
      </div>

      {isLive && (
        <div className="mt-2 h-1.5 rounded-full bg-surface-overlay overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-amber-400 via-teal-400 to-sky-400 transition-all duration-500"
            style={{ width: `${Math.max(normalizedProgress, 3)}%` }}
          />
        </div>
      )}

      {plan.length > 0 && steps.length === 0 && (
        <div className="mt-2.5 rounded-lg border border-border/60 bg-surface-overlay/35 p-2.5">
          <p className="text-[10px] uppercase tracking-wide text-text-muted mb-1.5">Execution Plan</p>
          <div className="space-y-1">
            {plan.slice(0, 6).map((item) => (
              <div key={`${item.index}-${item.tool}`} className="text-[11px] text-text-secondary truncate">
                {item.index}. {item.instruction}
              </div>
            ))}
          </div>
        </div>
      )}

      {steps.length > 0 && (
        <div className="mt-2.5 space-y-1.5">
          {steps.map((step) => (
            <StepRow key={`${step.index}-${step.status}-${step.elapsed || ''}`} step={step} />
          ))}
        </div>
      )}

      {artifacts.length > 0 && (
        <div className="mt-2.5 text-[10px] text-text-muted">
          {artifacts.length} artifact{artifacts.length === 1 ? '' : 's'} generated
        </div>
      )}
    </div>
  );
}

export default memo(SkillProgressPanel);

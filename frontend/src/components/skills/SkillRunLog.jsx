'use client';

import { useState, useEffect } from 'react';
import {
  CheckCircle2, XCircle, Clock, Loader2,
  ChevronDown, ChevronRight, Search, Globe2, Code2, Zap,
} from 'lucide-react';
import useSkillStore from '@/stores/useSkillStore';

const TOOL_META = {
  rag: { icon: Search, label: 'RAG Search', color: 'var(--accent)' },
  web_search: { icon: Globe2, label: 'Web Search', color: '#38bdf8' },
  research: { icon: Globe2, label: 'Deep Research', color: '#818cf8' },
  python_auto: { icon: Code2, label: 'Python Auto', color: '#a78bfa' },
  llm: { icon: Zap, label: 'LLM', color: '#fbbf24' },
};

export default function SkillRunLog({ runId, onBack }) {
  const loadRunDetail = useSkillStore((s) => s.loadRunDetail);
  // `undefined` means loading, `null` means not found.
  const [run, setRun] = useState(undefined);
  const [expandedSteps, setExpandedSteps] = useState({});

  useEffect(() => {
    if (!runId) return;
    let cancelled = false;

    loadRunDetail(runId).then((data) => {
      if (!cancelled) {
        setRun(data ?? null);
      }
    });

    return () => {
      cancelled = true;
    };
  }, [runId, loadRunDetail]);

  if (run === undefined) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-5 h-5 animate-spin text-text-muted" />
      </div>
    );
  }

  if (!run) {
    return (
      <div className="text-center py-8">
        <XCircle className="w-5 h-5 text-text-muted mx-auto mb-2" />
        <p className="text-[12px] text-text-muted">Run not found</p>
      </div>
    );
  }

  const steps = run.step_logs || [];

  return (
    <div className="flex-1 overflow-y-auto p-4 custom-scrollbar">
      {/* Run Header */}
      <div className="skills-runlog-header p-4 rounded-xl mb-4">
        <div className="flex items-center justify-between mb-2">
          <h4 className="text-[14px] font-bold text-text-primary">{run.skill_title}</h4>
          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
            run.status === 'completed' ? 'skills-run-status-ok' :
            run.status === 'failed' ? 'skills-run-status-fail' :
            'skills-run-status-pending'
          }`}>
            {run.status}
          </span>
        </div>
        <div className="flex flex-wrap items-center gap-3 text-[11px] text-text-muted">
          <span className="flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {new Date(run.created_at).toLocaleString()}
          </span>
          {run.elapsed_time > 0 && (
            <span>{run.elapsed_time.toFixed(1)}s total</span>
          )}
          <span>{steps.length} steps</span>
        </div>

        {/* Variables */}
        {run.variables && Object.keys(run.variables).length > 0 && (
          <div className="mt-3">
            <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Variables</h5>
            <div className="flex flex-wrap gap-1.5">
              {Object.entries(run.variables).map(([k, v]) => (
                <span key={k} className="skills-var-badge text-[10px] px-2 py-0.5 rounded font-mono">
                  {k}={String(v).slice(0, 40)}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Timeline */}
      {steps.length > 0 && (
        <div className="space-y-1.5">
          <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">Execution Timeline</h5>
          {steps.map((step, idx) => {
            const meta = TOOL_META[step.tool] || TOOL_META.llm;
            const Icon = meta.icon;
            const isExpanded = expandedSteps[idx];
            const skipped = step.skipped === true;
            const success = skipped || step.success === true || (step.success === undefined && !step.error);

            return (
              <div key={idx} className="skills-runlog-step rounded-xl overflow-hidden">
                <button
                  onClick={() => setExpandedSteps((p) => ({ ...p, [idx]: !p[idx] }))}
                  className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left hover:bg-surface-raised/50 transition-colors"
                >
                  <div className={`w-5 h-5 rounded flex items-center justify-center shrink-0 ${
                    skipped ? 'skills-step-pending' : (success ? 'skills-step-ok' : 'skills-step-fail')
                  }`}>
                    {skipped ? (
                      <Clock className="w-3 h-3" />
                    ) : success ? (
                      <CheckCircle2 className="w-3 h-3" />
                    ) : (
                      <XCircle className="w-3 h-3" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-[11px] text-text-primary font-medium truncate">{step.instruction}</p>
                    <div className="flex items-center gap-1.5 mt-0.5">
                      <Icon className="w-3 h-3" style={{ color: meta.color }} />
                      <span className="text-[9px] font-bold" style={{ color: meta.color }}>{meta.label}</span>
                      {step.elapsed_seconds && (
                        <span className="text-[9px] text-text-muted">{step.elapsed_seconds.toFixed(1)}s</span>
                      )}
                    </div>
                  </div>
                  {isExpanded ? <ChevronDown className="w-3 h-3 text-text-muted" /> : <ChevronRight className="w-3 h-3 text-text-muted" />}
                </button>

                {isExpanded && (
                  <div className="px-3 pb-3">
                    {step.content && (
                      <div className="skills-step-output p-3 rounded-lg text-[11px] text-text-secondary whitespace-pre-wrap max-h-[200px] overflow-y-auto custom-scrollbar">
                        {step.content}
                      </div>
                    )}
                    {step.error && (
                      <div className="skills-step-error mt-2 p-2.5 rounded-lg text-[11px] text-red-300">
                        Error: {step.error}
                      </div>
                    )}
                    {step.skip_reason && (
                      <div className="skills-step-error mt-2 p-2.5 rounded-lg text-[11px] text-amber-200">
                        Skipped: {step.skip_reason}
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Error */}
      {run.error && (
        <div className="skills-step-error mt-4 p-3 rounded-xl text-[12px] text-red-300">
          {run.error}
        </div>
      )}
    </div>
  );
}

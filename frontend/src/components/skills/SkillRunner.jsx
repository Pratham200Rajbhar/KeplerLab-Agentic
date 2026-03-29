'use client';

import { useState, useCallback } from 'react';
import {
  Play, Loader2, CheckCircle2, XCircle, AlertTriangle,
  Clock, Search, Globe2, Code2, Zap, ChevronDown, ChevronRight,
  Download, RotateCcw,
} from 'lucide-react';
import useSkillStore from '@/stores/useSkillStore';
import { useToast } from '@/stores/useToastStore';

const TOOL_META = {
  rag: { icon: Search, label: 'RAG Search', color: 'var(--accent)' },
  web_search: { icon: Globe2, label: 'Web Search', color: '#38bdf8' },
  research: { icon: Globe2, label: 'Deep Research', color: '#818cf8' },
  python_auto: { icon: Code2, label: 'Python Auto', color: '#a78bfa' },
  llm: { icon: Zap, label: 'LLM Reasoning', color: '#fbbf24' },
};

function StepItem({ step, isExpanded, onToggle }) {
  const meta = TOOL_META[step.tool] || TOOL_META.llm;
  const Icon = meta.icon;
  const hasDetails = Boolean(step.content || step.error || step.reason);

  return (
    <div className="skills-step-item rounded-xl overflow-hidden transition-all">
      <button
        onClick={onToggle}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 text-left transition-colors hover:bg-surface-raised/50"
      >
        <div className={`skills-step-status w-6 h-6 rounded-lg flex items-center justify-center shrink-0 ${
          step.status === 'completed' ? 'skills-step-ok' :
          step.status === 'failed' ? 'skills-step-fail' :
          step.status === 'skipped' ? 'skills-step-pending' :
          step.status === 'running' ? 'skills-step-running' :
          'skills-step-pending'
        }`}>
          {step.status === 'running' ? (
            <Loader2 className="w-3 h-3 animate-spin" />
          ) : step.status === 'completed' ? (
            <CheckCircle2 className="w-3 h-3" />
          ) : step.status === 'failed' ? (
            <XCircle className="w-3 h-3" />
          ) : step.status === 'skipped' ? (
            <AlertTriangle className="w-3 h-3" />
          ) : (
            <span className="text-[10px] font-bold">{step.index}</span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[12px] text-text-primary font-medium truncate">{step.instruction}</p>
          <div className="flex items-center gap-1.5 mt-0.5">
            <Icon className="w-3 h-3" style={{ color: meta.color }} />
            <span className="text-[10px] font-semibold" style={{ color: meta.color }}>{meta.label}</span>
            {step.elapsed && (
              <span className="text-[10px] text-text-muted">· {step.elapsed.toFixed(1)}s</span>
            )}
          </div>
        </div>

        {hasDetails && (
          isExpanded ? <ChevronDown className="w-3.5 h-3.5 text-text-muted shrink-0" /> : <ChevronRight className="w-3.5 h-3.5 text-text-muted shrink-0" />
        )}
      </button>

      {isExpanded && hasDetails && (
        <div className="skills-step-content px-3 pb-3">
          {step.content && (
            <div className="skills-step-output p-3 rounded-lg text-[11px] text-text-secondary leading-relaxed whitespace-pre-wrap max-h-[200px] overflow-y-auto custom-scrollbar">
              {step.content}
            </div>
          )}
          {step.error && (
            <div className="skills-step-error mt-2 p-2 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
              <p className="text-[11px] text-red-300">{step.error}</p>
            </div>
          )}
          {step.reason && (
            <div className="skills-step-error mt-2 p-2 rounded-lg flex items-start gap-2">
              <AlertTriangle className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
              <p className="text-[11px] text-amber-200">{step.reason}</p>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function SkillRunner({ skill, notebookId, materialIds = [], onBack }) {
  const toast = useToast();
  const currentRun = useSkillStore((s) => s.currentRun);
  const isRunning = useSkillStore((s) => s.isRunning);
  const executeSkill = useSkillStore((s) => s.executeSkill);
  const clearRun = useSkillStore((s) => s.clearRun);

  const [variables, setVariables] = useState(() => {
    const vars = {};
    skill?.parsed?.inputs?.forEach((inp) => {
      vars[inp.name] = inp.default_value || '';
    });
    return vars;
  });
  const [streamToChat, setStreamToChat] = useState(true);
  const [expandedSteps, setExpandedSteps] = useState({});

  const handleRun = useCallback(async () => {
    if (!skill?.id) return;

    // Validate required variables
    const missing = Object.entries(variables)
      .filter(([_, v]) => !v.trim())
      .map(([k]) => k);

    if (missing.length > 0) {
      toast.error(`Please fill in: ${missing.join(', ')}`);
      return;
    }

    try {
      await executeSkill(skill.id, {
        variables,
        notebookId,
        materialIds,
        streamToChat,
      });
    } catch (err) {
      toast.error(err.message || 'Execution failed');
    }
  }, [skill, variables, notebookId, materialIds, streamToChat, executeSkill, toast]);

  const toggleStep = useCallback((index) => {
    setExpandedSteps((prev) => ({ ...prev, [index]: !prev[index] }));
  }, []);

  const hasStarted = currentRun && currentRun.status !== 'starting';

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Variable Inputs */}
      {!hasStarted && skill?.parsed?.inputs?.length > 0 && (
        <div className="skills-runner-inputs px-4 py-3 border-b border-border shrink-0">
          <h4 className="text-[11px] font-bold text-text-muted uppercase tracking-wider mb-2.5">Input Variables</h4>
          <div className="space-y-2">
            {skill.parsed.inputs.map((inp) => (
              <div key={inp.name}>
                <label className="text-[11px] text-text-secondary font-medium mb-1 block">
                  {inp.name}
                  {inp.description && (
                    <span className="text-text-muted font-normal ml-1">({inp.description})</span>
                  )}
                </label>
                <input
                  type="text"
                  value={variables[inp.name] || ''}
                  onChange={(e) => setVariables((v) => ({ ...v, [inp.name]: e.target.value }))}
                  placeholder={`Enter ${inp.name}...`}
                  className="skills-runner-input w-full px-3 py-2 rounded-lg text-[12px] outline-none transition-all"
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Run Button */}
      {!hasStarted && (
        <div className="px-4 py-3 shrink-0">
          <label className="flex items-center justify-between gap-2 mb-2.5 text-[11px] text-text-secondary">
            <span>Mirror live progress in chat panel</span>
            <input
              type="checkbox"
              checked={streamToChat}
              onChange={(e) => setStreamToChat(e.target.checked)}
              className="skills-checkbox w-3.5 h-3.5 rounded"
            />
          </label>
          <button
            onClick={handleRun}
            disabled={isRunning}
            className="skills-run-btn w-full py-3 px-4 rounded-xl font-semibold flex items-center justify-center gap-2 transition-all disabled:opacity-50"
          >
            {isRunning ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Starting...</>
            ) : (
              <><Play className="w-4 h-4" /> Execute Skill</>
            )}
          </button>
        </div>
      )}

      {/* Execution Progress */}
      {currentRun && (
        <div className="flex-1 overflow-y-auto px-4 py-3 custom-scrollbar">
          {/* Status Header */}
          <div className="skills-run-header flex items-center justify-between mb-3 p-3 rounded-xl">
            <div className="flex items-center gap-2">
              {currentRun.status === 'completed' || currentRun.status === 'completed_with_errors' ? (
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
              ) : currentRun.status === 'failed' ? (
                <XCircle className="w-4 h-4 text-red-400" />
              ) : (
                <Loader2 className="w-4 h-4 text-accent animate-spin" />
              )}
              <span className="text-[12px] font-semibold text-text-primary capitalize">
                {currentRun.message || currentRun.status}
              </span>
            </div>
            {currentRun.elapsed && (
              <span className="text-[10px] text-text-muted flex items-center gap-1">
                <Clock className="w-3 h-3" /> {currentRun.elapsed.toFixed(1)}s
              </span>
            )}
          </div>

          {/* Progress Bar */}
          {isRunning && (
            <div className="skills-progress-bar mb-4 h-1.5 rounded-full overflow-hidden">
              <div
                className="skills-progress-fill h-full rounded-full transition-all duration-700 ease-out"
                style={{ width: `${Math.max(currentRun.progress || 0, 3)}%` }}
              />
            </div>
          )}

          {/* Plan Preview */}
          {currentRun.plan?.length > 0 && currentRun.steps?.length === 0 && (
            <div className="mb-3">
              <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">Execution Plan</h5>
              {currentRun.plan.map((p, i) => {
                const meta = TOOL_META[p.tool] || TOOL_META.llm;
                return (
                  <div key={i} className="flex items-center gap-2 py-1.5 text-[11px] text-text-secondary">
                    <span className="text-accent font-bold w-4">{p.index}</span>
                    <span className="truncate flex-1">{p.instruction}</span>
                    <span className="text-[9px] font-bold uppercase shrink-0" style={{ color: meta.color }}>{p.tool}</span>
                  </div>
                );
              })}
            </div>
          )}

          {/* Steps */}
          {currentRun.steps?.length > 0 && (
            <div className="space-y-1.5">
              {currentRun.steps.map((step) => (
                <StepItem
                  key={step.index}
                  step={step}
                  isExpanded={expandedSteps[step.index]}
                  onToggle={() => toggleStep(step.index)}
                />
              ))}
            </div>
          )}

          {/* Artifacts */}
          {currentRun.artifacts?.length > 0 && (
            <div className="mt-4">
              <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">Artifacts</h5>
              {currentRun.artifacts.map((art, i) => (
                <div key={i} className="skills-artifact flex items-center gap-2 p-2 rounded-lg mb-1">
                  <Download className="w-3.5 h-3.5 text-accent" />
                  <span className="text-[11px] text-text-primary">{art.filename || `Artifact ${i + 1}`}</span>
                </div>
              ))}
            </div>
          )}

          {/* Final Output */}
          {currentRun.finalOutput && !isRunning && (
            <div className="mt-4">
              <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-2">Final Output</h5>
              <div className="skills-final-output p-3 rounded-xl text-[12px] text-text-secondary leading-relaxed whitespace-pre-wrap max-h-[300px] overflow-y-auto custom-scrollbar">
                {currentRun.finalOutput}
              </div>
            </div>
          )}

          {/* Re-run / Back */}
          {!isRunning && currentRun.status && currentRun.status !== 'starting' && (
            <div className="flex items-center gap-2 mt-4">
              <button
                onClick={() => { clearRun(); }}
                className="skills-btn-secondary flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[12px] font-medium"
              >
                <RotateCcw className="w-3.5 h-3.5" /> Run Again
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

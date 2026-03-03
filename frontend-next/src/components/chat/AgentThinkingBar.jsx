'use client';

import { memo, useEffect, useRef, useState } from 'react';

const STEP_ICONS = {
  rag_tool: '🔍', research_tool: '🌐', python_tool: '🐍', data_profiler: '🧠',
  quiz_tool: '📝', flashcard_tool: '🃏', ppt_tool: '📊', file_generator: '📄',
  code_repair: '🔧', default: '⚡',
};

function getStepIcon(label = '') {
  const key = Object.keys(STEP_ICONS).find(k => label.toLowerCase().includes(k));
  return STEP_ICONS[key] || STEP_ICONS.default;
}

export default memo(function AgentThinkingBar({
  isActive, currentStep, stepNumber, totalSteps, isRepair = false, repairCount = 0,
}) {
  const [elapsed, setElapsed] = useState(0);
  const startRef = useRef(Date.now());
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isActive) { setElapsed(0); return; }
    startRef.current = Date.now();
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed(Math.floor((Date.now() - startRef.current) / 1000)), 1000);
    return () => clearInterval(timerRef.current);
  }, [isActive]);

  if (!isActive) return null;

  const icon = getStepIcon(currentStep || '');
  const elapsedStr = elapsed > 0 ? `${elapsed}s` : '';

  return (
    <div className={`flex items-center gap-3 px-4 py-3 mb-2 rounded-2xl border animate-fade-in ${
      isRepair ? 'bg-amber-500/5 border-amber-500/25 dark:bg-amber-500/8' : 'bg-accent/5 border-accent/20'}`}>
      {isRepair ? (
        <span className="text-base shrink-0 animate-pulse">🔧</span>
      ) : (
        <div className="relative w-5 h-5 shrink-0">
          <div className="absolute inset-0 rounded-full border-2 border-accent/20" />
          <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-accent" style={{ animation: 'spin 0.8s linear infinite' }} />
        </div>
      )}
      <span className="flex items-center gap-1.5 text-sm flex-1 min-w-0">
        <span className="shrink-0">{icon}</span>
        <span className={`truncate ${isRepair ? 'text-amber-600 dark:text-amber-400' : 'text-text-secondary'}`}>
          {isRepair ? `Fixing error (attempt ${repairCount})…` : (currentStep || 'Thinking…')}
        </span>
      </span>
      <div className="flex items-center gap-2 shrink-0">
        {stepNumber > 0 && (
          <span className="text-xs font-medium px-2 py-0.5 rounded-full bg-surface-overlay text-text-muted tabular-nums">Step {stepNumber}</span>
        )}
        {elapsedStr && <span className="text-xs text-text-muted tabular-nums">{elapsedStr}</span>}
      </div>
    </div>
  );
});

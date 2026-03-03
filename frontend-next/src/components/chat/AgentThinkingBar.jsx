'use client';

import { memo, useEffect, useRef, useState } from 'react';

const TOOL_LABELS = {
  rag_tool:       'Searching your materials',
  research_tool:  'Researching the web',
  python_tool:    'Running code',
  data_profiler:  'Analyzing data',
  quiz_tool:      'Generating quiz',
  flashcard_tool: 'Creating flashcards',
  ppt_tool:       'Building slides',
  code_repair:    'Fixing error',
};

const THINKING_CYCLE = ['Thinking', 'Processing', 'Analyzing', 'Working'];

function resolveLabel(step, isRepair, repairCount) {
  if (isRepair) return `Fixing error (attempt ${repairCount})`;
  if (!step) return null;
  const key = Object.keys(TOOL_LABELS).find(k => step.toLowerCase().includes(k));
  return key ? TOOL_LABELS[key] : step;
}

export default memo(function AgentThinkingBar({
  isActive, currentStep, stepNumber, totalSteps, isRepair = false, repairCount = 0,
}) {
  const [cycleIdx, setCycleIdx] = useState(0);
  const timerRef = useRef(null);

  useEffect(() => {
    if (!isActive || currentStep) { clearInterval(timerRef.current); return; }
    setCycleIdx(0);
    timerRef.current = setInterval(() => setCycleIdx(i => (i + 1) % THINKING_CYCLE.length), 1800);
    return () => clearInterval(timerRef.current);
  }, [isActive, currentStep]);

  if (!isActive) return null;

  const label = resolveLabel(currentStep, isRepair, repairCount) || THINKING_CYCLE[cycleIdx];

  return (
    <div className="flex items-center gap-1.5 px-1 pb-2 animate-fade-in">
      <span className="flex gap-0.5 items-end h-3 shrink-0">
        <span className="w-0.5 h-1.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '0ms' }} />
        <span className="w-0.5 h-2.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '150ms' }} />
        <span className="w-0.5 h-1.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '300ms' }} />
      </span>
      <span className={`text-xs transition-all duration-500 ${isRepair ? 'text-amber-500' : 'text-text-muted'}`}>
        {label}…
      </span>
    </div>
  );
});

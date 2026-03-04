'use client';

import { memo, useEffect, useRef, useState } from 'react';
import {
  Search,
  Code2,
  Globe,
  FileDown,
  Layers,
  HelpCircle,
  GitFork,
  Presentation,
  Wrench,
  Brain,
  Sparkles,
} from 'lucide-react';

/**
 * Map tool names to lucide-react icons
 */
const TOOL_ICONS = {
  rag_tool:             Search,
  rag_search:           Search,
  research_tool:        Globe,
  web_search:           Globe,
  web_research_tool:    Globe,
  python_tool:          Code2,
  python_executor:      Code2,
  code_generation_tool: Code2,
  data_profiler:        Brain,
  file_generator:       FileDown,
  flashcard_tool:       Layers,
  flashcard_gen:        Layers,
  quiz_tool:            HelpCircle,
  quiz_gen:             HelpCircle,
  mindmap_gen:          GitFork,
  ppt_tool:             Presentation,
  ppt_gen:              Presentation,
  code_repair:          Wrench,
  agent_task_tool:      Sparkles,
};

const TOOL_LABELS = {
  rag_tool:             'Searching materials',
  research_tool:        'Researching the web',
  python_tool:          'Running code',
  data_profiler:        'Analyzing data',
  quiz_tool:            'Generating quiz',
  flashcard_tool:       'Creating flashcards',
  ppt_tool:             'Building slides',
  code_repair:          'Fixing error',
  agent_task_tool:      'Executing task',
  web_research_tool:    'Deep searching',
  code_generation_tool: 'Generating code',
};

const THINKING_CYCLE = ['Thinking', 'Processing', 'Analyzing', 'Working'];

function resolveToolKey(step) {
  if (!step) return null;
  return Object.keys(TOOL_LABELS).find((k) => step.toLowerCase().includes(k)) || null;
}

function resolveLabel(step, isRepair, repairCount) {
  if (isRepair) return `Fixing error (attempt ${repairCount})`;
  if (!step) return null;
  const key = resolveToolKey(step);
  return key ? TOOL_LABELS[key] : step;
}

function formatElapsed(ms) {
  const secs = Math.floor(ms / 1000);
  if (secs < 60) return `${secs}s`;
  const mins = Math.floor(secs / 60);
  const rem = secs % 60;
  return `${mins}m ${rem}s`;
}

export default memo(function AgentThinkingBar({
  isActive,
  currentStep,
  stepNumber,
  totalSteps,
  isRepair = false,
  repairCount = 0,
}) {
  const [cycleIdx, setCycleIdx] = useState(0);
  const [elapsed, setElapsed] = useState(0);
  const cycleTimerRef = useRef(null);
  const elapsedTimerRef = useRef(null);
  const startTimeRef = useRef(null);

  // Cycle through "Thinking..." labels when no step
  useEffect(() => {
    if (!isActive || currentStep) {
      clearInterval(cycleTimerRef.current);
      return;
    }
    const resetTimer = setTimeout(() => setCycleIdx(0), 0);
    cycleTimerRef.current = setInterval(
      () => setCycleIdx((i) => (i + 1) % THINKING_CYCLE.length),
      1800,
    );
    return () => {
      clearTimeout(resetTimer);
      clearInterval(cycleTimerRef.current);
    };
  }, [isActive, currentStep]);

  // Elapsed time counter
  useEffect(() => {
    if (isActive) {
      startTimeRef.current = Date.now();
      elapsedTimerRef.current = setInterval(() => {
        setElapsed(Date.now() - startTimeRef.current);
      }, 100);
    } else {
      clearInterval(elapsedTimerRef.current);
    }
    return () => clearInterval(elapsedTimerRef.current);
  }, [isActive]);

  if (!isActive) return null;

  const label = resolveLabel(currentStep, isRepair, repairCount) || THINKING_CYCLE[cycleIdx];
  const toolKey = resolveToolKey(currentStep);
  const ToolIcon = toolKey ? TOOL_ICONS[toolKey] : Sparkles;
  const statusText = isRepair ? 'repairing' : 'running';

  return (
    <div className="flex items-center gap-2 px-1 pb-2 animate-fade-in">
      {/* Animated status pill */}
      <div
        className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium border transition-all duration-300 ${
          isRepair
            ? 'bg-amber-500/10 text-amber-400 border-amber-500/20'
            : 'bg-accent/10 text-accent border-accent/20'
        }`}
      >
        {/* Tool icon */}
        {ToolIcon && <ToolIcon className="w-3.5 h-3.5 shrink-0" />}

        {/* Tool name */}
        <span className="truncate max-w-[180px]">{label}</span>

        {/* Separator */}
        <span className="text-text-muted/30">·</span>

        {/* Status */}
        <span className="text-text-muted text-[11px]">{statusText}</span>

        {/* Separator */}
        <span className="text-text-muted/30">·</span>

        {/* Elapsed time */}
        <span className="text-text-muted text-[11px] tabular-nums">
          {formatElapsed(elapsed)}
        </span>

        {/* Pulsing dot */}
        <span
          className="w-1.5 h-1.5 rounded-full shrink-0"
          style={{
            backgroundColor: isRepair ? 'rgb(245 158 11)' : 'var(--accent)',
            animation: 'agent-pulse 1.5s ease-in-out infinite',
          }}
        />
      </div>

      <style jsx>{`
        @keyframes agent-pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.3; }
        }
      `}</style>
    </div>
  );
});

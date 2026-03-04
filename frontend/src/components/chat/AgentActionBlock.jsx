'use client';

import { useState, memo, createElement } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  Search, Globe, Code2, Brain, FileDown, Layers,
  HelpCircle, Presentation, Wrench, Sparkles, ChevronDown,
} from 'lucide-react';

/* ─────────────────────────────────────────────────────
   Redesigned AgentActionBlock:
   - Collapsible cards with status badges
   - Grouped under a single "Agent Run" parent block
   - Failed steps → red left border
   - CSS max-height transition (no Framer Motion)
───────────────────────────────────────────────────── */

const TOOL_ICONS = {
  rag_tool:             Search,
  research_tool:        Globe,
  web_research_tool:    Globe,
  python_tool:          Code2,
  code_generation_tool: Code2,
  code_executor:        Code2,
  data_profiler:        Brain,
  file_generator:       FileDown,
  flashcard_tool:       Layers,
  quiz_tool:            HelpCircle,
  ppt_tool:             Presentation,
  code_repair:          Wrench,
  agent_task_tool:      Sparkles,
};

const TOOL_META = {
  rag_tool:             'Searching materials',
  research_tool:        'Researching the web',
  python_tool:          'Running analysis',
  quiz_tool:            'Generating quiz',
  flashcard_tool:       'Creating flashcards',
  ppt_tool:             'Building slides',
  data_profiler:        'Profiling dataset',
  file_generator:       'Generating file',
  code_executor:        'Executing code',
  agent_task_tool:      'Executing task',
  web_research_tool:    'Researching (structured)',
  code_generation_tool: 'Generating code',
  code_repair:          'Fixing error',
};

function getToolLabel(tool) {
  return TOOL_META[tool] || (tool ? tool.replace(/_/g, ' ') : 'Processing');
}

function getToolIcon(tool) {
  return TOOL_ICONS[tool] || Sparkles;
}

const STATUS_STYLES = {
  running: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  done:    'bg-green-500/20 text-green-400 border-green-500/30',
  success: 'bg-green-500/20 text-green-400 border-green-500/30',
  error:   'bg-red-500/20 text-red-400 border-red-500/30',
  failed:  'bg-red-500/20 text-red-400 border-red-500/30',
};

function StatusBadge({ status }) {
  const normalized = (status || 'done').toLowerCase();
  const label = normalized === 'success' ? 'done' : normalized;
  const style = STATUS_STYLES[normalized] || STATUS_STYLES.done;
  return (
    <span
      className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium border ${style}`}
      title={label}
    >
      {label}
    </span>
  );
}

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="text-[11px] px-2 py-0.5 rounded bg-surface-overlay hover:bg-surface-raised text-text-muted hover:text-text-secondary transition-all tabular-nums"
      aria-label="Copy to clipboard"
    >
      {copied ? '✓ copied' : 'copy'}
    </button>
  );
}

/**
 * A single collapsible step card.
 */
function StepCard({ step, index }) {
  const [isOpen, setIsOpen] = useState(false);
  const isError = step.status === 'error' || step.status === 'failed';
  const hasContent = !!(step.code || step.stdout || step.stderr || step.result_summary);
  const toolIcon = getToolIcon(step.tool);
  const label = getToolLabel(step.tool);
  const attempts = step._attempts || 1;

  return (
    <div
      className={`rounded-lg border transition-all duration-200 ${
        isError ? 'border-l-2 border-l-red-500 border-border/20' : 'border-border/20'
      }`}
    >
      {/* Card header */}
      <button
        onClick={() => hasContent && setIsOpen((v) => !v)}
        className={`w-full flex items-center gap-2 px-3 py-2 text-left transition-colors ${
          hasContent ? 'cursor-pointer hover:bg-surface-overlay/30' : 'cursor-default'
        }`}
        aria-expanded={isOpen}
        aria-label={`Step ${index + 1}: ${label}`}
      >
        {createElement(toolIcon, { className: 'w-3.5 h-3.5 shrink-0 text-text-muted' })}
        <span className="text-[13px] text-text-secondary font-medium flex-1 min-w-0 truncate">
          Step {index + 1}: {label}
        </span>
        {attempts > 1 && (
          <span className="text-[10px] tabular-nums text-text-muted/50">×{attempts}</span>
        )}
        <span className="text-text-muted text-[11px] flex items-center gap-2">
          <span className="mr-1">{step.tool}</span>
          <StatusBadge status={step.status} />
        </span>
        {step.time_taken != null && (
          <span className="text-[11px] tabular-nums text-text-muted/50 shrink-0">
            {step.time_taken}s
          </span>
        )}
        {hasContent && (
          <ChevronDown
            className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 shrink-0 ${
              isOpen ? 'rotate-180' : ''
            }`}
          />
        )}
      </button>

      {/* Collapsible content with CSS max-height transition */}
      <div
        className="overflow-hidden transition-[max-height] duration-300 ease-in-out"
        style={{ maxHeight: isOpen ? '600px' : '0px' }}
      >
        <div className="px-3 pb-3 space-y-1.5 border-t border-border/10">
          {step.result_summary && (
            <p className="text-xs text-text-muted mt-2">{step.result_summary}</p>
          )}
          {step.code && (
            <div className="rounded-lg overflow-hidden border border-border/20 mt-2">
              <div className="flex items-center justify-between px-2.5 py-1 border-b border-border/20">
                <span className="text-[10px] text-text-muted uppercase tracking-wide">code</span>
                <CopyBtn text={step.code} />
              </div>
              <div className="max-h-48 overflow-y-auto">
                <SyntaxHighlighter
                  language="python"
                  style={oneDark}
                  customStyle={{ margin: 0, padding: '8px 10px', fontSize: '11px', lineHeight: '1.6', background: 'var(--surface-sunken)' }}
                >
                  {step.code}
                </SyntaxHighlighter>
              </div>
            </div>
          )}
          {step.stdout && (
            <pre className="text-[11px] font-mono p-2 rounded-lg bg-surface/60 border border-border/20 max-h-32 overflow-y-auto whitespace-pre-wrap text-text-muted">
              {step.stdout}
            </pre>
          )}
          {step.stderr && (
            <pre className="text-[11px] font-mono p-2 rounded-lg bg-red-500/5 border border-red-500/15 max-h-28 overflow-y-auto whitespace-pre-wrap text-red-400">
              {step.stderr}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
}

export default memo(function AgentActionBlock({ stepLog = [], toolsUsed = [], totalTime = 0, isStreaming = false }) {
  const [isParentOpen, setIsParentOpen] = useState(false);

  if (!stepLog.length && !toolsUsed.length) return null;
  if (isStreaming) return null;

  const timeStr = totalTime > 0 ? `${totalTime.toFixed(1)}s` : '';

  /* Collapse consecutive same-tool attempts into a single row */
  const collapsed = [];
  for (const step of stepLog) {
    const prev = collapsed[collapsed.length - 1];
    if (prev && prev.tool === step.tool) {
      const attempts = (prev._attempts || 1) + 1;
      collapsed[collapsed.length - 1] = { ...step, _attempts: attempts };
    } else {
      collapsed.push({ ...step, _attempts: 1 });
    }
  }

  const errorCount = collapsed.filter((s) => s.status === 'error' || s.status === 'failed').length;

  return (
    <div className="mb-3">
      {/* Agent Run parent block — collapsible */}
      <button
        onClick={() => setIsParentOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 rounded-lg bg-surface-overlay/30 hover:bg-surface-overlay/50 transition-colors cursor-pointer text-left"
        aria-expanded={isParentOpen}
        aria-label={`Agent Run — ${collapsed.length} steps`}
      >
        <Sparkles className="w-3.5 h-3.5 text-accent shrink-0" />
        <span className="text-[13px] font-medium text-text-secondary flex-1">
          Agent Run
        </span>
        <span className="text-[11px] text-text-muted tabular-nums">
          {collapsed.length} step{collapsed.length !== 1 ? 's' : ''}
        </span>
        {errorCount > 0 && (
          <span className="text-[11px] text-red-400">{errorCount} failed</span>
        )}
        {timeStr && (
          <span className="text-[11px] tabular-nums text-text-muted/50">{timeStr}</span>
        )}
        <ChevronDown
          className={`w-3.5 h-3.5 text-text-muted transition-transform duration-200 shrink-0 ${
            isParentOpen ? 'rotate-180' : ''
          }`}
        />
      </button>

      {/* Individual step cards */}
      <div
        className="overflow-hidden transition-[max-height] duration-300 ease-in-out"
        style={{ maxHeight: isParentOpen ? `${collapsed.length * 300 + 100}px` : '0px' }}
      >
        <div className="mt-1.5 space-y-1.5 pl-2">
          {collapsed.map((step, idx) => (
            <StepCard key={step.id || idx} step={step} index={idx} />
          ))}
        </div>
      </div>
    </div>
  );
});

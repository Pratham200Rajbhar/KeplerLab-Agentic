'use client';

import { useState, memo, useEffect } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

/* ─────────────────────────────────────────────────────
   Minimal, animated step display.
   – During streaming: animated cycling text (no boxes)
   – After done: one clean line per step with icon + label + time
   – Python/code steps get a subtle collapsible output block
───────────────────────────────────────────────────── */

const TOOL_META = {
  rag_tool:       { icon: '🔍', label: 'Searching your materials' },
  research_tool:  { icon: '🌐', label: 'Researching the web' },
  python_tool:    { icon: '🐍', label: 'Running analysis' },
  quiz_tool:      { icon: '📝', label: 'Generating quiz' },
  flashcard_tool: { icon: '🃏', label: 'Creating flashcards' },
  ppt_tool:       { icon: '📊', label: 'Building slides' },
  data_profiler:  { icon: '🧠', label: 'Profiling dataset' },
  file_generator: { icon: '📄', label: 'Generating file' },
  code_executor:  { icon: '⚙️', label: 'Executing code' },
};

function getToolMeta(tool) {
  return TOOL_META[tool] || { icon: '⚡', label: tool ? tool.replace(/_/g, ' ') : 'Processing' };
}

function CopyBtn({ text }) {
  const [copied, setCopied] = useState(false);
  return (
    <button
      onClick={async () => { await navigator.clipboard.writeText(text); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      className="text-[11px] px-2 py-0.5 rounded bg-surface-overlay hover:bg-surface-raised text-text-muted hover:text-text-secondary transition-all tabular-nums"
    >
      {copied ? '✓ copied' : 'copy'}
    </button>
  );
}

/* A single completed step row — simple text line, no boxes */
function StepRow({ step, idx }) {
  const [showCode, setShowCode] = useState(false);
  const meta = getToolMeta(step.tool);
  const isCode = !!(step.code || step.stdout);
  const isError = step.status === 'error';
  const attempts = step._attempts || 1;

  return (
    <div className="py-0.5">
      <div className="flex items-center gap-2">
        <span className="text-xs shrink-0" aria-hidden>{meta.icon}</span>
        <span className={`text-[13px] ${
          isError ? 'text-red-400' : 'text-text-muted'
        }`}>
          {meta.label}
        </span>
        {attempts > 1 && (
          <span className="text-[11px] tabular-nums text-text-muted/40">×{attempts}</span>
        )}
        {step.time_taken != null && (
          <span className="text-[11px] tabular-nums text-text-muted/50">{step.time_taken}s</span>
        )}
        {isError ? (
          <span className="text-[11px] text-red-400">✗</span>
        ) : (
          <span className="text-[11px]" style={{ color: 'var(--accent)' }}>✓</span>
        )}
        {isCode && (
          <button
            onClick={() => setShowCode(v => !v)}
            className="text-[11px] text-text-muted/50 hover:text-text-muted ml-1 transition-colors"
          >
            {showCode ? 'hide' : 'details'}
          </button>
        )}
      </div>
      {isCode && showCode && (
        <div className="ml-5 mt-1.5 space-y-1.5">
          {step.code && (
            <div className="rounded-lg overflow-hidden border border-border/20">
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
      )}
    </div>
  );
}

export default memo(function AgentActionBlock({ stepLog = [], toolsUsed = [], totalTime = 0, isStreaming = false }) {
  if (!stepLog.length && !toolsUsed.length) return null;

  const timeStr = totalTime > 0 ? `${totalTime.toFixed(1)}s` : '';

  /* During streaming: don't render here — ChatPanel's live view handles it */
  if (isStreaming) return null;

  /* Collapse consecutive same-tool attempts into a single row (keep last entry).
     This prevents showing 7 "Searching ✗" rows when the planner retried. */
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

  /* After completion: clean inline step list */
  return (
    <div className="mb-3 space-y-0.5">
      {collapsed.map((step, idx) => (
        <StepRow key={idx} step={step} idx={idx} />
      ))}
      {totalTime > 0 && (
        <div className="pt-1">
          <span className="text-[11px] tabular-nums text-text-muted/40">{timeStr} total</span>
        </div>
      )}
    </div>
  );
});

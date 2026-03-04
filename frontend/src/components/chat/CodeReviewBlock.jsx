'use client';

/**
 * CodeReviewBlock — /code slash command output component.
 *
 * Displays LLM-generated code + explanation and lets the user choose:
 *   [Run in Sandbox]  → executes via /agent/run-generated, streams stdout
 *   [Copy Only]       → copies code to clipboard, no execution
 *
 * Contract:
 * - Never auto-executes. Execution is always user-initiated.
 * - Streams stdout line-by-line on run.
 * - Shows exit code + elapsed time on completion.
 * - Execution is sandbox-isolated; no host access.
 */

import { useState, useRef, useEffect, useCallback } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { runGeneratedCode } from '@/lib/api/chat';
import { readSSEStream } from '@/lib/utils/helpers';

const LANG_LABELS = {
  python: 'Python', py: 'Python',
  javascript: 'JavaScript', js: 'JavaScript',
  typescript: 'TypeScript', ts: 'TypeScript',
  bash: 'Bash', sh: 'Bash',
  sql: 'SQL',
};

function langLabel(lang = 'python') {
  return LANG_LABELS[lang.toLowerCase()] ?? lang;
}

function CopyButton({ text, className = '' }) {
  const [copied, setCopied] = useState(false);
  const copy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch { /* ignore */ }
  }, [text]);
  return (
    <button
      onClick={copy}
      className={`text-[11px] px-2 py-0.5 rounded transition-all tabular-nums
        bg-surface-overlay hover:bg-surface-raised text-text-muted hover:text-text-secondary
        ${className}`}
    >
      {copied ? '✓ Copied' : 'Copy'}
    </button>
  );
}

export default function CodeReviewBlock({
  code = '',
  language = 'python',
  explanation = '',
  dependencies = [],
  notebookId,
  sessionId = null,
}) {
  const [collapsed, setCollapsed] = useState(false);
  const [runState, setRunState] = useState('idle'); // idle | running | done | error
  const [stdout, setStdout] = useState('');
  const [exitCode, setExitCode] = useState(null);
  const [elapsed, setElapsed] = useState(null);
  const [copyDone, setCopyDone] = useState(false);
  const terminalRef = useRef(null);
  const abortRef = useRef(null);

  useEffect(() => {
    if (terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [stdout]);

  // Cleanup on unmount
  useEffect(() => () => abortRef.current?.abort(), []);

  const handleRunInSandbox = async () => {
    if (runState === 'running') return;
    setRunState('running');
    setStdout('');
    setExitCode(null);
    setElapsed(null);

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const response = await runGeneratedCode(
        code, language, notebookId, sessionId, 30, ac.signal,
      );
      if (!response.body) throw new Error('No response body from sandbox');

      await readSSEStream(response.body, {
        stdout: (payload) => {
          const line = payload.line ?? '';
          setStdout((prev) => (prev ? prev + '\n' + line : line));
        },
        result: (payload) => {
          setExitCode(payload.exit_code ?? 0);
          setElapsed(payload.elapsed ?? null);
          if (payload.stderr) {
            setStdout((prev) => (prev ? prev + '\n[stderr]\n' + payload.stderr : '[stderr]\n' + payload.stderr));
          }
        },
        error: (payload) => {
          setStdout((prev) => (prev ? prev + '\n⚠ ' + (payload.error ?? 'Unknown error') : '⚠ ' + (payload.error ?? 'Unknown error')));
          setExitCode(-1);
        },
        done: (payload) => {
          if (payload?.elapsed && elapsed === null) setElapsed(payload.elapsed);
          setRunState(exitCode === 0 || exitCode === null ? 'done' : 'error');
        },
      });
    } catch (err) {
      if (err.name !== 'AbortError') {
        setStdout((prev) => (prev ? prev + '\n⚠ ' + err.message : '⚠ ' + err.message));
        setExitCode(-1);
      }
    } finally {
      setRunState((s) => (s === 'running' ? 'done' : s));
      abortRef.current = null;
    }
  };

  const handleCopyOnly = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopyDone(true);
      setTimeout(() => setCopyDone(false), 2000);
    } catch { /* ignore */ }
  };

  const handleStop = () => {
    abortRef.current?.abort();
    setRunState('done');
  };

  const exitOk = exitCode === 0;
  const hasOutput = stdout.length > 0;

  return (
    <div className="code-review-block rounded-xl border border-border/40 overflow-hidden bg-surface-sunken my-3">
      {/* ── Header ─────────────────────────────────────────────── */}
      <div className="flex items-center justify-between px-3.5 py-2 border-b border-border/30 bg-surface-raised/50">
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-semibold uppercase tracking-wider text-text-muted">
            Code Proposal
          </span>
          <span className="text-[10px] font-mono px-1.5 py-0.5 rounded bg-purple-500/15 text-purple-400 border border-purple-500/20">
            {langLabel(language)}
          </span>
          {dependencies.length > 0 && (
            <span className="text-[10px] text-text-muted">
              deps: {dependencies.join(', ')}
            </span>
          )}
        </div>
        <div className="flex items-center gap-1.5">
          <CopyButton text={code} />
          <button
            onClick={() => setCollapsed((v) => !v)}
            className="text-[11px] text-text-muted/60 hover:text-text-muted transition-colors"
          >
            {collapsed ? '▶ Expand' : '▼ Collapse'}
          </button>
        </div>
      </div>

      {/* ── Code block ────────────────────────────────────────── */}
      {!collapsed && (
        <div className="relative">
          <SyntaxHighlighter
            language={language.toLowerCase()}
            style={oneDark}
            customStyle={{
              margin: 0,
              padding: '12px 14px',
              fontSize: '12.5px',
              lineHeight: '1.65',
              background: 'var(--surface-sunken)',
              maxHeight: '400px',
              overflowY: 'auto',
            }}
          >
            {code}
          </SyntaxHighlighter>
        </div>
      )}

      {/* ── Explanation ────────────────────────────────────────── */}
      {explanation && (
        <div className="px-4 py-3 border-t border-border/20 bg-surface/40">
          <p className="text-[11px] font-semibold text-text-muted uppercase tracking-wider mb-1">
            Why this approach
          </p>
          <p className="text-sm text-text-secondary leading-relaxed">{explanation}</p>
        </div>
      )}

      {/* ── Action buttons ────────────────────────────────────── */}
      <div className="flex items-center gap-2.5 px-4 py-3 border-t border-border/20 bg-surface-raised/30">
        {/* Run in Sandbox */}
        {runState === 'idle' || runState === 'done' || runState === 'error' ? (
          <button
            onClick={handleRunInSandbox}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium
              bg-green-600 hover:bg-green-500 text-white transition-all active:scale-95"
          >
            <span>▶</span>
            {runState === 'idle' ? 'Run in Sandbox' : 'Re-run'}
          </button>
        ) : (
          <button
            onClick={handleStop}
            className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium
              bg-red-600/80 hover:bg-red-500 text-white transition-all"
          >
            <span>■</span> Stop
          </button>
        )}

        {/* Copy Only */}
        <button
          onClick={handleCopyOnly}
          className="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-sm font-medium
            border border-border/50 text-text-secondary hover:bg-surface-overlay hover:text-text-primary
            transition-all active:scale-95"
        >
          {copyDone ? '✓ Copied' : 'Copy Only'}
        </button>

        {/* Exit status */}
        {exitCode !== null && (
          <span
            className={`ml-auto text-[11px] font-mono px-2 py-0.5 rounded-md border
              ${exitOk
                ? 'bg-green-500/10 text-green-400 border-green-500/20'
                : 'bg-red-500/10 text-red-400 border-red-500/20'
              }`}
          >
            exit&nbsp;{exitCode}
            {elapsed !== null && <> &nbsp;·&nbsp; {elapsed}s</>}
          </span>
        )}

        {/* Running spinner */}
        {runState === 'running' && exitCode === null && (
          <span className="ml-auto flex items-center gap-1.5 text-[11px] text-text-muted animate-pulse">
            <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-ping" />
            Running…
          </span>
        )}
      </div>

      {/* ── Terminal output ────────────────────────────────────── */}
      {(hasOutput || runState === 'running') && (
        <div className="border-t border-border/20">
          <div className="flex items-center gap-2 px-4 py-1.5 bg-[#1a1a2e]">
            <span className="text-[10px] font-semibold text-text-muted uppercase tracking-wider">
              Terminal
            </span>
            {runState === 'running' && (
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 animate-ping" />
            )}
          </div>
          <pre
            ref={terminalRef}
            className="px-4 py-3 text-[12px] font-mono text-green-300 bg-[#0d0d1a] max-h-64
              overflow-y-auto whitespace-pre-wrap leading-relaxed"
          >
            {stdout || (runState === 'running' ? 'Running…' : '')}
          </pre>
        </div>
      )}
    </div>
  );
}

'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Play, Square, Copy, Check, Terminal, Sparkles, Loader2, Code2, ChevronDown, ChevronRight } from 'lucide-react';
import ArtifactViewer from './ArtifactViewer';
import { runGeneratedCode } from '@/lib/api/chat';
import { streamSSE } from '@/lib/stream/streamClient';

const CONSOLE_SUCCESS = 'text-green-400';
const CONSOLE_ERROR = 'text-red-400';
const CONSOLE_INFO = 'text-text-muted';

const SUPPORTED_LANGUAGES = [
  { value: 'python',     label: 'Python',     color: 'text-blue-400' },
  { value: 'javascript', label: 'JavaScript', color: 'text-yellow-400' },
  { value: 'typescript', label: 'TypeScript', color: 'text-blue-300' },
  { value: 'java',       label: 'Java',       color: 'text-orange-400' },
  { value: 'go',         label: 'Go',         color: 'text-cyan-400' },
  { value: 'rust',       label: 'Rust',       color: 'text-orange-300' },
  { value: 'cpp',        label: 'C++',        color: 'text-purple-400' },
  { value: 'c',          label: 'C',          color: 'text-purple-300' },
  { value: 'bash',       label: 'Bash',       color: 'text-green-400' },
];

/**
 * CodeWorkspace — interactive code editor with:
 *   - Language selector
 *   - Run / Stop buttons
 *   - Stdin (Program Input) panel
 *   - Console output
 *   - Artifact viewer
 *   - AI-edit box
 *
 * Props:
 *   codeBlocks  — array of {code, language, step_index} from streaming events
 *   notebookId  — required to call the execute endpoint
 *   sessionId   — optional
 *   isStreaming  — whether the parent is still generating (blocks running)
 */
export default function CodeWorkspace({ codeBlocks, notebookId, sessionId, isStreaming }) {
  const initialCode = codeBlocks?.[0]?.code || '';
  const initialLanguage = codeBlocks?.[0]?.language || 'python';

  const [code, setCode] = useState(initialCode);
  const [language, setLanguage] = useState(initialLanguage);
  const [stdin, setStdin] = useState('');
  const [showStdin, setShowStdin] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [consoleLines, setConsoleLines] = useState([]);
  const [exitCode, setExitCode] = useState(null);
  const [elapsed, setElapsed] = useState(null);
  const [runArtifacts, setRunArtifacts] = useState([]);
  const [instruction, setInstruction] = useState('');
  const [isApplying, setIsApplying] = useState(false);
  const [copied, setCopied] = useState(false);
  const consoleRef = useRef(null);
  const abortRef = useRef(null);

  // Keep code + language in sync while parent is still streaming
  useEffect(() => {
    if (isStreaming && codeBlocks?.[0]?.code) {
      setCode(codeBlocks[0].code);
      if (codeBlocks[0].language) setLanguage(codeBlocks[0].language);
    }
  }, [isStreaming, codeBlocks]);

  // Auto-scroll console
  useEffect(() => {
    if (consoleRef.current) {
      consoleRef.current.scrollTop = consoleRef.current.scrollHeight;
    }
  }, [consoleLines]);

  const addLine = useCallback((text, type = 'info') => {
    setConsoleLines((prev) => [...prev, { text, type }]);
  }, []);

  const handleRun = useCallback(async () => {
    if (isRunning || !code.trim() || !notebookId) return;

    setIsRunning(true);
    setConsoleLines([]);
    setExitCode(null);
    setElapsed(null);
    setRunArtifacts([]);

    const ac = new AbortController();
    abortRef.current = ac;

    try {
      const response = await runGeneratedCode(
        code, language, notebookId, sessionId, 30, ac.signal, stdin,
      );

      await streamSSE(
        response,
        {
          execution_start: () => {
            addLine(`▶ Running ${language}…`, 'info');
          },
          install_progress: (data) => {
            if (data.status === 'installing') addLine(`📦 Installing ${data.package}…`, 'info');
            else if (data.status === 'done') addLine(`✓ ${data.package} ready`, 'info');
            else addLine(`✗ Failed to install ${data.package}`, 'error');
          },
          execution_blocked: (data) => {
            addLine(`🚫 Blocked: ${data.reason}`, 'error');
            setExitCode(1);
            setIsRunning(false);
          },
          repair_suggestion: (data) => {
            if (data.code) {
              setCode(data.code);
              addLine(`⚡ Auto-repaired: ${data.explanation}`, 'info');
            }
          },
          artifact: (data) => {
            setRunArtifacts((prev) => [...prev, data]);
          },
          execution_done: (data) => {
            setExitCode(data.exit_code ?? 0);
            setElapsed(data.elapsed ?? null);
            if (data.stdout?.trim()) addLine(data.stdout.trim(), 'output');
            if (data.stderr?.trim()) addLine(data.stderr.trim(), 'error');
            if (!data.stdout && !data.stderr) addLine(data.summary || 'Done', 'info');
            setIsRunning(false);
          },
          error: (data) => {
            addLine(`✗ ${data.error || 'Unknown error'}`, 'error');
            setExitCode(1);
            setIsRunning(false);
          },
          done: () => setIsRunning(false),
        },
        ac.signal,
      );

      setIsRunning(false);
    } catch (err) {
      if (err.name !== 'AbortError') {
        addLine(`✗ ${err.message}`, 'error');
        setExitCode(1);
      }
      setIsRunning(false);
    } finally {
      abortRef.current = null;
    }
  }, [code, language, stdin, notebookId, sessionId, isRunning, addLine]);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setIsRunning(false);
    addLine('⏹ Stopped', 'info');
  }, [addLine]);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(code);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [code]);

  /**
   * AI code edit — sends instruction + current code to the /chat CODE_EXECUTION
   * pipeline which generates updated code via the code generation tool.
   */
  const handleAIApply = useCallback(async () => {
    if (!instruction.trim() || isApplying || !notebookId) return;
    setIsApplying(true);

    try {
      const { apiFetch } = await import('@/lib/api/config');
      const { streamSSE: sse } = await import('@/lib/stream/streamClient');

      const prompt =
        `Modify this ${language} code to: ${instruction.trim()}\n\n` +
        `Current code:\n\`\`\`${language}\n${code}\n\`\`\`\n\nReturn only the modified ${language} code.`;

      const body = {
        message: prompt,
        notebook_id: notebookId,
        intent_override: 'CODE_EXECUTION',
        stream: true,
        material_ids: [],
      };
      if (sessionId) body.session_id = sessionId;

      const resp = await apiFetch('/chat', {
        method: 'POST',
        body: JSON.stringify(body),
      });

      await sse(resp, {
        code_block: (data) => {
          if (data.code) {
            setCode(data.code);
            if (data.language) setLanguage(data.language);
            setInstruction('');
            setConsoleLines([]);
            setExitCode(null);
          }
        },
        token: () => {},
        done: () => setIsApplying(false),
        error: () => setIsApplying(false),
      });
    } catch {
      // silently fail — code unchanged
    } finally {
      setIsApplying(false);
    }
  }, [instruction, code, language, notebookId, sessionId, isApplying]);

  const hasConsole = consoleLines.length > 0 || isRunning;
  const langMeta = SUPPORTED_LANGUAGES.find((l) => l.value === language) || SUPPORTED_LANGUAGES[0];

  return (
    <div
      className="mt-2 rounded-xl overflow-hidden shadow-sm shadow-black/20"
    >
      {/* ── Toolbar ── */}
      <div
        className="flex items-center justify-between px-3 py-2"
        style={{ background: 'rgba(255,255,255,0.03)' }}
      >
        {/* Language selector */}
        <div className="flex items-center gap-2">
          <Code2 size={13} className={langMeta.color} />
          <select
            value={language}
            onChange={(e) => { setLanguage(e.target.value); setConsoleLines([]); setExitCode(null); }}
            disabled={isRunning}
            className="bg-transparent text-xs font-medium text-text-muted border-none outline-none cursor-pointer appearance-none"
            title="Select language"
          >
            {SUPPORTED_LANGUAGES.map((l) => (
              <option key={l.value} value={l.value} className="bg-surface-raised">
                {l.label}
              </option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1.5">
          {/* Stdin toggle */}
          <button
            onClick={() => setShowStdin((v) => !v)}
            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-primary px-2 py-1 rounded hover:bg-surface-overlay transition-colors"
            title="Toggle program input (stdin)"
          >
            {showStdin ? <ChevronDown size={12} /> : <ChevronRight size={12} />}
            Input
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-xs text-text-muted hover:text-text-primary px-2 py-1 rounded hover:bg-surface-overlay transition-colors"
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy'}
          </button>

          {isRunning ? (
            <button
              onClick={handleStop}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-error/15 text-error hover:bg-error/25 transition-colors"
            >
              <Square size={11} fill="currentColor" />
              Stop
            </button>
          ) : (
            <button
              onClick={handleRun}
              disabled={!code.trim() || !notebookId || isStreaming}
              className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg bg-green-500/15 text-green-400 hover:bg-green-500/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
              title={!notebookId ? 'Notebook required to run code' : `Run ${langMeta.label}`}
            >
              <Play size={11} fill="currentColor" />
              Run
            </button>
          )}
        </div>
      </div>

      {/* ── Code editor ── */}
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        spellCheck={false}
        rows={Math.max(4, Math.min(code.split('\n').length + 1, 20))}
        className="w-full bg-transparent font-mono text-xs text-text-primary p-4 resize-none outline-none"
        style={{ lineHeight: '1.7', background: 'rgba(0,0,0,0.15)' }}
      />

      {/* ── Stdin panel ── */}
      {showStdin && (
        <div
          className="bg-black/10"
        >
          <div
            className="flex items-center gap-2 px-3 py-1.5"
            style={{ background: 'rgba(255,255,255,0.02)' }}
          >
            <Terminal size={11} className="text-text-muted" />
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
              Program Input (stdin)
            </span>
          </div>
          <textarea
            value={stdin}
            onChange={(e) => setStdin(e.target.value)}
            spellCheck={false}
            rows={3}
            placeholder="Type program input here, one value per line…"
            className="w-full bg-transparent font-mono text-xs text-text-primary p-4 resize-y outline-none placeholder:text-text-muted/40"
            style={{ background: 'rgba(0,0,0,0.1)' }}
          />
        </div>
      )}

      {/* ── Console output ── */}
      {hasConsole && (
        <div className="bg-black/20">
          <div
            className="flex items-center gap-2 px-3 py-1.5"
            style={{ background: 'rgba(255,255,255,0.02)' }}
          >
            <Terminal size={11} className="text-text-muted" />
            <span className="text-[11px] font-semibold text-text-muted uppercase tracking-wider">
              Console
            </span>
            {exitCode !== null && (
              <span
                className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-medium ${
                  exitCode === 0
                    ? 'bg-green-500/10 text-green-400'
                    : 'bg-error/10 text-error'
                }`}
              >
                {exitCode === 0 ? 'OK' : `Exit ${exitCode}`}
              </span>
            )}
            {elapsed != null && (
              <span className="text-[10px] text-text-muted/40 tabular-nums">
                {elapsed.toFixed(2)}s
              </span>
            )}
          </div>

          <div
            ref={consoleRef}
            className="px-4 py-3 font-mono text-xs leading-relaxed max-h-44 overflow-y-auto"
            style={{ background: 'rgba(0,0,0,0.2)' }}
          >
            {isRunning && consoleLines.length === 0 && (
              <div className="flex items-center gap-2 text-text-muted/60">
                <Loader2 size={11} className="animate-spin" />
                Running…
              </div>
            )}
            {consoleLines.map((line, i) => (
              <div
                key={i}
                className={`whitespace-pre-wrap break-all ${
                  line.type === 'error'
                    ? CONSOLE_ERROR
                    : line.type === 'output'
                    ? 'text-text-primary'
                    : CONSOLE_INFO
                }`}
              >
                {line.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── Run artifacts ── */}
      {runArtifacts.length > 0 && (
        <div className="p-3 bg-black/10">
          <ArtifactViewer artifacts={runArtifacts} />
        </div>
      )}

      {/* ── AI edit box ── */}
      <div
        className="px-3 py-2.5 bg-black/30"
      >
        <div className="flex items-center gap-2">
          <div
            className="flex-1 flex items-center gap-2 rounded-lg px-3 py-2"
            style={{
              background: 'var(--surface-raised, #1e1e2e)',
            }}
          >
            <Sparkles size={12} className="text-accent shrink-0" />
            <input
              type="text"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAIApply()}
              placeholder={`Modify with AI… e.g. add error handling`}
              disabled={isApplying}
              className="flex-1 bg-transparent text-xs text-text-primary placeholder:text-text-muted outline-none"
            />
            {isApplying && <Loader2 size={11} className="text-accent animate-spin shrink-0" />}
          </div>
          <button
            onClick={handleAIApply}
            disabled={!instruction.trim() || isApplying || !notebookId}
            className="text-xs px-3 py-2 rounded-lg bg-accent/15 text-accent hover:bg-accent/25 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

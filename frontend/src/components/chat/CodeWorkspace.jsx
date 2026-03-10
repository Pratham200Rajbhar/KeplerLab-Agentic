'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { Play, Square, Copy, Check, Terminal, Sparkles, Loader2, Code2, ChevronDown, ChevronRight } from 'lucide-react';
import ArtifactViewer from './ArtifactViewer';
import { runGeneratedCode } from '@/lib/api/chat';
import { streamSSE } from '@/lib/stream/streamClient';

const LANG_META = {
  python:     { label: 'Python',     color: 'text-blue-400' },
  javascript: { label: 'JavaScript', color: 'text-yellow-400' },
  typescript: { label: 'TypeScript', color: 'text-blue-300' },
  java:       { label: 'Java',       color: 'text-orange-400' },
  go:         { label: 'Go',         color: 'text-cyan-400' },
  rust:       { label: 'Rust',       color: 'text-orange-300' },
  cpp:        { label: 'C++',        color: 'text-purple-400' },
  c:          { label: 'C',          color: 'text-purple-300' },
  bash:       { label: 'Bash',       color: 'text-green-400' },
};

const LANG_LIST = Object.entries(LANG_META).map(([value, meta]) => ({ value, ...meta }));


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

  
  useEffect(() => {
    if (isStreaming && codeBlocks?.[0]?.code) {
      setCode(codeBlocks[0].code);
      if (codeBlocks[0].language) setLanguage(codeBlocks[0].language);
    }
  }, [isStreaming, codeBlocks]);

  
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
      
    } finally {
      setIsApplying(false);
    }
  }, [instruction, code, language, notebookId, sessionId, isApplying]);

  const hasConsole = consoleLines.length > 0 || isRunning;
  const langMeta = LANG_META[language] || LANG_META.python;

  return (
    <div className="mt-2 rounded-xl border border-white/[0.06] bg-white/[0.02] overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-white/[0.04]">
        <div className="flex items-center gap-2">
          <Code2 size={13} className={langMeta.color} />
          <select
            value={language}
            onChange={(e) => { setLanguage(e.target.value); setConsoleLines([]); setExitCode(null); }}
            disabled={isRunning}
            className="bg-transparent text-xs font-medium text-text-muted border-none outline-none cursor-pointer appearance-none"
            title="Select language"
          >
            {LANG_LIST.map(l => (
              <option key={l.value} value={l.value} className="bg-surface-raised">{l.label}</option>
            ))}
          </select>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={() => setShowStdin(v => !v)}
            className="flex items-center gap-1 text-[11px] text-text-muted hover:text-text-primary px-1.5 py-1 rounded hover:bg-white/[0.04] transition-colors"
          >
            {showStdin ? <ChevronDown size={11} /> : <ChevronRight size={11} />}
            stdin
          </button>

          <button
            onClick={handleCopy}
            className="flex items-center gap-1 text-[11px] text-text-muted hover:text-text-primary px-1.5 py-1 rounded hover:bg-white/[0.04] transition-colors"
          >
            {copied ? <Check size={11} /> : <Copy size={11} />}
            {copied ? 'Copied' : 'Copy'}
          </button>

          {isRunning ? (
            <button
              onClick={handleStop}
              className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-md bg-red-500/10 text-red-400 hover:bg-red-500/15 transition-colors"
            >
              <Square size={10} fill="currentColor" />
              Stop
            </button>
          ) : (
            <button
              onClick={handleRun}
              disabled={!code.trim() || !notebookId || isStreaming}
              className="flex items-center gap-1 text-[11px] px-2.5 py-1 rounded-md bg-green-500/10 text-green-400 hover:bg-green-500/15 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              title={!notebookId ? 'Notebook required' : `Run ${langMeta.label}`}
            >
              <Play size={10} fill="currentColor" />
              Run
            </button>
          )}
        </div>
      </div>

      {/* Code editor */}
      <textarea
        value={code}
        onChange={(e) => setCode(e.target.value)}
        spellCheck={false}
        rows={Math.max(4, Math.min(code.split('\n').length + 1, 20))}
        className="w-full bg-black/10 font-mono text-xs text-text-primary p-3.5 resize-none outline-none"
        style={{ lineHeight: '1.7' }}
      />

      {/* Stdin */}
      {showStdin && (
        <div className="border-t border-white/[0.04]">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/[0.02]">
            <Terminal size={10} className="text-text-muted/60" />
            <span className="text-[10px] font-medium text-text-muted/60 uppercase tracking-wider">stdin</span>
          </div>
          <textarea
            value={stdin}
            onChange={(e) => setStdin(e.target.value)}
            spellCheck={false}
            rows={2}
            placeholder="Program input…"
            className="w-full bg-black/5 font-mono text-xs text-text-primary p-3.5 resize-y outline-none placeholder:text-text-muted/30"
          />
        </div>
      )}

      {/* Console */}
      {hasConsole && (
        <div className="border-t border-white/[0.04]">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-white/[0.02]">
            <Terminal size={10} className="text-text-muted/60" />
            <span className="text-[10px] font-medium text-text-muted/60 uppercase tracking-wider">output</span>
            {exitCode !== null && (
              <span className={`ml-auto text-[10px] px-1.5 py-0.5 rounded font-medium ${
                exitCode === 0 ? 'bg-green-500/10 text-green-400' : 'bg-red-500/10 text-red-400'
              }`}>
                {exitCode === 0 ? 'OK' : `Exit ${exitCode}`}
              </span>
            )}
            {elapsed != null && (
              <span className="text-[10px] text-text-muted/40 tabular-nums">{elapsed.toFixed(2)}s</span>
            )}
          </div>

          <div
            ref={consoleRef}
            className="px-3.5 py-2.5 font-mono text-xs leading-relaxed max-h-44 overflow-y-auto bg-black/10"
          >
            {isRunning && consoleLines.length === 0 && (
              <div className="flex items-center gap-2 text-text-muted/50">
                <Loader2 size={11} className="animate-spin" />
                Running…
              </div>
            )}
            {consoleLines.map((line, i) => (
              <div
                key={i}
                className={`whitespace-pre-wrap break-all ${
                  line.type === 'error' ? 'text-red-400' : line.type === 'output' ? 'text-text-primary' : 'text-text-muted'
                }`}
              >
                {line.text}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Artifacts */}
      {runArtifacts.length > 0 && (
        <div className="p-3 border-t border-white/[0.04]">
          <ArtifactViewer artifacts={runArtifacts} />
        </div>
      )}

      {/* AI Modify bar */}
      <div className="px-3 py-2 border-t border-white/[0.04] bg-white/[0.01]">
        <div className="flex items-center gap-2">
          <div className="flex-1 flex items-center gap-2 rounded-lg px-2.5 py-1.5 bg-white/[0.03] border border-white/[0.06]">
            <Sparkles size={11} className="text-accent/60 shrink-0" />
            <input
              type="text"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && handleAIApply()}
              placeholder="Modify with AI…"
              disabled={isApplying}
              className="flex-1 bg-transparent text-xs text-text-primary placeholder:text-text-muted/40 outline-none"
            />
            {isApplying && <Loader2 size={11} className="text-accent animate-spin shrink-0" />}
          </div>
          <button
            onClick={handleAIApply}
            disabled={!instruction.trim() || isApplying || !notebookId}
            className="text-[11px] px-2.5 py-1.5 rounded-md bg-accent/10 text-accent hover:bg-accent/15 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
          >
            Apply
          </button>
        </div>
      </div>
    </div>
  );
}

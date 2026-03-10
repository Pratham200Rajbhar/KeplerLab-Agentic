'use client';

import { memo, useState, useCallback, useRef, useEffect } from 'react';
import { Play, Copy, Check, Loader2, AlertTriangle, CheckCircle2 } from 'lucide-react';
import OutputRenderer from './OutputRenderer';


function CodePanel({
  code: initialCode,
  language = 'python',
  status = 'awaiting_run',
  onRun,
  installPills = [],
  repairAttempt = 0,
  repairedCode = null,
  repairedExplanation = null,
  executionBlocked = null,
  artifacts = [],
  exitCode = null,
}) {
  const [code, setCode] = useState(() => repairedCode || initialCode || '');
  const [copied, setCopied] = useState(false);
  const textareaRef = useRef(null);

  
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      setCode(repairedCode || initialCode || '');
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [initialCode, repairedCode]);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      
      const ta = document.createElement('textarea');
      ta.value = code;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  }, [code]);

  const handleRun = useCallback(() => {
    if (onRun && code.trim()) {
      onRun(code);
    }
  }, [onRun, code]);

  const isEditable = status === 'awaiting_run' || status === 'repaired' || status === 'blocked';
  const isRunning = status === 'executing';
  const isDone = status === 'done';
  const isBlocked = status === 'blocked';

  return (
    <div className="space-y-3">
      {}
      {repairAttempt > 0 && repairedCode && (
        <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 px-2.5 py-1 rounded-md border border-amber-500/20 w-fit">
          <AlertTriangle className="w-3 h-3" />
          <span>Auto-repaired (attempt {repairAttempt}/3)</span>
        </div>
      )}
      {repairedExplanation && (
        <p className="text-xs text-text-muted">{repairedExplanation}</p>
      )}

      {}
      <div className="rounded-lg overflow-hidden bg-[#1e1e2e] shadow-lg">
        {}
        <div className="flex items-center justify-between px-3 py-1.5 bg-surface-raised/50">
          <span className="text-[10px] font-mono text-text-muted uppercase tracking-wider">
            {language}
          </span>
        </div>

        {}
        {isEditable ? (
          <textarea
            ref={textareaRef}
            value={code}
            onChange={(e) => setCode(e.target.value)}
            className="w-full bg-transparent text-text-primary font-mono text-[13px] leading-relaxed p-3 resize-none min-h-[100px] focus:outline-none"
            spellCheck={false}
            style={{
              height: Math.min(Math.max(code.split('\n').length * 20 + 24, 100), 400),
              tabSize: 4,
            }}
          />
        ) : (
          <pre className="text-text-primary font-mono text-[13px] leading-relaxed p-3 overflow-x-auto max-h-[400px]">
            <code>{code}</code>
          </pre>
        )}
      </div>

      {}
      <div className="flex items-center gap-2">
        {}
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md border border-border/40 bg-surface-raised hover:bg-surface-overlay transition-colors text-text-secondary"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 text-emerald-400" />
              <span className="text-emerald-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="w-3 h-3" />
              <span>Copy</span>
            </>
          )}
        </button>

        {}
        {isRunning ? (
          <button
            disabled
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-blue-500/20 text-blue-400 cursor-not-allowed shadow-sm"
          >
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Running...</span>
          </button>
        ) : isDone && exitCode === 0 ? (
          <button
            disabled
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 cursor-not-allowed"
          >
            <CheckCircle2 className="w-3 h-3" />
            <span>Ran</span>
          </button>
        ) : (
          <button
            onClick={handleRun}
            disabled={!code.trim() || isBlocked}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md bg-emerald-500/15 text-emerald-400 border border-emerald-500/30 hover:bg-emerald-500/25 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <Play className="w-3 h-3" />
            <span>Run</span>
          </button>
        )}
      </div>

      {}
      {installPills.length > 0 && (
        <div className="flex flex-wrap gap-1.5">
          {installPills.map((pill, i) => (
            <span
              key={i}
              className={`text-[10px] px-2 py-0.5 rounded-full border ${
                pill.status === 'done'
                  ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                  : pill.status === 'failed'
                  ? 'bg-red-500/10 text-red-400 border-red-500/20'
                  : 'bg-blue-500/10 text-blue-400 border-blue-500/20 animate-pulse'
              }`}
            >
              {pill.status === 'installing' && 'Installing '}
              {pill.package}
              {pill.status === 'done' && ' ✓'}
              {pill.status === 'failed' && ' ✗'}
            </span>
          ))}
        </div>
      )}

      {}
      {executionBlocked && (
        <div className="flex items-center gap-2 text-xs text-red-400 bg-red-500/10 px-3 py-2 rounded-md border border-red-500/20">
          <AlertTriangle className="w-3.5 h-3.5 shrink-0" />
          <span>Execution blocked: {executionBlocked}</span>
        </div>
      )}

      {}
      {artifacts.length > 0 && (
        <div className="space-y-2">
          {artifacts.map((art, i) => (
            <OutputRenderer key={i} artifact={art} />
          ))}
        </div>
      )}
    </div>
  );
}

export default memo(CodePanel);

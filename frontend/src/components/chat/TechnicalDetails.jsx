'use client';

import { memo, useState } from 'react';
import { ChevronDown, ChevronUp, Code2, Terminal, Wrench } from 'lucide-react';

/**
 * TechnicalDetails — collapsible section showing code and execution logs.
 * 
 * Props:
 *   code: { code: string, language: string }
 *   logs: [{ timestamp, type, message }]
 *   toolOutputs: [{ tool, output, duration }]
 *   defaultOpen: boolean
 */
function TechnicalDetails({ code, logs = [], toolOutputs = [], defaultOpen = false }) {
  const [isOpen, setIsOpen] = useState(defaultOpen);

  const hasContent = code || logs.length > 0 || toolOutputs.length > 0;

  if (!hasContent) {
    return null;
  }

  return (
    <div className="technical-details mt-4">
      {/* Toggle button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 text-xs text-text-muted hover:text-text-secondary transition-colors"
      >
        <Code2 className="w-3.5 h-3.5" />
        <span>Technical Details</span>
        {isOpen ? (
          <ChevronUp className="w-3.5 h-3.5" />
        ) : (
          <ChevronDown className="w-3.5 h-3.5" />
        )}
      </button>

      {/* Content */}
      {isOpen && (
        <div className="mt-3 space-y-4 rounded-lg overflow-hidden shadow-sm">
          {/* Generated code */}
          {code && code.code && (
            <CodeSection code={code.code} language={code.language} />
          )}

          {/* Tool outputs */}
          {toolOutputs.length > 0 && (
            <ToolOutputsSection outputs={toolOutputs} />
          )}

          {/* Execution logs */}
          {logs.length > 0 && (
            <LogsSection logs={logs} />
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Code section with syntax highlighting placeholder.
 */
function CodeSection({ code, language = 'python' }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback
      const ta = document.createElement('textarea');
      ta.value = code;
      document.body.appendChild(ta);
      ta.select();
      document.execCommand('copy');
      document.body.removeChild(ta);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  return (
    <div>
      <div className="flex items-center justify-between px-3 py-2 bg-surface-raised/50">
        <div className="flex items-center gap-2">
          <Code2 className="w-3.5 h-3.5 text-text-muted" />
          <span className="text-xs text-text-muted uppercase tracking-wider">{language}</span>
        </div>
        <button
          onClick={handleCopy}
          className="text-xs text-text-muted hover:text-text-secondary transition-colors"
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
      <pre className="p-3 text-[12px] font-mono text-text-secondary overflow-x-auto max-h-[300px] bg-[#1e1e2e]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

/**
 * Tool outputs section.
 */
function ToolOutputsSection({ outputs }) {
  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-2 bg-surface-raised/50">
        <Wrench className="w-3.5 h-3.5 text-text-muted" />
        <span className="text-xs text-text-muted">Tool Outputs</span>
      </div>
      <div className="divide-y divide-border/20">
        {outputs.map((output, idx) => (
          <div key={idx} className="px-3 py-2">
            <div className="flex items-center justify-between mb-1">
              <span className="text-xs font-medium text-text-secondary capitalize">
                {output.tool?.replace(/_/g, ' ') || 'Tool'}
              </span>
              {output.duration > 0 && (
                <span className="text-[10px] text-text-muted">
                  {(output.duration / 1000).toFixed(2)}s
                </span>
              )}
            </div>
            <p className="text-xs text-text-muted line-clamp-3">{output.output}</p>
          </div>
        ))}
      </div>
    </div>
  );
}

/**
 * Execution logs section.
 */
function LogsSection({ logs }) {
  return (
    <div>
      <div className="flex items-center gap-2 px-3 py-2 bg-surface-raised/50 border-b border-border/20">
        <Terminal className="w-3.5 h-3.5 text-text-muted" />
        <span className="text-xs text-text-muted">Execution Logs</span>
      </div>
      <div className="p-2 max-h-[200px] overflow-y-auto font-mono text-[11px]">
        {logs.map((log, idx) => (
          <div
            key={idx}
            className={`px-2 py-0.5 ${
              log.type === 'error'
                ? 'text-red-400'
                : log.type === 'warning'
                  ? 'text-amber-400'
                  : 'text-text-muted'
            }`}
          >
            <span className="text-text-muted/50 mr-2">
              {new Date(log.timestamp).toLocaleTimeString()}
            </span>
            {log.message}
          </div>
        ))}
      </div>
    </div>
  );
}

export default memo(TechnicalDetails);

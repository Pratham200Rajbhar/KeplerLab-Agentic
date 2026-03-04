'use client';

import { useState, memo, useCallback } from 'react';
import {
  Check, Copy, ChevronRight, Lightbulb, ThumbsUp, ThumbsDown,
  Search, Globe, Code2, Brain, ClipboardList, BookOpen, Monitor,
  Wrench, RotateCcw, Pencil, Trash2, X, SendHorizonal,
} from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';
import AgentStepsPanel from './AgentStepsPanel';
import AgentActionBlock from './AgentActionBlock';
import GeneratedFileCard from './GeneratedFileCard';
import ExecutionPanel from './ExecutionPanel';
import ChartRenderer from './ChartRenderer';
import BlockHoverMenu from './BlockHoverMenu';
import CommandBadge from './CommandBadge';

const TOOL_BADGE = {
  rag_tool:       { Icon: Search,        label: 'RAG Search' },
  research_tool:  { Icon: Globe,         label: 'Web Research' },
  python_tool:    { Icon: Code2,         label: 'Python' },
  data_profiler:  { Icon: Brain,         label: 'Data Profile' },
  quiz_tool:      { Icon: ClipboardList, label: 'Quiz' },
  flashcard_tool: { Icon: BookOpen,      label: 'Flashcards' },
  ppt_tool:       { Icon: Monitor,       label: 'Slides' },
  code_repair:    { Icon: Wrench,        label: 'Code Repair' },
};

function tryParseDataAnalysis(content) {
  if (!content) return null;
  const trimmed = content.trim();
  if (!trimmed.startsWith('{') || !trimmed.endsWith('}')) return null;
  try {
    const parsed = JSON.parse(trimmed);
    if ('stdout' in parsed || 'base64_chart' in parsed || 'explanation' in parsed) return parsed;
  } catch { /* skip */ }
  return null;
}

function tryParseResearchJSON(content) {
  if (!content) return null;
  const trimmed = content.trim();
  if (!trimmed.startsWith('{')) return null;
  try {
    const p = JSON.parse(trimmed);
    if (!('executive_summary' in p) && !('key_findings' in p) && !('findings' in p)) return null;
    const lines = [];
    if (p.executive_summary) lines.push(`## Summary\n\n${p.executive_summary}`);
    const findings = p.key_findings || p.findings || [];
    if (findings.length) { lines.push(`\n## Key Findings\n`); findings.forEach(f => lines.push(`- ${typeof f === 'string' ? f : JSON.stringify(f)}`)); }
    if (p.methodology) lines.push(`\n## Methodology\n\n${p.methodology}`);
    if (p.conclusion) lines.push(`\n## Conclusion\n\n${p.conclusion}`);
    if (p.limitations) lines.push(`\n## Limitations\n\n${p.limitations}`);
    const sources = p.sources || p.references || [];
    if (sources.length) {
      lines.push(`\n## Sources\n`);
      sources.forEach((s, i) => {
        const url = typeof s === 'string' ? s : (s.url || s.link || '');
        const title = typeof s === 'object' ? (s.title || s.name || url) : url;
        lines.push(url ? `${i + 1}. [${title}](${url})` : `${i + 1}. ${title}`);
      });
    }
    return lines.join('\n');
  } catch { /* skip */ }
  return null;
}

function tryParseMultiSource(content) {
  if (!content || !content.includes('[Source ') || !/\[Source \d+ — [^\]]+\]/.test(content)) return null;
  const rawBlocks = content.split(/\n---\n/);
  const blocks = [];
  for (const block of rawBlocks) {
    const trimmed = block.trim();
    if (!trimmed) continue;
    const m = trimmed.match(/^\[Source \d+ — ([^\]]+)\]\n?([\s\S]*)/);
    if (!m) { if (trimmed) blocks.push({ tool: null, raw: trimmed, json: null }); continue; }
    const tool = m[1].trim();
    const body = m[2].trim();
    let json = null;
    if (body.startsWith('{') && body.endsWith('}')) { try { json = JSON.parse(body); } catch { /* skip */ } }
    blocks.push({ tool, raw: body, json });
  }
  return blocks.length > 0 ? blocks : null;
}

function extractPythonCode(content) {
  if (!content) return null;
  const match = content.match(/```python\n([\s\S]*?)```/);
  return match ? match[1] : null;
}

function ActionButton({ icon, activeIcon, label, onClick, isActive = false }) {
  const [active, setActive] = useState(isActive);
  return (
    <button onClick={() => { setActive(!active); onClick?.(!active); }} title={label}
      className={`inline-flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-150 ${
        active ? 'text-accent bg-accent/10' : 'text-text-muted hover:text-text-secondary hover:bg-surface-overlay'}`}>
      {active ? (activeIcon || icon) : icon}
    </button>
  );
}

function CopyActionButton({ content }) {
  const [copied, setCopied] = useState(false);
  return (
    <button onClick={async () => { await navigator.clipboard.writeText(content); setCopied(true); setTimeout(() => setCopied(false), 2000); }}
      title={copied ? 'Copied!' : 'Copy'}
      className={`inline-flex items-center justify-center w-7 h-7 rounded-lg transition-all duration-150 ${
        copied ? 'text-success bg-success-subtle' : 'text-text-muted hover:text-text-secondary hover:bg-surface-overlay'}`}>
      {copied ? <Check className="w-3.5 h-3.5" strokeWidth={2.5} /> : <Copy className="w-3.5 h-3.5" />}
    </button>
  );
}

export default memo(function ChatMessage({ message, notebookId, onRetry, onEdit, onDelete }) {
  const isUser = message.role === 'user';
  const blocks = message.blocks || [];
  const agentMeta = message.agentMeta || null;
  const stepLog = agentMeta?.step_log || message.stepLog || [];
  const generatedFiles = agentMeta?.generated_files || message.generatedFiles || [];

  /* ── User message edit state ── */
  const [isEditing, setIsEditing] = useState(false);
  const [editText, setEditText] = useState(message.content || '');

  const handleEditSave = useCallback(() => {
    if (editText.trim() && editText.trim() !== message.content) {
      onEdit?.(message.id, editText.trim());
    }
    setIsEditing(false);
  }, [editText, message.content, message.id, onEdit]);

  const handleEditCancel = useCallback(() => {
    setEditText(message.content || '');
    setIsEditing(false);
  }, [message.content]);

  const dataAnalysis = !isUser ? tryParseDataAnalysis(message.content) : null;
  const multiSource = !isUser && !dataAnalysis ? tryParseMultiSource(message.content) : null;
  const researchMarkdown = !isUser && !dataAnalysis && !multiSource ? tryParseResearchJSON(message.content) : null;
  const pythonCode = !isUser && !dataAnalysis && !multiSource && !researchMarkdown ? extractPythonCode(message.content) : null;

  const renderAIContent = () => {
    if (dataAnalysis) {
      return (
        <div className="markdown-content">
          {dataAnalysis.base64_chart && <ChartRenderer base64Chart={dataAnalysis.base64_chart} explanation={dataAnalysis.explanation} title="Data Analysis Chart" />}
          {!dataAnalysis.base64_chart && dataAnalysis.explanation && <MarkdownRenderer content={dataAnalysis.explanation} />}
          {dataAnalysis.stdout && (
            <details className="mt-3 group/raw" open={!dataAnalysis.explanation}>
              <summary className="cursor-pointer text-xs text-text-muted hover:text-text-secondary select-none list-none flex items-center gap-1.5 py-1">
                <ChevronRight className="w-3 h-3 transition-transform group-open/raw:rotate-90" />Raw output
              </summary>
              <pre className="mt-1.5 text-xs font-mono px-3 py-2.5 rounded-lg bg-surface-overlay border border-border/30 overflow-x-auto whitespace-pre-wrap text-text-secondary">{dataAnalysis.stdout}</pre>
            </details>
          )}
          {message.generatedCode && <ExecutionPanel code={message.generatedCode} initialOutput={dataAnalysis.stdout || ''} initialExitCode={dataAnalysis.exit_code ?? null} />}
        </div>
      );
    }
    if (researchMarkdown) return <div className="markdown-content"><MarkdownRenderer content={researchMarkdown} /></div>;
    if (multiSource) {
      return (
        <div className="space-y-4">
          {multiSource.map((block, i) => {
            const meta = block.tool ? TOOL_BADGE[block.tool] : null;
            const analysis = block.json && ('stdout' in block.json || 'base64_chart' in block.json || 'explanation' in block.json) ? block.json : null;
            const researchMd = !analysis && block.json ? tryParseResearchJSON(block.raw) : null;
            return (
              <div key={`${block.tool || 'block'}-${i}`}>
                {/* Tool badge — shown without source-N label */}
                {meta && (
                  <div className="flex items-center gap-1.5 mb-2">
                    <meta.Icon className="w-3.5 h-3.5 text-text-muted" />
                    <span className="text-xs text-text-muted font-medium">{meta.label}</span>
                  </div>
                )}
                {analysis ? (
                  <div className="markdown-content">
                    {analysis.base64_chart && <ChartRenderer base64Chart={analysis.base64_chart} explanation={analysis.explanation} title="Data Analysis Chart" />}
                    {!analysis.base64_chart && analysis.explanation && <MarkdownRenderer content={analysis.explanation} />}
                    {analysis.stdout && (
                      <details className="mt-2 group/raw">
                        <summary className="cursor-pointer text-xs text-text-muted hover:text-text-secondary select-none list-none flex items-center gap-1.5 py-1">
                          <ChevronRight className="w-3 h-3 transition-transform group-open/raw:rotate-90" />Raw output
                        </summary>
                        <pre className="mt-1 text-xs font-mono px-3 py-2 rounded-lg bg-surface-overlay border border-border/30 overflow-x-auto whitespace-pre-wrap text-text-secondary">{analysis.stdout}</pre>
                      </details>
                    )}
                  </div>
                ) : researchMd ? (
                  <div className="markdown-content"><MarkdownRenderer content={researchMd} /></div>
                ) : (
                  <div className="markdown-content"><MarkdownRenderer content={block.raw} /></div>
                )}
              </div>
            );
          })}
        </div>
      );
    }
    if (blocks.length > 0) {
      return (
        <div className="markdown-content">
          {blocks.map(block => (
            <BlockHoverMenu key={block.id} blockId={block.id}><MarkdownRenderer content={block.text} /></BlockHoverMenu>
          ))}
          {pythonCode && <ExecutionPanel code={pythonCode} />}
        </div>
      );
    }
    return (
      <div className="markdown-content">
        <MarkdownRenderer content={message.content} />
        {pythonCode && <ExecutionPanel code={pythonCode} />}
        {message.chartData?.base64_chart && <ChartRenderer base64Chart={message.chartData.base64_chart} explanation={message.chartData.explanation} title={message.chartData.title || 'Chart'} />}
      </div>
    );
  };

  if (isUser) {
    return (
      <div className="chat-msg chat-msg-user group flex justify-end py-3 px-1">
        <div className="max-w-[75%]">
          {message.slashCommand && (
            <div className="mb-1.5"><CommandBadge command={message.slashCommand} small /></div>
          )}
          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editText}
                onChange={(e) => setEditText(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleEditSave(); }
                  if (e.key === 'Escape') handleEditCancel();
                }}
                rows={Math.min(8, editText.split('\n').length + 1)}
                autoFocus
                className="w-full px-3 py-2 text-sm rounded-xl bg-surface-overlay text-text-primary border border-accent/50 focus:outline-none focus:ring-1 focus:ring-accent resize-none leading-relaxed"
              />
              <div className="flex items-center justify-end gap-2">
                <button onClick={handleEditCancel} className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-overlay transition-colors">
                  <X className="w-3 h-3" /> Cancel
                </button>
                <button onClick={handleEditSave} disabled={!editText.trim()} className="inline-flex items-center gap-1 px-2.5 py-1.5 text-xs rounded-lg bg-accent text-white hover:bg-accent/90 transition-colors disabled:opacity-40">
                  <SendHorizonal className="w-3 h-3" /> Send
                </button>
              </div>
            </div>
          ) : (
            <>
              <div className="user-bubble">
                <p className="whitespace-pre-wrap text-[15px] leading-relaxed">{message.content}</p>
              </div>
              <div className="flex items-center justify-end gap-0.5 mt-1 opacity-0 group-hover:opacity-100 transition-opacity duration-150">
                {onEdit && (
                  <button onClick={() => { setIsEditing(true); setEditText(message.content || ''); }} title="Edit message" className="inline-flex items-center justify-center w-6 h-6 rounded-lg text-text-muted hover:text-text-secondary hover:bg-surface-overlay transition-colors">
                    <Pencil className="w-3 h-3" />
                  </button>
                )}
                {onRetry && (
                  <button onClick={() => onRetry(message)} title="Retry" className="inline-flex items-center justify-center w-6 h-6 rounded-lg text-text-muted hover:text-text-secondary hover:bg-surface-overlay transition-colors">
                    <RotateCcw className="w-3 h-3" />
                  </button>
                )}
                {onDelete && (
                  <button onClick={() => onDelete(message.id)} title="Delete" className="inline-flex items-center justify-center w-6 h-6 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-colors">
                    <Trash2 className="w-3 h-3" />
                  </button>
                )}
              </div>
            </>
          )}
        </div>
      </div>
    );
  }

  return (
    <div className="chat-msg chat-msg-ai group py-5">
      <div className="flex gap-3 w-full">
        <div className="ai-avatar shrink-0 mt-0.5"><Lightbulb className="w-4 h-4" strokeWidth={1.5} /></div>
        <div className="flex-1 min-w-0">
          {stepLog.length > 0 && (
            <AgentActionBlock stepLog={stepLog} toolsUsed={agentMeta?.tools_used || []} totalTime={agentMeta?.total_time || 0} isStreaming={false} />
          )}
          {renderAIContent()}
          {generatedFiles.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {generatedFiles.map((file, idx) => (
                <GeneratedFileCard key={`${file.filename}-${idx}`} filename={file.filename} downloadUrl={file.download_url} size={file.size} fileType={file.type} />
              ))}
            </div>
          )}
          {message.citations?.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {message.citations.map((citation, idx) => (
                <span key={citation.source || idx} className="citation"><span className="citation-number">{idx + 1}</span><span className="truncate max-w-[100px]">{citation.source || 'Source'}</span></span>
              ))}
            </div>
          )}
          <div className="ai-action-bar opacity-0 group-hover:opacity-100 transition-opacity duration-150 mt-2 flex items-center gap-0.5">
            <CopyActionButton content={message.content} />
            <ActionButton label="Good response" icon={<ThumbsUp className="w-3.5 h-3.5" />} />
            <ActionButton label="Bad response" icon={<ThumbsDown className="w-3.5 h-3.5" />} />
            {onRetry && (
              <button onClick={() => onRetry(message)} title="Regenerate response" className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-text-muted hover:text-text-secondary hover:bg-surface-overlay transition-all duration-150">
                <RotateCcw className="w-3.5 h-3.5" />
              </button>
            )}
            {onDelete && (
              <button onClick={() => onDelete(message.id)} title="Delete message" className="inline-flex items-center justify-center w-7 h-7 rounded-lg text-text-muted hover:text-red-400 hover:bg-red-400/10 transition-all duration-150">
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            )}
          </div>
          {agentMeta?.tools_used?.length > 0 && !stepLog.length && (
            <div className="flex flex-wrap gap-1.5 mt-2.5">
              {[...new Set(agentMeta.tools_used)].map(tool => {
                const b = TOOL_BADGE[tool];
                if (!b) return null;
                return (
                  <span key={tool} className="inline-flex items-center gap-1 text-xs text-text-muted px-2 py-0.5 rounded-full bg-surface-overlay/60 border border-border/20">
                    <b.Icon className="w-3 h-3" /> {b.label}
                  </span>
                );
              })}
            </div>
          )}
          {agentMeta && !stepLog.length && <AgentStepsPanel meta={agentMeta} />}
        </div>
      </div>
    </div>
  );
});

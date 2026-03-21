'use client';

import { useRef, useCallback, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  ExternalLink, Download, FileText, FileImage, FileSpreadsheet,
  FileCode, FileBox, File, Loader2, CheckCircle2, AlertCircle,
} from 'lucide-react';
import CopyButton from './CopyButton';

// ── Artifact link card (replaces plain hyperlinks to /api/artifacts/) ──

const _ARTIFACT_ICONS = {
  png: FileImage, jpg: FileImage, jpeg: FileImage, gif: FileImage,
  svg: FileImage, webp: FileImage,
  csv: FileSpreadsheet, xlsx: FileSpreadsheet, xls: FileSpreadsheet,
  json: FileCode, py: FileCode, js: FileCode, html: FileCode,
  pkl: FileBox, pt: FileBox, h5: FileBox, onnx: FileBox,
  pdf: FileText, docx: FileText, doc: FileText, pptx: FileText,
  txt: FileText, md: FileText,
};

const _ARTIFACT_COLORS = {
  png: 'text-blue-400', jpg: 'text-blue-400', jpeg: 'text-blue-400',
  svg: 'text-blue-400', webp: 'text-blue-400',
  csv: 'text-emerald-400', xlsx: 'text-emerald-400', xls: 'text-emerald-400',
  json: 'text-amber-400', py: 'text-amber-400',
  pkl: 'text-purple-400', pt: 'text-purple-400', h5: 'text-purple-400',
  pdf: 'text-red-400', docx: 'text-blue-400', pptx: 'text-orange-400',
};

function ArtifactLinkCard({ href, filename }) {
  const [state, setState] = useState('idle');
  const ext = (filename || '').split('.').pop()?.toLowerCase() || '';
  const Icon = _ARTIFACT_ICONS[ext] || File;
  const iconColor = _ARTIFACT_COLORS[ext] || 'text-text-muted';

  const handleClick = useCallback(async () => {
    if (state === 'downloading') return;
    setState('downloading');
    try {
      const res = await fetch(href);
      if (!res.ok) throw new Error('Download failed');
      const blob = await res.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || 'download';
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      setState('success');
      setTimeout(() => setState('idle'), 2000);
    } catch {
      setState('error');
      setTimeout(() => setState('idle'), 3000);
    }
  }, [href, filename, state]);

  return (
    <span
      className="flex items-center gap-3 my-2 px-3 py-2.5 rounded-lg border border-border/30 bg-surface-secondary/30 hover:bg-surface-overlay transition-colors cursor-pointer"
      onClick={handleClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && handleClick()}
    >
      <span className="flex items-center justify-center w-9 h-9 rounded-lg bg-surface-raised shrink-0">
        <Icon className={`w-4 h-4 ${state === 'error' ? 'text-red-400' : iconColor}`} />
      </span>
      <span className="flex-1 min-w-0">
        <span className="block text-sm text-text-secondary font-medium truncate">{filename}</span>
        <span className="block text-xs text-text-muted mt-0.5">
          {state === 'error' ? 'Download failed — click to retry' : 'Click to download'}
        </span>
      </span>
      <span className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md shrink-0 transition-colors ${
        state === 'success'   ? 'bg-emerald-500/20 text-emerald-400' :
        state === 'error'     ? 'bg-red-500/20 text-red-400' :
        state === 'downloading' ? 'bg-accent/20 text-accent' :
                                  'bg-accent/10 text-accent'
      }`}>
        {state === 'downloading' && <><Loader2 className="w-3 h-3 animate-spin" /><span>Saving…</span></>}
        {state === 'success'     && <><CheckCircle2 className="w-3 h-3" /><span>Saved</span></>}
        {state === 'error'       && <><AlertCircle className="w-3 h-3" /><span>Retry</span></>}
        {state === 'idle'        && <><Download className="w-3 h-3" /><span>Download</span></>}
      </span>
    </span>
  );
}

const customCodeTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: 'transparent',
    borderRadius: '0 0 12px 12px',
    margin: 0,
    padding: '20px',
    fontSize: '13px',
    lineHeight: '1.6',
  },
  'code[class*="language-"]': {
    ...oneDark['code[class*="language-"]'],
    background: 'transparent',
  },
};

const REMARK_PLUGINS = [remarkGfm, remarkMath];
const REHYPE_PLUGINS = [rehypeRaw, rehypeKatex];


export function sanitizeStreamingMarkdown(text) {
  if (!text) return '';
  let result = text;
  const fenceMatches = result.match(/^(`{3,})/gm);
  if (fenceMatches && fenceMatches.length % 2 !== 0) result += '\n```';
  const tildeFences = result.match(/^(~{3,})/gm);
  if (tildeFences && tildeFences.length % 2 !== 0) result += '\n~~~';
  return result;
}

export default function MarkdownRenderer({ content }) {
  const safeContent = typeof content === 'string' ? content : String(content || '');
  const isInsidePre = useRef(false);

  const codeComponent = useCallback(({ className, children, ...props }) => {
    const match = /language-(\w+)/.exec(className || '');
    const codeString = String(children).replace(/\n$/, '');
    const isBlock = isInsidePre.current || Boolean(match) || Boolean(className) || codeString.includes('\n');
    if (isBlock) {
      const language = match ? match[1] : 'text';
      return (
        <div className="md-code-block-wrapper group">
          <div className="md-code-header">
            <div className="md-code-controls">
              <span className="md-code-dot md-code-dot-red" />
              <span className="md-code-dot md-code-dot-amber" />
              <span className="md-code-dot md-code-dot-green" />
            </div>
            <div className="md-code-meta">
              <span className="md-code-language">{language}</span>
              <CopyButton code={codeString} />
            </div>
          </div>
          <SyntaxHighlighter
            style={customCodeTheme}
            language={language}
            PreTag="div"
            lineNumberStyle={{ minWidth: '3.25em', paddingRight: '1.5em', borderRight: '1px solid var(--border)', marginRight: '1.25em', opacity: 0.35 }}
            customStyle={{
              margin: 0,
              borderRadius: '0 0 12px 12px',
              border: '1px solid var(--border)',
              borderTop: 'none',
              background: 'transparent',
            }}
            codeTagProps={{
              style: {
                fontFamily: 'var(--font-jetbrains, "JetBrains Mono", monospace)',
                fontSize: '13px',
              }
            }}
          >
            {codeString}
          </SyntaxHighlighter>
        </div>
      );
    }
    return <code className="md-inline-code" {...props}>{children}</code>;
  }, []);

  return (
    <ReactMarkdown
      remarkPlugins={REMARK_PLUGINS}
      rehypePlugins={REHYPE_PLUGINS}
      components={{
        h1: ({ children }) => <h1 className="md-heading md-h1">{children}</h1>,
        h2: ({ children }) => <h2 className="md-heading md-h2">{children}</h2>,
        h3: ({ children }) => <h3 className="md-heading md-h3">{children}</h3>,
        h4: ({ children }) => <h4 className="md-heading md-h4">{children}</h4>,
        h5: ({ children }) => <h5 className="md-heading md-h5">{children}</h5>,
        h6: ({ children }) => <h6 className="md-heading md-h6">{children}</h6>,
        p: ({ children, node }) => {
          const hasBlock = node?.children?.some(c =>
            c.tagName === 'img' || c.tagName === 'div' || c.tagName === 'pre' || c.tagName === 'table'
          );
          if (hasBlock) return <div className="md-paragraph">{children}</div>;
          return <p className="md-paragraph">{children}</p>;
        },
        ul: ({ children, className }) => {
          const isTaskList = className?.includes('contains-task-list');
          return <ul className={`md-list md-ul ${isTaskList ? 'md-task-list' : ''}`}>{children}</ul>;
        },
        ol: ({ children, start }) => <ol className="md-list md-ol" start={start}>{children}</ol>,
        li: ({ children, className }) => {
          const isTask = className?.includes('task-list-item');
          return <li className={`md-list-item ${isTask ? 'md-task-item' : ''}`}>{children}</li>;
        },
        input: ({ checked, type, ...props }) => {
          if (type === 'checkbox') return <input type="checkbox" checked={checked} readOnly className="md-task-checkbox" {...props} />;
          return <input type={type} {...props} />;
        },
        code: codeComponent,
        pre: ({ children }) => {
          isInsidePre.current = true;
          const result = <>{children}</>;
          isInsidePre.current = false;
          return result;
        },
        blockquote: ({ children }) => (
          <blockquote className="md-blockquote"><div className="md-blockquote-content">{children}</div></blockquote>
        ),
        a: ({ href, children }) => {
          // Render artifact links as download cards instead of plain hyperlinks
          if (href && href.includes('/api/artifacts/')) {
            const filename = typeof children === 'string'
              ? children
              : Array.isArray(children)
                ? children.map(c => (typeof c === 'string' ? c : '')).join('')
                : String(children || '');
            return <ArtifactLinkCard href={href} filename={filename.trim() || href.split('/').pop()} />;
          }
          return (
            <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
              {children}<ExternalLink className="w-3 h-3 inline-block ml-0.5 opacity-50" />
            </a>
          );
        },
        table: ({ children }) => <div className="md-table-wrapper"><table className="md-table">{children}</table></div>,
        thead: ({ children }) => <thead className="md-thead">{children}</thead>,
        tbody: ({ children }) => <tbody className="md-tbody">{children}</tbody>,
        tr: ({ children }) => <tr className="md-tr">{children}</tr>,
        th: ({ children, style }) => <th className="md-th" style={style}>{children}</th>,
        td: ({ children, style }) => <td className="md-td" style={style}>{children}</td>,
        strong: ({ children }) => <strong className="md-strong">{children}</strong>,
        em: ({ children }) => <em className="md-em">{children}</em>,
        del: ({ children }) => <del className="md-del">{children}</del>,
        hr: () => <hr className="md-hr" />,
        img: ({ src, alt }) => (
          <div className="md-image-wrapper">
            {/* eslint-disable-next-line @next/next/no-img-element -- user-provided markdown image; src/dimensions unknown at build time */}
            <img src={src} alt={alt} className="md-image" loading="lazy" />
            {alt && <span className="md-image-caption">{alt}</span>}
          </div>
        ),
        details: ({ children }) => <details className="md-details">{children}</details>,
        summary: ({ children }) => <summary className="md-summary">{children}</summary>,
        sup: ({ children }) => <sup className="md-sup">{children}</sup>,
        sub: ({ children }) => <sub className="md-sub">{children}</sub>,
      }}
    >
      {safeContent}
    </ReactMarkdown>
  );
}

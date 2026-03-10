'use client';

import { useRef, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkMath from 'remark-math';
import rehypeRaw from 'rehype-raw';
import rehypeKatex from 'rehype-katex';
import 'katex/dist/katex.min.css';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { ExternalLink } from 'lucide-react';
import CopyButton from './CopyButton';

const customCodeTheme = {
  ...oneDark,
  'pre[class*="language-"]': {
    ...oneDark['pre[class*="language-"]'],
    background: 'var(--surface-sunken)',
    borderRadius: '0 0 12px 12px',
    margin: 0,
    padding: '16px',
    fontSize: '13px',
    lineHeight: '1.7',
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
        <div className="md-code-block-wrapper">
          <div className="md-code-header">
            <span className="md-code-language">{language}</span>
            <CopyButton code={codeString} />
          </div>
          <SyntaxHighlighter
            style={customCodeTheme}
            language={language}
            PreTag="div"
            customStyle={{ margin: 0, borderRadius: '0 0 12px 12px', border: '1px solid var(--border)', borderTop: 'none' }}
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
        a: ({ href, children }) => (
          <a href={href} target="_blank" rel="noopener noreferrer" className="md-link">
            {children}<ExternalLink className="w-3 h-3 inline-block ml-0.5 opacity-50" />
          </a>
        ),
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

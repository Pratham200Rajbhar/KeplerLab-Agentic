'use client';

import { useMemo } from 'react';
import { Table, Code, FileText } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const STRUCTURED_EXTS = ['csv', 'tsv', 'xlsx', 'xls', 'ods'];
const CODE_EXTS = ['json', 'xml', 'html', 'js', 'ts', 'jsx', 'tsx', 'py', 'java', 'c', 'cpp', 'rb', 'go', 'rs', 'sh', 'yaml', 'yml', 'toml', 'ini', 'cfg', 'sql'];
const MARKDOWN_EXTS = ['md', 'markdown'];

function getFileExt(filename) {
  if (!filename) return '';
  return filename.split('.').pop()?.toLowerCase() || '';
}

function parseStructuredText(text) {
  const sections = [];
  const sectionRegex = /===\s*(.+?)\s*===/g;
  let match;
  const splits = [];
  while ((match = sectionRegex.exec(text)) !== null) {
    splits.push({ label: match[1], start: match.index + match[0].length });
  }
  if (splits.length === 0) {
    sections.push({ label: 'Data', content: text.trim() });
  } else {
    for (let i = 0; i < splits.length; i++) {
      const end = i + 1 < splits.length ? text.lastIndexOf('===', splits[i + 1].start - 3) : text.length;
      sections.push({ label: splits[i].label, content: text.slice(splits[i].start, end).trim() });
    }
  }
  return sections.map(s => ({ label: s.label, ...parseTabularContent(s.content) }));
}

function parseTabularContent(text) {
  const lines = text.split('\n').filter(l => l.trim());
  if (lines.length === 0) return { headers: [], rows: [], raw: text };
  const headerLine = lines[0];
  const headers = headerLine.trim().split(/\s{2,}/).map(h => h.trim()).filter(Boolean);
  if (headers.length < 2) return { headers: [], rows: [], raw: text };
  const colPositions = [];
  let searchStart = 0;
  for (const header of headers) {
    const idx = headerLine.indexOf(header, searchStart);
    colPositions.push(idx);
    searchStart = idx + header.length;
  }
  const rows = [];
  for (let i = 1; i < lines.length; i++) {
    const line = lines[i];
    const cells = [];
    for (let c = 0; c < colPositions.length; c++) {
      const start = colPositions[c];
      const end = c + 1 < colPositions.length ? colPositions[c + 1] : line.length;
      cells.push(line.slice(start, end).trim());
    }
    rows.push(cells);
  }
  return { headers, rows, raw: text };
}

function formatCell(value) {
  if (value === '' || value === 'NaN' || value === 'nan') return <span className="doc-preview-null">—</span>;
  if (/^-?\d+(\.\d+)?$/.test(value)) return <span className="doc-preview-number">{value}</span>;
  return value;
}

function DataTable({ headers, rows, label, maxRows = 200 }) {
  const displayRows = rows.slice(0, maxRows);
  const hasMore = rows.length > maxRows;
  return (
    <div className="doc-preview-table-section">
      {label && (
        <div className="doc-preview-sheet-label">
          <Table className="w-4 h-4" /><span>{label}</span>
          <span className="doc-preview-row-count">{rows.length} rows × {headers.length} cols</span>
        </div>
      )}
      <div className="doc-preview-table-wrapper">
        <table className="doc-preview-table">
          <thead><tr><th className="doc-preview-th doc-preview-th-index">#</th>{headers.map((h, i) => <th key={i} className="doc-preview-th">{h}</th>)}</tr></thead>
          <tbody>{displayRows.map((row, ri) => (
            <tr key={ri} className={ri % 2 === 0 ? 'doc-preview-tr-even' : 'doc-preview-tr-odd'}>
              <td className="doc-preview-td doc-preview-td-index">{ri}</td>
              {row.map((cell, ci) => <td key={ci} className="doc-preview-td">{formatCell(cell)}</td>)}
            </tr>
          ))}</tbody>
        </table>
      </div>
      {hasMore && <div className="doc-preview-truncated">Showing {maxRows} of {rows.length} rows</div>}
    </div>
  );
}

function CodePreview({ text, language }) {
  return (
    <div className="doc-preview-code-section">
      <div className="doc-preview-code-header"><Code className="w-4 h-4" /><span>{language.toUpperCase()}</span></div>
      <div className="doc-preview-code-content"><MarkdownRenderer content={`\`\`\`${language}\n${text}\n\`\`\``} /></div>
    </div>
  );
}

function getTypeBadge(type) {
  const badges = {
    pdf: { label: 'PDF Document', color: 'text-red-400 bg-red-500/10 border-red-500/20' },
    doc: { label: 'Word Document', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
    docx: { label: 'Word Document', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20' },
    pptx: { label: 'Presentation', color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
    ppt: { label: 'Presentation', color: 'text-orange-400 bg-orange-500/10 border-orange-500/20' },
    txt: { label: 'Plain Text', color: 'text-gray-400 bg-gray-500/10 border-gray-500/20' },
    md: { label: 'Markdown', color: 'text-purple-400 bg-purple-500/10 border-purple-500/20' },
    rtf: { label: 'Rich Text', color: 'text-teal-400 bg-teal-500/10 border-teal-500/20' },
  };
  const badge = badges[type] || { label: 'Document', color: 'text-gray-400 bg-gray-500/10 border-gray-500/20' };
  return <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${badge.color}`}>{badge.label}</span>;
}

function TextPreview({ text, type }) {
  const sections = useMemo(() => {
    const sectionRegex = /===\s*(.+?)\s*===/g;
    const parts = [];
    let lastEnd = 0;
    let match;
    while ((match = sectionRegex.exec(text)) !== null) {
      if (match.index > lastEnd) {
        const before = text.slice(lastEnd, match.index).trim();
        if (before) parts.push({ type: 'text', content: before });
      }
      parts.push({ type: 'header', content: match[1] });
      lastEnd = match.index + match[0].length;
    }
    if (lastEnd < text.length) {
      const rest = text.slice(lastEnd).trim();
      if (rest) parts.push({ type: 'text', content: rest });
    }
    return parts.length > 0 ? parts : [{ type: 'text', content: text }];
  }, [text]);

  return (
    <div className="doc-preview-text-section">
      <div className="doc-preview-type-badge">{getTypeBadge(type)}</div>
      <div className="doc-preview-text-content">
        {sections.map((section, i) => {
          if (section.type === 'header') {
            return (
              <div key={i} className="doc-preview-section-header">
                <div className="doc-preview-section-line" /><span>{section.content}</span><div className="doc-preview-section-line" />
              </div>
            );
          }
          return <div key={i} className="doc-preview-text-block markdown-content"><MarkdownRenderer content={section.content} /></div>;
        })}
      </div>
    </div>
  );
}

export default function DocumentPreview({ content, filename }) {
  const ext = getFileExt(filename);

  const rendered = useMemo(() => {
    if (!content) return null;
    if (STRUCTURED_EXTS.includes(ext)) {
      const tables = parseStructuredText(content);
      const hasValidTables = tables.some(t => t.headers && t.headers.length >= 2);
      if (hasValidTables) {
        return (
          <div className="doc-preview-structured">
            <div className="doc-preview-type-badge">
              <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
                <Table className="w-3.5 h-3.5" />Spreadsheet Data
              </span>
            </div>
            {tables.map((table, i) =>
              table.headers && table.headers.length >= 2
                ? <DataTable key={i} headers={table.headers} rows={table.rows} label={table.label} />
                : <pre key={i} className="doc-preview-raw">{table.raw}</pre>
            )}
          </div>
        );
      }
    }
    if (CODE_EXTS.includes(ext)) {
      const lang = ext === 'yml' ? 'yaml' : ext === 'js' ? 'javascript' : ext === 'ts' ? 'typescript' : ext === 'py' ? 'python' : ext === 'rb' ? 'ruby' : ext;
      return <CodePreview text={content} language={lang} />;
    }
    if (MARKDOWN_EXTS.includes(ext)) {
      return (
        <div className="doc-preview-text-section">
          <div className="doc-preview-type-badge">{getTypeBadge(ext)}</div>
          <div className="doc-preview-text-block markdown-content"><MarkdownRenderer content={content} /></div>
        </div>
      );
    }
    return <TextPreview text={content} type={ext || 'txt'} />;
  }, [content, ext]);

  if (!content) {
    return (
      <div className="doc-preview-empty">
        <FileText className="w-12 h-12 text-text-muted/30" strokeWidth={1.5} />
        <p className="text-sm text-text-muted mt-3">No text content available for this source.</p>
      </div>
    );
  }

  return <div className="doc-preview-root">{rendered}</div>;
}

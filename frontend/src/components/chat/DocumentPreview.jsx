'use client';

import { useMemo } from 'react';
import {
  Table, Code, FileText, FileCode, AlignLeft, Hash, Layers,
  BookOpen, Database, Braces, Globe, SplitSquareHorizontal,
} from 'lucide-react';
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
    pdf:  { label: 'PDF Document',  color: 'text-red-400 bg-red-500/10 border-red-500/20',       icon: <FileText className="w-3 h-3" /> },
    doc:  { label: 'Word Document', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',     icon: <FileText className="w-3 h-3" /> },
    docx: { label: 'Word Document', color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',     icon: <FileText className="w-3 h-3" /> },
    pptx: { label: 'Presentation',  color: 'text-orange-400 bg-orange-500/10 border-orange-500/20', icon: <Layers className="w-3 h-3" /> },
    ppt:  { label: 'Presentation',  color: 'text-orange-400 bg-orange-500/10 border-orange-500/20', icon: <Layers className="w-3 h-3" /> },
    txt:  { label: 'Plain Text',    color: 'text-gray-400 bg-gray-500/10 border-gray-500/20',     icon: <AlignLeft className="w-3 h-3" /> },
    md:   { label: 'Markdown',      color: 'text-purple-400 bg-purple-500/10 border-purple-500/20', icon: <Hash className="w-3 h-3" /> },
    markdown: { label: 'Markdown',  color: 'text-purple-400 bg-purple-500/10 border-purple-500/20', icon: <Hash className="w-3 h-3" /> },
    rtf:  { label: 'Rich Text',     color: 'text-teal-400 bg-teal-500/10 border-teal-500/20',     icon: <BookOpen className="w-3 h-3" /> },
    json: { label: 'JSON',          color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20', icon: <Braces className="w-3 h-3" /> },
    xml:  { label: 'XML',           color: 'text-pink-400 bg-pink-500/10 border-pink-500/20',     icon: <Code className="w-3 h-3" /> },
    html: { label: 'HTML',          color: 'text-orange-400 bg-orange-500/10 border-orange-500/20', icon: <Globe className="w-3 h-3" /> },
    csv:  { label: 'CSV Data',      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', icon: <Database className="w-3 h-3" /> },
    tsv:  { label: 'TSV Data',      color: 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20', icon: <Database className="w-3 h-3" /> },
    xlsx: { label: 'Spreadsheet',   color: 'text-green-400 bg-green-500/10 border-green-500/20',  icon: <Table className="w-3 h-3" /> },
    xls:  { label: 'Spreadsheet',   color: 'text-green-400 bg-green-500/10 border-green-500/20',  icon: <Table className="w-3 h-3" /> },
    ods:  { label: 'Spreadsheet',   color: 'text-green-400 bg-green-500/10 border-green-500/20',  icon: <Table className="w-3 h-3" /> },
    py:   { label: 'Python',        color: 'text-sky-400 bg-sky-500/10 border-sky-500/20',         icon: <FileCode className="w-3 h-3" /> },
    js:   { label: 'JavaScript',    color: 'text-yellow-400 bg-yellow-500/10 border-yellow-500/20', icon: <FileCode className="w-3 h-3" /> },
    ts:   { label: 'TypeScript',    color: 'text-blue-400 bg-blue-500/10 border-blue-500/20',     icon: <FileCode className="w-3 h-3" /> },
    sql:  { label: 'SQL',           color: 'text-indigo-400 bg-indigo-500/10 border-indigo-500/20', icon: <SplitSquareHorizontal className="w-3 h-3" /> },
    yaml: { label: 'YAML',          color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',     icon: <FileCode className="w-3 h-3" /> },
    yml:  { label: 'YAML',          color: 'text-rose-400 bg-rose-500/10 border-rose-500/20',     icon: <FileCode className="w-3 h-3" /> },
    toml: { label: 'TOML',          color: 'text-amber-400 bg-amber-500/10 border-amber-500/20',  icon: <FileCode className="w-3 h-3" /> },
    sh:   { label: 'Shell Script',  color: 'text-gray-400 bg-gray-500/10 border-gray-500/20',    icon: <FileCode className="w-3 h-3" /> },
  };
  const badge = badges[type] || { label: 'Document', color: 'text-gray-400 bg-gray-500/10 border-gray-500/20', icon: <FileText className="w-3 h-3" /> };
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${badge.color}`}>
      {badge.icon}{badge.label}
    </span>
  );
}

function getDocStats(text) {
  const words = text.trim().split(/\s+/).filter(Boolean).length;
  const lines = text.split('\n').length;
  const chars = text.length;
  const sections = (text.match(/===\s*.+?\s*===/g) || []).length;
  return { words, lines, chars, sections };
}

function splitKeyValuePairs(line) {
  const pairs = [];
  const pairRegex = /([A-Za-z][A-Za-z0-9 _-]{1,40}):\s*([^\n]+?)(?=\s+[A-Za-z][A-Za-z0-9 _-]{1,40}:|$)/g;
  let match;
  while ((match = pairRegex.exec(line)) !== null) {
    const key = match[1].trim();
    const value = match[2].trim();
    if (key && value) pairs.push({ key, value });
  }
  return pairs;
}

function normalizeTranscriptText(text) {
  if (!text) return '';
  if (text.includes('\n')) return text;

  // Add breathing space in long single-line transcripts.
  const punctuated = text.replace(/([.!?।])\s+/g, '$1\n');
  if (punctuated.includes('\n')) return punctuated;

  const words = text.split(/\s+/).filter(Boolean);
  const lines = [];
  for (let i = 0; i < words.length; i += 18) {
    lines.push(words.slice(i, i + 18).join(' '));
  }
  return lines.join('\n');
}

function parseResourceStructuredContent(text) {
  const lines = text.split('\n');
  const metadata = [];
  const sections = [];
  let sawBody = false;
  let currentSection = null;

  const flushSection = () => {
    if (!currentSection) return;
    const content = currentSection.content.join('\n').trim();
    if (content) {
      sections.push({
        title: currentSection.title,
        kind: currentSection.kind,
        content: currentSection.kind === 'transcript' ? normalizeTranscriptText(content) : content,
      });
    }
    currentSection = null;
  };

  for (const rawLine of lines) {
    const line = rawLine.trim();

    if (!line) {
      if (currentSection) currentSection.content.push('');
      continue;
    }

    const sectionMatch = line.match(/^(Description|Transcript|Summary|Notes|Key Points)\s*:\s*(.*)$/i);
    if (sectionMatch) {
      sawBody = true;
      flushSection();
      const title = sectionMatch[1][0].toUpperCase() + sectionMatch[1].slice(1).toLowerCase();
      const kind = title.toLowerCase() === 'transcript' ? 'transcript' : 'text';
      currentSection = { title, kind, content: [] };
      if (sectionMatch[2]) currentSection.content.push(sectionMatch[2]);
      continue;
    }

    if (!sawBody) {
      const pairs = splitKeyValuePairs(line);
      if (pairs.length > 0) {
        metadata.push(...pairs);
        continue;
      }
    }

    sawBody = true;
    if (!currentSection) {
      currentSection = { title: 'Content', kind: 'text', content: [] };
    }
    currentSection.content.push(rawLine);
  }

  flushSection();

  if (metadata.length < 2 && sections.length === 0) {
    return null;
  }

  return { metadata, sections };
}

function DocStatsBar({ text }) {
  const stats = useMemo(() => getDocStats(text), [text]);
  return (
    <div className="doc-preview-stats-bar">
      <span>{stats.words.toLocaleString()} words</span>
      <span className="doc-preview-stats-sep" />
      <span>{stats.lines.toLocaleString()} lines</span>
      <span className="doc-preview-stats-sep" />
      <span>{stats.chars >= 1000 ? `${(stats.chars / 1000).toFixed(1)}k` : stats.chars} chars</span>
      {stats.sections > 0 && (
        <><span className="doc-preview-stats-sep" /><span>{stats.sections} sections</span></>
      )}
    </div>
  );
}

function TextPreview({ text, type }) {
  const structured = useMemo(() => parseResourceStructuredContent(text), [text]);
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
      <div className="doc-preview-header-row">
        <div className="doc-preview-type-badge">{getTypeBadge(type)}</div>
        <DocStatsBar text={text} />
      </div>

      {structured && (
        <div className="mb-5 space-y-4">
          {structured.metadata.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {structured.metadata.map((item, idx) => (
                <div key={`${item.key}-${idx}`} className="rounded-lg border border-border bg-surface-raised/50 p-3">
                  <div className="text-[11px] uppercase tracking-wide text-text-muted mb-1">{item.key}</div>
                  {item.value.startsWith('http://') || item.value.startsWith('https://') ? (
                    <a
                      href={item.value}
                      target="_blank"
                      rel="noreferrer"
                      className="text-sm text-accent-light hover:underline break-all"
                    >
                      {item.value}
                    </a>
                  ) : (
                    <div className="text-sm text-text-primary leading-relaxed break-words">{item.value}</div>
                  )}
                </div>
              ))}
            </div>
          )}

          {structured.sections.length > 0 && (
            <div className="space-y-3">
              {structured.sections.map((section, idx) => (
                <div key={`${section.title}-${idx}`} className="rounded-lg border border-border bg-surface-overlay/50 p-3 sm:p-4">
                  <div className="text-xs font-semibold uppercase tracking-wide text-text-secondary mb-2">{section.title}</div>
                  {section.kind === 'transcript' ? (
                    <pre className="text-[13px] leading-7 text-text-primary whitespace-pre-wrap break-words font-sans">
                      {section.content}
                    </pre>
                  ) : (
                    <div className="text-sm text-text-secondary whitespace-pre-wrap leading-relaxed">
                      {section.content}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!structured && (
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
      )}
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
            <div className="doc-preview-header-row">
              <div className="doc-preview-type-badge">
                <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border text-emerald-400 bg-emerald-500/10 border-emerald-500/20">
                  <Table className="w-3 h-3" />Spreadsheet Data
                </span>
              </div>
              <DocStatsBar text={content} />
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
          <div className="doc-preview-header-row">
            <div className="doc-preview-type-badge">{getTypeBadge(ext)}</div>
            <DocStatsBar text={content} />
          </div>
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

'use client';

import { useState, useCallback, memo } from 'react';
import {
  X,
  Pin,
  PinOff,
  BarChart3,
  FileDown,
  Table2,
  Code2,
  Download,
  Copy,
  Check,
} from 'lucide-react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';

/**
 * ArtifactPanel — sliding right panel that appears when agent produces artifacts.
 *
 * Triggered by `artifact` SSE event or clicking any artifact in chat.
 *
 * Tabs: Charts | Files | Tables | Code
 * Pin/unpin keeps panel open. Unpinned closes after user interaction.
 */

const TABS = [
  { id: 'charts', label: 'Charts', Icon: BarChart3 },
  { id: 'files',  label: 'Files',  Icon: FileDown },
  { id: 'tables', label: 'Tables', Icon: Table2 },
  { id: 'code',   label: 'Code',   Icon: Code2 },
];

function TabButton({ tab, count, isActive, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg transition-all ${
        isActive
          ? 'bg-accent/15 text-accent border border-accent/30'
          : 'text-text-muted hover:text-text-secondary hover:bg-surface-overlay/40 border border-transparent'
      }`}
      aria-selected={isActive}
      role="tab"
    >
      <tab.Icon className="w-3.5 h-3.5" />
      {tab.label}
      {count > 0 && (
        <span className={`text-[10px] px-1 py-0 rounded-full ${
          isActive ? 'bg-accent/20 text-accent' : 'bg-surface-overlay text-text-muted'
        }`}>{count}</span>
      )}
    </button>
  );
}

/* ── Tab Content ── */
function ChartTab({ charts, onDownload }) {
  if (!charts.length) return <EmptyTab label="No charts" />;
  return (
    <div className="space-y-4 p-4">
      {charts.map((chart, i) => (
        <div key={chart.id || i} className="space-y-2">
          {chart.title && <p className="text-sm font-medium text-text-secondary">{chart.title}</p>}
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={chart.url || chart.src || `data:image/png;base64,${chart.base64}`}
            alt={chart.title || `Chart ${i + 1}`}
            className="w-full rounded-lg max-h-80 object-contain bg-surface-sunken"
          />
          <button
            onClick={() => onDownload?.(chart)}
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 transition-colors"
            aria-label={`Download ${chart.title || 'chart'} as PNG`}
          >
            <Download className="w-3.5 h-3.5" />
            Download PNG
          </button>
        </div>
      ))}
    </div>
  );
}

function FilesTab({ files }) {
  if (!files.length) return <EmptyTab label="No files" />;
  return (
    <div className="space-y-1 p-4">
      {files.map((file, i) => (
        <a
          key={file.id || i}
          href={file.download_url || file.url || '#'}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-3 px-3 py-2.5 rounded-lg hover:bg-surface-overlay/40 transition-colors group"
        >
          <FileDown className="w-4 h-4 text-text-muted shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-sm text-text-secondary truncate">{file.filename || file.name}</p>
            {file.size && (
              <p className="text-[11px] text-text-muted">{formatFileSize(file.size)}</p>
            )}
          </div>
          <Download className="w-3.5 h-3.5 text-text-muted opacity-0 group-hover:opacity-100 transition-opacity" />
        </a>
      ))}
    </div>
  );
}

function TablesTab({ tables }) {
  const [copiedIdx, setCopiedIdx] = useState(null);

  if (!tables.length) return <EmptyTab label="No tables" />;

  const handleCopyCSV = async (table, idx) => {
    const headers = table.headers || [];
    const rows = table.rows || [];
    const csv = [headers.join(','), ...rows.map((r) => r.join(','))].join('\n');
    await navigator.clipboard.writeText(csv);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="space-y-4 p-4">
      {tables.map((table, i) => (
        <div key={table.id || i} className="space-y-2">
          {table.title && <p className="text-sm font-medium text-text-secondary">{table.title}</p>}
          <div className="overflow-auto max-h-64 rounded-lg border border-border/20">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-surface-raised">
                <tr>
                  {(table.headers || []).map((h, j) => (
                    <th key={j} className="px-2.5 py-1.5 text-left font-medium text-text-muted border-b border-border/20">
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {(table.rows || []).map((row, ri) => (
                  <tr key={ri} className="border-b border-border/10 last:border-0">
                    {row.map((cell, ci) => (
                      <td key={ci} className="px-2.5 py-1.5 text-text-secondary">{cell}</td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <button
            onClick={() => handleCopyCSV(table, i)}
            className="inline-flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 transition-colors"
            aria-label="Copy table as CSV"
          >
            {copiedIdx === i ? (
              <><Check className="w-3.5 h-3.5" /> Copied</>
            ) : (
              <><Copy className="w-3.5 h-3.5" /> Copy as CSV</>
            )}
          </button>
        </div>
      ))}
    </div>
  );
}

function CodeTab({ codeBlocks }) {
  const [copiedIdx, setCopiedIdx] = useState(null);

  if (!codeBlocks.length) return <EmptyTab label="No code" />;

  const handleCopy = async (code, idx) => {
    await navigator.clipboard.writeText(code);
    setCopiedIdx(idx);
    setTimeout(() => setCopiedIdx(null), 2000);
  };

  return (
    <div className="space-y-4 p-4">
      {codeBlocks.map((block, i) => (
        <div key={block.id || i} className="space-y-1">
          {block.title && <p className="text-sm font-medium text-text-secondary">{block.title}</p>}
          <div className="rounded-lg overflow-hidden border border-border/20">
            <div className="flex items-center justify-between px-2.5 py-1 border-b border-border/20">
              <span className="text-[10px] text-text-muted uppercase tracking-wide">
                {block.language || 'code'}
              </span>
              <button
                onClick={() => handleCopy(block.code, i)}
                className="text-[11px] px-2 py-0.5 rounded bg-surface-overlay hover:bg-surface-raised text-text-muted transition-all"
                aria-label="Copy code"
              >
                {copiedIdx === i ? '✓ copied' : 'copy'}
              </button>
            </div>
            <div className="max-h-64 overflow-y-auto">
              <SyntaxHighlighter
                language={block.language || 'python'}
                style={oneDark}
                customStyle={{ margin: 0, padding: '10px 12px', fontSize: '12px', lineHeight: '1.6', background: 'var(--surface-sunken)' }}
              >
                {block.code}
              </SyntaxHighlighter>
            </div>
          </div>
        </div>
      ))}
    </div>
  );
}

function EmptyTab({ label }) {
  return (
    <div className="flex items-center justify-center h-32 text-xs text-text-muted">{label}</div>
  );
}

function formatFileSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1048576) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1048576).toFixed(1)} MB`;
}

/* ── Main Panel ── */
function ArtifactPanel({ isOpen, onClose, artifacts = {} }) {
  const [activeTab, setActiveTab] = useState(null);
  const [isPinned, setIsPinned] = useState(false);

  const charts = artifacts.charts || [];
  const files = artifacts.files || [];
  const tables = artifacts.tables || [];
  const codeBlocks = artifacts.code || [];

  // Auto-select first tab with content
  const resolvedTab = activeTab || (
    charts.length ? 'charts' :
    files.length ? 'files' :
    tables.length ? 'tables' :
    codeBlocks.length ? 'code' : 'charts'
  );

  const counts = { charts: charts.length, files: files.length, tables: tables.length, code: codeBlocks.length };
  const totalArtifacts = charts.length + files.length + tables.length + codeBlocks.length;

  // Skip tabs if only one type has artifacts
  const hasMultipleTypes = [charts.length, files.length, tables.length, codeBlocks.length].filter(Boolean).length > 1;

  const handleDownloadChart = useCallback((chart) => {
    const link = document.createElement('a');
    link.href = chart.url || chart.src || `data:image/png;base64,${chart.base64}`;
    link.download = `${chart.title || 'chart'}.png`;
    link.click();
  }, []);

  if (!isOpen || !totalArtifacts) return null;

  return (
    <div
      className="fixed right-0 top-0 h-full w-[400px] max-w-full bg-surface-raised border-l border-border/30 z-50 flex flex-col shadow-2xl"
      style={{ animation: 'slideInRight 0.25s ease-out' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-border/20">
        <span className="text-sm font-semibold text-text-primary">Artifacts</span>
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setIsPinned((v) => !v)}
            className="btn-icon p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted transition-all"
            title={isPinned ? 'Unpin panel' : 'Pin panel open'}
            aria-label={isPinned ? 'Unpin artifact panel' : 'Pin artifact panel open'}
          >
            {isPinned ? <PinOff className="w-3.5 h-3.5" /> : <Pin className="w-3.5 h-3.5" />}
          </button>
          <button
            onClick={onClose}
            className="btn-icon p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted transition-all"
            title="Close"
            aria-label="Close artifact panel"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Tab bar */}
      {hasMultipleTypes && (
        <div className="flex items-center gap-1 px-3 py-2 border-b border-border/10" role="tablist">
          {TABS.map((tab) => (
            <TabButton
              key={tab.id}
              tab={tab}
              count={counts[tab.id]}
              isActive={resolvedTab === tab.id}
              onClick={() => setActiveTab(tab.id)}
            />
          ))}
        </div>
      )}

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {resolvedTab === 'charts' && <ChartTab charts={charts} onDownload={handleDownloadChart} />}
        {resolvedTab === 'files' && <FilesTab files={files} />}
        {resolvedTab === 'tables' && <TablesTab tables={tables} />}
        {resolvedTab === 'code' && <CodeTab codeBlocks={codeBlocks} />}
      </div>

      <style jsx>{`
        @keyframes slideInRight {
          from { transform: translateX(100%); }
          to   { transform: translateX(0); }
        }
      `}</style>
    </div>
  );
}

export default memo(ArtifactPanel);

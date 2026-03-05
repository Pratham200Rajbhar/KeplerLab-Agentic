'use client';

import { memo, useState, useEffect, useCallback } from 'react';
import { Table2, ChevronDown, ChevronUp, Download, AlertCircle, Loader2 } from 'lucide-react';

/**
 * ArtifactTablePreview — displays a preview of CSV/JSON data as a table.
 * 
 * Features:
 * - Shows first 10 rows by default
 * - Expandable to show more rows
 * - Scrollable for wide tables
 * - Download button
 *
 * Props:
 *   artifact: { id, filename, downloadUrl, size }
 *   onDownload: (artifact) => void
 *   maxPreviewRows: number (default: 10)
 */

const MAX_PREVIEW_ROWS = 10;
const MAX_EXPANDED_ROWS = 100;

function ArtifactTablePreview({ artifact, onDownload, maxPreviewRows = MAX_PREVIEW_ROWS }) {
  // Initialize loading state based on whether we have a URL
  const hasUrl = Boolean(artifact.downloadUrl);
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(hasUrl);
  const [error, setError] = useState(hasUrl ? null : 'No download URL');
  const [isExpanded, setIsExpanded] = useState(false);

  const isCSV = artifact.filename?.toLowerCase().endsWith('.csv');
  const isJSON = artifact.filename?.toLowerCase().endsWith('.json');

  // Fetch and parse data
  useEffect(() => {
    if (!artifact.downloadUrl) {
      return;
    }

    let cancelled = false;

    (async () => {
      try {
        const res = await fetch(artifact.downloadUrl);
        if (!res.ok) throw new Error('Failed to fetch');
        
        const result = isJSON ? await res.json() : await res.text();
        if (cancelled) return;

        if (isJSON) {
          setData(parseJSONToTable(result));
        } else if (isCSV) {
          setData(parseCSVToTable(result));
        } else {
          setError('Unsupported format');
        }
      } catch (err) {
        if (!cancelled) {
          setError(err.message || 'Failed to load data');
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    })();

    return () => { cancelled = true; };
  }, [artifact.downloadUrl, isCSV, isJSON]);

  const handleDownload = useCallback(() => {
    onDownload?.(artifact);
  }, [artifact, onDownload]);

  // Handle case where there's no download URL
  if (!artifact.downloadUrl) {
    return <DownloadFallback artifact={artifact} onDownload={handleDownload} />;
  }

  // Loading state
  if (loading) {
    return (
      <div className="rounded-lg border border-border/30 p-4">
        <div className="flex items-center gap-2 text-text-muted">
          <Loader2 className="w-4 h-4 animate-spin" />
          <span className="text-sm">Loading table preview...</span>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="rounded-lg border border-border/30 p-4">
        <div className="flex items-center gap-2 text-red-400 mb-3">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm">{error}</span>
        </div>
        <DownloadFallback artifact={artifact} onDownload={handleDownload} />
      </div>
    );
  }

  if (!data || !data.headers || data.headers.length === 0) {
    return <DownloadFallback artifact={artifact} onDownload={handleDownload} />;
  }

  const { headers, rows } = data;
  const totalRows = rows.length;
  const displayRows = isExpanded
    ? rows.slice(0, MAX_EXPANDED_ROWS)
    : rows.slice(0, maxPreviewRows);
  const hasMore = totalRows > displayRows.length;
  const canExpand = totalRows > maxPreviewRows;

  return (
    <div className="rounded-lg border border-border/30 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-3 py-2 bg-surface-raised/50 border-b border-border/20">
        <div className="flex items-center gap-2">
          <Table2 className="w-4 h-4 text-emerald-400" />
          <span className="text-sm text-text-secondary font-medium truncate">
            {artifact.filename}
          </span>
          <span className="text-xs text-text-muted">
            ({totalRows} row{totalRows !== 1 ? 's' : ''})
          </span>
        </div>
        {onDownload && (
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 transition-colors"
          >
            <Download className="w-3 h-3" />
            Download
          </button>
        )}
      </div>

      {/* Table */}
      <div className="overflow-x-auto" style={{ maxHeight: isExpanded ? '500px' : '320px' }}>
        <table className="w-full text-xs font-mono">
          <thead className="sticky top-0 bg-surface-raised z-10">
            <tr>
              <th className="text-left px-2.5 py-2 text-text-muted font-normal border-b border-border/30 w-10">
                #
              </th>
              {headers.map((header, i) => (
                <th
                  key={i}
                  className="text-left px-2.5 py-2 text-text-secondary font-medium border-b border-border/30 whitespace-nowrap"
                >
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayRows.map((row, ri) => (
              <tr
                key={ri}
                className={ri % 2 === 0 ? 'bg-surface-primary/10' : 'bg-surface-secondary/10'}
              >
                <td className="px-2.5 py-1.5 text-text-muted border-r border-border/10">
                  {ri + 1}
                </td>
                {row.map((cell, ci) => (
                  <td
                    key={ci}
                    className="px-2.5 py-1.5 text-text-secondary whitespace-nowrap max-w-[200px] truncate"
                    title={String(cell)}
                  >
                    {formatCell(cell)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Footer with expand/collapse */}
      {(canExpand || hasMore) && (
        <div className="flex items-center justify-between px-3 py-2 bg-surface-raised/30 border-t border-border/20">
          {hasMore && (
            <span className="text-xs text-text-muted">
              Showing {displayRows.length} of {totalRows} rows
            </span>
          )}
          {canExpand && (
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors ml-auto"
            >
              {isExpanded ? (
                <>
                  <ChevronUp className="w-3 h-3" />
                  Show less
                </>
              ) : (
                <>
                  <ChevronDown className="w-3 h-3" />
                  Show more
                </>
              )}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Fallback download card when preview fails.
 */
function DownloadFallback({ artifact, onDownload }) {
  return (
    <button
      onClick={onDownload}
      className="w-full flex items-center gap-3 px-3 py-2.5 rounded-lg border border-border/30 bg-surface-secondary/30 hover:bg-surface-overlay transition-colors"
    >
      <Table2 className="w-5 h-5 text-emerald-400 shrink-0" />
      <div className="text-left min-w-0 flex-1">
        <p className="text-sm text-text-secondary font-medium truncate">{artifact.filename}</p>
        <p className="text-xs text-text-muted">Click to download</p>
      </div>
      <Download className="w-4 h-4 text-text-muted shrink-0" />
    </button>
  );
}

/**
 * Parse CSV text to table data.
 */
function parseCSVToTable(text) {
  const lines = text.split('\n').filter((line) => line.trim());
  if (lines.length === 0) return { headers: [], rows: [] };

  // Simple CSV parsing (handles basic cases)
  const parseRow = (line) => {
    const result = [];
    let current = '';
    let inQuotes = false;

    for (let i = 0; i < line.length; i++) {
      const char = line[i];
      if (char === '"') {
        inQuotes = !inQuotes;
      } else if (char === ',' && !inQuotes) {
        result.push(current.trim());
        current = '';
      } else {
        current += char;
      }
    }
    result.push(current.trim());
    return result;
  };

  const headers = parseRow(lines[0]);
  const rows = lines.slice(1).map(parseRow);

  return { headers, rows };
}

/**
 * Parse JSON to table data.
 */
function parseJSONToTable(json) {
  let data = json;

  // Handle wrapped JSON
  if (typeof data === 'object' && !Array.isArray(data)) {
    // Look for common data keys
    const dataKey = Object.keys(data).find((k) =>
      ['data', 'rows', 'records', 'items', 'results'].includes(k.toLowerCase())
    );
    if (dataKey && Array.isArray(data[dataKey])) {
      data = data[dataKey];
    } else {
      // Convert single object to single-row table
      data = [data];
    }
  }

  if (!Array.isArray(data) || data.length === 0) {
    return { headers: [], rows: [] };
  }

  // Extract headers from first object
  const headers = Object.keys(data[0] || {});

  // Convert objects to rows
  const rows = data.map((item) =>
    headers.map((h) => (item && item[h] !== undefined ? item[h] : ''))
  );

  return { headers, rows };
}

/**
 * Format cell value for display.
 */
function formatCell(value) {
  if (value === null || value === undefined) return '';
  if (typeof value === 'object') return JSON.stringify(value);
  if (typeof value === 'number') {
    // Format numbers nicely
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toLocaleString(undefined, { maximumFractionDigits: 4 });
  }
  return String(value);
}

export default memo(ArtifactTablePreview);

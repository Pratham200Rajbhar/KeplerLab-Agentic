'use client';

import { memo, useState, useEffect } from 'react';
import { FileText, AlertCircle } from 'lucide-react';

import DocViewerRenderer from '../viewer/DocViewerRenderer';

/**
 * OutputRenderer — renders ALL agent-produced files inline inside the message bubble.
 *
 * Props:
 *   artifact: { filename, mime, display_type, url, size }
 *
 * Rules:
 *   - NEVER render a download button
 *   - NEVER render a save button
 *   - Show filename only as a non-clickable label
 *   - All fetch() calls handle errors gracefully
 */

function formatSize(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function ErrorMessage({ filename }) {
  return (
    <div className="flex items-center gap-2 text-red-400 text-xs py-2 px-3 rounded-lg bg-red-500/5 border border-red-500/20">
      <AlertCircle className="h-3.5 w-3.5 shrink-0" />
      <span>Could not load {filename}</span>
    </div>
  );
}

function FileLabel({ filename }) {
  return (
    <span className="text-[11px] text-text-muted font-mono block mb-1 truncate max-w-full">
      {filename}
    </span>
  );
}

/* ── Image Renderer ── */
function ImageRenderer({ url, filename }) {
  const [fullscreen, setFullscreen] = useState(false);
  const [error, setError] = useState(false);

  if (error) return <ErrorMessage filename={filename} />;

  return (
    <>
      <div
        className="rounded-lg overflow-hidden border border-border/30 cursor-pointer"
        onClick={() => setFullscreen(true)}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={url}
          alt={filename}
          className="w-full h-auto max-h-[480px] object-contain bg-white/5"
          onError={() => setError(true)}
        />
      </div>

      {/* Fullscreen overlay */}
      {fullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center cursor-pointer"
          onClick={() => setFullscreen(false)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={url}
            alt={filename}
            className="max-w-[90vw] max-h-[90vh] object-contain"
          />
        </div>
      )}
    </>
  );
}

/* ── CSV Table Renderer ── */
function CsvTableRenderer({ url, filename }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('Fetch failed');
        return r.text();
      })
      .then((text) => {
        if (cancelled) return;
        const rows = text.split('\n').filter(Boolean).map((row) => row.split(','));
        setData(rows);
      })
      .catch(() => !cancelled && setError(true));
    return () => { cancelled = true; };
  }, [url]);

  if (error) return <ErrorMessage filename={filename} />;
  if (!data) return <div className="text-xs text-text-muted py-2">Loading table…</div>;

  const headers = data[0] || [];
  const rows = data.slice(1);

  return (
    <div>
      <FileLabel filename={filename} />
      <div className="rounded-lg overflow-hidden bg-surface-overlay/20" style={{ maxHeight: '320px', overflowY: 'auto' }}>
        <table className="w-full text-xs font-mono">
          <thead className="sticky top-0 bg-surface-raised z-10">
            <tr>
              {headers.map((h, i) => (
                <th key={i} className="text-left px-2.5 py-1.5 text-text-secondary font-medium bg-surface-raised/30 whitespace-nowrap">
                  {h.trim()}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, ri) => (
              <tr key={ri} className={ri % 2 === 0 ? 'bg-surface-primary/20' : 'bg-surface-secondary/20'}>
                {row.map((cell, ci) => (
                  <td key={ci} className="px-2.5 py-1 text-text-secondary whitespace-nowrap">
                    {cell.trim()}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

/* ── JSON Tree Renderer ── */
function JsonTreeRenderer({ url, filename }) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('Fetch failed');
        return r.json();
      })
      .then((json) => !cancelled && setData(json))
      .catch(() => !cancelled && setError(true));
    return () => { cancelled = true; };
  }, [url]);

  if (error) return <ErrorMessage filename={filename} />;
  if (data === null) return <div className="text-xs text-text-muted py-2">Loading JSON…</div>;

  return (
    <div>
      <FileLabel filename={filename} />
      <pre className="text-xs font-mono px-3 py-2 rounded-lg bg-surface-overlay border border-border/30 overflow-x-auto overflow-y-auto whitespace-pre-wrap text-text-secondary" style={{ maxHeight: '400px' }}>
        {JSON.stringify(data, null, 2)}
      </pre>
    </div>
  );
}

/* ── Text Preview Renderer ── */
function TextPreviewRenderer({ url, filename }) {
  const [text, setText] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetch(url)
      .then((r) => {
        if (!r.ok) throw new Error('Fetch failed');
        return r.text();
      })
      .then((t) => !cancelled && setText(t))
      .catch(() => !cancelled && setError(true));
    return () => { cancelled = true; };
  }, [url]);

  if (error) return <ErrorMessage filename={filename} />;
  if (text === null) return <div className="text-xs text-text-muted py-2">Loading text…</div>;

  return (
    <div>
      <FileLabel filename={filename} />
      <pre
        className="text-[13px] font-mono px-3 py-2 rounded-lg bg-surface-overlay/60 overflow-x-auto overflow-y-auto whitespace-pre-wrap text-text-secondary leading-relaxed shadow-sm"
        style={{ maxHeight: '400px' }}
      >
        {text}
      </pre>
    </div>
  );
}

/* ── HTML Preview Renderer ── */
function HtmlPreviewRenderer({ url, filename }) {
  return (
    <div>
      <FileLabel filename={filename} />
      <iframe
        src={url}
        sandbox="allow-scripts allow-same-origin"
        className="w-full rounded-lg bg-white/5"
        style={{ height: '480px', border: 'none' }}
        title={filename}
      />
    </div>
  );
}

/* ── Document Embed Renderer ── */
function DocEmbedRenderer({ url, filename }) {
  return (
    <div>
      <FileLabel filename={filename} />
      <div className="w-full rounded-lg shadow-md overflow-hidden bg-surface" style={{ height: '520px' }}>
        <DocViewerRenderer url={url} filename={filename} />
      </div>
    </div>
  );
}

/* ── Audio Player Renderer ── */
function AudioPlayerRenderer({ url, filename }) {
  return (
    <div>
      <FileLabel filename={filename} />
      <audio controls src={url} className="w-full mt-1" />
    </div>
  );
}

/* ── Video Player Renderer ── */
function VideoPlayerRenderer({ url, filename }) {
  return (
    <div>
      <video
        controls
        src={url}
        className="w-full rounded-lg mt-1"
        style={{ maxHeight: '360px' }}
      />
    </div>
  );
}

/* ── File Card (generic fallback) ── */
function FileCardRenderer({ filename, mime, size }) {
  return (
    <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-surface-secondary/30 shadow-sm transition-all hover:bg-surface-secondary/50">
      <FileText className="h-5 w-5 text-text-muted shrink-0" />
      <div className="min-w-0">
        <p className="text-xs text-text-secondary font-medium truncate">{filename}</p>
        <p className="text-[10px] text-text-muted">
          {mime}{size > 0 ? ` • ${formatSize(size)}` : ''}
        </p>
      </div>
    </div>
  );
}

/* ── Main OutputRenderer ── */
function OutputRenderer({ artifact }) {
  if (!artifact) return null;

  const { filename, mime, display_type, url, size } = artifact;

  switch (display_type) {
    case 'image':
      return <ImageRenderer url={url} filename={filename} />;
    case 'csv_table':
      return <CsvTableRenderer url={url} filename={filename} />;
    case 'json_tree':
      return <JsonTreeRenderer url={url} filename={filename} />;
    case 'text_preview':
      return <TextPreviewRenderer url={url} filename={filename} />;
    case 'html_preview':
      return <HtmlPreviewRenderer url={url} filename={filename} />;
    case 'pdf_embed':
    case 'doc_embed':
      return <DocEmbedRenderer url={url} filename={filename} />;
    case 'audio_player':
      return <AudioPlayerRenderer url={url} filename={filename} />;
    case 'video_player':
      return <VideoPlayerRenderer url={url} filename={filename} />;
    case 'file_card':
    default:
      return <FileCardRenderer filename={filename} mime={mime} size={size} />;
  }
}

export default memo(OutputRenderer);

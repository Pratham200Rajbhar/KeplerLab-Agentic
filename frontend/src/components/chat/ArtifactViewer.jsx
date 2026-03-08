'use client';

import { Download, FileText, FileSpreadsheet, FileCode, FileArchive } from 'lucide-react';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';

const IMAGE_MIMES = new Set(['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml', 'image/webp']);
const IMAGE_DISPLAY = new Set(['image', 'chart', 'plot', 'figure', 'heatmap']);

function isImageArtifact(artifact) {
  return IMAGE_MIMES.has(artifact.mime) || IMAGE_DISPLAY.has(artifact.display_type);
}

function formatBytes(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function FileIcon({ mime, displayType }) {
  if (mime?.includes('spread') || mime?.includes('excel') || displayType === 'csv') return <FileSpreadsheet size={15} className="text-green-400" />;
  if (mime?.includes('json') || mime?.includes('html') || displayType === 'code') return <FileCode size={15} className="text-blue-400" />;
  if (mime?.includes('zip') || mime?.includes('tar')) return <FileArchive size={15} className="text-orange-400" />;
  return <FileText size={15} className="text-text-muted" />;
}

function ArtifactCard({ artifact }) {
  const isImage = isImageArtifact(artifact);
  const apiUrl = artifact.url ? `${API_BASE}${artifact.url}` : null;

  if (isImage && apiUrl) {
    return (
      <div
        className="rounded-xl overflow-hidden border"
        style={{ borderColor: 'rgba(255,255,255,0.08)' }}
      >
        {/* eslint-disable-next-line @next/next/no-img-element */}
        <img
          src={apiUrl}
          alt={artifact.filename || 'Generated image'}
          className="w-full max-h-96 object-contain"
          style={{ background: '#0a0a12' }}
          onError={(e) => {
            e.currentTarget.parentElement.style.display = 'none';
          }}
        />
        <div
          className="flex items-center justify-between px-3 py-2 border-t"
          style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(0,0,0,0.2)' }}
        >
          <span className="text-xs text-text-muted truncate">{artifact.filename}</span>
          {apiUrl && (
            <a
              href={apiUrl}
              download={artifact.filename}
              className="ml-3 shrink-0 flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
            >
              <Download size={11} />
              Save
            </a>
          )}
        </div>
      </div>
    );
  }

  // Generic file card
  return (
    <div
      className="flex items-center gap-3 px-3.5 py-3 rounded-xl border"
      style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.08)' }}
    >
      <div
        className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
        style={{ background: 'rgba(255,255,255,0.05)' }}
      >
        <FileIcon mime={artifact.mime} displayType={artifact.display_type} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium text-text-primary truncate">{artifact.filename}</div>
        {artifact.size > 0 && (
          <div className="text-xs text-text-muted mt-0.5">{formatBytes(artifact.size)}</div>
        )}
      </div>
      {apiUrl && (
        <a
          href={apiUrl}
          download={artifact.filename}
          className="shrink-0 flex items-center gap-1.5 text-xs text-accent hover:text-accent/80 transition-colors px-3 py-1.5 rounded-lg border border-accent/25 hover:bg-accent/10"
        >
          <Download size={12} />
          Download
        </a>
      )}
    </div>
  );
}

/**
 * ArtifactViewer — renders a list of agent/code-execution output artifacts.
 * Images are displayed inline; other files get download cards.
 */
export default function ArtifactViewer({ artifacts }) {
  if (!artifacts?.length) return null;

  return (
    <div className="space-y-2">
      {artifacts.map((art, i) => (
        <ArtifactCard key={art.id || i} artifact={art} />
      ))}
    </div>
  );
}

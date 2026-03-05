'use client';

import { memo, useCallback, useState } from 'react';
import {
  FileText,
  Download,
  FileImage,
  FileSpreadsheet,
  FileCode,
  FileBox,
  File,
  Loader2,
  AlertCircle,
  CheckCircle2,
} from 'lucide-react';

/**
 * ArtifactDownloadCard — displays a download card for artifacts.
 * 
 * Shows file icon, filename, size, and download button.
 * Handles download states: idle, downloading, success, error.
 *
 * Props:
 *   artifact: { id, filename, mimeType, downloadUrl, size }
 *   onDownload: (artifact) => Promise<void> | void
 *   error: string | null - external error message
 */

const FILE_ICONS = {
  // Images
  png: FileImage,
  jpg: FileImage,
  jpeg: FileImage,
  gif: FileImage,
  svg: FileImage,
  webp: FileImage,
  
  // Data
  csv: FileSpreadsheet,
  xlsx: FileSpreadsheet,
  xls: FileSpreadsheet,
  json: FileCode,
  
  // Models
  pkl: FileBox,
  pickle: FileBox,
  h5: FileBox,
  pt: FileBox,
  pth: FileBox,
  onnx: FileBox,
  joblib: FileBox,
  
  // Documents
  pdf: FileText,
  docx: FileText,
  doc: FileText,
  txt: FileText,
  md: FileText,
  
  // Code
  py: FileCode,
  js: FileCode,
  html: FileCode,
};

const FILE_COLORS = {
  // Images
  png: 'text-blue-400',
  jpg: 'text-blue-400',
  jpeg: 'text-blue-400',
  
  // Data
  csv: 'text-emerald-400',
  xlsx: 'text-emerald-400',
  json: 'text-amber-400',
  
  // Models
  pkl: 'text-purple-400',
  h5: 'text-purple-400',
  pt: 'text-purple-400',
  
  // Documents
  pdf: 'text-red-400',
  docx: 'text-blue-400',
  txt: 'text-text-secondary',
};

function ArtifactDownloadCard({ artifact, onDownload, error: externalError }) {
  const [downloadState, setDownloadState] = useState('idle'); // idle, downloading, success, error
  const [error, setError] = useState(externalError || null);

  const ext = (artifact.filename || '').split('.').pop()?.toLowerCase() || '';
  const Icon = FILE_ICONS[ext] || File;
  const iconColor = FILE_COLORS[ext] || 'text-text-muted';

  const handleDownload = useCallback(async () => {
    if (downloadState === 'downloading') return;

    setDownloadState('downloading');
    setError(null);

    try {
      if (onDownload) {
        await onDownload(artifact);
      } else if (artifact.downloadUrl) {
        // Direct download fallback
        const link = document.createElement('a');
        link.href = artifact.downloadUrl;
        link.download = artifact.filename || 'download';
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      }
      setDownloadState('success');
      // Reset to idle after showing success
      setTimeout(() => setDownloadState('idle'), 2000);
    } catch (err) {
      setError(err.message || 'Download failed');
      setDownloadState('error');
    }
  }, [artifact, onDownload, downloadState]);

  return (
    <div
      className={`flex items-center gap-3 px-3 py-2.5 rounded-lg border transition-colors ${
        error
          ? 'border-red-500/30 bg-red-500/5'
          : 'border-border/30 bg-surface-secondary/30 hover:bg-surface-overlay'
      }`}
    >
      {/* File icon */}
      <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-surface-raised shrink-0">
        <Icon className={`w-5 h-5 ${error ? 'text-red-400' : iconColor}`} />
      </div>

      {/* File info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm text-text-secondary font-medium truncate" title={artifact.filename}>
          {artifact.filename}
        </p>
        <div className="flex items-center gap-2 text-xs text-text-muted">
          {artifact.size > 0 && <span>{formatSize(artifact.size)}</span>}
          {artifact.mimeType && artifact.size > 0 && <span>•</span>}
          {artifact.mimeType && <span>{formatMimeType(artifact.mimeType)}</span>}
        </div>
        {error && (
          <p className="text-xs text-red-400 mt-0.5">{error}</p>
        )}
      </div>

      {/* Download button */}
      <button
        onClick={handleDownload}
        disabled={downloadState === 'downloading'}
        className={`flex items-center gap-1.5 px-3 py-1.5 text-xs rounded-md transition-colors shrink-0 ${
          downloadState === 'success'
            ? 'bg-emerald-500/20 text-emerald-400 cursor-default'
            : downloadState === 'error'
              ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
              : downloadState === 'downloading'
                ? 'bg-accent/20 text-accent cursor-wait'
                : 'bg-accent/10 text-accent hover:bg-accent/20'
        }`}
      >
        {downloadState === 'downloading' && (
          <>
            <Loader2 className="w-3 h-3 animate-spin" />
            <span>Downloading</span>
          </>
        )}
        {downloadState === 'success' && (
          <>
            <CheckCircle2 className="w-3 h-3" />
            <span>Downloaded</span>
          </>
        )}
        {downloadState === 'error' && (
          <>
            <AlertCircle className="w-3 h-3" />
            <span>Retry</span>
          </>
        )}
        {downloadState === 'idle' && (
          <>
            <Download className="w-3 h-3" />
            <span>Download</span>
          </>
        )}
      </button>
    </div>
  );
}

/**
 * Format file size for display.
 */
function formatSize(bytes) {
  if (!bytes || bytes <= 0) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

/**
 * Format mime type for display.
 */
function formatMimeType(mime) {
  if (!mime) return '';
  // Extract just the type part
  const parts = mime.split('/');
  if (parts.length === 2) {
    return parts[1].replace('+', ' / ');
  }
  return mime;
}

/**
 * Compact variant for inline use.
 */
export function ArtifactDownloadCompact({ artifact, onDownload }) {
  const ext = (artifact.filename || '').split('.').pop()?.toLowerCase() || '';
  const Icon = FILE_ICONS[ext] || File;
  const iconColor = FILE_COLORS[ext] || 'text-text-muted';

  return (
    <button
      onClick={() => onDownload?.(artifact)}
      className="inline-flex items-center gap-1.5 px-2 py-1 text-xs rounded-md border border-border/30 bg-surface-secondary/30 hover:bg-surface-overlay transition-colors"
    >
      <Icon className={`w-3 h-3 ${iconColor}`} />
      <span className="text-text-secondary truncate max-w-[120px]">{artifact.filename}</span>
      <Download className="w-3 h-3 text-text-muted" />
    </button>
  );
}

export default memo(ArtifactDownloadCard);

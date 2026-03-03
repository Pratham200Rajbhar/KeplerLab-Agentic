'use client';

import { useState, memo } from 'react';
import { Eye, Download } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import { apiFetch } from '@/lib/api/config';

const FILE_STYLES = {
  spreadsheet: { icon: '📊', border: 'border-green-500/30', bg: 'bg-green-500/5' },
  document: { icon: '📝', border: 'border-blue-500/30', bg: 'bg-blue-500/5' },
  image: { icon: '🖼️', border: 'border-purple-500/30', bg: 'bg-purple-500/5' },
  data: { icon: '🗃️', border: 'border-gray-500/30', bg: 'bg-gray-500/5' },
  web: { icon: '🌐', border: 'border-cyan-500/30', bg: 'bg-cyan-500/5' },
  text: { icon: '📄', border: 'border-gray-500/30', bg: 'bg-gray-500/5' },
  file: { icon: '📁', border: 'border-gray-500/30', bg: 'bg-gray-500/5' },
};

function getStyleFromFilename(filename, fileType) {
  const ext = filename.split('.').pop()?.toLowerCase();
  if (ext === 'pdf') return { icon: '📕', border: 'border-red-500/30', bg: 'bg-red-500/5' };
  if (ext === 'csv') return { icon: '🗃️', border: 'border-gray-500/30', bg: 'bg-gray-500/5' };
  return FILE_STYLES[fileType] || FILE_STYLES.file;
}

function formatSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function isPreviewable(filename) {
  const ext = filename.split('.').pop()?.toLowerCase();
  return ['png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'].includes(ext);
}

export default memo(function GeneratedFileCard({ filename, downloadUrl, size, fileType }) {
  const [showPreview, setShowPreview] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const style = getStyleFromFilename(filename, fileType);

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const tokenRes = await apiFetch('/auth/file-token');
      const { token } = await tokenRes.json();
      const a = document.createElement('a');
      a.href = `${downloadUrl}?token=${token}`;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
    } catch (err) {
      console.error('Download failed:', err);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <>
      <div className={`inline-flex items-center gap-3 px-3 py-2.5 rounded-xl border ${style.border} ${style.bg} hover:shadow-sm transition-all max-w-xs`}>
        <span className="text-xl shrink-0">{style.icon}</span>
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium text-text-primary truncate" title={filename}>{filename}</p>
          <p className="text-xs text-text-muted">{formatSize(size)}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          {isPreviewable(filename) && (
            <button onClick={() => setShowPreview(true)} className="p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted hover:text-text-primary transition-colors" title="Preview">
              <Eye className="w-4 h-4" strokeWidth={1.5} />
            </button>
          )}
          <button onClick={handleDownload} disabled={downloading} className="p-1.5 rounded-lg hover:bg-surface-overlay text-accent hover:text-accent-dark transition-colors disabled:opacity-50" title="Download">
            {downloading ? <div className="w-4 h-4 border-2 border-accent border-t-transparent rounded-full animate-spin" /> : <Download className="w-4 h-4" />}
          </button>
        </div>
      </div>
      {showPreview && (
        <Modal isOpen={showPreview} onClose={() => setShowPreview(false)} title={filename} size="lg">
          <div className="flex items-center justify-center p-4">
            <img src={downloadUrl} alt={filename} className="max-w-full max-h-[70vh] rounded-lg object-contain" />
          </div>
        </Modal>
      )}
    </>
  );
});

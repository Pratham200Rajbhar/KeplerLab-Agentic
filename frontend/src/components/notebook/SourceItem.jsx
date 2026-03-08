'use client';

import { useState, useRef, useEffect, memo } from 'react';
import {
  Youtube, Globe, FileText, Presentation, Sheet, Music, Film,
  Archive, Image as ImageIcon, FileType, File, MoreVertical, Eye, Pencil,
  Trash2, Check,
} from 'lucide-react';
import { useConfirm } from '@/stores/useConfirmStore';

function inferSourceType(filename) {
  if (!filename) return 'file';
  const lower = filename.toLowerCase();
  if (lower.startsWith('http://') || lower.startsWith('https://')) {
    if (lower.includes('youtube.com') || lower.includes('youtu.be')) return 'youtube';
    return 'url';
  }
  return 'file';
}

function getSourceIcon(type, filename) {
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (type === 'youtube') return <Youtube className="w-5 h-5" />;
  if (type === 'url') return <Globe className="w-5 h-5" />;
  if (ext === 'pdf') return <FileText className="w-5 h-5" />;
  if (ext === 'docx' || ext === 'doc') return <FileText className="w-5 h-5" />;
  if (ext === 'pptx' || ext === 'ppt') return <Presentation className="w-5 h-5" />;
  if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') return <Sheet className="w-5 h-5" />;
  if (ext === 'mp3' || ext === 'wav' || ext === 'ogg' || ext === 'm4a') return <Music className="w-5 h-5" />;
  if (ext === 'mp4' || ext === 'avi' || ext === 'mov' || ext === 'mkv' || ext === 'webm') return <Film className="w-5 h-5" />;
  if (ext === 'zip' || ext === 'rar' || ext === '7z' || ext === 'tar' || ext === 'gz') return <Archive className="w-5 h-5" />;
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'gif' || ext === 'svg' || ext === 'webp') return <ImageIcon className="w-5 h-5" />;
  if (type === 'text' || ext === 'txt') return <FileType className="w-5 h-5" />;
  return <File className="w-5 h-5" />;
}

function getSourceTypeColor(type, filename) {
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (type === 'youtube') return 'text-red-500 bg-gradient-to-br from-red-500/20 to-red-600/5';
  if (type === 'url') return 'text-blue-500 bg-gradient-to-br from-blue-500/20 to-blue-600/5';
  if (ext === 'pdf') return 'text-red-500 bg-gradient-to-br from-red-500/20 to-red-600/5';
  if (ext === 'docx' || ext === 'doc') return 'text-blue-500 bg-gradient-to-br from-blue-500/20 to-blue-600/5';
  if (ext === 'pptx' || ext === 'ppt') return 'text-orange-500 bg-gradient-to-br from-orange-500/20 to-orange-600/5';
  if (ext === 'xlsx' || ext === 'xls' || ext === 'csv') return 'text-green-500 bg-gradient-to-br from-green-500/20 to-green-600/5';
  if (ext === 'mp3' || ext === 'wav' || ext === 'ogg' || ext === 'm4a') return 'text-purple-500 bg-gradient-to-br from-purple-500/20 to-purple-600/5';
  if (ext === 'mp4' || ext === 'avi' || ext === 'mov' || ext === 'mkv' || ext === 'webm') return 'text-pink-500 bg-gradient-to-br from-pink-500/20 to-pink-600/5';
  if (ext === 'zip' || ext === 'rar' || ext === '7z' || ext === 'tar' || ext === 'gz') return 'text-amber-500 bg-gradient-to-br from-amber-500/20 to-amber-600/5';
  if (ext === 'png' || ext === 'jpg' || ext === 'jpeg' || ext === 'gif' || ext === 'svg' || ext === 'webp') return 'text-teal-500 bg-gradient-to-br from-teal-500/20 to-teal-600/5';
  if (type === 'text' || ext === 'txt') return 'text-gray-400 bg-gradient-to-br from-gray-500/20 to-gray-600/5';
  return 'text-slate-400 bg-gradient-to-br from-slate-500/20 to-slate-600/5';
}

function getStatusLabel(status) {
  if (!status) return null;
  const map = {
    pending: 'Waiting...',
    processing: 'Parsing...',
    ocr_running: 'Running OCR...',
    transcribing: 'Transcribing...',
    embedding: 'Embedding...',
    failed: 'Failed',
  };
  return map[status] || null;
}

function getStatusStyle(status) {
  const styles = {
    pending: { bg: 'bg-gray-500/10', text: 'text-gray-400' },
    processing: { bg: 'bg-blue-500/10', text: 'text-blue-400' },
    ocr_running: { bg: 'bg-indigo-500/10', text: 'text-indigo-400' },
    transcribing: { bg: 'bg-purple-500/10', text: 'text-purple-400' },
    embedding: { bg: 'bg-teal-500/10', text: 'text-teal-400' },
    failed: { bg: 'bg-red-500/10', text: 'text-red-400' },
  };
  return styles[status] || styles.pending;
}

export default memo(function SourceItem({
  source, checked, active, anySelected, onClick, onToggle, onSeeText, onRename, onRemove,
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const confirm = useConfirm();

  const sourceType = source.source_type || source.sourceType || inferSourceType(source.filename);
  const displayName = source.title || source.filename;

  useEffect(() => {
    if (!menuOpen) return;
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false);
    };
    document.addEventListener('click', handler);
    return () => document.removeEventListener('click', handler);
  }, [menuOpen]);

  const handleRename = async (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    const newName = await confirm({
      title: 'Rename source',
      message: 'Enter a new name for this source.',
      prompt: true,
      defaultValue: displayName,
    });
    if (newName != null && newName.trim()) {
      onRename?.(source, newName.trim());
    }
  };

  const handleRemove = async (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    const ok = await confirm({
      title: 'Remove source',
      message: `Remove "${displayName}" from sources?`,
      variant: 'danger',
      confirmLabel: 'Remove',
    });
    if (ok) onRemove?.(source);
  };

  const handleSeeText = (e) => {
    e.stopPropagation();
    setMenuOpen(false);
    onSeeText?.(source);
  };

  const isProcessing = source.status && !['completed', 'failed'].includes(source.status);
  const isFailed = source.status === 'failed';
  const statusLabel = getStatusLabel(source.status);
  const statusStyle = getStatusStyle(source.status);

  return (
    <div
      className={`source-item group flex items-start gap-3 px-3 py-2.5 rounded-lg transition-all
        ${checked ? 'bg-accent/5 ring-0 shadow-sm' : 'hover:bg-surface-100'}
        ${isProcessing ? 'bg-surface-overlay/50' : ''}`}
    >
      {/* Icon */}
      <div className={`shrink-0 w-8 h-8 flex items-center justify-center rounded-lg backdrop-blur-sm shadow-inner ${getSourceTypeColor(sourceType, source.filename)} ${isProcessing ? 'animate-pulse' : ''} ${isFailed ? 'grayscale opacity-50' : ''}`}>
        <div className="scale-90 flex items-center justify-center drop-shadow-md">
          {getSourceIcon(sourceType, source.filename)}
        </div>
      </div>

      {/* Name */}
      <div className="flex-1 min-w-0 flex flex-col justify-center pt-0.5 max-w-full">
        <p className={`text-[13px] truncate leading-tight ${active ? 'text-text-primary font-medium' : isFailed ? 'text-danger line-through' : 'text-text-secondary font-medium'}`}>
          {displayName}
        </p>
        {(isProcessing || isFailed) && (
          <div className="mt-2 mb-1 flex items-center gap-2">
            <div className={`relative inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full ${statusStyle.bg} ${isProcessing ? 'animate-pulse' : ''}`} title={statusLabel} role="status">
              {isProcessing && (
                <div className={`w-1.5 h-1.5 rounded-full bg-current ${statusStyle.text} animate-ping absolute left-2 opacity-75`} />
              )}
              <div className={`w-1.5 h-1.5 rounded-full fill-current bg-current ${statusStyle.text} ${isProcessing ? 'ml-3' : ''}`} />
              <span className={`text-[10px] font-semibold tracking-wide uppercase ${statusStyle.text}`}>
                {statusLabel}
              </span>
            </div>
            {isProcessing && (
              <div className="flex-1 max-w-[100px] h-1 bg-surface-overlay rounded-full overflow-hidden">
                <div className={`h-full bg-current rounded-full ${statusStyle.text} animate-[progress_2s_ease-in-out_infinite]`} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* Context menu */}
      <div className="relative flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity" ref={menuRef}>
        <button
          onClick={(e) => { e.stopPropagation(); setMenuOpen((o) => !o); }}
          className="p-1.5 rounded-md text-text-muted hover:text-text-primary hover:bg-surface-100 transition-colors"
          title="More actions"
        >
          <MoreVertical className="w-4 h-4" />
        </button>
        {menuOpen && (
          <div
            className="absolute right-0 top-full mt-1 z-20 min-w-[160px] py-1 rounded-xl animate-scale-in"
            style={{ background: 'var(--surface-raised)', boxShadow: 'var(--shadow-elevated)' }}
            onClick={(e) => e.stopPropagation()}
          >
            <button onClick={handleSeeText} className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-overlay hover:text-text-primary flex items-center gap-2">
              <Eye className="w-4 h-4" /> View text
            </button>
            <button onClick={handleRename} className="w-full px-3 py-2 text-left text-sm text-text-secondary hover:bg-surface-overlay hover:text-text-primary flex items-center gap-2">
              <Pencil className="w-4 h-4" /> Rename
            </button>
            <button onClick={handleRemove} className="w-full px-3 py-2 text-left text-sm text-danger hover:bg-danger-subtle flex items-center gap-2">
              <Trash2 className="w-4 h-4" /> Remove source
            </button>
          </div>
        )}
      </div>

      {/* Checkbox / Spinner */}
      {isProcessing ? (
        <div className="shrink-0 w-4 h-4 flex items-center justify-center mt-0.5">
          <div className={`w-4 h-4 loading-spinner ${statusStyle.text}`} />
        </div>
      ) : (
        <button
          onClick={(e) => { e.stopPropagation(); onToggle(source); }}
          className={`shrink-0 w-4 h-4 mt-0.5 rounded-[4px] flex items-center justify-center transition-all ${checked ? 'bg-accent shadow-sm shadow-accent/30' : 'bg-surface-raised hover:bg-surface-overlay'
            }`}
          disabled={isFailed}
          title={checked ? 'Deselect' : 'Select'}
        >
          {checked && <Check className="w-3 h-3 text-white" strokeWidth={3} />}
        </button>
      )}
    </div>
  );
});

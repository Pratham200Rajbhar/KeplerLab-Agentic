'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import {
  uploadBatch, uploadBatchWithAutoNotebook, uploadUrl,
  uploadText, validateFiles, getMaxUploadSizeMB,
} from '@/lib/api/materials';
import { X, CloudUpload, Globe, File, FileText, Loader2, Link, CheckCircle } from 'lucide-react';
import { useToast } from '@/stores/useToastStore';

const TABS = [
  { id: 'files', label: 'Upload Files', icon: File },
  { id: 'web', label: 'Website / URL', icon: Globe },
  { id: 'text', label: 'Paste Text', icon: FileText },
];

const FORMAT_GROUPS = [
  { icon: '📄', label: 'Documents', formats: 'PDF, DOCX, TXT, PPTX, XLSX' },
  { icon: '🖼️', label: 'Images', formats: 'JPG, PNG, GIF (OCR)' },
  { icon: '🎵', label: 'Media', formats: 'MP3, MP4, WAV, AVI, MOV' },
  { icon: '🌐', label: 'Web', formats: 'Webpages, YouTube' },
];

export default function UploadDialog({
  isOpen, onClose, currentNotebook, draftMode,
  onMaterialAdded, setCurrentNotebook, setDraftMode,
}) {
  const [activeTab, setActiveTab] = useState('files');
  const [dragActive, setDragActive] = useState(false);
  const [loading, setLoading] = useState(false);
  const [url, setUrl] = useState('');
  const [textContent, setTextContent] = useState('');
  const [textTitle, setTextTitle] = useState('');
  const router = useRouter();
  const toast = useToast();
  const dialogRef = useRef(null);

  // Escape key to close
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e) => { if (e.key === 'Escape' && !loading) onClose(); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, loading, onClose]);

  // Focus trap
  useEffect(() => {
    if (!isOpen) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = dialog.querySelectorAll('button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
    if (focusable.length > 0) focusable[0].focus();
    const trap = (e) => {
      if (e.key !== 'Tab' || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) { if (document.activeElement === first) { e.preventDefault(); last.focus(); } }
      else { if (document.activeElement === last) { e.preventDefault(); first.focus(); } }
    };
    dialog.addEventListener('keydown', trap);
    return () => dialog.removeEventListener('keydown', trap);
  }, [isOpen]);
  const fileInputRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      setActiveTab('files');
      setUrl('');
      setTextContent('');
      setTextTitle('');
      setDragActive(false);
    }
  }, [isOpen]);

  const handleDrag = useCallback((e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  }, []);

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length) handleFileUpload(Array.from(e.dataTransfer.files));
  };

  const handleFileUpload = async (files) => {
    if (!files?.length) return;
    const validationErr = validateFiles(files);
    if (validationErr) {
      toast.error(validationErr.details || validationErr.message);
      return;
    }
    setLoading(true);
    try {
      let result;
      if (draftMode && currentNotebook?.isDraft) {
        result = await uploadBatchWithAutoNotebook(files);
        if (result.notebook) {
          setCurrentNotebook(result.notebook);
          setDraftMode(false);
          router.replace(`/notebook/${result.notebook.id}`);
        }
      } else {
        const nbId = currentNotebook?.isDraft ? null : currentNotebook?.id;
        result = await uploadBatch(files, nbId);
      }
      result.materials?.forEach((m) => {
        if (m.status !== 'error') {
          onMaterialAdded({
            id: m.material_id, filename: m.filename, title: m.title || m.filename,
            chunkCount: m.chunk_count, status: m.status, sourceType: 'file',
          });
        }
      });
      onClose();
    } catch (error) {
      toast.error(error.details || error.message || 'Upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleUrlUpload = async () => {
    if (!url.trim()) { toast.error('Please enter a URL'); return; }
    try {
      const parsed = new URL(url.trim());
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        toast.error('Only HTTP and HTTPS URLs are supported');
        return;
      }
    } catch {
      toast.error('Please enter a valid URL');
      return;
    }
    setLoading(true);
    try {
      const autoCreate = !currentNotebook || currentNotebook.isDraft || draftMode;
      const notebookId = autoCreate ? null : currentNotebook.id;
      const result = await uploadUrl(url.trim(), notebookId, autoCreate, 'auto');
      if (result.notebook) {
        setCurrentNotebook(result.notebook);
        setDraftMode(false);
        router.replace(`/notebook/${result.notebook.id}`);
      }
      onMaterialAdded({
        id: result.material_id, filename: result.filename, title: result.title || result.filename,
        chunkCount: result.chunk_count, status: result.status, sourceType: result.source_type ?? 'url',
      });
      setUrl('');
      onClose();
    } catch (error) {
      toast.error(error.details || error.message || 'URL upload failed');
    } finally {
      setLoading(false);
    }
  };

  const handleTextUpload = async () => {
    if (!textContent.trim() || !textTitle.trim()) {
      toast.error('Please enter both title and content');
      return;
    }
    setLoading(true);
    try {
      const autoCreate = !currentNotebook || currentNotebook.isDraft || draftMode;
      const notebookId = autoCreate ? null : currentNotebook.id;
      const result = await uploadText(textContent.trim(), textTitle.trim(), notebookId, autoCreate);
      if (result.notebook) {
        setCurrentNotebook(result.notebook);
        setDraftMode(false);
        router.replace(`/notebook/${result.notebook.id}`);
      }
      onMaterialAdded({
        id: result.material_id, filename: result.filename, title: result.title || result.filename,
        chunkCount: result.chunk_count, status: result.status, sourceType: 'text',
      });
      setTextContent('');
      setTextTitle('');
      onClose();
    } catch (error) {
      toast.error(error.details || error.message || 'Text upload failed');
    } finally {
      setLoading(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center animate-fade-in bg-backdrop backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Upload sources"
      ref={dialogRef}
    >
      <div className="relative w-full max-w-[680px] mx-4 flex flex-col rounded-2xl overflow-hidden animate-scale-in bg-surface-raised border border-border shadow-glass max-h-[88vh]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-border">
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-accent-subtle">
              <CloudUpload className="w-5 h-5 text-accent-light" />
            </div>
            <div>
              <h2 className="text-base font-semibold text-text-primary leading-tight">Add Sources</h2>
              <p className="text-xs text-text-muted mt-0.5">Upload files, links, or paste text to your notebook</p>
            </div>
          </div>
          <button onClick={onClose} disabled={loading} className="btn-icon w-8 h-8 rounded-lg" title="Close">
            <X className="w-4 h-4" />
          </button>
        </div>

        {/* Tabs */}
        <div className="px-6 pt-4 pb-0">
          <div className="flex gap-1 p-1 rounded-xl bg-surface-overlay">
            {TABS.map((tab) => {
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`flex items-center justify-center gap-2 flex-1 px-3 py-2 rounded-lg text-sm font-medium transition-all duration-150 ${
                    activeTab === tab.id
                      ? 'text-text-primary bg-surface-raised shadow-sm'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                >
                  <TabIcon className="w-4 h-4" />
                  {tab.label}
                </button>
              );
            })}
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'files' && (
            <div className="space-y-5">
              <div
                className={`relative flex flex-col items-center justify-center rounded-2xl px-8 py-12 border border-dashed transition-all duration-200 cursor-pointer ${
                  dragActive ? 'border-accent bg-accent/5' : 'border-border hover:border-accent/30 hover:bg-surface-overlay'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !loading && fileInputRef.current?.click()}
              >
                <div className={`w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-all duration-200 border ${dragActive ? 'scale-110 bg-accent-subtle border-[var(--accent-border)]' : 'bg-surface-overlay border-border-light'}`}>
                  <CloudUpload className={`w-7 h-7 ${dragActive ? 'text-accent-light' : 'text-text-muted'}`} />
                </div>
                <p className="text-sm font-medium text-text-primary mb-1">
                  {dragActive ? 'Drop files here' : 'Drag & drop files here'}
                </p>
                <p className="text-xs text-text-muted mb-4">or click to browse • max {getMaxUploadSizeMB()} MB per file</p>
                <input
                  ref={fileInputRef}
                  type="file"
                  multiple
                  className="hidden"
                  accept=".pdf,.txt,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.csv,.jpg,.jpeg,.png,.gif,.bmp,.tiff,.mp3,.wav,.m4a,.mp4,.avi,.mov,.mkv"
                  onChange={(e) => e.target.files && handleFileUpload(Array.from(e.target.files))}
                />
                <button
                  onClick={(e) => { e.stopPropagation(); fileInputRef.current?.click(); }}
                  disabled={loading}
                  className="btn-primary text-sm px-5 py-2"
                >
                  {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</> : 'Choose Files'}
                </button>
              </div>
              <div className="grid grid-cols-2 gap-2">
                {FORMAT_GROUPS.map(({ icon, label, formats }) => (
                  <div key={label} className="flex items-start gap-2.5 px-3 py-2.5 rounded-xl bg-surface-overlay border border-border-light">
                    <span className="text-base leading-none mt-0.5">{icon}</span>
                    <div className="min-w-0">
                      <p className="text-xs font-medium text-text-secondary">{label}</p>
                      <p className="text-2xs text-text-muted truncate">{formats}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'web' && (
            <div className="space-y-5">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Website or YouTube URL</label>
                <div className="flex gap-2.5">
                  <div className="relative flex-1">
                    <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted">
                      <Link className="w-4 h-4" />
                    </div>
                    <input
                      type="url"
                      placeholder="https://example.com or YouTube link…"
                      value={url}
                      onChange={(e) => setUrl(e.target.value)}
                      onKeyDown={(e) => e.key === 'Enter' && handleUrlUpload()}
                      className="input pl-10"
                    />
                  </div>
                  <button onClick={handleUrlUpload} disabled={loading || !url.trim()} className="btn-primary whitespace-nowrap px-5">
                    {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</> : 'Add Source'}
                  </button>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-2.5">
                {[
                  { icon: '🌐', title: 'Any Website', desc: 'Articles, blogs, docs' },
                  { icon: '▶️', title: 'YouTube', desc: 'Auto transcript extraction' },
                  { icon: '📰', title: 'News & Wikis', desc: 'Rich content parsing' },
                  { icon: '🔍', title: 'Auto Detect', desc: 'Smart source recognition' },
                ].map(({ icon, title, desc }) => (
                  <div key={title} className="flex items-center gap-3 px-3.5 py-3 rounded-xl bg-surface-overlay border border-border-light">
                    <span className="text-lg">{icon}</span>
                    <div>
                      <p className="text-xs font-medium text-text-secondary">{title}</p>
                      <p className="text-2xs text-text-muted">{desc}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {activeTab === 'text' && (
            <div className="space-y-4">
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Title</label>
                <input type="text" placeholder="Give your content a title…" value={textTitle} onChange={(e) => setTextTitle(e.target.value)} className="input" />
              </div>
              <div>
                <label className="block text-xs font-medium text-text-secondary mb-2">Content</label>
                <textarea placeholder="Paste or type your text here…" value={textContent} onChange={(e) => setTextContent(e.target.value)} rows={7} className="input resize-none leading-relaxed" />
              </div>
              <button onClick={handleTextUpload} disabled={loading || !textContent.trim() || !textTitle.trim()} className="btn-primary w-full justify-center py-2.5">
                {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Adding…</> : <><CheckCircle className="w-4 h-4" /> Add Text Source</>}
              </button>
            </div>
          )}
        </div>

        {loading && (
          <div className="absolute inset-0 rounded-2xl flex items-center justify-center z-10 bg-backdrop backdrop-blur-sm">
            <div className="flex flex-col items-center gap-3">
              <div className="loading-spinner w-8 h-8" />
              <p className="text-sm text-text-secondary">Processing your source…</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

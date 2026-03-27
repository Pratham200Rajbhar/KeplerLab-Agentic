'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import AIResourceBuilder from '@/components/materials/AIResourceBuilder';
import {
  uploadBatch, uploadBatchWithAutoNotebook, uploadUrl,
  uploadText, validateFiles, getMaxUploadSizeMB,
} from '@/lib/api/materials';
import { X, CloudUpload, Globe, File, FileText, Loader2, Link, CheckCircle, AlertCircle, Zap, Clock } from 'lucide-react';
import { useToast } from '@/stores/useToastStore';
import useAppStore from '@/stores/useAppStore';

const TABS = [
  { id: 'files', label: 'Upload Files', icon: File, desc: 'PDF, DOCX, images & more' },
  { id: 'web', label: 'Website / URL', icon: Globe, desc: 'Articles & YouTube' },
  { id: 'text', label: 'Paste Text', icon: FileText, desc: 'Enter raw text' },
  { id: 'ai', label: 'AI Resource', icon: Zap, desc: 'Generate content' },
];

const FORMAT_GROUPS = [
  { icon: '📄', label: 'Documents', formats: 'PDF, DOCX, TXT, PPTX, XLSX', ext: ['.pdf', '.docx', '.txt', '.pptx', '.xlsx'] },
  { icon: '🖼️', label: 'Images', formats: 'JPG, PNG, GIF (OCR)', ext: ['.jpg', '.png', '.gif'] },
  { icon: '🎵', label: 'Media', formats: 'MP3, MP4, WAV, AVI, MOV', ext: ['.mp3', '.mp4', '.wav', '.avi', '.mov'] },
  { icon: '🌐', label: 'Web', formats: 'Webpages, YouTube', ext: ['http', 'https', 'youtube'] },
];

const QUICK_URLS = [
  { name: 'Example Article', url: 'https://example.com' },
  { name: 'YouTube Video', url: 'https://www.youtube.com/watch?v=dQw4w9WgXcQ' },
  { name: 'Wikipedia', url: 'https://en.wikipedia.org' },
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
  const [uploadedFiles, setUploadedFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [urlError, setUrlError] = useState('');
  const [recentSources, setRecentSources] = useState([]);
  const router = useRouter();
  const toast = useToast();
  const dialogRef = useRef(null);

  
  useEffect(() => {
    if (!isOpen) return;
    const handleKey = (e) => { if (e.key === 'Escape' && !loading) onClose(); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [isOpen, loading, onClose]);

  
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
      setUploadedFiles([]);
      setUrlError('');
      setUploadProgress({});
      // Load recent sources from localStorage
      try {
        const recent = JSON.parse(localStorage.getItem('recentSources') || '[]');
        setRecentSources(recent.slice(0, 3));
      } catch {
        setRecentSources([]);
      }
    }
  }, [isOpen]);

  const validateUrl = (urlString) => {
    setUrlError('');
    if (!urlString.trim()) {
      setUrlError('Please enter a URL');
      return false;
    }
    try {
      const parsed = new URL(urlString.trim());
      if (!['http:', 'https:'].includes(parsed.protocol)) {
        setUrlError('Only HTTP and HTTPS URLs are supported');
        return false;
      }
      return true;
    } catch {
      setUrlError('Please enter a valid URL (e.g., https://example.com)');
      return false;
    }
  };

  const saveToRecentSources = (source) => {
    try {
      const recent = JSON.parse(localStorage.getItem('recentSources') || '[]');
      const filtered = recent.filter(s => s.url !== source.url);
      const updated = [source, ...filtered].slice(0, 5);
      localStorage.setItem('recentSources', JSON.stringify(updated));
      setRecentSources(updated.slice(0, 3));
    } catch {
      // Silently fail if localStorage is not available
    }
  };

  const getFileIcon = (filename) => {
    const ext = filename.split('.').pop()?.toLowerCase();
    if (['pdf'].includes(ext)) return '📄';
    if (['doc', 'docx', 'txt', 'rtf'].includes(ext)) return '📝';
    if (['xls', 'xlsx', 'csv'].includes(ext)) return '📊';
    if (['ppt', 'pptx'].includes(ext)) return '🎨';
    if (['jpg', 'jpeg', 'png', 'gif', 'bmp', 'webp'].includes(ext)) return '🖼️';
    if (['mp3', 'wav', 'm4a', 'flac'].includes(ext)) return '🎵';
    if (['mp4', 'avi', 'mov', 'mkv', 'webm'].includes(ext)) return '🎬';
    return '📦';
  };

  const formatFileSize = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return Math.round((bytes / Math.pow(k, i)) * 10) / 10 + ' ' + sizes[i];
  };

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
    
    // Update UI with file list
    setUploadedFiles(Array.from(files).map(f => ({
      name: f.name,
      size: f.size,
      status: 'pending'
    })));
    
    setLoading(true);
    try {
      let result;
      if (draftMode && currentNotebook?.isDraft) {
        result = await uploadBatchWithAutoNotebook(files);
        if (result.notebook) {
          useAppStore.getState().setNewlyCreatedNotebookId(result.notebook.id);
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
      toast.success(`Successfully uploaded ${result.materials?.filter(m => m.status !== 'error').length || 0} file(s)`);
      onClose();
    } catch (error) {
      toast.error(error.details || error.message || 'Upload failed');
      setUploadedFiles([]);
    } finally {
      setLoading(false);
    }
  };

  const handleUrlUpload = async () => {
    if (!validateUrl(url)) return;
    
    setLoading(true);
    try {
      const autoCreate = !currentNotebook || currentNotebook.isDraft || draftMode;
      const notebookId = autoCreate ? null : currentNotebook.id;
      const result = await uploadUrl(url.trim(), notebookId, autoCreate, 'auto');
      if (result.notebook) {
        useAppStore.getState().setNewlyCreatedNotebookId(result.notebook.id);
        setCurrentNotebook(result.notebook);
        setDraftMode(false);
        router.replace(`/notebook/${result.notebook.id}`);
      }
      onMaterialAdded({
        id: result.material_id, filename: result.filename, title: result.title || result.filename,
        chunkCount: result.chunk_count, status: result.status, sourceType: result.source_type ?? 'url',
      });
      saveToRecentSources({ url: url.trim(), title: result.title || result.filename });
      setUrl('');
      toast.success('Source added successfully');
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
        useAppStore.getState().setNewlyCreatedNotebookId(result.notebook.id);
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
      toast.success('Text source added successfully');
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
      className="workspace-upload-overlay fixed inset-0 z-[120] flex items-start sm:items-center justify-center px-4 pt-24 sm:pt-0 animate-fade-in"
      onClick={(e) => { if (e.target === e.currentTarget && !loading) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Upload sources"
      ref={dialogRef}
    >
      <div className="workspace-upload-shell relative w-full max-w-[680px] flex flex-col rounded-2xl overflow-hidden animate-scale-in max-h-[calc(100vh-7rem)] sm:max-h-[88vh]">
        {}
        {}
        <div className="workspace-upload-header flex items-center justify-between px-6 py-5 border-b border-divider">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl flex items-center justify-center bg-gradient-to-br from-accent/20 to-accent/10">
              <CloudUpload className="w-5 h-5 text-accent-light" />
            </div>
            <div>
              <h2 className="text-lg font-semibold text-text-primary">Add Sources</h2>
              <p className="text-xs text-text-muted mt-0.5">Drag files, paste links, or add content</p>
            </div>
          </div>
          <button onClick={onClose} disabled={loading} className="btn-icon w-8 h-8 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors" title="Close (Esc)">
            <X className="w-4 h-4" />
          </button>
        </div>

        {}
        <div className="px-6 pt-4 pb-2">
          <div className="workspace-upload-tabs flex gap-1 p-1 bg-neutral-50 dark:bg-neutral-900 rounded-xl">
            {TABS.map((tab) => {
              const TabIcon = tab.icon;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id)}
                  className={`workspace-upload-tab flex items-center gap-2 flex-1 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-150 ${
                    activeTab === tab.id
                      ? 'workspace-upload-tab-active bg-white dark:bg-neutral-800 text-text-primary shadow-sm'
                      : 'text-text-muted hover:text-text-secondary'
                  }`}
                  title={tab.desc}
                >
                  <TabIcon className="w-4 h-4 flex-shrink-0" />
                  <span className="hidden sm:inline">{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {}
        <div className="flex-1 overflow-y-auto px-6 py-5">
          {activeTab === 'files' && (
            <div className="space-y-5">
              <div
                className={`workspace-upload-dropzone relative flex flex-col items-center justify-center rounded-2xl px-8 py-16 transition-all duration-200 cursor-pointer border-2 border-dashed ${
                  dragActive 
                    ? 'bg-accent/8 border-accent-light scale-[1.02]' 
                    : 'bg-neutral-50 dark:bg-neutral-900 border-neutral-200 dark:border-neutral-800 hover:border-accent/40'
                }`}
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !loading && fileInputRef.current?.click()}
              >
                <div className={`workspace-upload-drop-icon w-16 h-16 rounded-2xl flex items-center justify-center mb-4 transition-all duration-200 ${dragActive ? 'scale-110 bg-accent-light/20' : 'bg-neutral-100 dark:bg-neutral-800'}`}>
                  <CloudUpload className={`w-8 h-8 transition-colors ${dragActive ? 'text-accent-light' : 'text-text-muted'}`} />
                </div>
                <p className="text-base font-semibold text-text-primary mb-1">
                  {dragActive ? 'Drop files here' : 'Drag files here to upload'}
                </p>
                <p className="text-sm text-text-muted mb-5">or click to browse • max {getMaxUploadSizeMB()} MB per file</p>
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
                  className="btn-primary text-sm px-6 py-2.5 flex items-center gap-2"
                >
                  {loading ? (
                    <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</>
                  ) : (
                    <><File className="w-4 h-4" /> Choose Files</>
                  )}
                </button>
              </div>

              {uploadedFiles.length > 0 && (
                <div className="space-y-2 max-h-[120px] overflow-y-auto">
                  {uploadedFiles.map((file, idx) => (
                    <div key={idx} className="flex items-center gap-3 p-3 bg-neutral-50 dark:bg-neutral-900 rounded-lg">
                      <span className="text-lg">{getFileIcon(file.name)}</span>
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium text-text-primary truncate">{file.name}</p>
                        <p className="text-xs text-text-muted">{formatFileSize(file.size)}</p>
                      </div>
                      {file.status === 'pending' && <Loader2 className="w-4 h-4 animate-spin text-accent-light" />}
                      {file.status === 'complete' && <CheckCircle className="w-4 h-4 text-green-500" />}
                    </div>
                  ))}
                </div>
              )}

              <div className="grid grid-cols-2 gap-2">
                {FORMAT_GROUPS.slice(0, 3).map(({ icon, label, formats }) => (
                  <div key={label} className="workspace-upload-format-item flex items-start gap-2.5 px-3 py-2.5 rounded-xl bg-neutral-50 dark:bg-neutral-900 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                    <span className="text-base leading-none mt-0.5">{icon}</span>
                    <div className="min-w-0">
                      <p className="text-xs font-semibold text-text-secondary">{label}</p>
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
                <label className="block text-sm font-semibold text-text-secondary mb-2">Website or YouTube URL</label>
                <div className="flex gap-2.5">
                  <div className="relative flex-1">
                    <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-text-muted">
                      <Link className="w-4 h-4" />
                    </div>
                    <input
                      type="url"
                      placeholder="https://example.com or https://youtube.com/watch?v=..."
                      value={url}
                      onChange={(e) => {
                        setUrl(e.target.value);
                        setUrlError('');
                      }}
                      onKeyDown={(e) => e.key === 'Enter' && handleUrlUpload()}
                      className={`input pl-10 ${urlError ? 'border-red-500 focus:ring-red-500' : ''}`}
                    />
                  </div>
                  <button onClick={handleUrlUpload} disabled={loading || !url.trim()} className="workspace-upload-primary btn-primary whitespace-nowrap px-5 flex items-center gap-2">
                    {loading ? (
                      <><Loader2 className="w-4 h-4 animate-spin" /> Processing…</>
                    ) : (
                      <><Link className="w-4 h-4" /> Add</>
                    )}
                  </button>
                </div>
                {urlError && (
                  <div className="flex items-center gap-2 mt-2 text-sm text-red-600 dark:text-red-400">
                    <AlertCircle className="w-4 h-4 flex-shrink-0" />
                    <span>{urlError}</span>
                  </div>
                )}
              </div>

              {recentSources.length > 0 && (
                <div>
                  <div className="flex items-center gap-2 mb-3">
                    <Clock className="w-4 h-4 text-text-muted" />
                    <label className="text-xs font-semibold text-text-secondary">Recent</label>
                  </div>
                  <div className="space-y-2">
                    {recentSources.map((source, idx) => (
                      <button
                        key={idx}
                        onClick={() => {
                          setUrl(source.url);
                          setUrlError('');
                        }}
                        className="w-full text-left flex items-center gap-3 p-2.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
                      >
                        <Globe className="w-4 h-4 text-accent-light flex-shrink-0" />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-text-primary truncate">{source.title}</p>
                          <p className="text-xs text-text-muted truncate">{source.url}</p>
                        </div>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="grid grid-cols-2 gap-2.5">
                {[
                  { icon: '🌐', title: 'Any Website', desc: 'Articles, blogs, docs' },
                  { icon: '▶️', title: 'YouTube', desc: 'Auto transcript extraction' },
                  { icon: '📰', title: 'News', desc: 'Rich content parsing' },
                  { icon: '🔍', title: 'Auto Detect', desc: 'Smart recognition' },
                ].map(({ icon, title, desc }) => (
                  <div key={title} className="workspace-upload-format-item flex items-center gap-3 px-3.5 py-3 rounded-xl bg-neutral-50 dark:bg-neutral-900 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors">
                    <span className="text-lg">{icon}</span>
                    <div>
                      <p className="text-xs font-semibold text-text-secondary">{title}</p>
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
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-semibold text-text-secondary">Title *</label>
                  <span className="text-xs text-text-muted">{textTitle.length} characters</span>
                </div>
                <input 
                  type="text" 
                  placeholder="e.g., My Research Notes, Meeting Summary…" 
                  value={textTitle} 
                  onChange={(e) => setTextTitle(e.target.value)} 
                  maxLength={100}
                  className="input" 
                />
              </div>
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="block text-sm font-semibold text-text-secondary">Content *</label>
                  <span className="text-xs text-text-muted">{textContent.length} characters</span>
                </div>
                <textarea 
                  placeholder="Paste or type your text here… (minimum 10 characters)" 
                  value={textContent} 
                  onChange={(e) => setTextContent(e.target.value)} 
                  rows={8}
                  className="input resize-none leading-relaxed focus:ring-2 focus:ring-accent-light" 
                />
              </div>
              <button 
                onClick={handleTextUpload} 
                disabled={loading || !textContent.trim() || !textTitle.trim() || textContent.length < 10} 
                className="workspace-upload-primary btn-primary w-full justify-center py-2.5 flex items-center gap-2"
              >
                {loading ? (
                  <><Loader2 className="w-4 h-4 animate-spin" /> Adding…</>
                ) : (
                  <><CheckCircle className="w-4 h-4" /> Add Text Source</>
                )}
              </button>
            </div>
          )}

          {activeTab === 'ai' && (
            <AIResourceBuilder
              currentNotebook={currentNotebook}
              draftMode={draftMode}
              onMaterialAdded={onMaterialAdded}
              setCurrentNotebook={setCurrentNotebook}
              setDraftMode={setDraftMode}
              onClose={onClose}
            />
          )}
        </div>

        {loading && (
          <div className="workspace-upload-loading absolute inset-0 rounded-2xl flex items-center justify-center z-10 bg-white/80 dark:bg-neutral-950/80 backdrop-blur-sm">
            <div className="flex flex-col items-center gap-4">
              <div className="loading-spinner w-10 h-10 border-2 border-neutral-200 dark:border-neutral-800 border-t-accent-light rounded-full animate-spin" />
              <div className="text-center">
                <p className="text-sm font-semibold text-text-primary">Processing your source…</p>
                <p className="text-xs text-text-muted mt-1">This may take a moment</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

'use client';

import { useState, useCallback, useEffect } from 'react';
import {
  Settings, Search, FileText, ChevronDown, Globe,
  Check, Minus, AlertTriangle, Upload, X,
} from 'lucide-react';
import { useRouter } from 'next/navigation';
import useAppStore from '@/stores/useAppStore';
import useAuthStore from '@/stores/useAuthStore';
import { useToast } from '@/stores/useToastStore';
import {
  uploadBatch, uploadBatchWithAutoNotebook, getMaterials,
  getMaterialText, deleteMaterial, updateMaterial, webSearch, uploadUrl,
} from '@/lib/api/materials';
import useMaterialUpdates from '@/hooks/useMaterialUpdates';
import usePodcastStore from '@/stores/usePodcastStore';
import SourceItem from '@/components/notebook/SourceItem';
import UploadDialog from '@/components/notebook/UploadDialog';
import WebSearchDialog from '@/components/notebook/WebSearchDialog';
import DocumentPreview from '@/components/chat/DocumentPreview';

const ALL_FILE_TYPES = [
  { id: '', label: 'Any type' },
  { id: 'pdf', label: 'PDF Document (.pdf)' },
  { id: 'doc', label: 'Word Document (.doc, .docx)' },
  { id: 'ppt', label: 'PowerPoint (.ppt, .pptx)' },
  { id: 'xls', label: 'Excel (.xls, .xlsx)' },
  { id: 'txt', label: 'Text File (.txt)' },
  { id: 'csv', label: 'CSV File (.csv)' },
  { id: 'rtf', label: 'Rich Text Format (.rtf)' },
  { id: 'md', label: 'Markdown (.md)' },
  { id: 'json', label: 'JSON (.json)' },
  { id: 'xml', label: 'XML (.xml)' },
];

export default function Sidebar({ onNavigate }) {
  const router = useRouter();
  const { user } = useAuthStore();
  const toast = useToast();

  const {
    materials, setMaterials, currentMaterial, setCurrentMaterial,
    addMaterial, setLoadingState, loading, currentNotebook,
    setCurrentNotebook, draftMode, setDraftMode, selectedSources,
    setSelectedSources, toggleSourceSelection, selectAllSources,
    deselectAllSources,
  } = useAppStore();

  const handlePodcastWsEvent = usePodcastStore((s) => s.handleWsEvent);

  const [dragActive, setDragActive] = useState(false);
  const [width, setWidth] = useState(320);
  const [isResizing, setIsResizing] = useState(false);
  const [showTextModal, setShowTextModal] = useState(false);
  const [modalText, setModalText] = useState('');
  const [modalFilename, setModalFilename] = useState('');
  const [modalSourceFilename, setModalSourceFilename] = useState('');
  const [modalLoading, setModalLoading] = useState(false);
  const [showUploadDialog, setShowUploadDialog] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedFileType, setSelectedFileType] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  const [showSearchDialog, setShowSearchDialog] = useState(false);
  const [searchError, setSearchError] = useState(null);
  const [loadError, setLoadError] = useState(null);

  const minWidth = 260;
  const maxWidth = 600;

  const loadMaterials = useCallback(async (autoSelect = false) => {
    if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
      try {
        setLoadError(null);
        const loaded = await getMaterials(currentNotebook.id);
        const formatted = loaded.map((m) => ({
          id: m.id, filename: m.filename, title: m.title,
          status: m.status, chunkCount: m.chunk_count, source_type: m.source_type,
        }));
        setMaterials(formatted);
        // Only auto-select first material if none is currently selected in store
        const store = useAppStore.getState();
        if (formatted.length > 0 && !store.currentMaterial) {
          setCurrentMaterial(formatted[0]);
        }
        if (autoSelect) {
          const completedIds = formatted.filter((m) => m.status === 'completed').map((m) => m.id);
          if (completedIds.length > 0) {
            setSelectedSources((prev) => new Set([...prev, ...completedIds]));
          }
        }
      } catch {
        setLoadError('Failed to load sources. Click to retry.');
      }
    }
  }, [currentNotebook?.id, currentNotebook?.isDraft, draftMode, setMaterials, setCurrentMaterial, setSelectedSources]);

  useEffect(() => {
    loadMaterials(true);
  }, [currentNotebook?.id, loadMaterials]);

  // WebSocket real-time updates
  const handleWsMessage = useCallback((msg) => {
    if (msg.type?.startsWith('podcast_')) {
      handlePodcastWsEvent(msg);
      return;
    }
    if (msg.type === 'material_update' && msg.material_id) {
      setMaterials((prev) =>
        prev.map((m) =>
          m.id === msg.material_id
            ? { ...m, status: msg.status, ...(msg.title ? { title: msg.title } : {}), ...(msg.error ? { error: msg.error } : {}) }
            : m,
        ),
      );
      if (msg.status === 'completed' || msg.status === 'failed') {
        loadMaterials();
        if (msg.status === 'completed') {
          setSelectedSources((prev) => new Set([...prev, msg.material_id]));
        }
      }
    }
  }, [setMaterials, loadMaterials, setSelectedSources, handlePodcastWsEvent]);

  useMaterialUpdates(user?.id || null, handleWsMessage);

  // Fallback polling for processing materials
  useEffect(() => {
    const hasProcessing = materials.some((m) => m.status && !['completed', 'failed'].includes(m.status));
    if (!hasProcessing) return;
    const interval = setInterval(() => loadMaterials(true), 8000);
    return () => clearInterval(interval);
  }, [materials, loadMaterials]);

  // Resize handling
  const handleMouseMove = useCallback((e) => {
    if (isResizing) {
      const newWidth = e.clientX;
      if (newWidth >= minWidth && newWidth <= maxWidth) setWidth(newWidth);
    }
  }, [isResizing]);

  const handleMouseUp = useCallback(() => setIsResizing(false), []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const handleFileUpload = async (files) => {
    if (!files?.length) return;
    setLoadingState('upload', true);
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
        result = await uploadBatch(files, currentNotebook?.id);
      }
      result.materials?.forEach((m) => {
        if (m.status !== 'error') {
          addMaterial({ id: m.material_id, filename: m.filename, chunkCount: m.chunk_count, status: m.status });
        }
      });
    } catch (error) {
      toast.error('Upload failed: ' + error.message);
    } finally {
      setLoadingState('upload', false);
    }
  };

  const handleSearchSubmit = async (e) => {
    if (e.key !== 'Enter' || !searchQuery.trim()) return;
    setIsSearching(true);
    setShowSearchDialog(true);
    setSearchResults([]);
    setSearchError(null);
    try {
      let fileType = selectedFileType;
      let cleanQuery = searchQuery.trim();
      const filetypeMatch = cleanQuery.match(/filetype:(\w+)/i);
      if (filetypeMatch) {
        if (!fileType) fileType = filetypeMatch[1];
        cleanQuery = cleanQuery.replace(/filetype:\w+/gi, '').trim();
      }
      const results = await webSearch(cleanQuery, fileType);
      setSearchResults(results);
    } catch (error) {
      setSearchError(error.message || 'Failed to search');
    } finally {
      setIsSearching(false);
    }
  };

  const handleAddWebSources = async (selectedResults) => {
    if (!selectedResults?.length) return;
    setLoadingState('upload', true);
    try {
      let currentNbId = currentNotebook?.isDraft ? null : currentNotebook?.id;
      let newlyCreatedNotebook = null;
      for (const resObj of selectedResults) {
        const autoCreate = !currentNbId;
        const res = await uploadUrl(resObj.link, currentNbId, autoCreate, 'auto', resObj.title);
        if (res.notebook && !newlyCreatedNotebook) {
          newlyCreatedNotebook = res.notebook;
          currentNbId = res.notebook.id;
          setCurrentNotebook(res.notebook);
          setDraftMode(false);
        }
        addMaterial({ id: res.material_id, filename: res.filename, title: resObj.title, status: res.status, source_type: res.source_type || 'url' });
      }
      if (newlyCreatedNotebook) router.replace(`/notebook/${newlyCreatedNotebook.id}`);
    } catch {
      toast.error('Failed to add some sources');
    } finally {
      setLoadingState('upload', false);
      loadMaterials();
    }
  };

  const handleDrag = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') setDragActive(true);
    else if (e.type === 'dragleave') setDragActive(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files?.length) handleFileUpload(Array.from(e.dataTransfer.files));
  };

  const handleSeeText = async (source) => {
    setModalFilename(source.title || source.filename);
    setModalSourceFilename(source.filename || '');
    setModalText('');
    setModalLoading(true);
    setShowTextModal(true);
    try {
      const response = await getMaterialText(source.id);
      setModalText(response.text);
      if (response.filename) setModalSourceFilename(response.filename);
    } catch {
      setModalText('Error: Failed to load material text.');
    } finally {
      setModalLoading(false);
    }
  };

  const handleRemoveSource = async (source) => {
    try {
      await deleteMaterial(source.id);
      const next = materials.filter((m) => m.id !== source.id);
      setMaterials(next);
      if (currentMaterial?.id === source.id) setCurrentMaterial(next.length > 0 ? next[0] : null);
    } catch (error) {
      toast.error('Failed to remove source: ' + error.message);
    }
  };

  const handleRenameSource = async (source, newName) => {
    try {
      const isUrlOrYoutube = (source.source_type || source.sourceType) === 'url' || (source.source_type || source.sourceType) === 'youtube';
      const payload = isUrlOrYoutube ? { title: newName } : { filename: newName };
      await updateMaterial(source.id, payload);
      const updates = isUrlOrYoutube ? { title: newName } : { filename: newName };
      setMaterials((prev) => prev.map((m) => (m.id === source.id ? { ...m, ...updates } : m)));
      if (currentMaterial?.id === source.id) setCurrentMaterial({ ...currentMaterial, ...updates });
    } catch (error) {
      toast.error('Failed to rename source: ' + error.message);
    }
  };

  return (
    <>
      <aside
        className="h-full overflow-hidden flex flex-col relative bg-surface text-text-primary"
        style={{ width: `${width}px`, minWidth: `${minWidth}px` }}
      >
        {/* Header */}
        <div className="panel-header px-4">
          <div className="flex justify-between items-center w-full">
            <div className="flex items-center gap-2">
              <span className="text-text-primary font-semibold text-sm tracking-tight">Sources</span>
              {materials.length > 0 && (
                <span className="text-[10px] font-semibold px-1.5 py-0.5 rounded-full" style={{ background: 'var(--accent-subtle)', color: 'var(--accent)' }}>
                  {materials.length}
                </span>
              )}
            </div>
            <button className="btn-icon-sm" onClick={() => toast.info('Source settings coming soon!')} aria-label="Source settings">
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Add Source & Search */}
        <div className="p-4 space-y-5">
          <button
            className="w-full py-2.5 px-4 rounded-xl border border-dashed border-accent/30 bg-accent/5 hover:bg-accent/10 hover:border-accent/50 transition-all flex items-center justify-center gap-2 text-sm text-accent font-semibold"
            onClick={() => setShowUploadDialog(true)}
            disabled={loading.upload}
          >
            {loading.upload ? <div className="loading-spinner w-4 h-4" /> : <span className="text-base leading-none font-bold">+</span>}
            Add sources
          </button>

          {/* Search Box */}
          <div className="p-3 rounded-xl space-y-3 relative overflow-hidden bg-surface-raised">
            <div className="absolute top-0 right-0 w-24 h-24 bg-accent/5 rounded-full blur-2xl pointer-events-none transform translate-x-8 -translate-y-8" />
            <div className="flex items-center gap-2.5 px-3 py-2 rounded-lg bg-surface focus-within:ring-1 focus-within:ring-accent/20 transition-all relative z-10">
              <Search className="w-3.5 h-3.5 text-accent" />
              <input
                type="text"
                placeholder="Search the web for sources..."
                className="bg-transparent text-xs w-full outline-none text-text-primary placeholder:text-text-muted"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleSearchSubmit}
              />
            </div>
            <div className="flex items-center justify-between relative z-10">
              <div className="flex flex-col relative w-[160px]">
                <div className="absolute inset-y-0 left-0 pl-2.5 flex items-center pointer-events-none">
                  <FileText className="w-3 h-3 text-text-muted" />
                </div>
                <select
                  value={selectedFileType || ''}
                  onChange={(e) => setSelectedFileType(e.target.value || null)}
                  className="block w-full pl-7 pr-6 py-1.5 text-[11.5px] font-medium text-text-secondary bg-surface rounded-lg appearance-none focus:outline-none hover:bg-surface-raised transition-colors cursor-pointer truncate"
                >
                  {ALL_FILE_TYPES.map((ft) => (
                    <option key={ft.id} value={ft.id} className="bg-surface text-text-primary">{ft.label}</option>
                  ))}
                </select>
                <div className="absolute inset-y-0 right-0 pr-2 flex items-center pointer-events-none">
                  <ChevronDown className="w-3 h-3 text-text-muted" />
                </div>
              </div>
              <button
                onClick={() => handleSearchSubmit({ key: 'Enter' })}
                disabled={!searchQuery.trim()}
                className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg bg-accent hover:bg-accent-light text-white shadow-lg shadow-accent-dark/20 transition-all font-semibold text-[12px] disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                <Globe className="w-3.5 h-3.5 group-hover:rotate-12 transition-transform" /> Web
              </button>
            </div>
          </div>
        </div>

        {/* Select All */}
        <div className="px-4 pt-3 pb-2 flex justify-between items-center">
          <span className="text-[10.5px] font-semibold text-text-muted uppercase tracking-wider">All Sources</span>
          <button
            onClick={() => selectedSources.size === materials.length && materials.length > 0 ? deselectAllSources() : selectAllSources()}
            className={`flex items-center justify-center w-4 h-4 rounded-[4px] border transition-colors ${selectedSources.size === materials.length && materials.length > 0
              ? 'bg-transparent border-text-primary text-text-primary'
              : selectedSources.size > 0 ? 'bg-transparent border-border-strong text-text-muted' : 'border-border bg-transparent hover:border-border-strong'
              }`}
            title={selectedSources.size === materials.length && materials.length > 0 ? 'Deselect all' : 'Select all'}
          >
            {selectedSources.size === materials.length && materials.length > 0 ? (
              <Check className="w-3 h-3" strokeWidth={2.5} />
            ) : selectedSources.size > 0 ? (
              <Minus className="w-3 h-3" strokeWidth={2.5} />
            ) : null}
          </button>
        </div>

        {/* Sources List */}
        <div
          className={`flex-1 overflow-y-auto transition-colors ${dragActive ? 'bg-accent/5' : ''}`}
          onDragEnter={handleDrag} onDragLeave={handleDrag} onDragOver={handleDrag} onDrop={handleDrop}
        >
          {loadError && (
            <button onClick={() => { setLoadError(null); loadMaterials(); }} className="w-full px-4 py-2 text-xs text-danger bg-danger-subtle hover:bg-danger-subtle transition-colors flex items-center gap-2">
              <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> {loadError}
            </button>
          )}
          {materials.length > 0 ? (
            <div className="p-2">
              <div className="space-y-0.5">
                {materials.map((source) => (
                  <SourceItem
                    key={source.id}
                    source={source}
                    checked={selectedSources.has(source.id)}
                    active={currentMaterial?.id === source.id}
                    anySelected={selectedSources.size > 0}
                    onClick={() => setCurrentMaterial(source)}
                    onToggle={() => toggleSourceSelection(source.id)}
                    onSeeText={handleSeeText}
                    onRename={handleRenameSource}
                    onRemove={handleRemoveSource}
                  />
                ))}
              </div>
            </div>
          ) : (
            <div className="h-full p-4">
              <div className={`dropzone h-full ${dragActive ? 'dropzone-active' : ''}`}>
                <div className="empty-state-icon"><Upload className="w-8 h-8 text-text-muted" /></div>
                <p className="empty-state-title">Add sources</p>
                <p className="empty-state-description mt-1">Upload PDFs, docs, or text files to get started</p>
              </div>
            </div>
          )}
        </div>

        {/* Resize Handle */}
        <div
          className={`absolute top-0 right-0 w-1.5 h-full cursor-col-resize transition-colors z-10 group ${isResizing ? 'bg-accent/50' : 'hover:bg-accent/30'}`}
          onMouseDown={() => setIsResizing(true)}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize sidebar"
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-text-muted/20 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </aside>

      {/* Text Modal */}
      {showTextModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-backdrop backdrop-blur-sm p-4 sm:p-6" onClick={() => setShowTextModal(false)}>
          <div className="bg-surface rounded-2xl shadow-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden relative" style={{ border: '1px solid rgba(255,255,255,0.06)' }} onClick={(e) => e.stopPropagation()}>
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-3/4 h-32 bg-accent-subtle rounded-full blur-[60px] pointer-events-none" />
            <div className="p-4 sm:p-5 flex items-center justify-between bg-surface/80 backdrop-blur-xl z-10" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 rounded-lg bg-accent-subtle text-accent-light">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-[15px] font-semibold text-text-primary truncate">{modalFilename}</h3>
                  <p className="text-[13px] text-text-muted flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent" /> Document Preview
                  </p>
                </div>
              </div>
              <button onClick={() => setShowTextModal(false)} className="p-2 mr-1 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto bg-surface relative z-10 p-5 sm:p-8 custom-scrollbar">
              {modalLoading ? (
                <div className="flex flex-col items-center justify-center h-full gap-5">
                  <div className="relative">
                    <div className="loading-spinner w-12 h-12 text-accent" />
                    <div className="absolute inset-0 bg-accent-subtle blur-xl rounded-full" />
                  </div>
                  <p className="text-[14px] text-text-muted font-medium tracking-wide animate-pulse">Analyzing document content...</p>
                </div>
              ) : (
                <div className="max-w-5xl mx-auto rounded-xl">
                  <DocumentPreview content={modalText} filename={modalSourceFilename} />
                </div>
              )}
            </div>
            <div className="p-4 bg-surface/95 backdrop-blur-xl flex justify-end z-10 rounded-b-2xl" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
              <button onClick={() => setShowTextModal(false)} className="px-5 py-2 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors">Close Preview</button>
            </div>
          </div>
        </div>
      )}

      <UploadDialog
        isOpen={showUploadDialog}
        onClose={() => setShowUploadDialog(false)}
        currentNotebook={currentNotebook}
        draftMode={draftMode}
        onMaterialAdded={addMaterial}
        setCurrentNotebook={setCurrentNotebook}
        setDraftMode={setDraftMode}
      />

      <WebSearchDialog
        isOpen={showSearchDialog}
        onClose={() => setShowSearchDialog(false)}
        results={searchResults}
        isSearching={isSearching}
        error={searchError}
        query={searchQuery}
        onAddSelected={handleAddWebSources}
      />
    </>
  );
}

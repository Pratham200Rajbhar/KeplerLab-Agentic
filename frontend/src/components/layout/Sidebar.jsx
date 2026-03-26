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
import useResizablePanel from '@/hooks/useResizablePanel';
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
import { PANEL } from '@/lib/utils/constants';

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

  const materials = useAppStore((s) => s.materials);
  const setMaterials = useAppStore((s) => s.setMaterials);
  const currentMaterial = useAppStore((s) => s.currentMaterial);
  const setCurrentMaterial = useAppStore((s) => s.setCurrentMaterial);
  const addMaterial = useAppStore((s) => s.addMaterial);
  const setLoadingState = useAppStore((s) => s.setLoadingState);
  const loading = useAppStore((s) => s.loading);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const setCurrentNotebook = useAppStore((s) => s.setCurrentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const setSelectedSources = useAppStore((s) => s.setSelectedSources);
  const toggleSourceSelection = useAppStore((s) => s.toggleSourceSelection);
  const selectAllSources = useAppStore((s) => s.selectAllSources);
  const deselectAllSources = useAppStore((s) => s.deselectAllSources);
  const setNewlyCreatedNotebookId = useAppStore((s) => s.setNewlyCreatedNotebookId);
  const draftMode = useAppStore((s) => s.draftMode);
  const setDraftMode = useAppStore((s) => s.setDraftMode);

  const handlePodcastWsEvent = usePodcastStore((s) => s.handleWsEvent);

  const { width, startDrag } = useResizablePanel('left', {
    defaultWidth: PANEL.SIDEBAR.DEFAULT_WIDTH,
    minWidth: PANEL.SIDEBAR.MIN_WIDTH,
    maxWidth: PANEL.SIDEBAR.MAX_WIDTH,
  });

  const [dragActive, setDragActive] = useState(false);
  const [showTextModal, setShowTextModal] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
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
  const [loadError, setLoadError] = useState(null);
  const [isFileTypeDropdownOpen, setIsFileTypeDropdownOpen] = useState(false);

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
        
        const store = useAppStore.getState();
        if (formatted.length > 0 && !store.currentMaterial) {
          setCurrentMaterial(formatted[0]);
        }
        if (autoSelect) {
          const completedIds = formatted.filter((m) => m.status === 'completed').map((m) => m.id);
          if (completedIds.length > 0) {
            setSelectedSources((prev) => {
              const merged = [...new Set([...prev, ...completedIds])];
              return merged;
            });
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

  
  const handleWsMessage = useCallback((msg) => {
    if (msg.type?.startsWith('podcast_')) {
      handlePodcastWsEvent(msg);
      return;
    }
    if (msg.type === 'presentation_update_progress') {
      const store = useAppStore.getState();
      if (store.setPresentationUpdateProgress) {
        store.setPresentationUpdateProgress(msg.message);
      }
      return;
    }
    if (msg.type === 'notebook_update' && msg.notebook_id) {
      if (currentNotebook?.id === msg.notebook_id) {
        setCurrentNotebook({ ...currentNotebook, name: msg.name });
      }
      
      window.dispatchEvent(
        new CustomEvent('notebookNameUpdate', {
          detail: { id: msg.notebook_id, name: msg.name },
        })
      );
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
          setSelectedSources((prev) => {
            if (prev.includes(msg.material_id)) return prev;
            return [...prev, msg.material_id];
          });
        }
      }
    }
  }, [setMaterials, loadMaterials, setSelectedSources, handlePodcastWsEvent, currentNotebook, setCurrentNotebook]);

  useMaterialUpdates(user?.id || null, handleWsMessage);

  
  useEffect(() => {
    const hasProcessing = materials.some((m) => m.status && !['completed', 'failed'].includes(m.status));
    if (!hasProcessing) return;
    const interval = setInterval(() => loadMaterials(true), 8000);
    return () => clearInterval(interval);
  }, [materials, loadMaterials]);

  const handleFileUpload = async (files) => {
    if (!files?.length) return;
    setLoadingState('upload', true);
    try {
      let result;
      if (draftMode && currentNotebook?.isDraft) {
        result = await uploadBatchWithAutoNotebook(files);
        if (result.notebook) {
          setNewlyCreatedNotebookId(result.notebook.id);
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
      toast.error(error.message || 'Failed to search');
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
          setNewlyCreatedNotebookId(res.notebook.id);
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

  const closePreviewModal = useCallback(() => {
    setModalVisible(false);
    setTimeout(() => setShowTextModal(false), 280);
  }, []);

  useEffect(() => {
    if (!showTextModal) return;
    const onKey = (e) => { if (e.key === 'Escape') closePreviewModal(); };
    document.addEventListener('keydown', onKey);
    return () => document.removeEventListener('keydown', onKey);
  }, [showTextModal, closePreviewModal]);

  const handleSeeText = async (source) => {
    setModalFilename(source.title || source.filename);
    setModalSourceFilename(source.filename || '');
    setModalText('');
    setModalLoading(true);
    setShowTextModal(true);
    requestAnimationFrame(() => requestAnimationFrame(() => setModalVisible(true)));
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
        className="workspace-sidebar-shell h-full overflow-hidden flex flex-col relative text-text-primary"
        style={{ width: `${width}px` }}
      >
        {}
        <div className="workspace-sidebar-header flex items-center justify-between p-5 shrink-0">
          <div className="flex items-center gap-2.5">
            <span className="text-text-primary font-bold text-[13px] tracking-wide uppercase">Sources</span>
            {materials.length > 0 && (
              <span className="workspace-sidebar-count text-[10px] font-bold px-2 py-0.5 rounded-md text-accent">
                {materials.length}
              </span>
            )}
          </div>
          <button className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-all" onClick={() => toast.info('Source settings coming soon!')} aria-label="Source settings">
            <Settings className="w-4 h-4" />
          </button>
        </div>

        {}
        <div className="p-4 space-y-5 relative z-10">
          <button
            className="workspace-action-button group relative w-full py-3.5 px-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-all duration-300 overflow-hidden text-white shadow-lg"
            onClick={() => setShowUploadDialog(true)}
            disabled={loading.upload}
          >
            {}
            <div className="absolute inset-0 bg-gradient-to-r from-accent to-accent-light opacity-90 group-hover:opacity-100 transition-opacity" />
            <div className="absolute inset-0 bg-gradient-to-r from-accent-light to-accent opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
            
            {loading.upload ? (
              <div className="loading-spinner w-4 h-4 relative z-10" />
            ) : (
              <div className="w-5 h-5 relative z-10 flex border-none bg-white/20 rounded-lg items-center justify-center shrink-0 transform group-hover:scale-110 transition-transform">
                <span className="text-[15px] font-bold leading-none mb-0.5">+</span>
              </div>
            )}
            <span className="relative z-10 text-[14px] font-semibold tracking-wide">Add sources</span>
          </button>

          {}
          <div className="workspace-search-shell p-3.5 rounded-2xl space-y-3.5 relative">
            <div className="absolute top-0 right-0 w-32 h-32 bg-accent/10 rounded-full blur-[40px] pointer-events-none transform translate-x-12 -translate-y-12" />
            
            <div className="workspace-search-input flex items-center gap-2.5 px-4 py-3 rounded-xl transition-all relative z-10">
              <Search className="w-4 h-4 text-text-muted" />
              <input
                type="text"
                placeholder="Search the web for sources..."
                className="bg-transparent text-[13px] w-full outline-none text-text-primary placeholder:text-text-muted"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyDown={handleSearchSubmit}
              />
            </div>
            <div className="flex items-center justify-between relative z-10">
              <div className="relative" style={{ width: '60%' }}>
                <button
                  type="button"
                  onClick={() => setIsFileTypeDropdownOpen(!isFileTypeDropdownOpen)}
                  className="workspace-filetype-select w-full flex items-center justify-between px-3.5 py-2.5 text-[12.5px] font-semibold rounded-xl transition-all"
                >
                  <div className="flex items-center gap-2.5 truncate">
                    <FileText className="w-3.5 h-3.5 text-accent" />
                    <span className="truncate">{selectedFileType ? ALL_FILE_TYPES.find(f => f.id === selectedFileType)?.label : 'Any file type'}</span>
                  </div>
                  <ChevronDown className={`w-3.5 h-3.5 text-text-muted transition-transform ${isFileTypeDropdownOpen ? 'rotate-180' : ''}`} />
                </button>
                
                {isFileTypeDropdownOpen && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={() => setIsFileTypeDropdownOpen(false)} />
                    <div className="absolute top-full left-0 mt-2 w-[240px] max-h-[280px] overflow-y-auto bg-[#1C1C1E] border-none rounded-2xl shadow-[0_12px_40px_rgba(0,0,0,0.6)] z-50 py-2 custom-scrollbar animate-in fade-in slide-in-from-top-2">
                       {ALL_FILE_TYPES.map((ft) => (
                         <button
                           key={ft.id}
                           onClick={() => { setSelectedFileType(ft.id); setIsFileTypeDropdownOpen(false); }}
                           className={`w-full text-left px-4 py-2.5 text-[13px] font-semibold hover:bg-accent/10 transition-colors flex items-center gap-2.5 ${selectedFileType === ft.id ? 'text-accent bg-accent/5' : 'text-text-secondary hover:text-text-primary'}`}
                         >
                           {selectedFileType === ft.id && <Check className="w-3.5 h-3.5 text-accent shrink-0" />}
                           <span className={selectedFileType === ft.id ? '' : 'ml-6'}>{ft.label}</span>
                         </button>
                       ))}
                    </div>
                  </>
                )}
              </div>
              <button
                onClick={() => handleSearchSubmit({ key: 'Enter' })}
                disabled={!searchQuery.trim()}
                className="workspace-web-btn flex items-center gap-2 px-4 py-2.5 rounded-xl transition-all font-bold text-[13px] disabled:opacity-50 disabled:cursor-not-allowed group"
              >
                <Globe className="w-3.5 h-3.5 group-hover:scale-110 transition-transform" /> <span className="tracking-wide">Web</span>
              </button>
            </div>
          </div>
        </div>

        {}
        <div className="workspace-sources-meta px-5 pt-3 pb-2 flex justify-between items-center relative z-10">
          <span className="text-[10px] font-bold text-text-muted uppercase tracking-[0.15em]">All Sources</span>
          <button
            onClick={() => selectedSources.length === materials.length && materials.length > 0 ? deselectAllSources() : selectAllSources()}
            className={`flex items-center justify-center w-4 h-4 rounded-[4px] transition-colors ${selectedSources.length === materials.length && materials.length > 0
              ? 'bg-accent text-white shadow-sm'
              : selectedSources.length > 0 ? 'bg-text-muted/20 text-text-muted' : 'bg-surface-raised/50 hover:bg-surface-raised'
              }`}
            title={selectedSources.length === materials.length && materials.length > 0 ? 'Deselect all' : 'Select all'}
            aria-label={selectedSources.length === materials.length && materials.length > 0 ? 'Deselect all sources' : 'Select all sources'}
          >
            {selectedSources.length === materials.length && materials.length > 0 ? (
              <Check className="w-3 h-3" strokeWidth={2.5} />
            ) : selectedSources.length > 0 ? (
              <Minus className="w-3 h-3" strokeWidth={2.5} />
            ) : null}
          </button>
        </div>

        {}
        <div
          className={`workspace-source-list flex-1 overflow-y-auto transition-colors ${dragActive ? 'bg-accent/5' : ''}`}
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
                    checked={selectedSources.includes(source.id)}
                    active={currentMaterial?.id === source.id}
                    anySelected={selectedSources.length > 0}
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
            <div className="h-full p-4 flex items-center justify-center">
              <div className={`workspace-dropzone dropzone w-full h-full flex flex-col items-center justify-center rounded-3xl transition-all ${dragActive ? 'bg-accent/5' : ''}`}>
                <div className="w-16 h-16 bg-surface-raised rounded-full flex items-center justify-center mb-5 shadow-sm"><Upload className="w-7 h-7 text-text-muted" strokeWidth={1.5} /></div>
                <p className="text-[16px] font-bold text-text-primary tracking-tight">Add sources</p>
                <p className="text-[13.5px] text-text-muted mt-2 text-center max-w-[200px] leading-relaxed font-medium">Upload PDFs, docs, or text files to get started.</p>
              </div>
            </div>
          )}
        </div>

        {}
        <div
          className="absolute top-0 right-0 w-1.5 h-full cursor-col-resize transition-colors z-10 group hover:bg-accent/30"
          onMouseDown={startDrag}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize sidebar"
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-text-muted/20 opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>
      </aside>

      {}
      {showTextModal && (
        <div className={`workspace-doc-preview-overlay fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 transition-all duration-[280ms] ${modalVisible ? 'opacity-100' : 'opacity-0 pointer-events-none'}`} onClick={closePreviewModal}>
          <div className={`workspace-doc-preview-shell rounded-2xl w-full max-w-5xl h-[85vh] flex flex-col overflow-hidden relative transition-all duration-[280ms] ${modalVisible ? 'scale-100 opacity-100 translate-y-0' : 'scale-95 opacity-0 translate-y-5'}`} onClick={(e) => e.stopPropagation()}>
            <div className="workspace-doc-preview-header p-4 sm:p-5 flex items-center justify-between border-b border-border z-10 shrink-0">
              <div className="flex items-center gap-3 min-w-0">
                <div className="p-2 rounded-xl bg-accent-subtle text-accent-light shrink-0">
                  <FileText className="w-5 h-5" />
                </div>
                <div className="min-w-0">
                  <h3 className="text-[15px] font-semibold text-text-primary truncate">{modalFilename}</h3>
                  <p className="text-[12px] text-text-muted flex items-center gap-1.5 mt-0.5">
                    <span className="w-1.5 h-1.5 rounded-full bg-accent shrink-0" />
                    Document Preview
                    {modalSourceFilename && !modalLoading && (
                      <span className="text-text-muted/50">· {modalSourceFilename.split('.').pop()?.toUpperCase()}</span>
                    )}
                  </p>
                </div>
              </div>
              <button onClick={closePreviewModal} className="p-2 rounded-xl text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors shrink-0" aria-label="Close document preview">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="workspace-doc-preview-body flex-1 overflow-y-auto relative z-10 p-5 sm:p-8 custom-scrollbar">
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
            <div className="workspace-doc-preview-footer px-4 py-3 flex items-center justify-between border-t border-border z-10 shrink-0">
              <p className="text-[12px] text-text-muted">Press <kbd className="px-1.5 py-0.5 rounded bg-surface-overlay border border-border text-[11px] font-mono">Esc</kbd> to close</p>
              <button onClick={closePreviewModal} className="px-4 py-1.5 rounded-lg text-sm font-medium text-text-secondary hover:text-text-primary hover:bg-surface-raised transition-colors">Close</button>
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
        error={null}
        query={searchQuery}
        onAddSelected={handleAddWebSources}
      />
    </>
  );
}

'use client';

import { useState } from 'react';
import { Globe, AlertTriangle, Search, Check, Eye, ExternalLink } from 'lucide-react';
import Modal from '@/components/ui/Modal';

const VIEWABLE_EXTS = new Set(['.pdf', '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp', '.txt', '.csv', '.md', '.rtf']);

function getFileExt(url) {
  try {
    const path = new URL(url).pathname.toLowerCase();
    const dot = path.lastIndexOf('.');
    return dot !== -1 ? path.slice(dot) : '';
  } catch { return ''; }
}

function isFileUrl(url) { return VIEWABLE_EXTS.has(getFileExt(url)); }
function viewerHref(url) { return `/view?url=${encodeURIComponent(url)}`; }

function getDomain(url) {
  try { return new URL(url).hostname.replace(/^www\./, ''); }
  catch { return ''; }
}

export default function WebSearchDialog({ isOpen, onClose, results = [], onAddSelected, isSearching = false, error = null, query = '' }) {
  const [selectedResults, setSelectedResults] = useState(new Set());
  const [previewResult, setPreviewResult] = useState(null);

  if (!isOpen) return null;

  const toggleSelection = (result) => {
    const next = new Set(selectedResults);
    const exists = Array.from(next).find((r) => r.link === result.link);
    if (exists) next.delete(exists);
    else next.add(result);
    setSelectedResults(next);
  };

  const handleSelectAll = () => {
    setSelectedResults(selectedResults.size === results.length ? new Set() : new Set(results));
  };

  const handleAdd = () => {
    onAddSelected(Array.from(selectedResults));
    onClose();
    setSelectedResults(new Set());
    setPreviewResult(null);
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={() => { onClose(); setPreviewResult(null); }}
      title="Discover Web Resources"
      maxWidth={previewResult ? "max-w-[1150px] transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]" : "max-w-[650px] transition-all duration-500 ease-[cubic-bezier(0.23,1,0.32,1)]"}
      icon={
        <div className="p-1.5 rounded-lg bg-accent/10">
          <Globe className="w-5 h-5 text-accent" strokeWidth={1.5} />
        </div>
      }
      footer={
        <div className="flex justify-between items-center w-full bg-surface/50 backdrop-blur-md px-6 py-4 rounded-b-2xl">
          <span className="text-sm text-text-muted font-bold tracking-wide">{selectedResults.size} resources selected</span>
          <div className="flex gap-3">
            <button className="px-5 py-2.5 text-sm font-semibold text-text-secondary hover:text-text-primary hover:bg-surface-raised rounded-xl transition-all" onClick={() => { onClose(); setPreviewResult(null); }}>Cancel</button>
            <button className="px-6 py-2.5 text-sm font-bold bg-accent hover:bg-accent-light text-white rounded-xl shadow-[0_4px_15px_rgba(16,185,129,0.3)] disabled:opacity-50 disabled:cursor-not-allowed transition-all" onClick={handleAdd} disabled={selectedResults.size === 0}>Add to Notebook</button>
          </div>
        </div>
      }
    >
      <div className="flex h-[68vh] min-h-[520px] -mx-6 -mt-2 overflow-hidden relative">
        {}
        <div className="flex-1 flex flex-col h-full bg-transparent relative z-10 w-full transition-all duration-500 overflow-hidden">
          <div className="flex justify-between items-center px-6 pb-6 pt-2 shrink-0">
            <p className="text-[13px] font-medium text-text-muted">
              Results found for <span className="text-[#10B981] font-bold px-3 py-1.5 rounded-lg bg-[#10B981]/15 ml-2">&quot;{query}&quot;</span>
            </p>
            {results.length > 0 && (
              <button className="text-[11px] uppercase tracking-[0.15em] text-text-muted/70 hover:text-text-primary font-bold transition-all p-1" onClick={handleSelectAll}>
                {selectedResults.size === results.length ? 'DESELECT ALL' : 'SELECT ALL'}
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto pt-4 px-6 pr-4 custom-scrollbar pb-6 space-y-3">
            {isSearching ? (
              <div className="flex flex-col items-center justify-center h-full space-y-4">
                <div className="w-10 h-10 border-2 border-accent/20 border-t-accent rounded-full animate-spin" />
                <p className="text-[14px] text-text-muted animate-pulse font-bold tracking-wide">Scanning web resources...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full space-y-5 text-center px-4">
                <div className="p-4 bg-danger-subtle rounded-2xl border border-danger/10 shadow-sm">
                  <AlertTriangle className="w-10 h-10 text-danger" strokeWidth={1.5} />
                </div>
                <p className="text-[16px] font-bold text-danger">Search Interrupted</p>
                <p className="text-[14px] text-text-muted leading-relaxed font-medium max-w-[280px]">{error}</p>
              </div>
            ) : results.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full space-y-4 text-center">
                <div className="p-4 bg-surface-raised rounded-2xl shadow-sm">
                  <Search className="w-10 h-10 text-text-muted/40" strokeWidth={1.5} />
                </div>
                <p className="text-[16px] font-bold text-text-primary tracking-wide">No resources found</p>
                <p className="text-[13.5px] text-text-muted font-medium max-w-[220px]">Try broadening your search.</p>
              </div>
            ) : (
              results.map((result) => {
                const domain = getDomain(result.link);
                const isSelected = Array.from(selectedResults).some((r) => r.link === result.link);
                const isPreviewed = previewResult?.link === result.link;
                return (
                  <div
                    key={result.link}
                    onMouseEnter={() => setPreviewResult(result)}
                    onClick={() => { toggleSelection(result); setPreviewResult(result); }}
                    className={`relative py-3 px-4 rounded-2xl transition-all duration-300 cursor-pointer group ${
                      isSelected 
                        ? 'bg-surface-raised shadow-lg' 
                        : 'bg-transparent hover:bg-surface-raised/40'
                    } ${isPreviewed && !isSelected ? 'bg-surface-raised/20' : ''}`}
                  >
                    <div className="flex items-center gap-5">
                      <div className={`shrink-0 w-5 h-5 rounded-full flex items-center justify-center transition-all ${isSelected ? 'bg-[#10B981] shadow-md border-none' : 'border border-white/10 group-hover:border-white/20 bg-transparent cursor-pointer'}`}>
                        {isSelected && <Check className="w-3 h-3 text-white" strokeWidth={4} />}
                      </div>
                      <div className="flex-1 min-w-0 flex flex-col gap-1.5">
                        <h3 className={`text-[16px] font-bold leading-tight transition-colors line-clamp-2 ${isSelected || isPreviewed ? 'text-white' : 'text-white/90'}`}>{result.title}</h3>
                        <div className="flex items-center gap-2.5">
                          {domain && (
                            /* eslint-disable-next-line @next/next/no-img-element */
                            <img
                              src={`https://www.google.com/s2/favicons?sz=64&domain=${domain}`}
                              alt=""
                              className="shrink-0 w-3.5 h-3.5 rounded-sm object-contain opacity-70"
                              onError={(e) => { e.target.style.display = 'none'; }}
                            />
                          )}
                          <div className="flex items-center gap-2 truncate">
                            <span className="text-[11px] font-bold uppercase tracking-widest text-[#8a8a8e] truncate max-w-[140px]">{domain}</span>
                            <span className="text-[10px] text-[#48484a] shrink-0">●</span>
                            <span className="text-[12px] font-medium text-[#636366] truncate" title={result.link}>{result.link}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {}
        {previewResult && (
          <div className="w-[500px] shrink-0 h-full bg-[#1A1A1C] relative overflow-hidden animate-in slide-in-from-right-10 fade-in duration-500 shadow-2xl rounded-2xl my-2 mr-2 border border-white/5">
            <div className="flex flex-col h-full relative z-10">
              <div className="px-8 pt-8 pb-10 flex-1 overflow-y-auto custom-scrollbar relative">
                <div className="flex items-center gap-3 mb-6">
                  <div className="w-10 h-10 bg-black/40 rounded-full flex items-center justify-center shadow-inner">
                    {/* eslint-disable-next-line @next/next/no-img-element */}
                    <img src={`https://www.google.com/s2/favicons?sz=64&domain=${getDomain(previewResult.link)}`} alt="" className="w-5 h-5 object-contain opacity-80" onError={(e) => { e.target.style.display = 'none'; }} />
                  </div>
                  <h4 className="text-[12px] font-bold text-[#8a8a8e] tracking-[0.2em] uppercase">{getDomain(previewResult.link)}</h4>
                </div>
                
                <h3 className="text-[28px] font-extrabold text-white mb-6 leading-[1.2] tracking-tight">{previewResult.title}</h3>
                
                <div className="mb-10 relative">
                  <p className="text-[16px] text-[#a1a1aa] font-medium leading-[1.6] antialiased">{previewResult.snippet || 'No additional snippet available for this resource.'}</p>
                </div>
              </div>

              {}
              <div className="p-6 pt-0 mt-auto bg-gradient-to-t from-[#1A1A1C] to-transparent">
                {isFileUrl(previewResult.link) ? (
                  <a href={viewerHref(previewResult.link)} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between w-full px-7 py-4 bg-white text-black rounded-2xl transition-all shadow-lg hover:bg-gray-100 active:scale-[0.98] group">
                    <div className="flex items-center gap-4">
                      <Eye className="w-5 h-5" strokeWidth={2.5}/>
                      <span className="text-[14px] font-black uppercase tracking-wide">Open Document Preview</span>
                    </div>
                    <span className="text-[11px] font-bold bg-black/10 text-black px-3 py-1 rounded-full uppercase tracking-widest">{getFileExt(previewResult.link).slice(1)}</span>
                  </a>
                ) : (
                  <a href={previewResult.link} target="_blank" rel="noopener noreferrer" className="flex items-center justify-between w-full px-7 py-4 bg-[#2C2C2E] hover:bg-[#3C3C3E] text-white rounded-2xl transition-all shadow-xl active:scale-[0.98] group">
                    <div className="flex items-center gap-4">
                      <ExternalLink className="w-5 h-5 text-white/80" strokeWidth={2.5}/>
                      <span className="text-[14px] font-black uppercase tracking-wide">Visit Website</span>
                    </div>
                  </a>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

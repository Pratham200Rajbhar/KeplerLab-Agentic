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
        {/* Left: Results */}
        <div className="flex-1 flex flex-col h-full bg-transparent relative z-10 w-full transition-all duration-500 overflow-hidden">
          <div className="flex justify-between items-center px-6 pb-4 pt-2 shrink-0">
            <p className="text-[13px] font-medium text-text-muted">
              Results found for <span className="text-accent font-bold px-2.5 py-1 rounded-lg bg-accent/10 ml-1">&quot;{query}&quot;</span>
            </p>
            {results.length > 0 && (
              <button className="text-[11px] uppercase tracking-[0.15em] text-text-muted hover:text-accent font-bold transition-all p-1" onClick={handleSelectAll}>
                {selectedResults.size === results.length ? 'Deselect All' : 'Select All'}
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
                    className={`relative p-4 rounded-2xl transition-all duration-300 cursor-pointer group ${
                      isSelected 
                        ? 'bg-surface-raised shadow-lg -translate-y-0.5' 
                        : 'bg-transparent hover:bg-surface-raised/50 hover:-translate-y-0.5'
                    } ${isPreviewed && !isSelected ? 'bg-surface-raised/30' : ''}`}
                  >
                    <div className="flex items-center gap-4">
                      <div className={`shrink-0 w-6 h-6 rounded-full flex items-center justify-center transition-all ${isSelected ? 'bg-text-primary text-surface shadow-md' : 'bg-[#18181A] shadow-inner group-hover:bg-[#252528] cursor-pointer'}`}>
                        {isSelected && <Check className="w-3.5 h-3.5" strokeWidth={4} />}
                      </div>
                      <div className="flex-1 min-w-0 flex flex-col gap-1">
                        <h3 className={`text-[15px] font-bold leading-tight transition-colors line-clamp-1 ${isSelected || isPreviewed ? 'text-text-primary' : 'text-text-primary/80'}`}>{result.title}</h3>
                        <div className="flex items-center gap-2.5">
                          {domain && (
                            // eslint-disable-next-line @next/next/no-img-element -- external favicon URL; domain is dynamic
                            <img src={`https://www.google.com/s2/favicons?sz=64&domain=${domain}`} alt="" className="shrink-0 w-4 h-4 rounded-sm object-contain" onError={(e) => { e.target.style.display = 'none'; }} />
                          )}
                          <div className="flex items-center gap-2 truncate">
                            <span className="text-[11px] font-bold uppercase tracking-widest text-text-secondary truncate max-w-[120px]">{domain}</span>
                            <span className="text-text-muted/30 shrink-0">•</span>
                            <span className="text-[11px] font-medium text-text-muted truncate" title={result.link}>{result.link}</span>
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

        {/* Right: Preview Panel */}
        {previewResult && (
          <div className="w-[500px] shrink-0 h-full bg-[#161618] relative overflow-hidden animate-in slide-in-from-right-10 fade-in duration-500 shadow-2xl rounded-xl my-2 mr-2">
            <div className="absolute inset-x-0 top-0 h-40 bg-gradient-to-b from-white/[0.03] to-transparent pointer-events-none" />
            
            <div className="flex flex-col h-full relative z-10">
              <div className="px-8 pt-8 pb-10 flex-1 overflow-y-auto custom-scrollbar relative">
                <div className="flex items-center gap-4 mb-8">
                  <div className="p-3 bg-black/40 rounded-2xl shadow-inner group hover:bg-black/60 transition-all">
                    {/* eslint-disable-next-line @next/next/no-img-element -- external favicon URL; domain is dynamic */}
                    <img src={`https://www.google.com/s2/favicons?sz=64&domain=${getDomain(previewResult.link)}`} alt="" className="w-8 h-8 rounded-md object-contain" onError={(e) => { e.target.style.display = 'none'; }} />
                  </div>
                  <h4 className="text-[12px] font-bold text-text-muted tracking-[0.3em] uppercase">{getDomain(previewResult.link)}</h4>
                </div>
                
                <h3 className="text-[24px] font-black text-white mb-8 leading-[1.3] tracking-tighter decoration-white/20 decoration-4 underline-offset-8 transition-all">{previewResult.title}</h3>
                
                <div className="mb-10 relative pl-6">
                  <p className="text-[15.5px] text-text-secondary font-medium leading-[1.7] antialiased drop-shadow-sm">{previewResult.snippet || 'No additional snippet available for this resource.'}</p>
                </div>
              </div>

              {/* Action Floating Bar */}
              <div className="p-6 pt-0 mt-auto bg-gradient-to-t from-[#161618] to-transparent">
                {isFileUrl(previewResult.link) ? (
                  <a href={viewerHref(previewResult.link)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-3 w-full px-6 py-4 bg-white text-black text-[15px] font-black rounded-2xl transition-all shadow-[0_8px_30px_rgba(255,255,255,0.15)] hover:scale-[1.02] active:scale-[0.98] group">
                    <Eye className="w-5 h-5 group-hover:scale-110 transition-transform" strokeWidth={2.5}/>
                    <span className="tracking-tight uppercase">Open Document Preview</span>
                    <span className="ml-auto text-[10px] font-black bg-black/10 px-2 py-0.5 rounded-md tracking-tighter shadow-sm">{getFileExt(previewResult.link).slice(1)}</span>
                  </a>
                ) : (
                  <a href={previewResult.link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-3 w-full px-6 py-4 bg-[#2C2C2E] hover:bg-[#3C3C3E] text-white text-[15px] font-black rounded-2xl transition-all shadow-xl group">
                    <div className="p-2 bg-white/10 rounded-xl text-white group-hover:scale-110 transition-transform">
                      <ExternalLink className="w-5 h-5" strokeWidth={2.5}/>
                    </div>
                    <span className="tracking-tight uppercase">Visit Website</span>
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

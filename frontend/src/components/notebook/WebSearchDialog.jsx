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
      maxWidth="max-w-[1000px]"
      icon={<Globe className="w-5 h-5" strokeWidth={1.5} />}
      footer={
        <div className="flex justify-between items-center w-full">
          <span className="text-sm text-text-muted font-medium">{selectedResults.size} resources selected</span>
          <div className="flex gap-3">
            <button className="px-4 py-2 text-sm font-medium text-text-secondary hover:text-text-primary transition-colors" onClick={() => { onClose(); setPreviewResult(null); }}>Cancel</button>
            <button className="px-6 py-2 text-sm font-medium bg-accent hover:bg-accent-light text-white rounded-xl shadow-lg shadow-accent-dark/20 disabled:opacity-50 disabled:cursor-not-allowed transition-all" onClick={handleAdd} disabled={selectedResults.size === 0}>Add to Notebook</button>
          </div>
        </div>
      }
    >
      <div className="flex gap-6 h-[60vh] min-h-[450px]">
        {/* Left: Results */}
        <div className="w-[55%] flex flex-col h-full border-r border-border-strong/50 pr-6">
          <div className="flex justify-between items-center pb-4 border-b border-border-strong/50 shrink-0">
            <p className="text-sm text-text-muted">
              Results for <span className="text-accent-light font-medium font-mono">&quot;{query}&quot;</span>
            </p>
            {results.length > 0 && (
              <button className="text-[13px] text-accent-light hover:text-accent-light font-medium transition-colors" onClick={handleSelectAll}>
                {selectedResults.size === results.length ? 'Deselect All' : 'Select All'}
              </button>
            )}
          </div>

          <div className="flex-1 overflow-y-auto pt-4 pr-1 custom-scrollbar">
            {isSearching ? (
              <div className="flex flex-col items-center justify-center h-full space-y-4">
                <div className="w-8 h-8 border-2 border-accent/30 border-t-accent rounded-full animate-spin" />
                <p className="text-sm text-text-muted animate-pulse font-medium">Scanning the web...</p>
              </div>
            ) : error ? (
              <div className="flex flex-col items-center justify-center h-full space-y-4 text-center px-4">
                <div className="p-3 bg-danger-subtle rounded-full">
                  <AlertTriangle className="w-8 h-8 text-danger" strokeWidth={1.5} />
                </div>
                <p className="text-[15px] font-semibold text-danger">Search Interrupted</p>
                <p className="text-sm text-text-muted leading-relaxed">{error}</p>
              </div>
            ) : results.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full space-y-2 text-center">
                <Search className="w-12 h-12 text-text-muted mb-2" strokeWidth={1} />
                <p className="text-[15px] font-medium text-text-muted">No matching resources found</p>
                <p className="text-sm text-text-muted">Try broadening your search.</p>
              </div>
            ) : (
              <div className="space-y-2.5 pb-2">
                {results.map((result, idx) => {
                  const domain = getDomain(result.link);
                  const isSelected = Array.from(selectedResults).some((r) => r.link === result.link);
                  const isPreviewed = previewResult?.link === result.link;
                  return (
                    <div
                      key={result.link}
                      onMouseEnter={() => setPreviewResult(result)}
                      onClick={() => { toggleSelection(result); setPreviewResult(result); }}
                      className={`p-3 rounded-xl border transition-all cursor-pointer group ${
                        isSelected ? 'bg-accent-subtle border-accent/40' : 'bg-surface-overlay/40 border-border-strong/50 hover:bg-surface-overlay hover:border-border-strong'
                      } ${isPreviewed && !isSelected ? 'ring-1 ring-blue-500/20' : ''}`}
                    >
                      <div className="flex items-center gap-3.5">
                        <div className={`shrink-0 w-5 h-5 rounded-md border flex items-center justify-center transition-all ${isSelected ? 'bg-accent border-accent text-white' : 'border-border-strong bg-surface-100 group-hover:border-border-strong'}`}>
                          {isSelected && <Check className="w-3.5 h-3.5" strokeWidth={3.5} />}
                        </div>
                        {domain && (
                          // eslint-disable-next-line @next/next/no-img-element -- external favicon URL; domain is dynamic
                          <img src={`https://www.google.com/s2/favicons?sz=64&domain=${domain}`} alt="" className="shrink-0 w-6 h-6 rounded bg-surface-overlay object-contain" onError={(e) => { e.target.style.display = 'none'; }} />
                        )}
                        <div className="flex-1 min-w-0 flex flex-col justify-center gap-1">
                          <h3 className={`text-[14px] font-semibold transition-colors truncate ${isSelected ? 'text-accent-light' : 'text-text-primary group-hover:text-accent-light'}`}>{result.title}</h3>
                          <div className="flex items-center gap-2 text-[12px]">
                            <span className="font-medium text-accent-light/80 truncate max-w-[130px] shrink-0">{domain}</span>
                            <span className="text-text-muted shrink-0">•</span>
                            <span className="text-text-muted truncate min-w-0" title={result.link}>{result.link}</span>
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>

        {/* Right: Preview */}
        <div className="w-[45%] flex flex-col h-full pl-0">
          {previewResult ? (
            <div className="flex flex-col h-full min-h-0 bg-linear-to-br from-surface-overlay/80 to-surface-100/80 rounded-2xl border border-border-strong/50 overflow-hidden relative shadow-inner">
              <div className="absolute top-0 right-0 w-48 h-48 bg-accent-subtle rounded-full blur-3xl pointer-events-none transform translate-x-10 -translate-y-10" />
              <div className="p-6 flex-1 overflow-y-auto custom-scrollbar relative z-10 flex flex-col">
                <div className="flex items-center gap-3 mb-5">
                  {/* eslint-disable-next-line @next/next/no-img-element -- external favicon URL; domain is dynamic */}
                  <img src={`https://www.google.com/s2/favicons?sz=64&domain=${getDomain(previewResult.link)}`} alt="" className="w-10 h-10 rounded-lg bg-surface-overlay object-contain p-1 border border-border-strong/50" onError={(e) => { e.target.style.display = 'none'; }} />
                  <h4 className="text-[13px] font-medium text-accent-light/80 tracking-wide uppercase">{getDomain(previewResult.link)}</h4>
                </div>
                <h3 className="text-[19px] font-bold text-text-primary mb-4 leading-snug">{previewResult.title}</h3>
                <div className="mb-6 pb-6 border-b border-border-strong/50">
                  <p className="text-[14.5px] text-text-secondary leading-[1.7] antialiased">{previewResult.snippet || 'No additional snippet available.'}</p>
                </div>
                <div className="mt-auto pt-2">
                  {isFileUrl(previewResult.link) ? (
                    <a href={viewerHref(previewResult.link)} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 w-full px-4 py-3 bg-surface-overlay hover:bg-accent-subtle hover:border-accent/50 hover:text-accent-light text-text-secondary text-[14px] font-semibold rounded-xl transition-all border border-border-strong/80 group">
                      <Eye className="w-4 h-4" /> <span>View File</span>
                      <span className="text-xs font-normal text-text-muted uppercase tracking-wide">{getFileExt(previewResult.link).slice(1)}</span>
                    </a>
                  ) : (
                    <a href={previewResult.link} target="_blank" rel="noopener noreferrer" className="inline-flex items-center justify-center gap-2 w-full px-4 py-3 bg-surface-overlay hover:bg-accent-subtle hover:border-accent/50 hover:text-accent-light text-text-secondary text-[14px] font-semibold rounded-xl transition-all border border-border-strong/80 group">
                      <span>Visit Website</span> <ExternalLink className="w-4 h-4 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" strokeWidth={2.5} />
                    </a>
                  )}
                </div>
              </div>
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center p-8 bg-surface-overlay/10 rounded-2xl border border-dashed border-border-strong/50">
              <div className="w-16 h-16 bg-surface-overlay/40 rounded-full flex items-center justify-center mb-4">
                <Eye className="w-8 h-8 text-text-muted" strokeWidth={1.5} />
              </div>
              <p className="text-text-secondary font-semibold text-[15px]">Select a resource</p>
              <p className="text-[13.5px] text-text-muted mt-2 max-w-[220px] leading-relaxed">Hover or click any result to see details.</p>
            </div>
          )}
        </div>
      </div>
    </Modal>
  );
}

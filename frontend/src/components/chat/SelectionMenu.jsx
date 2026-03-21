'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { HelpCircle, RefreshCw, Languages, BookOpen, X, Search } from 'lucide-react';
import MiniBlockChat from './MiniBlockChat';

const LANG_OPTIONS = [
  'Hindi', 'Bengali', 'Marathi', 'Telugu', 'Tamil', 'Gujarati', 'Urdu', 'Kannada', 'Odia', 'Malayalam', 'Punjabi',
  'Spanish', 'French', 'German', 'Chinese', 'Arabic', 'Portuguese', 'Japanese'
];

export default function SelectionMenu() {
  const [selection, setSelection] = useState(null);
  const [menuPos, setMenuPos] = useState({ top: 0, left: 0 });
  const [blockId, setBlockId] = useState(null);
  const [miniChat, setMiniChat] = useState(null);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const [langSearch, setLangSearch] = useState('');
  
  const menuRef = useRef(null);

  const handleSelection = useCallback(() => {
    const sel = window.getSelection();
    if (!sel || sel.isCollapsed || !sel.toString().trim()) {
      return;
    }

    const range = sel.getRangeAt(0);
    const container = range.commonAncestorContainer;
    const element = container.nodeType === 3 ? container.parentElement : container;

    const selectionContainer = element.closest('.message-selection-container');
    if (!selectionContainer) {
      return;
    }

    const blockElement = element.closest('[data-block-id]');
    let id = blockElement?.getAttribute('data-block-id');
    
    // Fallback search for block ID if direct hit failed (e.g. selection spans multiple)
    if (!id) {
        const cloned = range.cloneContents();
        id = cloned.querySelector('[data-block-id]')?.getAttribute('data-block-id') || 
             cloned.firstElementChild?.closest('[data-block-id]')?.getAttribute('data-block-id');
    }

    if (!id) return; // CRITICAL: Only show if we have a block to act on

    const rect = range.getBoundingClientRect();
    
    setMenuPos({
      top: rect.top + window.scrollY - 60,
      left: rect.left + window.scrollX + rect.width / 2
    });
    setBlockId(id);
    setSelection(sel.toString());
    setShowLangPicker(false);
  }, []);

  useEffect(() => {
    const onMouseUp = (e) => {
      if (menuRef.current?.contains(e.target)) return;
      setTimeout(handleSelection, 10);
    };

    const onMouseDown = (e) => {
        if (menuRef.current?.contains(e.target)) return;
        if (miniChat) return;
        setSelection(null);
        setShowLangPicker(false);
    };

    document.addEventListener('mouseup', onMouseUp);
    document.addEventListener('mousedown', onMouseDown);
    return () => {
      document.removeEventListener('mouseup', onMouseUp);
      document.removeEventListener('mousedown', onMouseDown);
    };
  }, [handleSelection, miniChat]);

  const openAction = (action, lang = '') => {
    setMiniChat({ action, lang, selection });
    setShowLangPicker(false);
    setLangSearch('');
  };

  if (!selection && !miniChat) return null;

  return (
    <>
      {selection && !miniChat && (
        <div 
          ref={menuRef}
          className="fixed z-[1000] bg-[#0c0c0e]/90 backdrop-blur-xl border border-white/5 rounded-2xl shadow-[0_20px_50px_rgba(0,0,0,0.5)] p-1.5 flex items-center gap-1 animate-scale-in transition-all duration-200"
          style={{ 
            top: menuPos.top, 
            left: menuPos.left,
            transform: 'translateX(-50%)'
          }}
        >
          <button 
            className="flex flex-col items-center justify-center w-11 h-11 hover:bg-white/5 rounded-xl transition-all group"
            onClick={() => openAction('ask')}
          >
            <HelpCircle className="w-4 h-4 text-text-secondary group-hover:text-accent transition-colors" />
            <span className="text-[9px] font-medium text-text-muted mt-0.5 uppercase tracking-tighter">Ask</span>
          </button>
          
          <button 
            className="flex flex-col items-center justify-center w-11 h-11 hover:bg-white/5 rounded-xl transition-all group"
            onClick={() => openAction('simplify')}
          >
            <RefreshCw className="w-4 h-4 text-text-secondary group-hover:text-accent transition-colors" />
            <span className="text-[9px] font-medium text-text-muted mt-0.5 uppercase tracking-tighter">Simp</span>
          </button>

          <div className="relative">
            <button 
              className={`flex flex-col items-center justify-center w-11 h-11 hover:bg-white/5 rounded-xl transition-all group ${showLangPicker ? 'bg-white/10' : ''}`}
              onClick={() => setShowLangPicker(!showLangPicker)}
            >
              <Languages className={`w-4 h-4 transition-colors ${showLangPicker ? 'text-accent' : 'text-text-secondary group-hover:text-accent'}`} />
              <span className="text-[9px] font-medium text-text-muted mt-0.5 uppercase tracking-tighter">Trans</span>
            </button>
            
            {showLangPicker && (
              <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-4 w-52 bg-[#0c0c0e] border border-white/5 rounded-2xl shadow-[0_30px_70px_rgba(0,0,0,0.7)] overflow-hidden z-[1001] animate-fade-in">
                <div className="p-3 bg-white/[0.02] border-b border-white/[0.05]">
                  <div className="relative">
                    <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-text-muted" />
                    <input 
                      type="text" 
                      placeholder="Search language..." 
                      value={langSearch}
                      onChange={e => setLangSearch(e.target.value)}
                      autoFocus
                      className="w-full bg-white/[0.03] text-xs pl-8 pr-3 py-2 rounded-lg text-text-primary placeholder:text-text-muted focus:outline-none focus:ring-1 focus:ring-accent/30 transition-all font-medium"
                    />
                  </div>
                </div>
                <div className="max-h-56 overflow-y-auto p-1.5 custom-scrollbar">
                  {LANG_OPTIONS.filter(l => l.toLowerCase().includes(langSearch.toLowerCase())).map(lang => (
                    <button 
                      key={lang} 
                      className="w-full text-left px-3 py-2.5 text-xs text-text-secondary hover:bg-accent/10 hover:text-accent rounded-lg transition-all font-medium mb-0.5 last:mb-0"
                      onClick={() => openAction('translate', lang)}
                    >
                      {lang}
                    </button>
                  ))}
                  {LANG_OPTIONS.filter(l => l.toLowerCase().includes(langSearch.toLowerCase())).length === 0 && (
                    <div className="py-6 text-center text-xs text-text-muted italic">No languages found</div>
                  ) }
                </div>
              </div>
            )}
          </div>

          <button 
            className="flex flex-col items-center justify-center w-11 h-11 hover:bg-white/5 rounded-xl transition-all group"
            onClick={() => openAction('explain')}
          >
            <BookOpen className="w-4 h-4 text-text-secondary group-hover:text-accent transition-colors" />
            <span className="text-[9px] font-medium text-text-muted mt-0.5 uppercase tracking-tighter">Expl</span>
          </button>
          
          <div className="w-px h-6 bg-white/5 mx-1" />
          
          <button 
            className="w-9 h-11 flex items-center justify-center hover:bg-danger/10 text-text-muted hover:text-danger rounded-xl transition-all"
            onClick={() => {
                setSelection(null);
                window.getSelection().removeAllRanges();
            }}
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {miniChat && (
        <div className="fixed inset-0 z-[2000] flex items-center justify-center p-4 bg-black/40 backdrop-blur-md animate-fade-in" onClick={(e) => {
            if (e.target === e.currentTarget) {
                setMiniChat(null);
                setSelection(null);
            }
        }}>
          <div className="w-full max-w-lg shadow-2xl animate-scale-in">
             <MiniBlockChat 
              blockId={blockId} 
              action={miniChat.action} 
              lang={miniChat.lang} 
              selection={miniChat.selection}
              onClose={() => {
                setMiniChat(null);
                setSelection(null);
              }} 
            />
          </div>
        </div>
      )}
    </>
  );
}

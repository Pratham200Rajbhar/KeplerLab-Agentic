'use client';

import { useState, useRef, useEffect } from 'react';
import { HelpCircle, RefreshCw, Languages, BookOpen } from 'lucide-react';
import MiniBlockChat from './MiniBlockChat';

const LANG_OPTIONS = [
  'Hindi', 'Bengali', 'Marathi', 'Telugu', 'Tamil', 'Gujarati', 'Urdu', 'Kannada', 'Odia', 'Malayalam', 'Punjabi',
  'Spanish', 'French', 'German', 'Chinese', 'Arabic', 'Portuguese', 'Japanese'
];

export default function BlockHoverMenu({ blockId, children }) {
  const [hovered, setHovered] = useState(false);
  const [miniChat, setMiniChat] = useState(null);
  const [showLangPicker, setShowLangPicker] = useState(false);
  const [langSearch, setLangSearch] = useState('');
  const ref = useRef(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) {
        setShowLangPicker(false);
        setHovered(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const openAction = (action, lang = '') => {
    setMiniChat({ action, lang });
    setShowLangPicker(false);
    setLangSearch('');
  };

  return (
    <div ref={ref} className="block-hover-wrapper"
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => { if (!showLangPicker) setHovered(false); }}>
      <div className="block-hover-content">
        {children}
        {(hovered || showLangPicker) && !miniChat && blockId && (
          <div className="block-hover-actions">
            <button className="block-action-btn" title="Ask a question" onClick={() => openAction('ask')}>
              <HelpCircle className="w-3.5 h-3.5" /><span>Ask</span>
            </button>
            <button className="block-action-btn" title="Simplify" onClick={() => openAction('simplify')}>
              <RefreshCw className="w-3.5 h-3.5" /><span>Simplify</span>
            </button>
            <div className="block-hover-lang-wrapper">
              <button className="block-action-btn" title="Translate" onClick={() => setShowLangPicker(v => !v)}>
                <Languages className="w-3.5 h-3.5" /><span>Translate</span>
              </button>
              {showLangPicker && (
                <div className="lang-picker flex flex-col max-h-[250px] w-40">
                  <div className="px-2 pb-1 border-b border-[var(--border)]">
                    <input type="text" placeholder="Search language..." value={langSearch}
                      onChange={e => setLangSearch(e.target.value)} autoFocus onClick={e => e.stopPropagation()}
                      className="w-full bg-[var(--surface-overlay)] text-[var(--text-primary)] text-xs px-2 py-1.5 rounded focus:outline-none focus:ring-1 focus:ring-[var(--accent)]" />
                  </div>
                  <div className="overflow-y-auto overflow-x-hidden flex-1 py-1 custom-scrollbar">
                    {LANG_OPTIONS.filter(l => l.toLowerCase().includes(langSearch.toLowerCase())).length > 0 ? (
                      LANG_OPTIONS.filter(l => l.toLowerCase().includes(langSearch.toLowerCase())).map(lang => (
                        <button key={lang} className="lang-picker-item" onClick={() => openAction('translate', lang)}>{lang}</button>
                      ))
                    ) : (
                      <div className="px-3 py-2 text-xs text-[var(--text-muted)] text-center">No results</div>
                    )}
                  </div>
                </div>
              )}
            </div>
            <button className="block-action-btn" title="Explain in depth" onClick={() => openAction('explain')}>
              <BookOpen className="w-3.5 h-3.5" /><span>Explain</span>
            </button>
          </div>
        )}
      </div>
      {miniChat && blockId && <MiniBlockChat blockId={blockId} action={miniChat.action} lang={miniChat.lang} onClose={() => setMiniChat(null)} />}
    </div>
  );
}

'use client';

import { useState } from 'react';
import { X, Sparkles } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import { suggestPresentationCount } from '@/lib/api/presentation';

export default function PresentationDialog({ onClose, onGenerate, loading, materialIds = [] }) {
  const [instruction, setInstruction] = useState('');
  const [theme, setTheme] = useState('modern');
  const [customTheme, setCustomTheme] = useState('');
  const [maxSlides, setMaxSlides] = useState(12);
  const [aiSuggest, setAiSuggest] = useState(false);
  const [suggesting, setSuggesting] = useState(false);
  const [reasoning, setReasoning] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const finalInstruction = [
      instruction.trim(),
      theme === 'custom' && customTheme.trim() ? `Style Requirement: ${customTheme.trim()}` : ''
    ].filter(Boolean).join('\n\n');

    onGenerate({
      instruction: finalInstruction || undefined,
      theme,
      maxSlides,
    });
  };

  const handleAiSuggest = async (enabled) => {
    setAiSuggest(enabled);
    if (!enabled) {
      setReasoning('');
      return;
    }
    if (!materialIds?.length) return;
    setSuggesting(true);
    try {
      const data = await suggestPresentationCount(materialIds);
      if (data?.suggested_count) {
        setMaxSlides(data.suggested_count);
      }
      setReasoning(data?.reasoning || '');
    } finally {
      setSuggesting(false);
    }
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit} className="studio-dialog-v3">
        <div className="studio-dialog-v3-header">
          <div className="studio-dialog-v3-icon">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>slideshow</span>
          </div>
          <div>
            <h3 className="studio-dialog-v3-title">Presentation Builder</h3>
            <p className="studio-dialog-v3-subtitle">Select style and slide count for a polished deck</p>
          </div>
          <button type="button" onClick={onClose} className="studio-dialog-v3-close" aria-label="Close presentation dialog">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="studio-dialog-v3-body">
          <div className="studio-dialog-v3-grid">
            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Theme</label>
              </div>
              <div className="grid grid-cols-2 gap-2">
              {['modern', 'academic', 'creative', 'custom'].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setTheme(item)}
                    className={`studio-dialog-v3-segment ${theme === item ? 'active' : ''}`}
                >
                  {item}
                </button>
              ))}
            </div>
            {theme === 'custom' && (
              <div className="mt-3 animate-fade-in">
                <input
                  type="text"
                  value={customTheme}
                  onChange={(e) => setCustomTheme(e.target.value)}
                  placeholder="e.g. Cyberpunk with neon greens and deep purples"
                    className="studio-dialog-v3-input"
                />
              </div>
            )}
          </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Number of Slides</label>
                <label className="studio-dialog-v3-toggle cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiSuggest}
                  onChange={(e) => handleAiSuggest(e.target.checked)}
                />
                  <span>AI Suggest</span>
              </label>
            </div>

              <div className="studio-dialog-v3-range-row">
              <input
                type="range"
                min={1}
                max={60}
                value={maxSlides}
                onChange={(e) => setMaxSlides(Number(e.target.value))}
                  className="studio-dialog-v3-range"
                disabled={aiSuggest && suggesting}
              />
              <input
                type="number"
                min={1}
                value={maxSlides}
                onChange={(e) => setMaxSlides(Math.max(1, Number(e.target.value || 1)))}
                  className="studio-dialog-v3-number w-20"
                disabled={aiSuggest && suggesting}
              />
            </div>

            {aiSuggest && (
                <div className="studio-dialog-v3-note">
                  {suggesting ? 'Analyzing selected materials...' : reasoning}
                </div>
            )}
          </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Generation Instruction (optional)</label>
              </div>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              placeholder="Focus on key metrics and include one summary table."
                className="studio-dialog-v3-textarea"
            />
          </div>

            <div className="studio-dialog-v3-note flex items-center gap-2">
              <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>Balanced decks usually perform best between 8 and 16 slides.</span>
            </div>
          </div>
        </div>

        <div className="studio-dialog-v3-footer">
          <button type="button" onClick={onClose} className="studio-dialog-v3-btn ghost">
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="studio-dialog-v3-btn primary"
          >
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

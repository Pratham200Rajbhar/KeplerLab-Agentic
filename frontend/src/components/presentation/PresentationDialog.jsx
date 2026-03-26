'use client';

import { useState } from 'react';
import { X } from 'lucide-react';
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
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h3 className="text-base font-semibold text-[var(--text-primary)]">Generate Presentation</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)]">
            <X className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Theme</label>
            <div className="grid grid-cols-2 gap-2">
              {['modern', 'academic', 'creative', 'custom'].map((item) => (
                <button
                  key={item}
                  type="button"
                  onClick={() => setTheme(item)}
                  className={`px-3 py-2 rounded-lg border text-xs capitalize transition-colors ${
                    theme === item
                      ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)] font-medium'
                      : 'border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)]'
                  }`}
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
                  className="w-full px-3 py-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-sm focus:outline-none focus:border-[var(--accent)]"
                />
              </div>
            )}
          </div>

          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Number of Slides</label>
              <label className="flex items-center gap-2 text-[11px] text-[var(--text-muted)]">
                <input
                  type="checkbox"
                  checked={aiSuggest}
                  onChange={(e) => handleAiSuggest(e.target.checked)}
                />
                AI Suggest
              </label>
            </div>

            <div className="flex items-center gap-3">
              <input
                type="range"
                min={1}
                max={60}
                value={maxSlides}
                onChange={(e) => setMaxSlides(Number(e.target.value))}
                className="flex-1"
                disabled={aiSuggest && suggesting}
              />
              <input
                type="number"
                min={1}
                value={maxSlides}
                onChange={(e) => setMaxSlides(Math.max(1, Number(e.target.value || 1)))}
                className="w-20 px-2 py-1 rounded border border-[var(--border)] bg-[var(--surface)] text-sm text-[var(--text-primary)]"
                disabled={aiSuggest && suggesting}
              />
            </div>

            {aiSuggest && (
              <p className="mt-1 text-[11px] text-[var(--text-muted)]">
                {suggesting ? 'Analyzing selected materials...' : reasoning}
              </p>
            )}
          </div>



          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Generation Instruction (optional)</label>
            <textarea
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              rows={4}
              placeholder="Focus on key metrics and include one summary table."
              className="w-full px-3 py-2 rounded-lg bg-[var(--surface)] border border-[var(--border)] text-sm resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[var(--border)]">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[var(--text-secondary)]">
            Cancel
          </button>
          <button
            type="submit"
            disabled={loading}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--accent)] text-white disabled:opacity-60"
          >
            {loading ? 'Generating...' : 'Generate'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

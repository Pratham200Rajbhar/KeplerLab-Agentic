'use client';

import { useState } from 'react';
import Modal from '@/components/ui/Modal';
import { X } from 'lucide-react';

/* ─────────────────── Flashcard Config Dialog ─────────────────── */
export function FlashcardConfigDialog({ onGenerate, onCancel }) {
  const onConfirm = onGenerate;
  const onClose = onCancel;
  const [topic, setTopic] = useState('');
  const [cardCount, setCardCount] = useState(10);
  const [aiSuggest, setAiSuggest] = useState(false);
  const [difficulty, setDifficulty] = useState('medium');
  const [instructions, setInstructions] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({ topic, cardCount: aiSuggest ? null : cardCount, difficulty, additionalInstructions: instructions });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <h3 className="text-base font-semibold text-[var(--text-primary)]">Flashcard Settings</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors" aria-label="Close flashcard settings">
            <X className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Topic */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
              Focus Topic <span className="text-[var(--text-muted)]">(optional)</span>
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Chapter 3 key concepts"
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface-overlay)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            />
          </div>

          {/* Card Count */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Number of Cards</label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiSuggest}
                  onChange={(e) => setAiSuggest(e.target.checked)}
                  className="w-3 h-3 accent-emerald-500"
                />
                <span className="text-[11px] text-[var(--accent)]">AI Suggest</span>
              </label>
            </div>
            {aiSuggest ? (
              <p className="text-[11px] text-[var(--text-muted)] italic">AI will choose the optimal card count based on content length.</p>
            ) : (
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={5}
                  max={150}
                  value={cardCount}
                  onChange={(e) => setCardCount(Number(e.target.value))}
                  className="flex-1 accent-emerald-500"
                />
                <input
                  type="number"
                  min={5}
                  max={150}
                  value={cardCount}
                  onChange={(e) => setCardCount(Math.min(150, Math.max(5, Number(e.target.value))))}
                  className="w-14 px-2 py-1 text-xs rounded-lg bg-[var(--surface-overlay)] text-[var(--text-primary)] border border-[var(--border)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] text-center"
                />
              </div>
            )}
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Difficulty</label>
            <div className="flex gap-2">
              {['easy', 'medium', 'hard'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${difficulty === d
                    ? 'bg-[var(--accent)] text-white'
                    : 'bg-[var(--surface-overlay)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Additional Instructions */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
              Additional Instructions <span className="text-[var(--text-muted)]">(optional)</span>
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Any specific requirements..."
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface-overlay)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            Cancel
          </button>
          <button type="submit" className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors">
            Generate Flashcards
          </button>
        </div>
      </form>
    </Modal>
  );
}

/* ─────────────────── Quiz Config Dialog ─────────────────── */
export function QuizConfigDialog({ onGenerate, onCancel }) {
  const onConfirm = onGenerate;
  const onClose = onCancel;
  const [topic, setTopic] = useState('');
  const [mcqCount, setMcqCount] = useState(10);
  const [aiSuggest, setAiSuggest] = useState(false);
  const [difficulty, setDifficulty] = useState('medium');
  const [instructions, setInstructions] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({ topic, mcqCount: aiSuggest ? null : mcqCount, difficulty, additionalInstructions: instructions });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <h3 className="text-base font-semibold text-[var(--text-primary)]">Quiz Settings</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors" aria-label="Close quiz settings">
            <X className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Topic */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
              Focus Topic <span className="text-[var(--text-muted)]">(optional)</span>
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Machine Learning Basics"
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface-overlay)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
            />
          </div>

          {/* Question Count */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-medium text-[var(--text-secondary)]">Number of Questions</label>
              <label className="flex items-center gap-1.5 cursor-pointer">
                <input
                  type="checkbox"
                  checked={aiSuggest}
                  onChange={(e) => setAiSuggest(e.target.checked)}
                  className="w-3 h-3 accent-emerald-500"
                />
                <span className="text-[11px] text-[var(--accent)]">AI Suggest</span>
              </label>
            </div>
            {aiSuggest ? (
              <p className="text-[11px] text-[var(--text-muted)] italic">AI will choose the optimal question count based on content length.</p>
            ) : (
              <div className="flex items-center gap-3">
                <input
                  type="range"
                  min={5}
                  max={150}
                  value={mcqCount}
                  onChange={(e) => setMcqCount(Number(e.target.value))}
                  className="flex-1 accent-emerald-500"
                />
                <input
                  type="number"
                  min={5}
                  max={150}
                  value={mcqCount}
                  onChange={(e) => setMcqCount(Math.min(150, Math.max(5, Number(e.target.value))))}
                  className="w-14 px-2 py-1 text-xs rounded-lg bg-[var(--surface-overlay)] text-[var(--text-primary)] border border-[var(--border)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] text-center"
                />
              </div>
            )}
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Difficulty</label>
            <div className="flex gap-2">
              {['easy', 'medium', 'hard'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${difficulty === d
                    ? 'bg-[var(--accent)] text-white'
                    : 'bg-[var(--surface-overlay)] text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Additional Instructions */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
              Additional Instructions <span className="text-[var(--text-muted)]">(optional)</span>
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Any specific requirements..."
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface-overlay)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            Cancel
          </button>
          <button type="submit" className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors">
            Generate Quiz
          </button>
        </div>
      </form>
    </Modal>
  );
}

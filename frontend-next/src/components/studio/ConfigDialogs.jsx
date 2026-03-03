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
  const [difficulty, setDifficulty] = useState('medium');
  const [instructions, setInstructions] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({ topic, cardCount, difficulty, additionalInstructions: instructions });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <h3 className="text-base font-semibold text-(--text-primary)">Flashcard Settings</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-(--surface-overlay) transition-colors">
            <X className="w-4 h-4 text-(--text-muted)" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Topic */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">
              Focus Topic <span className="text-(--text-muted)">(optional)</span>
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Chapter 3 key concepts"
              className="w-full px-3 py-2 text-sm rounded-lg bg-(--surface-overlay) text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus:ring-1 focus:ring-(--accent)"
            />
          </div>

          {/* Card Count */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">
              Number of Cards
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={30}
                value={cardCount}
                onChange={(e) => setCardCount(Number(e.target.value))}
                className="flex-1 accent-(--accent)"
              />
              <span className="text-sm font-medium text-(--text-primary) w-8 text-center">{cardCount}</span>
            </div>
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">Difficulty</label>
            <div className="flex gap-2">
              {['easy', 'medium', 'hard'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${difficulty === d
                    ? 'bg-(--accent) text-white'
                    : 'bg-(--surface-overlay) text-(--text-secondary) hover:text-(--text-primary)'
                    }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Additional Instructions */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">
              Additional Instructions <span className="text-(--text-muted)">(optional)</span>
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Any specific requirements..."
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg bg-(--surface-overlay) text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus:ring-1 focus:ring-(--accent) resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-(--text-secondary) hover:text-(--text-primary) transition-colors">
            Cancel
          </button>
          <button type="submit" className="px-4 py-2 text-sm font-medium rounded-lg bg-(--accent) text-white hover:bg-(--accent-light) transition-colors">
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
  const [difficulty, setDifficulty] = useState('medium');
  const [instructions, setInstructions] = useState('');


  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({ topic, mcqCount, difficulty, additionalInstructions: instructions });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
          <h3 className="text-base font-semibold text-(--text-primary)">Quiz Settings</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-(--surface-overlay) transition-colors">
            <X className="w-4 h-4 text-(--text-muted)" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Topic */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">
              Focus Topic <span className="text-(--text-muted)">(optional)</span>
            </label>
            <input
              type="text"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              placeholder="e.g. Machine Learning Basics"
              className="w-full px-3 py-2 text-sm rounded-lg bg-(--surface-overlay) text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus:ring-1 focus:ring-(--accent)"
            />
          </div>

          {/* Question Count */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">
              Number of Questions
            </label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={25}
                value={mcqCount}
                onChange={(e) => setMcqCount(Number(e.target.value))}
                className="flex-1 accent-(--accent)"
              />
              <span className="text-sm font-medium text-(--text-primary) w-8 text-center">{mcqCount}</span>
            </div>
          </div>

          {/* Difficulty */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">Difficulty</label>
            <div className="flex gap-2">
              {['easy', 'medium', 'hard'].map((d) => (
                <button
                  key={d}
                  type="button"
                  onClick={() => setDifficulty(d)}
                  className={`flex-1 py-1.5 rounded-lg text-xs font-medium capitalize transition-all ${difficulty === d
                    ? 'bg-(--accent) text-white'
                    : 'bg-(--surface-overlay) text-(--text-secondary) hover:text-(--text-primary)'
                    }`}
                >
                  {d}
                </button>
              ))}
            </div>
          </div>

          {/* Additional Instructions */}
          <div>
            <label className="text-xs font-medium text-(--text-secondary) mb-1.5 block">
              Additional Instructions <span className="text-(--text-muted)">(optional)</span>
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Any specific requirements..."
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg bg-(--surface-overlay) text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus:ring-1 focus:ring-(--accent) resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-(--text-secondary) hover:text-(--text-primary) transition-colors">
            Cancel
          </button>
          <button type="submit" className="px-4 py-2 text-sm font-medium rounded-lg bg-(--accent) text-white hover:bg-(--accent-light) transition-colors">
            Generate Quiz
          </button>
        </div>
      </form>
    </Modal>
  );
}

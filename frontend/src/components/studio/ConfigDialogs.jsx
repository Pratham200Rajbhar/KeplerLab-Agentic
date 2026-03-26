'use client';

import { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { X, Loader2, Info, Sparkles, HelpCircle } from 'lucide-react';
import { suggestFlashcardCount, suggestQuizCount } from '@/lib/api/generation';

export function FlashcardConfigDialog({ onGenerate, onCancel, materialIds }) {
  const onConfirm = onGenerate;
  const onClose = onCancel;
  const [topic, setTopic] = useState('');
  const [cardCount, setCardCount] = useState(10);
  const [aiSuggest, setAiSuggest] = useState(false);
  const [difficulty, setDifficulty] = useState('medium');
  const [instructions, setInstructions] = useState('');
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestionReasoning, setSuggestionReasoning] = useState('');

  useEffect(() => {
    let mounted = true;
    if (aiSuggest && materialIds && materialIds.length > 0) {
      const fetchSuggestion = async () => {
        setIsSuggesting(true);
        try {
          const res = await suggestFlashcardCount(materialIds);
          if (mounted && res) {
            setCardCount(res.suggested_count);
            setSuggestionReasoning(res.reasoning);
          }
        } catch (error) {
          console.error('Failed to get flashcard suggestion:', error);
        } finally {
          if (mounted) setIsSuggesting(false);
        }
      };
      fetchSuggestion();
    } else {
      setSuggestionReasoning('');
    }
    return () => {
      mounted = false;
    };
  }, [aiSuggest, materialIds]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({
      topic,
      cardCount: aiSuggest ? null : cardCount,
      difficulty,
      additionalInstructions: instructions,
    });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit} className="studio-dialog-v3">
        <div className="studio-dialog-v3-header">
          <div className="studio-dialog-v3-icon">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              style
            </span>
          </div>
          <div>
            <h3 className="studio-dialog-v3-title">Flashcard Builder</h3>
            <p className="studio-dialog-v3-subtitle">Shape card count, topic focus, and study depth</p>
          </div>
          <button type="button" onClick={onClose} className="studio-dialog-v3-close" aria-label="Close flashcard settings">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="studio-dialog-v3-body">
          <div className="studio-dialog-v3-grid">
            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">
                  Focus Topic <span className="studio-dialog-v3-label-muted">(optional)</span>
                </label>
              </div>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Chapter 3 key concepts"
                className="studio-dialog-v3-input"
              />
            </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Number of Cards</label>
                <label className="studio-dialog-v3-toggle cursor-pointer">
                  <input
                    type="checkbox"
                    checked={aiSuggest}
                    onChange={(e) => setAiSuggest(e.target.checked)}
                  />
                  <span>AI Suggest</span>
                </label>
              </div>

              {aiSuggest ? (
                <div>
                  <div className="studio-dialog-v3-note">
                    {isSuggesting ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>AI is analyzing your selected materials...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1.5 text-[var(--accent)] font-semibold">
                          <Sparkles className="w-3.5 h-3.5" />
                          {cardCount} cards suggested
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">Adaptive estimate</span>
                      </div>
                    )}
                  </div>
                  {suggestionReasoning && !isSuggesting && (
                    <div className="studio-dialog-v3-note mt-2 flex gap-2">
                      <Info className="w-3.5 h-3.5 text-[var(--accent)] shrink-0 mt-0.5" />
                      <span>{suggestionReasoning}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="studio-dialog-v3-range-row">
                  <input
                    type="range"
                    min={5}
                    max={150}
                    value={cardCount}
                    onChange={(e) => setCardCount(Number(e.target.value))}
                    className="studio-dialog-v3-range"
                  />
                  <input
                    type="number"
                    min={5}
                    max={150}
                    value={cardCount}
                    onChange={(e) => setCardCount(Math.min(150, Math.max(5, Number(e.target.value))))}
                    className="studio-dialog-v3-number w-20"
                  />
                </div>
              )}
            </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Difficulty</label>
              </div>
              <div className="studio-dialog-v3-segments">
                {['easy', 'medium', 'hard'].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDifficulty(d)}
                    className={`studio-dialog-v3-segment ${difficulty === d ? 'active' : ''}`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">
                  Additional Instructions <span className="studio-dialog-v3-label-muted">(optional)</span>
                </label>
              </div>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Any specific requirements..."
                className="studio-dialog-v3-textarea"
              />
            </div>

            <div className="studio-dialog-v3-note flex items-center gap-2">
              <HelpCircle className="w-3.5 h-3.5 text-[var(--accent)]" />
              <span>Tip: Keep cards between 8 and 30 for faster review sessions.</span>
            </div>
          </div>
        </div>

        <div className="studio-dialog-v3-footer">
          <button type="button" onClick={onClose} className="studio-dialog-v3-btn ghost">
            Cancel
          </button>
          <button type="submit" className="studio-dialog-v3-btn primary">
            Generate Flashcards
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function QuizConfigDialog({ onGenerate, onCancel, materialIds }) {
  const onConfirm = onGenerate;
  const onClose = onCancel;
  const [topic, setTopic] = useState('');
  const [mcqCount, setMcqCount] = useState(10);
  const [aiSuggest, setAiSuggest] = useState(false);
  const [difficulty, setDifficulty] = useState('medium');
  const [instructions, setInstructions] = useState('');
  const [isSuggesting, setIsSuggesting] = useState(false);
  const [suggestionReasoning, setSuggestionReasoning] = useState('');

  useEffect(() => {
    let mounted = true;
    if (aiSuggest && materialIds && materialIds.length > 0) {
      const fetchSuggestion = async () => {
        setIsSuggesting(true);
        try {
          const res = await suggestQuizCount(materialIds);
          if (mounted && res) {
            setMcqCount(res.suggested_count);
            setSuggestionReasoning(res.reasoning);
          }
        } catch (error) {
          console.error('Failed to get quiz suggestion:', error);
        } finally {
          if (mounted) setIsSuggesting(false);
        }
      };
      fetchSuggestion();
    } else {
      setSuggestionReasoning('');
    }
    return () => {
      mounted = false;
    };
  }, [aiSuggest, materialIds]);

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({
      topic,
      mcqCount: aiSuggest ? null : mcqCount,
      difficulty,
      additionalInstructions: instructions,
    });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit} className="studio-dialog-v3">
        <div className="studio-dialog-v3-header">
          <div className="studio-dialog-v3-icon">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              quiz
            </span>
          </div>
          <div>
            <h3 className="studio-dialog-v3-title">Quiz Composer</h3>
            <p className="studio-dialog-v3-subtitle">Tune question volume, challenge level, and focus</p>
          </div>
          <button type="button" onClick={onClose} className="studio-dialog-v3-close" aria-label="Close quiz settings">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="studio-dialog-v3-body">
          <div className="studio-dialog-v3-grid">
            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">
                  Focus Topic <span className="studio-dialog-v3-label-muted">(optional)</span>
                </label>
              </div>
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Machine learning basics"
                className="studio-dialog-v3-input"
              />
            </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Number of Questions</label>
                <label className="studio-dialog-v3-toggle cursor-pointer">
                  <input
                    type="checkbox"
                    checked={aiSuggest}
                    onChange={(e) => setAiSuggest(e.target.checked)}
                  />
                  <span>AI Suggest</span>
                </label>
              </div>

              {aiSuggest ? (
                <div>
                  <div className="studio-dialog-v3-note">
                    {isSuggesting ? (
                      <div className="flex items-center gap-2">
                        <Loader2 className="w-3.5 h-3.5 animate-spin" />
                        <span>Analyzing content complexity...</span>
                      </div>
                    ) : (
                      <div className="flex items-center justify-between gap-2">
                        <span className="inline-flex items-center gap-1.5 text-[var(--accent)] font-semibold">
                          <Sparkles className="w-3.5 h-3.5" />
                          {mcqCount} questions suggested
                        </span>
                        <span className="text-[10px] text-[var(--text-muted)]">Smart estimate</span>
                      </div>
                    )}
                  </div>
                  {suggestionReasoning && !isSuggesting && (
                    <div className="studio-dialog-v3-note mt-2 flex gap-2">
                      <Info className="w-3.5 h-3.5 text-[var(--accent)] shrink-0 mt-0.5" />
                      <span>{suggestionReasoning}</span>
                    </div>
                  )}
                </div>
              ) : (
                <div className="studio-dialog-v3-range-row">
                  <input
                    type="range"
                    min={5}
                    max={150}
                    value={mcqCount}
                    onChange={(e) => setMcqCount(Number(e.target.value))}
                    className="studio-dialog-v3-range"
                  />
                  <input
                    type="number"
                    min={5}
                    max={150}
                    value={mcqCount}
                    onChange={(e) => setMcqCount(Math.min(150, Math.max(5, Number(e.target.value))))}
                    className="studio-dialog-v3-number w-20"
                  />
                </div>
              )}
            </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Difficulty</label>
              </div>
              <div className="studio-dialog-v3-segments">
                {['easy', 'medium', 'hard'].map((d) => (
                  <button
                    key={d}
                    type="button"
                    onClick={() => setDifficulty(d)}
                    className={`studio-dialog-v3-segment ${difficulty === d ? 'active' : ''}`}
                  >
                    {d}
                  </button>
                ))}
              </div>
            </div>

            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">
                  Additional Instructions <span className="studio-dialog-v3-label-muted">(optional)</span>
                </label>
              </div>
              <textarea
                value={instructions}
                onChange={(e) => setInstructions(e.target.value)}
                placeholder="Any specific requirements..."
                className="studio-dialog-v3-textarea"
              />
            </div>
          </div>
        </div>

        <div className="studio-dialog-v3-footer">
          <button type="button" onClick={onClose} className="studio-dialog-v3-btn ghost">
            Cancel
          </button>
          <button type="submit" className="studio-dialog-v3-btn primary">
            Generate Quiz
          </button>
        </div>
      </form>
    </Modal>
  );
}

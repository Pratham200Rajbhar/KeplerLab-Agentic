'use client';

import { useState, useEffect } from 'react';
import Modal from '@/components/ui/Modal';
import { X, Loader2, Info, Sparkles, HelpCircle, Check, Upload, FileUp, Video, Presentation } from 'lucide-react';
import { suggestFlashcardCount, suggestQuizCount } from '@/lib/api/generation';
import { getLanguages as getPodcastLanguages, getVoicesForLanguage as getPodcastVoicesForLanguage } from '@/lib/api/podcast';

function normalizeVoiceOption(voice) {
  if (!voice) return null;
  const id = voice.id || voice.voice_id || voice.voiceId;
  if (!id) return null;
  const name = voice.name || voice.label || id;
  const gender = voice.gender ? ` (${voice.gender})` : '';
  return {
    id,
    label: `${name}${gender}`,
    description: voice.description || '',
  };
}

const PALETTE_PRESETS = [
  {
    id: 'ai-auto',
    label: 'AI Auto',
    description: 'AI picks the perfect palette for your content',
    colors: ['#6366f1', '#0ea5e9', '#34d399'],
    icon: '✦',
  },
  {
    id: 'modern',
    label: 'Modern Blue',
    description: 'Dark navy with sky blue accent',
    colors: ['#0f172a', '#1e293b', '#38bdf8'],
    icon: null,
  },
  {
    id: 'academic',
    label: 'Academic Red',
    description: 'Deep midnight with crimson highlights',
    colors: ['#1a1a2e', '#16213e', '#e94560'],
    icon: null,
  },
  {
    id: 'corporate',
    label: 'Corporate Gold',
    description: 'Royal blue with gold accents',
    colors: ['#003566', '#001d3d', '#ffd60a'],
    icon: null,
  },
  {
    id: 'minimal',
    label: 'Clean White',
    description: 'Light minimal with indigo pop',
    colors: ['#ffffff', '#f8fafc', '#6366f1'],
    icon: null,
  },
  {
    id: 'bold',
    label: 'Bold Purple',
    description: 'Deep violet with coral energy',
    colors: ['#10002b', '#240046', '#ff6b6b'],
    icon: null,
  },
  {
    id: 'green',
    label: 'Emerald Scholar',
    description: 'Forest green with emerald accents',
    colors: ['#0d2818', '#1a3a28', '#34d399'],
    icon: null,
  },
];

const SLIDE_COUNT_OPTIONS = [5, 8, 10, 12, 15, 20, 25];
const AUDIENCE_OPTIONS = [
  { id: 'students', label: 'Students' },
  { id: 'professionals', label: 'Professionals' },
  { id: 'general', label: 'General' },
];

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

export function PresentationConfigDialog({ onGenerate, onCancel, loading = false, sourceCount = 0 }) {
  const [focus, setFocus] = useState('');
  const [selectedPalette, setSelectedPalette] = useState('ai-auto');
  const [slideCount, setSlideCount] = useState(10);
  const [audience, setAudience] = useState('students');
  const [customization, setCustomization] = useState('');

  const handleSubmit = (e) => {
    e.preventDefault();
    const paletteLabel = selectedPalette === 'ai-auto'
      ? ''
      : PALETTE_PRESETS.find(p => p.id === selectedPalette)?.label || '';
    const audienceNote = audience !== 'general'
      ? `Target audience: ${AUDIENCE_OPTIONS.find(a => a.id === audience)?.label || audience}. `
      : '';
    onGenerate({
      topic: focus.trim(),
      theme: paletteLabel,
      slideCount,
      additionalNotes: (audienceNote + customization.trim()).trim(),
    });
  };

  return (
    <Modal onClose={onCancel} maxWidth="lg">
      <form onSubmit={handleSubmit} className="studio-dialog-v3 studio-dialog-v3-presentation">
        <div className="studio-dialog-v3-header">
          <div className="studio-dialog-v3-icon">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>
              slideshow
            </span>
          </div>
          <div>
            <h3 className="studio-dialog-v3-title">Presentation Builder</h3>
            <p className="studio-dialog-v3-subtitle">
              16:9 AI slide deck · {sourceCount} source{sourceCount === 1 ? '' : 's'}
            </p>
          </div>
          <button type="button" onClick={onCancel} className="studio-dialog-v3-close" aria-label="Close presentation settings">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="studio-dialog-v3-body">
          <div className="studio-dialog-v3-grid">

            {/* Content Focus */}
            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">
                  Content Focus <span className="studio-dialog-v3-label-muted">(optional)</span>
                </label>
              </div>
              <input
                type="text"
                value={focus}
                onChange={(e) => setFocus(e.target.value)}
                placeholder="e.g., emphasize strategic decisions and outcomes"
                className="studio-dialog-v3-input"
                id="presentation-focus"
              />
            </div>

            {/* Audience */}
            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Audience</label>
              </div>
              <div className="studio-dialog-v3-segments">
                {AUDIENCE_OPTIONS.map((aud) => (
                  <button
                    key={aud.id}
                    type="button"
                    onClick={() => setAudience(aud.id)}
                    className={`studio-dialog-v3-segment ${audience === aud.id ? 'active' : ''}`}
                    id={`audience-${aud.id}`}
                  >
                    {aud.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Color Theme Palette Picker */}
            <div className="studio-dialog-v3-section" style={{ gridColumn: '1 / -1' }}>
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Color Theme &amp; Mood</label>
                {selectedPalette === 'ai-auto' && (
                  <span className="text-[10px] text-[var(--accent)] font-medium flex items-center gap-1">
                    <Sparkles className="w-3 h-3" /> Auto-selected for your content
                  </span>
                )}
              </div>
              <div className="grid grid-cols-4 gap-2 mt-1">
                {PALETTE_PRESETS.map((palette) => (
                  <button
                    key={palette.id}
                    type="button"
                    id={`palette-${palette.id}`}
                    onClick={() => setSelectedPalette(palette.id)}
                    title={palette.description}
                    className={[
                      'relative flex flex-col gap-1.5 p-2.5 rounded-xl border text-left transition-all duration-150',
                      selectedPalette === palette.id
                        ? 'border-[var(--accent)] bg-[var(--accent-subtle)] shadow-sm'
                        : 'border-[var(--border)] bg-[var(--surface-overlay)] hover:border-[var(--accent-border,var(--accent))] hover:bg-[var(--surface-raised)]',
                    ].join(' ')}
                  >
                    {/* Color swatches */}
                    <div className="flex items-center gap-1">
                      {palette.icon ? (
                        <div
                          className="w-full h-5 rounded-md flex items-center justify-center text-sm font-bold"
                          style={{ background: 'linear-gradient(135deg, #6366f1, #0ea5e9, #34d399)' }}
                        >
                          <span className="text-white text-[11px] font-bold">{palette.icon} AI</span>
                        </div>
                      ) : (
                        palette.colors.map((c, i) => (
                          <div
                            key={i}
                            className="flex-1 h-5 rounded-md"
                            style={{ backgroundColor: c, border: c === '#ffffff' || c === '#f8fafc' ? '1px solid rgba(0,0,0,0.1)' : 'none' }}
                          />
                        ))
                      )}
                    </div>
                    {/* Label */}
                    <span className="text-[10px] font-semibold text-[var(--text-secondary)] leading-none truncate">
                      {palette.label}
                    </span>
                    {/* Active indicator */}
                    {selectedPalette === palette.id && (
                      <div className="absolute top-1.5 right-1.5 w-3 h-3 rounded-full bg-[var(--accent)] flex items-center justify-center">
                        <Check className="w-2 h-2 text-white" />
                      </div>
                    )}
                  </button>
                ))}
              </div>
            </div>

            {/* Slide Count */}
            <div className="studio-dialog-v3-section" style={{ gridColumn: '1 / -1' }}>
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Slide Count</label>
                <span className="text-[10px] text-[var(--text-muted)] tabular-nums">
                  {slideCount} slides · 16:9 ratio
                </span>
              </div>
              <div className="flex items-center gap-1.5 flex-wrap">
                {SLIDE_COUNT_OPTIONS.map((n) => (
                  <button
                    key={n}
                    type="button"
                    onClick={() => setSlideCount(n)}
                    id={`slide-count-${n}`}
                    className={[
                      'px-3 py-1.5 rounded-lg text-[12px] font-medium border transition-all',
                      slideCount === n
                        ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)]'
                        : 'border-[var(--border)] bg-[var(--surface-overlay)] text-[var(--text-secondary)] hover:border-[var(--accent-border,var(--accent))]',
                    ].join(' ')}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>

            {/* Fine-tune */}
            <div className="studio-dialog-v3-section" style={{ gridColumn: '1 / -1' }}>
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">
                  Fine-tune <span className="studio-dialog-v3-label-muted">(optional)</span>
                </label>
              </div>
              <textarea
                value={customization}
                onChange={(e) => setCustomization(e.target.value)}
                placeholder="e.g., more diagrams, fewer paragraphs, executive summary at the end"
                className="studio-dialog-v3-textarea"
                id="presentation-finetune"
              />
            </div>

            {/* Info note */}
            <div className="studio-dialog-v3-note flex items-center gap-2" style={{ gridColumn: '1 / -1' }}>
              <Sparkles className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" />
              <span>Each slide is generated as a 1280×720 (16:9) image with a consistent color theme across all slides.</span>
            </div>

          </div>
        </div>

        <div className="studio-dialog-v3-footer">
          <button type="button" onClick={onCancel} className="studio-dialog-v3-btn ghost" disabled={loading}>
            Cancel
          </button>
          <button type="submit" className="studio-dialog-v3-btn primary" disabled={loading} id="presentation-generate-btn">
            {loading ? (
              <span className="inline-flex items-center gap-2">
                <Loader2 className="w-4 h-4 animate-spin" />
                Generating...
              </span>
            ) : (
              <span className="inline-flex items-center gap-2">
                <Sparkles className="w-4 h-4" />
                Create Presentation
              </span>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export function ExplainerConfigDialog({
  onGenerate,
  onUpload,
  onCancel,
  onOpenPresentation,
  presentations = [],
  loading = false,
}) {
  const [activeTab, setActiveTab] = useState(presentations.length > 0 ? 'existing' : 'upload');
  const [presentationId, setPresentationId] = useState(presentations[0]?.id || '');
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);

  const [languageOptions, setLanguageOptions] = useState([]);
  const [narrationLanguage, setNarrationLanguage] = useState('');
  const [voiceOptions, setVoiceOptions] = useState([]);
  const [voiceId, setVoiceId] = useState('');
  const [languagesLoading, setLanguagesLoading] = useState(true);
  const [languagesError, setLanguagesError] = useState('');
  const [voicesLoading, setVoicesLoading] = useState(false);
  const [voicesError, setVoicesError] = useState('');
  
  const [narrationStyle, setNarrationStyle] = useState('teacher');
  const [additionalNotes, setAdditionalNotes] = useState('');

  const NARRATION_STYLES = [
    { id: 'teacher', label: '🎓 Teacher', desc: 'Warm, clear, step-by-step guidance' },
    { id: 'storyteller', label: '📖 Storyteller', desc: 'Narrative, engaging and emotive' },
    { id: 'expert_analyst', label: '📊 Analyst', desc: 'Data-driven, precise and objective' },
    { id: 'conversational', label: '💬 Conversational', desc: 'Casual, direct and relatable' },
    { id: 'professional', label: '🎙️ Professional', desc: 'Polished, formal executive style' },
  ];

  useEffect(() => {
    let active = true;
    const loadLanguages = async () => {
      setLanguagesError('');
      try {
        const data = await getPodcastLanguages();
        if (!active) return;
        const nextOptions = (Array.isArray(data) ? data : [])
          .map((item) => ({ code: item?.code, label: item?.name }))
          .filter((item) => item.code && item.label);

        if (nextOptions.length === 0) {
          setLanguageOptions([]);
          setLanguagesError('No languages available.');
          return;
        }

        setLanguageOptions(nextOptions);
        setNarrationLanguage(prev => prev && nextOptions.some(l => l.code === prev) ? prev : nextOptions[0].code);
      } catch {
        if (!active) return;
        setLanguagesError('Failed to load languages.');
      } finally {
        if (active) setLanguagesLoading(false);
      }
    };
    loadLanguages();
    return () => { active = false; };
  }, []);

  useEffect(() => {
    let active = true;
    const loadVoices = async () => {
      if (!narrationLanguage) return;
      setVoicesLoading(true);
      setVoicesError('');
      try {
        const data = await getPodcastVoicesForLanguage(narrationLanguage);
        if (!active) return;
        const rawVoices = Array.isArray(data?.voices) ? data.voices : [];
        const normalized = rawVoices.map(normalizeVoiceOption).filter(Boolean);

        if (normalized.length === 0) {
          setVoicesError('No voices available.');
          setVoiceOptions([]);
          setVoiceId('');
          return;
        }
        setVoiceOptions(normalized);
        const defaultVoice = data?.defaults?.host;
        setVoiceId(prev => {
          if (prev && normalized.some(v => v.id === prev)) return prev;
          if (defaultVoice && normalized.some(v => v.id === defaultVoice)) return defaultVoice;
          return normalized[0].id;
        });
      } catch {
        if (!active) return;
        setVoicesError('Failed to load voices.');
      } finally {
        if (active) setVoicesLoading(false);
      }
    };
    loadVoices();
    return () => { active = false; };
  }, [narrationLanguage]);

  useEffect(() => {
    if (!presentationId || !presentations.some(p => p.id === presentationId)) {
      if (presentations.length > 0) setPresentationId(presentations[0].id);
    }
  }, [presentations, presentationId]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f && /\.(pptx?|ppt)$/i.test(f.name)) setFile(f);
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    if (activeTab === 'existing') {
        if (!presentationId) return;
        onGenerate({
            presentationId,
            voiceId,
            narrationStyle,
            narrationLanguage,
            presentationLanguage: narrationLanguage,
            additionalNotes,
        });
    } else {
        if (!file) return;
        onUpload?.({
            file,
            voiceId,
            narrationLanguage,
            narrationStyle,
            additionalNotes,
        });
    }
  };

  const isSubmitDisabled = loading || !voiceId || (activeTab === 'existing' ? !presentationId : !file);

  return (
    <Modal onClose={onCancel} maxWidth="max-w-4xl">
      <form onSubmit={handleSubmit} className="flex flex-col bg-[var(--surface-color)] sm:h-[80vh] md:h-[600px] rounded-2xl overflow-hidden shadow-2xl border border-[var(--border)]">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-[var(--border)] shrink-0 bg-[var(--surface-overlay)]/50">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-subtle)] flex items-center justify-center border border-[var(--accent-border)]">
              <Video className="w-5 h-5 text-[var(--accent)]" />
            </div>
            <div>
              <h3 className="text-[16px] font-bold text-[var(--text-primary)]">Explain Video Builder</h3>
              <p className="text-[12px] text-[var(--text-muted)] mt-0.5">Generate an AI-narrated video from your presentation slides</p>
            </div>
          </div>
          <button type="button" onClick={onCancel} className="p-2 -mr-2 text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors hover:bg-[var(--surface-overlay)] rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="flex flex-1 overflow-hidden flex-col md:flex-row">
            {/* Left Col - Input Source Selection */}
            <div className="w-full md:w-[280px] lg:w-[320px] flex flex-col border-r border-[var(--border)] bg-[var(--surface-overlay)] overflow-y-auto hidden-scrollbar">
                
                {/* Tab Switcher */}
                <div className="p-5 shrink-0">
                    <div className="flex p-1 bg-[var(--surface-color)] rounded-xl border border-[var(--border)] relative">
                        <button
                            type="button"
                            onClick={() => setActiveTab('existing')}
                            className={`flex flex-col items-center justify-center gap-1.5 flex-1 py-3 px-2 rounded-lg text-[11px] font-semibold transition-all z-10 ${
                                activeTab === 'existing' 
                                ? 'text-[var(--text-primary)] shadow-sm border border-[var(--border)] bg-[var(--surface-overlay)]' 
                                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent'
                            }`}
                        >
                            <Presentation className={`w-5 h-5 ${activeTab === 'existing' ? 'text-[var(--accent)]' : 'opacity-60'}`} />
                            AI Created Deck
                        </button>
                        <button
                            type="button"
                            onClick={() => setActiveTab('upload')}
                            className={`flex flex-col items-center justify-center gap-1.5 flex-1 py-3 px-2 rounded-lg text-[11px] font-semibold transition-all z-10 ${
                                activeTab === 'upload' 
                                ? 'text-[var(--text-primary)] shadow-sm border border-[var(--border)] bg-[var(--surface-overlay)]' 
                                : 'text-[var(--text-muted)] hover:text-[var(--text-secondary)] border border-transparent'
                            }`}
                        >
                            <FileUp className={`w-5 h-5 ${activeTab === 'upload' ? 'text-[var(--accent)]' : 'opacity-60'}`} />
                            Upload PPTX
                        </button>
                    </div>
                </div>

                <div className="px-5 pb-6 flex-1 flex flex-col">
                    {activeTab === 'existing' ? (
                        <div className="space-y-3">
                            {presentations.length === 0 ? (
                                <div className="text-center py-8 rounded-2xl border border-[var(--border)] bg-[var(--surface-color)]/50">
                                    <div className="w-12 h-12 mx-auto bg-[var(--surface-overlay)] rounded-full flex items-center justify-center border border-[var(--border)] mb-3">
                                        <Info className="w-5 h-5 text-[var(--text-muted)] opacity-60" />
                                    </div>
                                    <p className="text-[13px] font-semibold text-[var(--text-primary)]">No presentations found</p>
                                    <p className="text-[11px] text-[var(--text-muted)] mt-1.5 px-4 leading-relaxed">
                                        You need to generate an AI presentation first.
                                    </p>
                                    <button type="button" onClick={() => { onCancel(); onOpenPresentation(); }} className="mt-4 text-[12px] font-medium text-[var(--accent)] hover:underline flex items-center justify-center w-full">
                                        Create one now →
                                    </button>
                                </div>
                            ) : (
                                <div className="space-y-2">
                                    <p className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider mb-2 pl-1">Select Presentation</p>
                                    {presentations.map(item => (
                                        <button
                                            key={item.id}
                                            type="button"
                                            onClick={() => setPresentationId(item.id)}
                                            className={`w-full text-left p-3 rounded-xl border transition-all ${
                                                presentationId === item.id
                                                ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
                                                : 'border-[var(--border)] hover:border-[var(--text-muted)] bg-[var(--surface-color)]'
                                            }`}
                                        >
                                            <div className="flex items-center justify-between gap-2">
                                                <div className="min-w-0 flex-1">
                                                    <p className={`text-[12px] font-semibold truncate ${presentationId === item.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                                                        {item.title || 'Untitled'}
                                                    </p>
                                                    <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                                                        {item.data?.slideCount || item.data?.slides?.length || 0} slides
                                                    </p>
                                                </div>
                                                {presentationId === item.id && <Check className="w-4 h-4 text-[var(--accent)] shrink-0" />}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>
                    ) : (
                        <div className="flex flex-col h-full space-y-3">
                            <p className="text-[10px] font-semibold text-[var(--text-secondary)] uppercase tracking-wider pl-1">Custom Presentation File</p>
                            <label
                                onDrop={handleDrop}
                                onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
                                onDragLeave={() => setDragging(false)}
                                className={`flex-1 relative rounded-2xl border-2 border-dashed flex items-center justify-center p-6 text-center transition-all cursor-pointer min-h-[160px] ${
                                    dragging
                                    ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
                                    : file
                                    ? 'border-[var(--accent)] bg-[var(--accent-subtle)] border-solid'
                                    : 'border-[var(--border)] hover:border-[var(--text-muted)] bg-[var(--surface-color)]'
                                }`}
                                htmlFor="pptx-upload"
                            >
                                <input id="pptx-upload" type="file" accept=".ppt,.pptx" className="hidden" onChange={(e) => setFile(e.target.files?.[0])} />
                                {file ? (
                                    <div className="flex flex-col items-center justify-center gap-3">
                                        <div className="w-14 h-14 rounded-full bg-[var(--accent)]/10 text-[var(--accent)] flex items-center justify-center border border-[var(--accent)]/20 shadow-inner">
                                            <FileUp className="w-6 h-6" />
                                        </div>
                                        <div className="px-2">
                                            <p className="text-[13px] font-semibold text-[var(--text-primary)] break-words line-clamp-2">{file.name}</p>
                                            <p className="text-[11px] text-[var(--text-muted)] mt-0.5">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
                                        </div>
                                        <p className="text-[10px] text-[var(--accent)] hover:underline mt-1 font-medium">Click to change file</p>
                                    </div>
                                ) : (
                                    <div className="flex flex-col items-center gap-2 text-[var(--text-muted)]">
                                        <div className="w-12 h-12 rounded-full bg-[var(--surface-overlay)] flex items-center justify-center border border-[var(--border)] mb-1">
                                            <Upload className="w-5 h-5" />
                                        </div>
                                        <p className="text-[13px] font-semibold text-[var(--text-primary)]">Drop .pptx file here</p>
                                        <p className="text-[11px]">or click to browse (max 100MB)</p>
                                    </div>
                                )}
                            </label>
                            
                            {/* Pro tip card */}
                            <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-color)] p-3.5 mt-2 shadow-sm relative overflow-hidden">
                                <div className="absolute top-0 right-0 w-16 h-16 bg-gradient-to-bl from-[var(--accent)]/10 to-transparent rounded-bl-full pointer-events-none" />
                                <p className="text-[11px] font-bold text-[var(--text-primary)] flex items-center gap-1.5">
                                    <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" /> 
                                    Powered by Vision AI
                                </p>
                                <p className="text-[11px] text-[var(--text-muted)] mt-1.5 leading-relaxed relative z-10">
                                    Our engine &quot;sees&quot; your charts and diagrams to craft professional narration, matching exactly what&apos;s on screen.
                                </p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Right Col - Audio & Output Settings */}
            <div className="flex-1 p-6 md:p-8 flex flex-col overflow-y-auto hidden-scrollbar bg-[var(--surface-color)]">
                
                <div className="max-w-[500px] w-full mx-auto space-y-8">
                    {/* Voice Selection */}
                    <div>
                    <h4 className="text-[14px] font-bold text-[var(--text-primary)] mb-4">Voice & Language Settings</h4>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                        <div className="space-y-1.5">
                            <label className="text-[11px] text-[var(--text-secondary)] font-semibold uppercase tracking-wide">Language</label>
                            <select 
                                value={narrationLanguage}
                                onChange={e => setNarrationLanguage(e.target.value)}
                                className="w-full px-3.5 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] text-[13px] text-[var(--text-primary)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] outline-none shadow-sm transition-all"
                                disabled={languagesLoading}
                            >
                                {languageOptions.map(l => <option key={l.code} value={l.code}>{l.label}</option>)}
                            </select>
                        </div>

                        <div className="space-y-1.5">
                            <label className="text-[11px] text-[var(--text-secondary)] font-semibold uppercase tracking-wide">Narrator Voice</label>
                            <select 
                                value={voiceId}
                                onChange={e => setVoiceId(e.target.value)}
                                className="w-full px-3.5 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] text-[13px] text-[var(--text-primary)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] outline-none shadow-sm transition-all"
                                disabled={voicesLoading}
                            >
                                {voiceOptions.map(v => <option key={v.id} value={v.id}>{v.label}</option>)}
                            </select>
                            <p className="text-[10px] text-[var(--text-muted)] mt-1 px-1">{voicesLoading ? 'Loading catalogs...' : voicesError}</p>
                        </div>
                    </div>
                    </div>

                    {/* Persona & Tone */}
                    <div>
                    <h4 className="text-[14px] font-bold text-[var(--text-primary)] mb-4">AI Narration Persona</h4>
                    
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                        {NARRATION_STYLES.map(s => (
                            <button
                                key={s.id}
                                type="button"
                                onClick={() => setNarrationStyle(s.id)}
                                className={`flex flex-col text-left p-3 rounded-xl border transition-all ${
                                    narrationStyle === s.id
                                    ? 'bg-[var(--accent-subtle)] border-[var(--accent)] ring-1 ring-[var(--accent)] shadow-sm'
                                    : 'bg-[var(--surface-overlay)] border-[var(--border)] hover:border-[var(--text-muted)] hover:shadow-sm'
                                }`}
                            >
                                <div className="flex items-center justify-between w-full mb-1">
                                    <span className={`text-[13px] font-semibold ${narrationStyle === s.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>
                                        {s.label}
                                    </span>
                                    {narrationStyle === s.id && <div className="w-1.5 h-1.5 rounded-full bg-[var(--accent)] shrink-0" />}
                                </div>
                                <span className={`text-[11px] ${narrationStyle === s.id ? 'text-[var(--text-secondary)]' : 'text-[var(--text-muted)]'}`}>
                                    {s.desc}
                                </span>
                            </button>
                        ))}
                    </div>

                    <div className="mt-5 space-y-2">
                        <label className="text-[11px] text-[var(--text-secondary)] font-semibold uppercase tracking-wide flex items-center justify-between">
                            Custom Instructions
                            <span className="text-[var(--text-muted)] font-normal lowercase normal-case tracking-normal">optional</span>
                        </label>
                        <textarea
                            value={additionalNotes}
                            onChange={e => setAdditionalNotes(e.target.value)}
                            placeholder="e.g. Focus deeply on the financial metrics, assume the audience knows basic accounting terminology..."
                            rows={3}
                            className="w-full px-4 py-3 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] text-[13px] text-[var(--text-primary)] focus:border-[var(--accent)] focus:ring-1 focus:ring-[var(--accent)] outline-none resize-none placeholder-[var(--text-muted)]/60 shadow-inner"
                        />
                    </div>
                    </div>
                </div>

            </div>
        </div>

        {/* Footer */}
        <div className="px-6 py-4 border-t border-[var(--border)] bg-[var(--surface-overlay)]/40 flex items-center justify-end gap-3 shrink-0">
          <button type="button" onClick={onCancel} className="px-5 py-2.5 rounded-xl text-[13px] font-semibold text-[var(--text-secondary)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-overlay)] transition-colors" disabled={loading}>
            Cancel
          </button>
          <button
            type="submit"
            disabled={isSubmitDisabled}
            className="px-6 py-2.5 rounded-xl font-semibold text-[14px] text-white flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-lg transition-all"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-light, var(--accent)))' }}
          >
            {loading ? (
              <><Loader2 className="w-4 h-4 animate-spin" /> Starting Engine...</>
            ) : (
              <><Video className="w-4 h-4" /> Generate Explainer</>
            )}
          </button>
        </div>
      </form>
    </Modal>
  );
}

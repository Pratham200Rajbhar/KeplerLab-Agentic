'use client';

import { useState, useCallback, useEffect, useRef } from 'react';
import {
  Presentation,
  RefreshCw,
  Download,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Sparkles,
  X,
  Check,
  Play,
  LayoutGrid,
  Monitor,
  FileDown,
  FileText,
  Loader2,
} from 'lucide-react';

import usePresentationStore from '@/stores/usePresentationStore';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import {
  generatePresentation,
  getPresentation,
  regenerateSlide,
  exportPresentationPptx,
  exportPresentationPdf,
} from '@/lib/api/presentation';
import { apiConfig } from '@/lib/api/config';

// ── Helpers ───────────────────────────────────────────────────────────────────

const SLIDE_ASPECT = 'aspect-[16/9]';

function resolveUrl(path) {
  if (!path) return null;
  if (path.startsWith('http')) return path;
  return `${apiConfig.baseUrl}${path}`;
}

// ── ThemeStrip ────────────────────────────────────────────────────────────────

function ThemeStrip({ themeSpec }) {
  if (!themeSpec) return null;
  const swatches = [
    { color: themeSpec.primary, label: 'BG' },
    { color: themeSpec.secondary, label: 'Surface' },
    { color: themeSpec.accent, label: 'Accent' },
    { color: themeSpec.text, label: 'Text' },
    { color: themeSpec.muted, label: 'Muted' },
  ].filter(s => s.color && /^#[0-9a-fA-F]{6}$/.test(s.color));

  return (
    <div className="flex items-center gap-1.5 px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)]">
      <Sparkles className="w-3 h-3 text-[var(--accent)] shrink-0" />
      <div className="flex items-center gap-1 flex-1 overflow-hidden">
        {swatches.map((s) => (
          <div
            key={s.label}
            title={`${s.label}: ${s.color}`}
            className="w-4 h-4 rounded-full shrink-0 ring-1 ring-black/10"
            style={{ backgroundColor: s.color }}
          />
        ))}
        {themeSpec.font_family && (
          <span className="text-[10px] text-[var(--text-muted)] ml-1 truncate">
            {themeSpec.font_family}
          </span>
        )}
      </div>
      {themeSpec.mood && (
        <span className="text-[10px] text-[var(--accent)] font-medium capitalize shrink-0">
          {themeSpec.mood}
        </span>
      )}
    </div>
  );
}

// ── SlideSkeleton ─────────────────────────────────────────────────────────────

function SlideSkeleton({ index = 0 }) {
  return (
    <div className="relative w-full h-full bg-[var(--surface-overlay)] flex flex-col items-center justify-center gap-3 p-4">
      <div className="w-3/4 h-3 rounded-full bg-[var(--text-muted)]/10 animate-pulse" />
      <div className="w-1/2 h-2 rounded-full bg-[var(--text-muted)]/8 animate-pulse" />
      <div className="w-2/3 h-2 rounded-full bg-[var(--text-muted)]/6 animate-pulse" />
      <div className="absolute bottom-2 right-2 text-[9px] text-[var(--text-muted)]/30 font-mono">
        {index + 1}
      </div>
    </div>
  );
}

// ── ProgressBar ────────────────────────────────────────────────────────────────

function ProgressBar({ progress }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <span className="text-[11px] text-[var(--text-secondary)] font-medium">
          {progress.message}
        </span>
        <span className="text-[10px] text-[var(--text-muted)] tabular-nums font-mono">
          {Math.round(progress.pct || 0)}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-[var(--surface-overlay)] overflow-hidden">
        <div
          className="h-full rounded-full transition-all duration-700 ease-out"
          style={{
            width: `${Math.max(progress.pct || 0, 3)}%`,
            background: 'linear-gradient(90deg, var(--accent), var(--accent-light, var(--accent)))',
          }}
        />
      </div>
    </div>
  );
}

// ── PresentMode — true fullscreen presentation ────────────────────────────────
//
// Uses the Fullscreen API so the deck fills the entire display.
// Shows current slide at max 16:9; keyboard-driven navigation.
// HUD fades on inactivity; shows title + progress at bottom.

function PresentMode({ slides, initialIndex = 0, onExit, themeSpec }) {
  const [current, setCurrent] = useState(initialIndex);
  const [hudVisible, setHudVisible] = useState(true);
  const hudTimerRef = useRef(null);
  const containerRef = useRef(null);
  const slide = slides[current];
  const imageUrl = resolveUrl(slide?.imageUrl);

  // ── Fullscreen ────────────────────────────────────────────────────────────
  useEffect(() => {
    const el = document.documentElement;
    if (el.requestFullscreen) el.requestFullscreen().catch(() => {});
    return () => {
      if (document.fullscreenElement) document.exitFullscreen().catch(() => {});
    };
  }, []);

  // Exit present mode if user presses browser Esc to exit fullscreen
  useEffect(() => {
    const onFsChange = () => {
      if (!document.fullscreenElement) onExit();
    };
    document.addEventListener('fullscreenchange', onFsChange);
    return () => document.removeEventListener('fullscreenchange', onFsChange);
  }, [onExit]);

  // ── Keyboard ──────────────────────────────────────────────────────────────
  useEffect(() => {
    const onKey = (e) => {
      showHud();
      if (e.key === 'Escape') { onExit(); return; }
      if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'PageDown') {
        e.preventDefault();
        setCurrent((c) => Math.min(slides.length - 1, c + 1));
      }
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') {
        e.preventDefault();
        setCurrent((c) => Math.max(0, c - 1));
      }
      if (e.key === 'Home') setCurrent(0);
      if (e.key === 'End') setCurrent(slides.length - 1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onExit, slides.length]);

  // ── HUD auto-hide ─────────────────────────────────────────────────────────
  const showHud = useCallback(() => {
    setHudVisible(true);
    clearTimeout(hudTimerRef.current);
    hudTimerRef.current = setTimeout(() => setHudVisible(false), 3500);
  }, []);

  useEffect(() => {
    showHud();
    return () => clearTimeout(hudTimerRef.current);
  }, [showHud]);

  const progress = ((current + 1) / slides.length) * 100;

  // Background colour from theme spec
  const bg = themeSpec?.primary || '#000000';

  return (
    <div
      ref={containerRef}
      className="fixed inset-0 z-[9999] flex flex-col items-center justify-center select-none"
      style={{ backgroundColor: bg, cursor: hudVisible ? 'default' : 'none' }}
      onMouseMove={showHud}
      onClick={(e) => {
        // Click right half → next; left half → prev
        const rect = e.currentTarget.getBoundingClientRect();
        if (e.clientX > rect.left + rect.width / 2) {
          setCurrent((c) => Math.min(slides.length - 1, c + 1));
        } else {
          setCurrent((c) => Math.max(0, c - 1));
        }
      }}
    >
      {/* Slide image — fills 100vw × 100vh maintaining 16:9 */}
      <div className="relative flex items-center justify-center w-full h-full">
        {imageUrl ? (
          <img
            src={imageUrl}
            alt={slide?.title || `Slide ${current + 1}`}
            className="max-w-full max-h-full"
            style={{
              objectFit: 'contain',
              aspectRatio: '16/9',
              width: '100%',
              height: '100%',
            }}
            draggable={false}
          />
        ) : (
          <div
            className="flex items-center justify-center rounded-xl border border-white/10"
            style={{ width: '100%', height: '100%', maxWidth: '1280px', aspectRatio: '16/9' }}
          >
            <Presentation className="w-20 h-20 text-white/20" />
          </div>
        )}

        {/* ── HUD overlay ──────────────────────────────────────────────── */}
        <div
          className={`absolute inset-0 flex flex-col justify-between pointer-events-none transition-opacity duration-500 ${
            hudVisible ? 'opacity-100' : 'opacity-0'
          }`}
          style={{ pointerEvents: hudVisible ? 'auto' : 'none' }}
        >
          {/* Top bar */}
          <div
            className="flex items-center justify-between px-6 py-4"
            style={{
              background: 'linear-gradient(to bottom, rgba(0,0,0,0.6), transparent)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <span className="text-white/80 text-[13px] font-medium line-clamp-1">
              {slide?.title || `Slide ${current + 1}`}
            </span>
            <button
              onClick={(e) => { e.stopPropagation(); onExit(); }}
              className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors backdrop-blur-sm"
              title="Exit presentation (Esc)"
            >
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Bottom HUD */}
          <div
            style={{
              background: 'linear-gradient(to top, rgba(0,0,0,0.65), transparent)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            {/* Progress bar */}
            <div className="px-6 pt-4 pb-1">
              <div className="h-0.5 rounded-full bg-white/20 overflow-hidden">
                <div
                  className="h-full rounded-full bg-white/70 transition-all duration-300"
                  style={{ width: `${progress}%` }}
                />
              </div>
            </div>

            {/* Nav row */}
            <div className="flex items-center justify-center gap-6 px-6 pb-4 pt-2">
              <button
                onClick={(e) => { e.stopPropagation(); setCurrent((c) => Math.max(0, c - 1)); }}
                disabled={current === 0}
                className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors disabled:opacity-30"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>

              {/* Slide dots (max 20) */}
              <div className="flex items-center gap-1 overflow-hidden max-w-[300px]">
                {slides.slice(0, 20).map((_, i) => (
                  <button
                    key={i}
                    onClick={(e) => { e.stopPropagation(); setCurrent(i); }}
                    className={`rounded-full transition-all duration-200 ${
                      i === current
                        ? 'w-5 h-2 bg-white'
                        : 'w-2 h-2 bg-white/30 hover:bg-white/60'
                    }`}
                  />
                ))}
                {slides.length > 20 && (
                  <span className="text-white/40 text-[10px] ml-1">+{slides.length - 20}</span>
                )}
              </div>

              <button
                onClick={(e) => { e.stopPropagation(); setCurrent((c) => Math.min(slides.length - 1, c + 1)); }}
                disabled={current === slides.length - 1}
                className="p-2 rounded-xl bg-white/10 hover:bg-white/20 text-white transition-colors disabled:opacity-30"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>

            {/* Hint text */}
            <p className="text-center text-white/30 text-[10px] pb-3">
              ← → to navigate · Space to advance · Esc to exit · Click to advance
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

// ── SlideGrid ─────────────────────────────────────────────────────────────────

function SlideGrid({ slides, onPresent, onRegenerate, regeneratingIdx }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {slides.map((slide, idx) => {
        const thumb = resolveUrl(slide.imageUrl);
        return (
          <div
            key={slide.index}
            className={`group relative rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--surface-overlay)] transition-all hover:border-[var(--accent)] hover:shadow-md ${
              slide.status === 'completed' ? 'cursor-pointer' : 'cursor-default'
            }`}
            onClick={() => slide.status === 'completed' && onPresent(idx)}
          >
            <div className={SLIDE_ASPECT}>
              {slide.status === 'completed' && thumb ? (
                <img src={thumb} alt={slide.title} className="w-full h-full object-cover" />
              ) : slide.status === 'failed' ? (
                <div className="w-full h-full flex items-center justify-center bg-[var(--danger-subtle)]">
                  <AlertTriangle className="w-5 h-5 text-[var(--danger)]" />
                </div>
              ) : (
                <div className="w-full h-full"><SlideSkeleton index={slide.index} /></div>
              )}
            </div>
            {/* Slide number badge */}
            <div className="absolute top-1.5 left-1.5 px-1.5 py-0.5 rounded-md bg-black/60 text-white text-[9px] font-mono">
              {slide.index + 1}
            </div>
            {/* Play overlay on hover */}
            {slide.status === 'completed' && (
              <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/30">
                <div className="p-2 rounded-full bg-white/20 backdrop-blur-sm">
                  <Play className="w-4 h-4 text-white" />
                </div>
              </div>
            )}
            {/* Regen button */}
            {slide.status === 'completed' && (
              <button
                onClick={(e) => { e.stopPropagation(); onRegenerate(slide.index); }}
                disabled={regeneratingIdx === slide.index}
                className="absolute top-1.5 right-1.5 p-1 rounded-md bg-black/50 text-white/70 hover:text-white opacity-0 group-hover:opacity-100 transition-opacity"
                title="Regenerate"
              >
                <RefreshCw className={`w-3 h-3 ${regeneratingIdx === slide.index ? 'animate-spin' : ''}`} />
              </button>
            )}
            {/* Slide title */}
            <div className="absolute bottom-0 inset-x-0 px-2 py-1 bg-gradient-to-t from-black/60 to-transparent translate-y-full group-hover:translate-y-0 transition-transform">
              <p className="text-white text-[10px] font-medium truncate">{slide.title}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}

// ── ExportButtons ─────────────────────────────────────────────────────────────

function ExportButtons({ presentationId, title }) {
  const toast = useToast();
  const [loadingPptx, setLoadingPptx] = useState(false);
  const [loadingPdf, setLoadingPdf] = useState(false);

  const safeName = (ext) => {
    const base = (title || 'presentation').replace(/[^a-zA-Z0-9 _-]/g, '_').slice(0, 60);
    return `${base}.${ext}`;
  };

  const handlePptx = async () => {
    if (!presentationId || loadingPptx) return;
    setLoadingPptx(true);
    try {
      await exportPresentationPptx(presentationId, safeName('pptx'));
      toast.success('PPTX downloaded!');
    } catch (err) {
      toast.error(err.message || 'PPTX export failed');
    } finally {
      setLoadingPptx(false);
    }
  };

  const handlePdf = async () => {
    if (!presentationId || loadingPdf) return;
    setLoadingPdf(true);
    try {
      await exportPresentationPdf(presentationId, safeName('pdf'));
      toast.success('PDF downloaded!');
    } catch (err) {
      toast.error(err.message || 'PDF export failed');
    } finally {
      setLoadingPdf(false);
    }
  };

  return (
    <div className="flex items-center gap-1.5">
      <button
        id="export-pptx-btn"
        onClick={handlePptx}
        disabled={loadingPptx}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] text-[11px] font-medium text-[var(--text-secondary)] hover:text-[var(--accent)] hover:border-[var(--accent-border,var(--accent))] transition-all disabled:opacity-50"
        title="Download as PowerPoint"
      >
        {loadingPptx ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileDown className="w-3.5 h-3.5" />}
        PPTX
      </button>
      <button
        id="export-pdf-btn"
        onClick={handlePdf}
        disabled={loadingPdf}
        className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] text-[11px] font-medium text-[var(--text-secondary)] hover:text-[var(--accent)] hover:border-[var(--accent-border,var(--accent))] transition-all disabled:opacity-50"
        title="Download as PDF"
      >
        {loadingPdf ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <FileText className="w-3.5 h-3.5" />}
        PDF
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function PresentationGenerator({ onClose, onSaved }) {
  const toast = useToast();
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const setLoadingState = useAppStore((s) => s.setLoadingState);

  const phase = usePresentationStore((s) => s.phase);
  const slides = usePresentationStore((s) => s.slides);
  const themeSpec = usePresentationStore((s) => s.themeSpec);
  const progress = usePresentationStore((s) => s.progress);
  const error = usePresentationStore((s) => s.error);
  const presentationId = usePresentationStore((s) => s.presentationId);
  const reset = usePresentationStore((s) => s.reset);
  const setPhase = usePresentationStore((s) => s.setPhase);
  const setPresentationId = usePresentationStore((s) => s.setPresentationId);
  const setError = usePresentationStore((s) => s.setError);
  const setPresentationData = usePresentationStore((s) => s.setPresentationData);
  const setVideoData = usePresentationStore((s) => s.setVideoData);

  const [topic, setTopic] = useState('');
  const [regeneratingIdx, setRegeneratingIdx] = useState(null);
  const [presentMode, setPresentMode] = useState(false);
  const [presentStartIndex, setPresentStartIndex] = useState(0);
  const [currentSlideIdx, setCurrentSlideIdx] = useState(0);
  const [viewMode, setViewMode] = useState('carousel');
  const [deckTitle, setDeckTitle] = useState('');

  const syncedRef = useRef(null);

  useEffect(() => {
    if (!slides.length) { setCurrentSlideIdx(0); return; }
    setCurrentSlideIdx((prev) => Math.max(0, Math.min(prev, slides.length - 1)));
  }, [slides.length]);

  const syncFromServer = useCallback(async (id, silent = false) => {
    if (!id) return;
    try {
      const payload = await getPresentation(id);
      setPresentationData(payload);
      if (payload?.data?.title) setDeckTitle(payload.data.title);
      if (payload?.video) setVideoData(payload.video);
      onSaved?.();
    } catch (err) {
      if (!silent) toast.error(err.message || 'Failed to refresh presentation');
    }
  }, [onSaved, setPresentationData, setVideoData, toast]);

  const handleGenerate = useCallback(async () => {
    if (!currentNotebook?.id || selectedSources.length === 0) return;
    reset();
    setPhase('planning');
    setLoadingState('presentation', true);
    try {
      const started = await generatePresentation(
        currentNotebook.id,
        selectedSources,
        topic.trim() || null,
      );
      if (started?.id) setPresentationId(started.id);
    } catch (err) {
      setError(err.message || 'Failed to start presentation generation');
      toast.error(err.message || 'Failed to generate presentation');
      setLoadingState('presentation', false);
    }
  }, [currentNotebook?.id, selectedSources, topic, reset, setPhase, setLoadingState, setError, setPresentationId, toast]);

  useEffect(() => {
    if (!presentationId) return;
    if (syncedRef.current === presentationId) return;
    syncedRef.current = presentationId;
    syncFromServer(presentationId, true);
  }, [presentationId, syncFromServer]);

  useEffect(() => {
    if (!presentationId) return;
    if (phase === 'done') syncFromServer(presentationId, true);
  }, [phase, presentationId, syncFromServer]);

  useEffect(() => {
    if (phase === 'done' || phase === 'error' || phase === 'idle') {
      setLoadingState('presentation', false);
    }
  }, [phase, setLoadingState]);

  const handleRegenerate = useCallback(async (slideIndex) => {
    if (!presentationId || regeneratingIdx !== null) return;
    setRegeneratingIdx(slideIndex);
    try {
      await regenerateSlide(presentationId, slideIndex);
      toast.success(`Slide ${slideIndex + 1} regenerated`);
      await syncFromServer(presentationId, true);
    } catch (err) {
      toast.error(err.message || 'Failed to regenerate slide');
    } finally {
      setRegeneratingIdx(null);
    }
  }, [presentationId, regeneratingIdx, toast, syncFromServer]);

  const completedSlides = slides.filter((s) => s.status === 'completed');
  const activeSlide = slides[currentSlideIdx] || null;
  const activeImageUrl = resolveUrl(activeSlide?.imageUrl);

  const startPresent = useCallback((idx = 0) => {
    if (completedSlides.length === 0) return;
    // Map grid/carousel index to completedSlides index
    const target = slides[idx];
    const compIdx = completedSlides.findIndex(s => s.index === (target?.index ?? idx));
    setPresentStartIndex(Math.max(0, compIdx));
    setPresentMode(true);
  }, [completedSlides, slides]);

  // ── RENDER ─────────────────────────────────────────────────────────────────

  // Present Mode — overlays everything
  if (presentMode && completedSlides.length > 0) {
    return (
      <PresentMode
        slides={completedSlides}
        initialIndex={presentStartIndex}
        onExit={() => setPresentMode(false)}
        themeSpec={themeSpec}
      />
    );
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-4" id="presentation-generator-panel">

      {/* ── IDLE ── */}
      {phase === 'idle' && (
        <div className="space-y-4 animate-fade-in">
          <div className="text-center py-6">
            <div className="w-14 h-14 mx-auto rounded-2xl bg-gradient-to-br from-[var(--accent-subtle)] to-[var(--surface-overlay)] flex items-center justify-center mb-4 border border-[var(--border)]">
              <Presentation className="w-7 h-7 text-[var(--accent)]" />
            </div>
            <h3 className="text-[15px] font-bold text-[var(--text-primary)] mb-1">Slide Deck Generator</h3>
            <p className="text-[12px] text-[var(--text-muted)] max-w-[260px] mx-auto leading-relaxed">
              Generate a 16:9 AI slide deck from your sources. Present it, or download as PPTX / PDF.
            </p>
          </div>

          <div className="space-y-1.5">
            <label className="text-[11px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
              Focus topic <span className="normal-case font-normal text-[var(--text-muted)]">(optional)</span>
            </label>
            <input
              type="text"
              id="presentation-topic-input"
              value={topic}
              onChange={(e) => setTopic(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter') handleGenerate(); }}
              placeholder="e.g., Cloud Security Fundamentals"
              className="w-full px-3 py-2.5 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] text-[13px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] transition-colors"
            />
          </div>

          <button
            id="presentation-generate-btn"
            onClick={handleGenerate}
            disabled={selectedSources.length === 0}
            className="w-full py-3 px-4 rounded-xl font-semibold text-[13px] text-white flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg"
            style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-light, var(--accent)))' }}
          >
            <Sparkles className="w-4 h-4" />
            Generate Presentation
          </button>

          {selectedSources.length === 0 && (
            <p className="text-[11px] text-[var(--text-muted)] text-center">
              Select at least one source to continue.
            </p>
          )}
        </div>
      )}

      {/* ── PLANNING ── */}
      {phase === 'planning' && (
        <div className="flex flex-col items-center justify-center py-12 animate-fade-in">
          <div className="relative mb-6">
            <div className="loading-spinner w-12 h-12 text-[var(--accent)]" />
            <div className="absolute inset-0 bg-[var(--accent-subtle)] blur-2xl rounded-full -z-10" />
          </div>
          <p className="text-[14px] font-semibold text-[var(--text-primary)] mb-1">Planning your deck...</p>
          <p className="text-[12px] text-[var(--text-muted)] animate-pulse text-center max-w-[220px]">
            Building slide structure and generating a unique color theme
          </p>
        </div>
      )}

      {/* ── GENERATING / DONE ── */}
      {(phase === 'generating' || phase === 'done') && (
        <div className="space-y-3 animate-fade-in">

          {/* Progress */}
          {phase === 'generating' && <ProgressBar progress={progress} />}

          {/* Done banner + export buttons */}
          {phase === 'done' && (
            <div className="flex items-center gap-2 p-3 rounded-xl bg-[var(--accent-subtle)] border border-[var(--accent-border,var(--accent))]">
              <Check className="w-4 h-4 text-[var(--accent)] shrink-0" />
              <span className="text-[12px] font-medium text-[var(--text-primary)] flex-1">
                {progress.slidesCompleted} slides generated
              </span>
              <ExportButtons presentationId={presentationId} title={deckTitle} />
            </div>
          )}

          {/* Theme strip */}
          {themeSpec && <ThemeStrip themeSpec={themeSpec} />}

          {/* Toolbar */}
          {slides.length > 0 && (
            <div className="flex items-center gap-1.5">
              {/* Present button — the main action */}
              <button
                id="present-mode-btn"
                onClick={() => startPresent(currentSlideIdx)}
                disabled={completedSlides.length === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-semibold text-white border border-transparent transition-all disabled:opacity-40"
                style={{ background: 'var(--accent)' }}
                title="Present fullscreen (F11 style)"
              >
                <Play className="w-3.5 h-3.5" />
                Present
              </button>

              <div className="w-px h-4 bg-[var(--border)]" />

              <button
                onClick={() => setViewMode('carousel')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all ${
                  viewMode === 'carousel'
                    ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)]'
                    : 'border-[var(--border)] text-[var(--text-muted)]'
                }`}
              >
                <Monitor className="w-3.5 h-3.5" />
                Carousel
              </button>
              <button
                onClick={() => setViewMode('grid')}
                className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium border transition-all ${
                  viewMode === 'grid'
                    ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)]'
                    : 'border-[var(--border)] text-[var(--text-muted)]'
                }`}
              >
                <LayoutGrid className="w-3.5 h-3.5" />
                All Slides
              </button>

              <span className="ml-auto text-[10px] text-[var(--text-muted)] tabular-nums">
                {completedSlides.length}/{slides.length}
              </span>
            </div>
          )}

          {/* ── GRID VIEW ── */}
          {viewMode === 'grid' && (
            <SlideGrid
              slides={slides}
              onPresent={startPresent}
              onRegenerate={handleRegenerate}
              regeneratingIdx={regeneratingIdx}
            />
          )}

          {/* ── CAROUSEL VIEW ── */}
          {viewMode === 'carousel' && (
            <>
              <div className="rounded-2xl border border-[var(--border)] bg-[var(--surface-raised)] p-3">
                {/* Header */}
                <div className="flex items-center justify-between gap-2 mb-2">
                  <span className="text-[12px] font-semibold text-[var(--text-primary)]">
                    Slide {Math.min(currentSlideIdx + 1, Math.max(slides.length, 1))} / {slides.length || 0}
                  </span>
                  <div className="flex items-center gap-1.5">
                    {activeSlide?.status === 'completed' && (
                      <button
                        onClick={() => startPresent(currentSlideIdx)}
                        className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] font-medium text-white border-none transition-colors"
                        style={{ background: 'var(--accent)' }}
                        title="Present from this slide"
                      >
                        <Play className="w-3 h-3" /> Present
                      </button>
                    )}
                    {activeImageUrl && (
                      <a
                        href={activeImageUrl}
                        download={`slide_${currentSlideIdx + 1}.png`}
                        className="p-1.5 rounded-md border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--accent)] hover:border-[var(--accent-border)] transition-colors"
                        title="Download this slide as PNG"
                      >
                        <Download className="w-3.5 h-3.5" />
                      </a>
                    )}
                    {activeSlide && (
                      <button
                        onClick={() => handleRegenerate(activeSlide.index)}
                        disabled={regeneratingIdx === activeSlide.index}
                        className="p-1.5 rounded-md border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--accent)] hover:border-[var(--accent-border)] transition-colors disabled:opacity-50"
                        title="Regenerate slide"
                      >
                        <RefreshCw className={`w-3.5 h-3.5 ${regeneratingIdx === activeSlide.index ? 'animate-spin' : ''}`} />
                      </button>
                    )}
                  </div>
                </div>

                {/* Slide image — strict 16:9 */}
                <div
                  className={`${SLIDE_ASPECT} rounded-xl overflow-hidden border border-[var(--border)] bg-[var(--surface-overlay)] cursor-pointer`}
                  onClick={() => activeSlide?.status === 'completed' && startPresent(currentSlideIdx)}
                  title="Click to present"
                >
                  {!activeSlide && (
                    <div className="w-full h-full"><SlideSkeleton index={0} /></div>
                  )}
                  {activeSlide?.status === 'pending' && (
                    <div className="w-full h-full"><SlideSkeleton index={activeSlide.index} /></div>
                  )}
                  {activeSlide?.status === 'failed' && (
                    <div className="w-full h-full flex flex-col items-center justify-center gap-2 p-4 bg-[var(--danger-subtle)]">
                      <AlertTriangle className="w-6 h-6 text-[var(--danger)]" />
                      <p className="text-[11px] text-[var(--danger)]">Failed to generate</p>
                    </div>
                  )}
                  {activeSlide?.status === 'completed' && activeImageUrl && (
                    <div className="relative w-full h-full group">
                      <img
                        src={activeImageUrl}
                        alt={activeSlide.title || `Slide ${activeSlide.index + 1}`}
                        className="w-full h-full object-contain bg-black"
                        style={{ aspectRatio: '16/9' }}
                      />
                      {/* Play overlay */}
                      <div className="absolute inset-0 flex items-center justify-center opacity-0 group-hover:opacity-100 transition-opacity bg-black/20">
                        <div className="p-3 rounded-full bg-black/40 backdrop-blur-sm">
                          <Play className="w-6 h-6 text-white" />
                        </div>
                      </div>
                    </div>
                  )}
                </div>

                {/* Bullet preview */}
                {activeSlide?.status === 'completed' && (
                  <div className="mt-2 px-1">
                    <p className="text-[12px] font-semibold text-[var(--text-primary)] truncate">
                      {activeSlide.title}
                    </p>
                    {activeSlide.bullets?.length > 0 && (
                      <ul className="mt-1 space-y-0.5">
                        {activeSlide.bullets.slice(0, 3).map((b, i) => (
                          <li key={i} className="text-[11px] text-[var(--text-muted)] flex items-start gap-1">
                            <span className="text-[var(--accent)] shrink-0">•</span>
                            <span className="truncate">{b}</span>
                          </li>
                        ))}
                        {activeSlide.bullets.length > 3 && (
                          <li className="text-[10px] text-[var(--text-muted)]/60 italic">
                            +{activeSlide.bullets.length - 3} more
                          </li>
                        )}
                      </ul>
                    )}
                  </div>
                )}

                {/* Prev/Next */}
                <div className="mt-3 flex items-center justify-between gap-2">
                  <button
                    onClick={() => setCurrentSlideIdx((i) => Math.max(0, i - 1))}
                    disabled={currentSlideIdx === 0}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[var(--border)] text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-40"
                  >
                    <ChevronLeft className="w-3.5 h-3.5" /> Prev
                  </button>
                  <span className="text-[10px] text-[var(--text-muted)] tabular-nums">
                    {currentSlideIdx + 1} / {slides.length}
                  </span>
                  <button
                    onClick={() => setCurrentSlideIdx((i) => Math.min(slides.length - 1, i + 1))}
                    disabled={!slides.length || currentSlideIdx >= slides.length - 1}
                    className="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg border border-[var(--border)] text-[11px] text-[var(--text-secondary)] hover:text-[var(--text-primary)] disabled:opacity-40"
                  >
                    Next <ChevronRight className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Thumbnail strip */}
              <div className="flex gap-2 overflow-x-auto pb-1">
                {slides.map((slide, idx) => {
                  const thumb = resolveUrl(slide.imageUrl);
                  const isActive = idx === currentSlideIdx;
                  return (
                    <button
                      key={slide.index}
                      onClick={() => setCurrentSlideIdx(idx)}
                      className={`shrink-0 w-20 rounded-lg border overflow-hidden transition-all ${
                        isActive
                          ? 'border-[var(--accent)] shadow-md ring-1 ring-[var(--accent)]/30'
                          : 'border-[var(--border)] hover:border-[var(--accent-border,var(--accent))]'
                      }`}
                      title={slide.title || `Slide ${slide.index + 1}`}
                    >
                      <div className={SLIDE_ASPECT + ' bg-[var(--surface-overlay)]'}>
                        {slide.status === 'completed' && thumb ? (
                          <img src={thumb} alt={slide.title || `Slide ${slide.index + 1}`} className="w-full h-full object-cover" />
                        ) : (
                          <div className="w-full h-full flex items-center justify-center text-[9px] text-[var(--text-muted)] font-mono">
                            {slide.status === 'failed' ? '✕' : slide.index + 1}
                          </div>
                        )}
                      </div>
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      )}

      {/* ── ERROR ── */}
      {phase === 'error' && (
        <div className="flex flex-col items-center justify-center py-12 animate-fade-in">
          <div className="w-14 h-14 rounded-2xl bg-[var(--danger-subtle)] flex items-center justify-center mb-4 border border-[var(--danger-border)]">
            <AlertTriangle className="w-7 h-7 text-[var(--danger)]" />
          </div>
          <p className="text-[14px] font-semibold text-[var(--text-primary)] mb-1">Generation Failed</p>
          <p className="text-[12px] text-[var(--danger)] text-center max-w-[260px] mb-4">
            {error || 'Something went wrong. Please try again.'}
          </p>
          <button
            onClick={handleGenerate}
            className="px-4 py-2 rounded-xl text-[12px] font-medium bg-[var(--accent)] text-white hover:opacity-90 transition-opacity flex items-center gap-1.5"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Try Again
          </button>
        </div>
      )}
    </div>
  );
}

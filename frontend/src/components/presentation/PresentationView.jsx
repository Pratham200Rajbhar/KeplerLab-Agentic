'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  ChevronLeft, ChevronRight, Maximize2, Minimize2, Download, Grid,
  X
} from 'lucide-react';
import Modal from '@/components/ui/Modal';
import './PresentationView.css';

/* ─────────────────── Slide Scale Hook ─────────────────── */
function useSlideScale(containerRef) {
  const [scale, setScale] = useState(1);

  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const update = () => {
      const containerWidth = el.clientWidth;
      // Standard slide width is 960px
      const s = Math.min(containerWidth / 960, 1);
      setScale(s);
    };

    const observer = new ResizeObserver(update);
    observer.observe(el);
    update();

    return () => observer.disconnect();
  }, [containerRef]);

  return scale;
}

/* ─────────────────── Inline Presentation View ─────────────────── */
export default function InlinePresentationView({ presentation, onClose }) {
  const slides = presentation?.slides || presentation?.data?.slides || [];
  const [currentSlide, setCurrentSlide] = useState(0);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showOverview, setShowOverview] = useState(false);
  const containerRef = useRef(null);
  const scale = useSlideScale(containerRef);

  const goNext = useCallback(() => {
    setCurrentSlide((i) => Math.min(i + 1, slides.length - 1));
  }, [slides.length]);

  const goPrev = useCallback(() => {
    setCurrentSlide((i) => Math.max(i - 1, 0));
  }, []);

  // Keyboard navigation
  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'ArrowRight' || e.key === 'ArrowDown') goNext();
      else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') goPrev();
      else if (e.key === 'Escape') {
        if (isFullscreen) setIsFullscreen(false);
        else if (showOverview) setShowOverview(false);
      }
    };
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [goNext, goPrev, isFullscreen, showOverview]);

  const toggleFullscreen = () => {
    if (!document.fullscreenElement) {
      containerRef.current?.requestFullscreen?.();
      setIsFullscreen(true);
    } else {
      document.exitFullscreen?.();
      setIsFullscreen(false);
    }
  };

  useEffect(() => {
    const handler = () => setIsFullscreen(!!document.fullscreenElement);
    document.addEventListener('fullscreenchange', handler);
    return () => document.removeEventListener('fullscreenchange', handler);
  }, []);

  const handleDownload = () => {
    if (presentation?.data?.download_url || presentation?.download_url) {
      const url = presentation?.data?.download_url || presentation?.download_url;
      const a = document.createElement('a');
      a.href = url;
      a.download = 'presentation.pptx';
      a.click();
    }
  };

  if (!slides.length) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-sm text-[var(--text-muted)]">No slides available</p>
      </div>
    );
  }

  const slide = slides[currentSlide];

  return (
    <div ref={containerRef} className={`presentation-viewer ${isFullscreen ? 'fixed inset-0 z-50 bg-black' : ''}`}>
      {/* Controls bar */}
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setShowOverview(!showOverview)}
            className={`p-1.5 rounded-lg transition-colors ${
              showOverview ? 'bg-[var(--accent)] text-[var(--accent)]' : 'text-[var(--text-muted)] hover:bg-[var(--surface-overlay)]'
            }`}
          >
            <Grid className="w-4 h-4" />
          </button>
          <span className="text-xs text-[var(--text-muted)] tabular-nums">
            {currentSlide + 1} / {slides.length}
          </span>
        </div>
        <div className="flex items-center gap-1">
          {(presentation?.data?.download_url || presentation?.download_url) && (
            <button onClick={handleDownload} className="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors">
              <Download className="w-4 h-4" />
            </button>
          )}
          <button onClick={toggleFullscreen} className="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors">
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* Overview grid */}
      {showOverview ? (
        <div className="grid grid-cols-3 gap-2 max-h-[60vh] overflow-y-auto animate-fade-in">
          {slides.map((s, i) => (
            <button
              key={i}
              onClick={() => { setCurrentSlide(i); setShowOverview(false); }}
              className={`relative rounded-lg border overflow-hidden transition-all aspect-video ${
                i === currentSlide
                  ? 'border-[var(--accent)] ring-1 ring-[var(--accent)]'
                  : 'border-[var(--border)] hover:border-[var(--text-muted)]'
              }`}
            >
              {s.html ? (
                <div
                  className="w-full h-full p-2 text-[4px] leading-tight overflow-hidden bg-white text-gray-800"
                  // Safe: HTML is system-generated slide content from backend, not user input
                  dangerouslySetInnerHTML={{ __html: s.html }}
                />
              ) : (
                <div className="w-full h-full flex items-center justify-center bg-[var(--surface)] text-[var(--text-muted)] text-[10px]">
                  Slide {i + 1}
                </div>
              )}
              <span className="absolute bottom-1 right-1 text-[8px] bg-black/50 text-white px-1 rounded">{i + 1}</span>
            </button>
          ))}
        </div>
      ) : (
        <>
          {/* Main slide */}
          <div className="relative rounded-xl border border-[var(--border)] overflow-hidden bg-white aspect-video">
            {slide.html ? (
              <iframe
                srcDoc={`<!DOCTYPE html><html><head><style>body{margin:0;padding:24px;font-family:system-ui,-apple-system,sans-serif;color:#1a1a2e;overflow:hidden;}</style></head><body>${slide.html}</body></html>`}
                className="w-full h-full border-none"
                sandbox="allow-same-origin"
                title={`Slide ${currentSlide + 1}`}
              />
            ) : (
              <div className="flex items-center justify-center h-full text-[var(--text-muted)]">
                <p className="text-sm">Slide {currentSlide + 1}</p>
              </div>
            )}
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between mt-3">
            <button
              onClick={goPrev}
              disabled={currentSlide === 0}
              className="p-2 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-30"
            >
              <ChevronLeft className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>

            {/* Progress dots */}
            <div className="flex items-center gap-1 max-w-[60%] overflow-hidden">
              {slides.length <= 20
                ? slides.map((_, i) => (
                    <button
                      key={i}
                      onClick={() => setCurrentSlide(i)}
                      className={`w-1.5 h-1.5 rounded-full transition-all ${
                        i === currentSlide ? 'bg-[var(--accent)] scale-125' : 'bg-[var(--border)]'
                      }`}
                    />
                  ))
                : (
                  <div className="flex-1 h-1 rounded-full bg-[var(--surface)] overflow-hidden">
                    <div
                      className="h-full bg-[var(--accent)] rounded-full transition-all"
                      style={{ width: `${((currentSlide + 1) / slides.length) * 100}%` }}
                    />
                  </div>
                )}
            </div>

            <button
              onClick={goNext}
              disabled={currentSlide === slides.length - 1}
              className="p-2 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-30"
            >
              <ChevronRight className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}

/* ─────────────────── Presentation Config Dialog ─────────────────── */
export function PresentationConfigDialog({ onConfirm, onClose }) {
  const [maxSlides, setMaxSlides] = useState(10);
  const [theme, setTheme] = useState('modern');
  const [instructions, setInstructions] = useState('');

  const themes = [
    { id: 'modern', label: 'Modern', desc: 'Clean & minimal' },
    { id: 'academic', label: 'Academic', desc: 'Formal & structured' },
    { id: 'creative', label: 'Creative', desc: 'Bold & visual' },
  ];

  const handleSubmit = (e) => {
    e.preventDefault();
    onConfirm({ maxSlides, theme, additionalInstructions: instructions });
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h3 className="text-base font-semibold text-[var(--text-primary)]">Presentation Settings</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors">
            <X className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Slide count */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Max Slides</label>
            <div className="flex items-center gap-3">
              <input
                type="range"
                min={5}
                max={30}
                value={maxSlides}
                onChange={(e) => setMaxSlides(Number(e.target.value))}
                className="flex-1 accent-(--accent)"
              />
              <span className="text-sm font-medium text-[var(--text-primary)] w-8 text-center">{maxSlides}</span>
            </div>
          </div>

          {/* Theme */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Theme</label>
            <div className="grid grid-cols-3 gap-2">
              {themes.map((t) => (
                <button
                  key={t.id}
                  type="button"
                  onClick={() => setTheme(t.id)}
                  className={`text-left p-2.5 rounded-lg border transition-all ${
                    theme === t.id
                      ? 'border-[var(--accent)] bg-[var(--accent)]'
                      : 'border-[var(--border)] hover:border-[var(--text-muted)]'
                  }`}
                >
                  <span className="text-xs font-medium text-[var(--text-primary)] block">{t.label}</span>
                  <span className="text-[10px] text-[var(--text-muted)]">{t.desc}</span>
                </button>
              ))}
            </div>
          </div>

          {/* Instructions */}
          <div>
            <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
              Additional Instructions <span className="text-[var(--text-muted)]">(optional)</span>
            </label>
            <textarea
              value={instructions}
              onChange={(e) => setInstructions(e.target.value)}
              placeholder="Any specific requirements..."
              rows={2}
              className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] resize-none"
            />
          </div>
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[var(--border)]">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[var(--text-secondary)]">Cancel</button>
          <button type="submit" className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors">
            Generate Slides
          </button>
        </div>
      </form>
    </Modal>
  );
}

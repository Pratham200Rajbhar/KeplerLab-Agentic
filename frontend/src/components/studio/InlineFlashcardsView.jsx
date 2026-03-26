'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { ChevronLeft, ChevronRight, RotateCw, Download, List, Grid, Keyboard } from 'lucide-react';

export default function InlineFlashcardsView({ flashcards, onClose }) {
  const cards = useMemo(() => flashcards?.flashcards || flashcards?.cards || (Array.isArray(flashcards) ? flashcards : []), [flashcards]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [viewMode, setViewMode] = useState('card');
  const containerRef = useRef(null);

  const card = cards[currentIndex];

  const goNext = useCallback(() => {
    if (currentIndex < cards.length - 1) {
      setCurrentIndex((i) => i + 1);
      setFlipped(false);
    }
  }, [currentIndex, cards.length]);

  const goPrev = useCallback(() => {
    if (currentIndex > 0) {
      setCurrentIndex((i) => i - 1);
      setFlipped(false);
    }
  }, [currentIndex]);

  useEffect(() => {
    const handler = (e) => {
      if (e.key === 'ArrowRight' || e.key === 'n') goNext();
      else if (e.key === 'ArrowLeft' || e.key === 'p') goPrev();
      else if (e.key === ' ' || e.key === 'f') {
        e.preventDefault();
        setFlipped((f) => !f);
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [goNext, goPrev]);

  const handleExportPDF = async () => {
    try {
      const { jsPDF } = await import('jspdf');
      const doc = new jsPDF('p', 'mm', 'a4');
      const pageWidth = doc.internal.pageSize.getWidth();

      doc.setFontSize(16);
      doc.text('Flashcards', pageWidth / 2, 15, { align: 'center' });

      let y = 30;
      cards.forEach((c, i) => {
        if (y > 260) {
          doc.addPage();
          y = 20;
        }
        doc.setFontSize(11);
        doc.setFont(undefined, 'bold');
        doc.text(`${i + 1}. ${c.front || c.question || ''}`, 15, y, { maxWidth: pageWidth - 30 });
        y += 8;
        doc.setFont(undefined, 'normal');
        doc.setFontSize(10);
        const answer = c.back || c.answer || '';
        const lines = doc.splitTextToSize(answer, pageWidth - 30);
        doc.text(lines, 15, y);
        y += lines.length * 5 + 10;
      });

      doc.save('flashcards.pdf');
    } catch (err) {
      console.error('PDF export failed:', err);
    }
  };

  if (!cards.length) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-sm text-[var(--text-muted)]">No flashcards available</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-4 animate-fade-in">
      <div
        className="relative overflow-hidden rounded-2xl border border-[var(--border)] px-3 py-3 sm:px-4"
        style={{
          background:
            'radial-gradient(circle at top right, var(--accent-subtle), transparent 40%), linear-gradient(180deg, var(--surface-raised), var(--surface))',
        }}
      >
        <div className="absolute inset-0 pointer-events-none" style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }} />

        <div className="relative z-10 flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] p-1">
            <button
              onClick={() => setViewMode('card')}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${viewMode === 'card' ? 'bg-[var(--accent)] text-white shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              aria-label="Card view"
            >
              <Grid className="h-3.5 w-3.5" />
              Cards
            </button>
            <button
              onClick={() => setViewMode('list')}
              className={`flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs font-medium transition-colors ${viewMode === 'list' ? 'bg-[var(--accent)] text-white shadow-sm' : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'}`}
              aria-label="List view"
            >
              <List className="h-3.5 w-3.5" />
              List
            </button>
          </div>

          <button
            onClick={handleExportPDF}
            className="flex items-center gap-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] px-3 py-1.5 text-xs font-medium text-[var(--text-secondary)] transition-all hover:border-[var(--accent-border)] hover:text-[var(--text-primary)]"
          >
            <Download className="h-3.5 w-3.5" /> Export PDF
          </button>
        </div>

        <div className="relative z-10 mt-3 space-y-1.5">
          <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)]">
            <span>Card progress</span>
            <span className="font-medium text-[var(--text-secondary)]">{currentIndex + 1} / {cards.length}</span>
          </div>
          <div className="h-1.5 w-full overflow-hidden rounded-full bg-[var(--surface-overlay)]">
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
              style={{ width: `${((currentIndex + 1) / cards.length) * 100}%` }}
            />
          </div>
        </div>
      </div>

      {viewMode === 'card' ? (
        <>
          <div
            onClick={() => setFlipped(!flipped)}
            className="group relative h-[280px] cursor-pointer select-none rounded-2xl border border-[var(--border)] transition-all duration-300 hover:-translate-y-0.5 hover:border-[var(--accent-border)] sm:h-[320px]"
            style={{
              perspective: '1200px',
              background: 'linear-gradient(145deg, var(--surface-raised) 0%, var(--surface) 100%)',
              boxShadow: 'var(--shadow-card, 0 10px 30px rgba(0,0,0,0.2))',
            }}
          >
            <div
              className="relative h-full w-full transition-transform duration-500"
              style={{ transformStyle: 'preserve-3d', transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
            >
              <div
                className="absolute inset-0 flex flex-col justify-between rounded-2xl p-6 sm:p-8"
                style={{ backfaceVisibility: 'hidden' }}
              >
                <span className="inline-flex w-fit rounded-full border border-[var(--border)] bg-[var(--surface-overlay)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--text-muted)]">
                  Question
                </span>
                <p className="text-center text-base leading-relaxed text-[var(--text-primary)] sm:text-lg">
                  {card.front || card.question}
                </p>
                <div className="flex items-center justify-between text-[11px] text-[var(--text-muted)]">
                  <span>Tap to reveal answer</span>
                  <RotateCw className="h-3.5 w-3.5 transition-transform duration-300 group-hover:rotate-180" />
                </div>
              </div>

              <div
                className="absolute inset-0 flex flex-col justify-between rounded-2xl p-6 sm:p-8"
                style={{
                  backfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  background: 'linear-gradient(135deg, var(--accent-subtle), var(--surface))',
                  border: '1px solid var(--accent-border)',
                }}
              >
                <span className="inline-flex w-fit rounded-full border border-[var(--accent-border)] bg-[var(--surface)] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.22em] text-[var(--accent)]">
                  Answer
                </span>
                <p className="text-center text-base leading-relaxed text-[var(--text-primary)] sm:text-lg">
                  {card.back || card.answer}
                </p>
                <div className="text-right text-[11px] text-[var(--text-secondary)]">Tap to see question</div>
              </div>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] px-2 py-1.5">
            <button
              onClick={goPrev}
              disabled={currentIndex === 0}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-overlay)] disabled:cursor-not-allowed disabled:opacity-35"
              aria-label="Previous flashcard"
            >
              <ChevronLeft className="h-4 w-4" /> Prev
            </button>
            <span className="text-xs font-medium text-[var(--text-secondary)]">
              {currentIndex + 1} / {cards.length}
            </span>
            <button
              onClick={goNext}
              disabled={currentIndex === cards.length - 1}
              className="flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-xs text-[var(--text-secondary)] transition-colors hover:bg-[var(--surface-overlay)] disabled:cursor-not-allowed disabled:opacity-35"
              aria-label="Next flashcard"
            >
              Next <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          <p className="flex items-center justify-center gap-1.5 text-center text-[11px] text-[var(--text-muted)]">
            <Keyboard className="h-3.5 w-3.5" /> Press <span className="rounded border border-[var(--border)] px-1.5 py-0.5">Space</span> to flip, <span className="rounded border border-[var(--border)] px-1.5 py-0.5">Arrow keys</span> to navigate
          </p>
        </>
      ) : (
        <div className="max-h-[60vh] space-y-3 overflow-y-auto pr-1">
          <div className="sticky top-0 z-10 flex items-center justify-between rounded-lg border border-[var(--border)] bg-[var(--surface)]/95 px-3 py-2 backdrop-blur">
            <span className="text-[11px] font-medium tracking-[0.12em] text-[var(--text-muted)] uppercase">Flashcard List</span>
            <span className="text-xs text-[var(--text-secondary)]">{cards.length} cards</span>
          </div>

          {cards.map((c, i) => (
            <div
              key={c.id || c.front || c.question || i}
              className="rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] p-4 transition-all duration-200 hover:-translate-y-0.5 hover:border-[var(--accent-border)]"
            >
              <div className="mb-3 flex items-center justify-between gap-2">
                <div className="flex items-center gap-2">
                  <span className="inline-flex h-6 min-w-6 items-center justify-center rounded-full bg-[var(--accent-subtle)] px-2 text-[10px] font-semibold text-[var(--accent)]">
                    {i + 1}
                  </span>
                  <span className="text-[10px] uppercase tracking-[0.16em] text-[var(--text-muted)]">Question</span>
                </div>
                <button
                  onClick={() => {
                    setCurrentIndex(i);
                    setFlipped(false);
                    setViewMode('card');
                  }}
                  className="rounded-md border border-[var(--border)] px-2 py-1 text-[10px] font-medium uppercase tracking-[0.08em] text-[var(--text-secondary)] transition-colors hover:border-[var(--accent-border)] hover:text-[var(--text-primary)]"
                >
                  Open Card
                </button>
              </div>

              <div className="rounded-lg border border-[var(--border-light)] bg-[var(--surface)] px-3 py-2.5">
                <p className="text-sm font-medium leading-relaxed text-[var(--text-primary)]">{c.front || c.question}</p>
              </div>

              <div className="mb-2 mt-3 text-[10px] uppercase tracking-[0.16em] text-[var(--accent)]">Answer</div>
              <div className="rounded-lg border border-[var(--accent-border)] bg-[var(--accent-subtle)] px-3 py-2.5">
                <p className="text-sm leading-relaxed text-[var(--text-secondary)]">{c.back || c.answer}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

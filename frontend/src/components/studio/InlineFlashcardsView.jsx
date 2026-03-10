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
      {}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <button
            onClick={() => setViewMode('card')}
            className={`p-1.5 rounded-lg transition-colors ${viewMode === 'card' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-muted)] hover:bg-[var(--surface-overlay)]'}`}
            aria-label="Card view"
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-[var(--accent)] text-white' : 'text-[var(--text-muted)] hover:bg-[var(--surface-overlay)]'}`}
            aria-label="List view"
          >
            <List className="w-4 h-4" />
          </button>
        </div>
        <button
          onClick={handleExportPDF}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors border border-[var(--border)]"
        >
          <Download className="w-3.5 h-3.5" /> Export PDF
        </button>
      </div>

      {viewMode === 'card' ? (
        <>
          {}
          <div
            onClick={() => setFlipped(!flipped)}
            className="relative h-52 rounded-xl border border-[var(--border)] bg-[var(--surface)] cursor-pointer select-none hover:border-[var(--accent)] transition-colors"
            style={{ perspective: '1200px' }}
          >
            <div
              className="w-full h-full transition-transform duration-500 relative"
              style={{ transformStyle: 'preserve-3d', transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
            >
              {}
              <div
                className="absolute inset-0 p-6 flex flex-col items-center justify-center text-center rounded-xl bg-[var(--surface)]"
                style={{ backfaceVisibility: 'hidden' }}
              >
                <span className="text-[10px] uppercase tracking-widest text-[var(--text-muted)] mb-3 block font-medium">Question</span>
                <p className="text-sm text-[var(--text-primary)] leading-relaxed">{card.front || card.question}</p>
                <div className="absolute bottom-3 right-3 opacity-30">
                  <RotateCw className="w-3.5 h-3.5 text-[var(--text-muted)]" />
                </div>
              </div>
              {}
              <div
                className="absolute inset-0 p-6 flex flex-col items-center justify-center text-center rounded-xl"
                style={{
                  backfaceVisibility: 'hidden',
                  transform: 'rotateY(180deg)',
                  background: 'linear-gradient(135deg, var(--accent-subtle), var(--surface))',
                  border: '1px solid var(--accent-border)',
                }}
              >
                <span className="text-[10px] uppercase tracking-widest text-[var(--accent)] mb-3 block font-medium">Answer</span>
                <p className="text-sm text-[var(--text-primary)] leading-relaxed">{card.back || card.answer}</p>
              </div>
            </div>
          </div>

          {}
          <div className="flex items-center justify-between">
            <button
              onClick={goPrev}
              disabled={currentIndex === 0}
              className="p-2 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-30"
              aria-label="Previous flashcard"
            >
              <ChevronLeft className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>
            <span className="text-xs text-[var(--text-muted)]">
              {currentIndex + 1} / {cards.length}
            </span>
            <button
              onClick={goNext}
              disabled={currentIndex === cards.length - 1}
              className="p-2 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-30"
              aria-label="Next flashcard"
            >
              <ChevronRight className="w-5 h-5 text-[var(--text-secondary)]" />
            </button>
          </div>

          {}
          <p className="text-[10px] text-[var(--text-muted)] text-center flex items-center justify-center gap-1">
            <Keyboard className="w-3 h-3" /> Space to flip, arrows to navigate
          </p>
        </>
      ) : (
        
        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {cards.map((c, i) => (
            <div key={c.id || c.front || c.question || i} className="p-3 rounded-lg border border-[var(--border)] bg-[var(--surface)]">
              <p className="text-xs font-medium text-[var(--text-primary)] mb-1.5">
                <span className="text-[var(--text-muted)] mr-1">{i + 1}.</span>
                {c.front || c.question}
              </p>
              <p className="text-xs text-[var(--text-secondary)] pl-4 border-l-2 border-[var(--accent)]">
                {c.back || c.answer}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

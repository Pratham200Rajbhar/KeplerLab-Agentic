'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { ChevronLeft, ChevronRight, RotateCw, Download, List, Grid, Keyboard } from 'lucide-react';

export default function InlineFlashcardsView({ flashcards, onClose }) {
  const cards = useMemo(() => flashcards?.cards || flashcards || [], [flashcards]);
  const [currentIndex, setCurrentIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [viewMode, setViewMode] = useState('card'); // card | list
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

  // Keyboard navigation
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
        <p className="text-sm text-(--text-muted)">No flashcards available</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setViewMode('card')}
            className={`p-1.5 rounded-lg transition-colors ${viewMode === 'card' ? 'bg-(--accent)/10 text-(--accent)' : 'text-(--text-muted) hover:bg-(--surface-overlay)'}`}
          >
            <Grid className="w-4 h-4" />
          </button>
          <button
            onClick={() => setViewMode('list')}
            className={`p-1.5 rounded-lg transition-colors ${viewMode === 'list' ? 'bg-(--accent)/10 text-(--accent)' : 'text-(--text-muted) hover:bg-(--surface-overlay)'}`}
          >
            <List className="w-4 h-4" />
          </button>
        </div>
        <button
          onClick={handleExportPDF}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-(--text-secondary) hover:bg-(--surface-overlay) transition-colors"
        >
          <Download className="w-3.5 h-3.5" /> PDF
        </button>
      </div>

      {viewMode === 'card' ? (
        <>
          {/* Card view */}
          <div
            onClick={() => setFlipped(!flipped)}
            className="relative min-h-[200px] rounded-xl border border-(--border) bg-(--surface) cursor-pointer select-none transition-all hover:border-(--accent)/30 overflow-hidden"
            style={{ perspective: '1000px' }}
          >
            <div
              className="w-full h-full p-6 flex flex-col items-center justify-center text-center transition-transform duration-500"
              style={{ transform: flipped ? 'rotateY(180deg)' : 'rotateY(0deg)' }}
            >
              {!flipped ? (
                <div>
                  <span className="text-[10px] uppercase tracking-wider text-(--text-muted) mb-3 block">Question</span>
                  <p className="text-sm text-(--text-primary) leading-relaxed">{card.front || card.question}</p>
                </div>
              ) : (
                <div style={{ transform: 'rotateY(180deg)' }}>
                  <span className="text-[10px] uppercase tracking-wider text-(--accent) mb-3 block">Answer</span>
                  <p className="text-sm text-(--text-primary) leading-relaxed">{card.back || card.answer}</p>
                </div>
              )}
            </div>

            <div className="absolute bottom-3 right-3">
              <RotateCw className="w-3.5 h-3.5 text-(--text-muted) opacity-40" />
            </div>
          </div>

          {/* Navigation */}
          <div className="flex items-center justify-between">
            <button
              onClick={goPrev}
              disabled={currentIndex === 0}
              className="p-2 rounded-lg hover:bg-(--surface-overlay) transition-colors disabled:opacity-30"
            >
              <ChevronLeft className="w-5 h-5 text-(--text-secondary)" />
            </button>
            <span className="text-xs text-(--text-muted)">
              {currentIndex + 1} / {cards.length}
            </span>
            <button
              onClick={goNext}
              disabled={currentIndex === cards.length - 1}
              className="p-2 rounded-lg hover:bg-(--surface-overlay) transition-colors disabled:opacity-30"
            >
              <ChevronRight className="w-5 h-5 text-(--text-secondary)" />
            </button>
          </div>

          {/* Keyboard hint */}
          <p className="text-[10px] text-(--text-muted) text-center flex items-center justify-center gap-1">
            <Keyboard className="w-3 h-3" /> Space to flip, arrows to navigate
          </p>
        </>
      ) : (
        /* List view */
        <div className="space-y-2 max-h-[60vh] overflow-y-auto">
          {cards.map((c, i) => (
            <div key={i} className="p-3 rounded-lg border border-(--border) bg-(--surface)">
              <p className="text-xs font-medium text-(--text-primary) mb-1.5">
                <span className="text-(--text-muted) mr-1">{i + 1}.</span>
                {c.front || c.question}
              </p>
              <p className="text-xs text-(--text-secondary) pl-4 border-l-2 border-(--accent)/30">
                {c.back || c.answer}
              </p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

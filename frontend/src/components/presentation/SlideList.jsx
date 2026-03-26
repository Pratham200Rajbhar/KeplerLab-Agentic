'use client';

export default function SlideList({ slides = [], activeIndex = 0, onSelect }) {
  return (
    <div className="h-full overflow-y-auto pr-2 space-y-2">
      {slides.map((slide, idx) => (
        <button
          key={`slide-${idx}`}
          onClick={() => onSelect(idx)}
          className={`w-full text-left p-3 rounded-lg border transition-colors ${
            idx === activeIndex
              ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
              : 'border-[var(--border)] hover:bg-[var(--surface-overlay)]'
          }`}
        >
          <p className="text-xs text-[var(--text-muted)]">Slide {idx + 1}</p>
          <p className="text-sm font-medium text-[var(--text-primary)] line-clamp-2">{slide.title || 'Untitled slide'}</p>
        </button>
      ))}
    </div>
  );
}

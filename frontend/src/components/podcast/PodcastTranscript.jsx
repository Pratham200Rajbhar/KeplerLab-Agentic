'use client';

import { useEffect, useRef } from 'react';

export default function PodcastTranscript({ segments = [], currentIndex, onSegmentClick }) {
  const activeRef = useRef(null);
  const containerRef = useRef(null);

  
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [currentIndex]);

  if (!segments.length) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-xs text-[var(--text-muted)]">No transcript available</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="podcast-list">
      {segments.map((seg, i) => {
        const isActive = i === currentIndex;
        return (
          <button
            key={seg.id || i}
            ref={isActive ? activeRef : null}
            onClick={() => onSegmentClick?.(i)}
            className={`podcast-card podcast-fade-in-item ${
              isActive
                ? 'active'
                : ''
            }`}
            style={{ animationDelay: `${Math.min(i * 16, 160)}ms` }}
          >
            <div className="flex items-start gap-2">
              <span className={`podcast-speaker-chip ${(seg.speaker === 'host' || seg.speaker === 'HOST') ? 'host' : 'guest'}`}>
                {seg.speaker || 'Speaker'}
              </span>

              <p className="text-xs leading-relaxed text-[var(--text-secondary)]">
                {seg.text}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

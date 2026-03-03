'use client';

import { useEffect, useRef } from 'react';

export default function PodcastTranscript({ segments = [], currentIndex, onSegmentClick }) {
  const activeRef = useRef(null);
  const containerRef = useRef(null);

  // Auto-scroll to current segment
  useEffect(() => {
    if (activeRef.current) {
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [currentIndex]);

  if (!segments.length) {
    return (
      <div className="px-4 py-8 text-center">
        <p className="text-xs text-(--text-muted)">No transcript available</p>
      </div>
    );
  }

  return (
    <div ref={containerRef} className="px-3 py-2 space-y-1">
      {segments.map((seg, i) => {
        const isActive = i === currentIndex;
        return (
          <button
            key={seg.id || i}
            ref={isActive ? activeRef : null}
            onClick={() => onSegmentClick?.(i)}
            className={`w-full text-left px-3 py-2.5 rounded-lg transition-all ${
              isActive
                ? 'bg-(--accent)/10 border border-(--accent)/20'
                : 'hover:bg-(--surface-overlay) border border-transparent'
            }`}
          >
            <div className="flex items-start gap-2">
              {/* Speaker badge */}
              <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded mt-0.5 shrink-0 ${
                seg.speaker === 'host'
                  ? 'bg-(--accent)/15 text-(--accent)'
                  : 'bg-purple-500/15 text-purple-400'
              }`}>
                {seg.speaker || 'Speaker'}
              </span>

              {/* Text */}
              <p className={`text-xs leading-relaxed ${
                isActive ? 'text-(--text-primary)' : 'text-(--text-secondary)'
              }`}>
                {seg.text}
              </p>
            </div>
          </button>
        );
      })}
    </div>
  );
}

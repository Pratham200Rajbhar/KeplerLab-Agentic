'use client';

import { BookOpen, Bookmark } from 'lucide-react';

export default function PodcastChapterBar({ chapters = [], currentSegmentIndex, bookmarks = [], onChapterClick }) {
  if (!chapters.length) {
    return (
      <div className="px-4 py-8 text-center">
        <BookOpen className="w-5 h-5 text-(--text-muted) mx-auto mb-2 opacity-40" />
        <p className="text-xs text-(--text-muted)">No chapters available</p>
      </div>
    );
  }

  const bookmarkSet = new Set(bookmarks.map((b) => b.segment_index));

  return (
    <div className="px-3 py-2 space-y-1">
      {chapters.map((ch, i) => {
        const isActive =
          currentSegmentIndex >= ch.startSegment &&
          (i === chapters.length - 1 || currentSegmentIndex < chapters[i + 1]?.startSegment);
        const hasBookmark = bookmarkSet.has(ch.startSegment);

        return (
          <button
            key={ch.id || i}
            onClick={() => onChapterClick?.(ch)}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-all ${
              isActive
                ? 'bg-(--accent)/10 border border-(--accent)/20'
                : 'hover:bg-(--surface-overlay) border border-transparent'
            }`}
          >
            {/* Chapter number */}
            <span className={`w-6 h-6 flex items-center justify-center rounded-full text-[10px] font-bold shrink-0 ${
              isActive
                ? 'bg-(--accent) text-white'
                : 'bg-(--surface) text-(--text-muted)'
            }`}>
              {i + 1}
            </span>

            <div className="flex-1 min-w-0">
              <p className={`text-xs font-medium truncate ${
                isActive ? 'text-(--text-primary)' : 'text-(--text-secondary)'
              }`}>
                {ch.title || `Chapter ${i + 1}`}
              </p>
              {ch.summary && (
                <p className="text-[10px] text-(--text-muted) truncate mt-0.5">{ch.summary}</p>
              )}
            </div>

            {hasBookmark && (
              <Bookmark className="w-3 h-3 text-(--accent) shrink-0" fill="currentColor" />
            )}
          </button>
        );
      })}
    </div>
  );
}

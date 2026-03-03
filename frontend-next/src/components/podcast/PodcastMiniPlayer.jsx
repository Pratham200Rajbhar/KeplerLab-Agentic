'use client';

import { Pause, Play, SkipForward } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';
import usePodcastPlayer from '@/hooks/usePodcastPlayer';

/**
 * Persistent mini player bar shown when a podcast is playing
 * and the user navigates away from the podcast view.
 */
export default function PodcastMiniPlayer({ onExpand }) {
  const session = usePodcastStore((s) => s.session);
  const segments = usePodcastStore((s) => s.segments);
  const currentSegmentIndex = usePodcastStore((s) => s.currentSegmentIndex);

  const { isPlaying, togglePlayPause, nextSegment } = usePodcastPlayer();

  if (!session || !segments.length) return null;

  const seg = segments[currentSegmentIndex];
  const totalDuration = segments.reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const elapsed = segments.slice(0, currentSegmentIndex).reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const pct = totalDuration > 0 ? (elapsed / totalDuration) * 100 : 0;

  return (
    <div className="border-t border-(--border) bg-(--surface-overlay) px-3 py-2">
      {/* Tiny progress */}
      <div className="h-0.5 rounded-full bg-(--surface) mb-1.5 overflow-hidden">
        <div className="h-full bg-(--accent) rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>

      <div className="flex items-center gap-2">
        {/* Play/Pause */}
        <button onClick={togglePlayPause} className="shrink-0">
          {isPlaying ? (
            <Pause className="w-5 h-5 text-(--accent)" fill="currentColor" />
          ) : (
            <Play className="w-5 h-5 text-(--accent)" fill="currentColor" />
          )}
        </button>

        {/* Info */}
        <div className="flex-1 min-w-0 cursor-pointer" onClick={onExpand}>
          <p className="text-[10px] font-medium text-(--text-primary) truncate">
            {session.title || 'Podcast'}
          </p>
          <p className="text-[9px] text-(--text-muted) truncate">
            {seg?.speaker}: {seg?.text?.slice(0, 40)}...
          </p>
        </div>

        {/* Next */}
        <button onClick={nextSegment} className="shrink-0">
          <SkipForward className="w-4 h-4 text-(--text-muted)" />
        </button>
      </div>
    </div>
  );
}

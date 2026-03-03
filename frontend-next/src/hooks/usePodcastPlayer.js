'use client';

import { useEffect, useRef, useCallback } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';

/**
 * Manages segment-level audio playback with lookahead prefetch,
 * speed control, and seek/skip helpers.
 * Reads from usePodcastStore instead of PodcastContext.
 */
export default function usePodcastPlayer() {
  const {
    session,
    segments,
    currentSegmentIndex,
    isPlaying,
    playbackSpeed,
    _audioEl,
    playSegment,
    prefetchSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    setCurrentSegmentIndex,
  } = usePodcastStore();

  // Prefetch cache: keep next 2 segments in browser cache
  const prefetchedRef = useRef(new Set());

  const prefetchAhead = useCallback(() => {
    if (!segments.length) return;
    for (let i = 1; i <= 2; i++) {
      const idx = currentSegmentIndex + i;
      if (idx < segments.length && !prefetchedRef.current.has(idx)) {
        prefetchedRef.current.add(idx);
        prefetchSegment(idx);
      }
    }
  }, [segments, currentSegmentIndex, prefetchSegment]);

  useEffect(() => {
    prefetchAhead();
  }, [prefetchAhead]);

  // Reset prefetch cache on session change
  useEffect(() => {
    prefetchedRef.current.clear();
  }, [session?.id]);

  // Seek within the current segment
  const seekTo = useCallback(
    (timeInSeconds) => {
      if (_audioEl) {
        _audioEl.currentTime = timeInSeconds;
      }
    },
    [_audioEl],
  );

  // Skip forward/back by N seconds
  const skip = useCallback(
    (deltaSeconds) => {
      if (_audioEl) {
        _audioEl.currentTime = Math.max(0, _audioEl.currentTime + deltaSeconds);
      }
    },
    [_audioEl],
  );

  // Jump to a specific segment by index
  const jumpToSegment = useCallback(
    (index) => {
      if (index >= 0 && index < segments.length) {
        playSegment(index);
      }
    },
    [segments.length, playSegment],
  );

  const segmentDuration = _audioEl?.duration || 0;

  return {
    isPlaying,
    currentSegmentIndex,
    playbackSpeed,
    segmentDuration,
    playSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    seekTo,
    skip,
    jumpToSegment,
  };
}

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

  // ── Auto-advance: when a segment ends, play the next one ──
  useEffect(() => {
    const audio = _audioEl;
    if (!audio) return;

    const onEnded = () => {
      // Read latest state via getState() to avoid stale closures
      const { currentSegmentIndex: idx, segments: segs, playSegment: play, pause: pauseFn } =
        usePodcastStore.getState();
      if (idx < segs.length - 1) {
        play(idx + 1);
      } else {
        pauseFn();
      }
    };

    audio.addEventListener('ended', onEnded);
    return () => audio.removeEventListener('ended', onEnded);
  }, [_audioEl]);

  // Seek within the current segment.
  // Read the audio element from getState() at call time so we're not modifying
  // a value returned directly from a hook call (which the linter forbids).
  const seekTo = useCallback(
    (timeInSeconds) => {
      const audio = usePodcastStore.getState()._audioEl;
      if (audio) {
        audio.currentTime = timeInSeconds;
      }
    },
    [],
  );

  // Skip forward/back by N seconds
  const skip = useCallback(
    (deltaSeconds) => {
      const audio = usePodcastStore.getState()._audioEl;
      if (audio) {
        audio.currentTime = Math.max(0, audio.currentTime + deltaSeconds);
      }
    },
    [],
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

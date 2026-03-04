'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';

/**
 * Manages segment-level audio playback with lookahead prefetch,
 * speed control, and seek/skip helpers.
 *
 * Owns Audio element and cache via useRef (not stored in Zustand for serializability).
 */
export default function usePodcastPlayer() {
  const {
    session,
    segments,
    currentSegmentIndex,
    isPlaying,
    playbackSpeed,
    playSegment,
    prefetchSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    setCurrentSegmentIndex,
    setAudioRefs,
  } = usePodcastStore();

  // ── Audio refs owned by this hook (not in store) ──
  const audioElRef = useRef(typeof window !== 'undefined' ? new Audio() : null);
  const audioCacheRef = useRef(new Map());

  // Register refs with store so playback actions can access them
  useEffect(() => {
    setAudioRefs(audioElRef, audioCacheRef);
  }, [setAudioRefs]);

  // ── Cleanup audio on unmount ──
  useEffect(() => {
    const audio = audioElRef.current;
    const cache = audioCacheRef.current;
    return () => {
      if (audio) {
        audio.pause();
        audio.src = '';
      }
      if (cache) {
        cache.forEach(url => URL.revokeObjectURL(url));
        cache.clear();
      }
    };
  }, []);

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

  // ── Track segment duration via event listener (avoids reading ref during render) ──
  const [segmentDuration, setSegmentDuration] = useState(0);

  useEffect(() => {
    const audio = audioElRef.current;
    if (!audio) return;
    const update = () => setSegmentDuration(audio.duration || 0);
    audio.addEventListener('loadedmetadata', update);
    audio.addEventListener('durationchange', update);
    return () => {
      audio.removeEventListener('loadedmetadata', update);
      audio.removeEventListener('durationchange', update);
    };
  }, []);

  // ── Auto-advance: when a segment ends, play the next one ──
  useEffect(() => {
    const audio = audioElRef.current;
    if (!audio) return;

    const onEnded = () => {
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
  }, []);

  // Seek within the current segment.
  const seekTo = useCallback(
    (timeInSeconds) => {
      if (audioElRef.current) {
        audioElRef.current.currentTime = timeInSeconds;
      }
    },
    [],
  );

  // Skip forward/back by N seconds
  const skip = useCallback(
    (deltaSeconds) => {
      if (audioElRef.current) {
        audioElRef.current.currentTime = Math.max(0, audioElRef.current.currentTime + deltaSeconds);
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

'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';


export default function usePodcastPlayer() {
  const session = usePodcastStore((s) => s.session);
  const segments = usePodcastStore((s) => s.segments);
  const currentSegmentIndex = usePodcastStore((s) => s.currentSegmentIndex);
  const isPlaying = usePodcastStore((s) => s.isPlaying);
  const playbackSpeed = usePodcastStore((s) => s.playbackSpeed);
  const playSegment = usePodcastStore((s) => s.playSegment);
  const prefetchSegment = usePodcastStore((s) => s.prefetchSegment);
  const pause = usePodcastStore((s) => s.pause);
  const resume = usePodcastStore((s) => s.resume);
  const togglePlayPause = usePodcastStore((s) => s.togglePlayPause);
  const nextSegment = usePodcastStore((s) => s.nextSegment);
  const prevSegment = usePodcastStore((s) => s.prevSegment);
  const changeSpeed = usePodcastStore((s) => s.changeSpeed);
  const setAudioRefs = usePodcastStore((s) => s.setAudioRefs);

  
  const audioElRef = useRef(typeof window !== 'undefined' ? new Audio() : null);
  const audioCacheRef = useRef(new Map());
  const pendingSeekRef = useRef(null);

  
  useEffect(() => {
    setAudioRefs(audioElRef, audioCacheRef);
  }, [setAudioRefs]);

  
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

  
  useEffect(() => {
    prefetchedRef.current.clear();
  }, [session?.id]);

  
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

  useEffect(() => {
    const audio = audioElRef.current;
    if (!audio) return;

    const applyPendingSeek = () => {
      if (pendingSeekRef.current == null) return;
      try {
        audio.currentTime = Math.max(0, pendingSeekRef.current);
      } catch {
        // Best effort; if metadata is still not ready this will re-apply on next event.
      }
      pendingSeekRef.current = null;
    };

    audio.addEventListener('loadedmetadata', applyPendingSeek);
    audio.addEventListener('canplay', applyPendingSeek);

    return () => {
      audio.removeEventListener('loadedmetadata', applyPendingSeek);
      audio.removeEventListener('canplay', applyPendingSeek);
    };
  }, []);

  
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

  
  const seekTo = useCallback(
    (timeInSeconds) => {
      if (audioElRef.current) {
        audioElRef.current.currentTime = timeInSeconds;
      }
    },
    [],
  );

  const seekToOverall = useCallback(
    async (totalSeconds) => {
      if (!segments.length) return;

      const safeTotal = Math.max(0, Number(totalSeconds) || 0);
      const durationSeconds = segments.map((seg) => Math.max(0, (seg.durationMs || 0) / 1000));
      const fullDuration = durationSeconds.reduce((sum, s) => sum + s, 0);
      const clamped = fullDuration > 0 ? Math.min(safeTotal, fullDuration) : safeTotal;

      let running = 0;
      let targetIndex = segments.length - 1;
      let targetOffset = 0;

      for (let i = 0; i < durationSeconds.length; i++) {
        const segDur = durationSeconds[i];
        if (clamped <= running + segDur || i === durationSeconds.length - 1) {
          targetIndex = i;
          targetOffset = Math.max(0, clamped - running);
          break;
        }
        running += segDur;
      }

      if (targetIndex === currentSegmentIndex) {
        seekTo(targetOffset);
        return;
      }

      pendingSeekRef.current = targetOffset;
      await playSegment(targetIndex);

      const audio = audioElRef.current;
      if (audio && audio.readyState >= 1 && pendingSeekRef.current != null) {
        seekTo(targetOffset);
        pendingSeekRef.current = null;
      }
    },
    [segments, currentSegmentIndex, playSegment, seekTo],
  );

  
  const skip = useCallback(
    (deltaSeconds) => {
      if (audioElRef.current) {
        audioElRef.current.currentTime = Math.max(0, audioElRef.current.currentTime + deltaSeconds);
      }
    },
    [],
  );

  
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
    seekToOverall,
    skip,
    jumpToSegment,
  };
}

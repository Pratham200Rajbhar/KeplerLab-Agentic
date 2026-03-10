'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';


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

  
  const audioElRef = useRef(typeof window !== 'undefined' ? new Audio() : null);
  const audioCacheRef = useRef(new Map());

  
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
    skip,
    jumpToSegment,
  };
}

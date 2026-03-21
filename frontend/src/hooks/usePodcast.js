'use client';

import { useRef, useEffect, useCallback, useMemo } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';


export default function usePodcast() {
  // Use specific selectors for each action to ensure stable references
  const create = usePodcastStore((s) => s.create);
  const loadSessions = usePodcastStore((s) => s.loadSessions);
  const loadSession = usePodcastStore((s) => s.loadSession);
  const startGeneration = usePodcastStore((s) => s.startGeneration);
  const playSegment = usePodcastStore((s) => s.playSegment);
  const prefetchSegment = usePodcastStore((s) => s.prefetchSegment);
  const pause = usePodcastStore((s) => s.pause);
  const resume = usePodcastStore((s) => s.resume);
  const togglePlayPause = usePodcastStore((s) => s.togglePlayPause);
  const nextSegment = usePodcastStore((s) => s.nextSegment);
  const prevSegment = usePodcastStore((s) => s.prevSegment);
  const changeSpeed = usePodcastStore((s) => s.changeSpeed);
  const askQuestion = usePodcastStore((s) => s.askQuestion);
  const loadDoubts = usePodcastStore((s) => s.loadDoubts);
  const addBookmark = usePodcastStore((s) => s.addBookmark);
  const removeBookmark = usePodcastStore((s) => s.removeBookmark);
  const addAnnotation = usePodcastStore((s) => s.addAnnotation);
  const removeAnnotation = usePodcastStore((s) => s.removeAnnotation);
  const removeSession = usePodcastStore((s) => s.removeSession);
  const exportSession = usePodcastStore((s) => s.exportSession);
  const generateSummary = usePodcastStore((s) => s.generateSummary);
  const setPhase = usePodcastStore((s) => s.setPhase);
  const setSession = usePodcastStore((s) => s.setSession);
  const setInterruptOpen = usePodcastStore((s) => s.setInterruptOpen);
  const setError = usePodcastStore((s) => s.setError);
  const setGenerationProgress = usePodcastStore((s) => s.setGenerationProgress);

  // State selectors
  const session = usePodcastStore((s) => s.session);
  const sessions = usePodcastStore((s) => s.sessions);
  const phase = usePodcastStore((s) => s.phase);
  const isPlaying = usePodcastStore((s) => s.isPlaying);
  const currentTime = usePodcastStore((s) => s.currentTime);
  const currentSegmentIndex = usePodcastStore((s) => s.currentSegmentIndex);
  const segments = usePodcastStore((s) => s.segments);

  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const draftMode = useAppStore((s) => s.draftMode);

  const createAction = useCallback(async (config) => {
    if (!currentNotebook?.id) throw new Error('No notebook selected');
    return create(config, currentNotebook.id, selectedSources);
  }, [create, currentNotebook, selectedSources]);

  const loadSessionsAction = useCallback(() => {
    if (currentNotebook?.id) {
      loadSessions(currentNotebook.id, draftMode);
    }
  }, [loadSessions, currentNotebook, draftMode]);

  return useMemo(() => ({
    create: createAction,
    loadSessions: loadSessionsAction,
    loadSession,
    startGeneration,
    playSegment,
    prefetchSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    askQuestion,
    loadDoubts,
    addBookmark,
    removeBookmark,
    addAnnotation,
    removeAnnotation,
    removeSession,
    exportSession,
    generateSummary,
    setPhase,
    setSession,
    setInterruptOpen,
    setError,
    setGenerationProgress,
    session,
    sessions,
    phase,
    isPlaying,
    currentTime,
    currentSegmentIndex,
    segments,
    currentNotebook,
    selectedSources,
    draftMode,
  }), [
    createAction,
    loadSessionsAction,
    loadSession,
    startGeneration,
    playSegment,
    prefetchSegment,
    pause,
    resume,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    askQuestion,
    loadDoubts,
    addBookmark,
    removeBookmark,
    addAnnotation,
    removeAnnotation,
    removeSession,
    exportSession,
    generateSummary,
    setPhase,
    setSession,
    setInterruptOpen,
    setError,
    setGenerationProgress,
    session,
    sessions,
    phase,
    isPlaying,
    currentTime,
    currentSegmentIndex,
    segments,
    currentNotebook,
    selectedSources,
    draftMode,
  ]);
}

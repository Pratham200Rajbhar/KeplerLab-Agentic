'use client';

import { useEffect } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import PodcastSessionLibrary from './PodcastSessionLibrary';
import PodcastGenerating from './PodcastGenerating';
import PodcastPlayer from './PodcastPlayer';
import PodcastModeSelector from './PodcastModeSelector';

/**
 * Main podcast orchestrator.
 * Routes between: library → mode-select → generating → player
 */
export default function PodcastStudio() {
  const phase = usePodcastStore((s) => s.phase);
  const session = usePodcastStore((s) => s.session);
  const loadSessions = usePodcastStore((s) => s.loadSessions);
  const setPhase = usePodcastStore((s) => s.setPhase);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const draftMode = useAppStore((s) => s.draftMode);

  // Load sessions when notebook changes
  useEffect(() => {
    if (currentNotebook?.id && !draftMode) {
      loadSessions(currentNotebook.id, draftMode);
    }
  }, [currentNotebook?.id, draftMode, loadSessions]);

  // Show library by default
  if (phase === 'idle' || phase === 'library') {
    return (
      <PodcastSessionLibrary
        onNewPodcast={() => setPhase('mode-select')}
        onSelectSession={(sessionId) => {
          usePodcastStore.getState().loadSession(sessionId);
        }}
      />
    );
  }

  if (phase === 'mode-select') {
    return <PodcastModeSelector />;
  }

  if (phase === 'generating') {
    return <PodcastGenerating />;
  }

  if (phase === 'player' && session) {
    return <PodcastPlayer />;
  }

  return null;
}

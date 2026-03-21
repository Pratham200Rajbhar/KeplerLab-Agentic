'use client';

import { useEffect } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import PodcastSessionLibrary from './PodcastSessionLibrary';
import PodcastGenerating from './PodcastGenerating';
import PodcastPlayer from './PodcastPlayer';
import PodcastModeSelector from './PodcastModeSelector';


export default function PodcastStudio({ onClose, onRequestNew }) {
  const phase = usePodcastStore((s) => s.phase);
  const session = usePodcastStore((s) => s.session);
  const loadSessions = usePodcastStore((s) => s.loadSessions);
  const setPhase = usePodcastStore((s) => s.setPhase);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const draftMode = useAppStore((s) => s.draftMode);

  
  useEffect(() => {
    if (currentNotebook?.id && !draftMode) {
      loadSessions(currentNotebook.id, draftMode);
    }
  }, [currentNotebook?.id, draftMode, loadSessions]);

  
  if (phase === 'generating') {
    return <PodcastGenerating />;
  }

  if (phase === 'player' && session) {
    return <PodcastPlayer onClose={onClose} />;
  }

  return (
    <div className="flex flex-col items-center justify-center p-8 text-center gap-4">
      <p className="text-sm text-[var(--text-muted)]">No active podcast session.</p>
      <button onClick={onRequestNew} className="btn-primary">Create New Podcast</button>
    </div>
  );
}

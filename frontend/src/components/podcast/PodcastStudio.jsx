'use client';

import { useCallback, useEffect, useMemo } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import PodcastSessionLibrary from './PodcastSessionLibrary';
import PodcastGenerating from './PodcastGenerating';
import PodcastPlayer from './PodcastPlayer';


export default function PodcastStudio({ onClose, onRequestNew }) {
  const phase = usePodcastStore((s) => s.phase);
  const session = usePodcastStore((s) => s.session);
  const sessions = usePodcastStore((s) => s.sessions);
  const loading = usePodcastStore((s) => s.loading);
  const error = usePodcastStore((s) => s.error);
  const loadSessions = usePodcastStore((s) => s.loadSessions);
  const loadSession = usePodcastStore((s) => s.loadSession);
  const setPhase = usePodcastStore((s) => s.setPhase);

  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const draftMode = useAppStore((s) => s.draftMode);
  const selectedSources = useAppStore((s) => s.selectedSources);

  useEffect(() => {
    if (currentNotebook?.id && !draftMode) {
      loadSessions(currentNotebook.id, draftMode);
    }
  }, [currentNotebook?.id, draftMode, loadSessions]);

  const handleSelectSession = useCallback(
    async (sessionId) => {
      if (!sessionId) return;
      await loadSession(sessionId);
      setPhase('player');
    },
    [loadSession, setPhase],
  );

  if (phase === 'generating') {
    return (
      <div className="podcast-shell flex flex-col h-full animate-fade-in">
        <div className="podcast-hero">
          <p className="podcast-eyebrow">AI Podcast</p>
          <h3 className="podcast-title">Generating Podcast</h3>
          <p className="text-[11px] text-[var(--text-muted)] mt-1">You can keep working while this finishes in the background.</p>
        </div>
        <div className="px-3 py-3">
          <PodcastGenerating />
        </div>
        <div className="px-3 pb-3 mt-auto">
          <button
            onClick={() => setPhase('idle')}
            className="podcast-pill-btn w-full justify-center text-[var(--text-secondary)]"
            disabled={loading}
          >
            Back to Library
          </button>
        </div>
      </div>
    );
  }

  if (phase === 'player' && session) {
    return <PodcastPlayer onClose={() => setPhase('idle')} />;
  }

  return (
    <div className="podcast-shell flex flex-col h-full animate-fade-in">
      <div className="podcast-hero">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="podcast-eyebrow">AI Podcast</p>
            <h3 className="podcast-title">Podcast Sessions</h3>
            <p className="text-[11px] text-[var(--text-muted)] mt-1.5">Open an existing session or create a new one.</p>
          </div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-overlay)] text-[10px] font-semibold text-[var(--text-secondary)] whitespace-nowrap">
            {selectedSources.length} source{selectedSources.length === 1 ? '' : 's'}
          </div>
        </div>
        {error && (
          <div className="text-[11px] text-red-400 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-2 mt-3">
            {error}
          </div>
        )}
      </div>

      <div className="flex-1 min-h-0 px-3 pb-3 mt-2">
        <section className="podcast-studio-panel h-full min-h-0 overflow-y-auto custom-scrollbar">
          <PodcastSessionLibrary
            onNewPodcast={onRequestNew}
            onSelectSession={handleSelectSession}
          />
        </section>
      </div>

      {onClose && (
        <div className="px-3 pb-3">
          <button
            onClick={onClose}
            className="podcast-pill-btn w-full justify-center text-[var(--text-secondary)]"
          >
            Back to Studio
          </button>
        </div>
      )}
    </div>
  );
}

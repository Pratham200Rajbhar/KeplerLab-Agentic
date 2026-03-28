'use client';

import { useCallback, useEffect, useMemo } from 'react';
import { FolderOpen, Mic, Radio, Sparkles } from 'lucide-react';
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

  const playableSessions = useMemo(
    () =>
      (sessions || []).filter((s) =>
        ['ready', 'playing', 'paused', 'completed'].includes((s.status || '').toLowerCase())
      ),
    [sessions],
  );

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
            <p className="podcast-eyebrow">AI Podcast Studio</p>
            <h3 className="podcast-title">Clean Audio Learning Workspace</h3>
            <p className="text-[11px] text-[var(--text-muted)] mt-1.5">Create, manage, and replay two-host podcasts from your selected sources.</p>
          </div>
          <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-[var(--border)] bg-[var(--surface-overlay)] text-[10px] font-semibold text-[var(--text-secondary)] whitespace-nowrap">
            <FolderOpen className="w-3.5 h-3.5" />
            {selectedSources.length} source{selectedSources.length === 1 ? '' : 's'}
          </div>
        </div>
      </div>

      <div className="podcast-studio-grid flex-1 min-h-0 px-3 pb-3">
        <section className="podcast-studio-panel min-h-0 overflow-y-auto custom-scrollbar">
          <PodcastSessionLibrary
            onNewPodcast={onRequestNew}
            onSelectSession={handleSelectSession}
          />
        </section>

        <section className="podcast-studio-panel podcast-studio-quick">
          <div className="space-y-3">
            <div className="inline-flex items-center gap-2 text-[10px] font-semibold uppercase tracking-[0.1em] text-[var(--text-muted)]">
              <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
              Quick Start
            </div>
            <h4 className="text-[15px] font-semibold text-[var(--text-primary)] leading-tight">
              Build a better podcast in three steps
            </h4>
            <div className="space-y-2.5 text-[12px] text-[var(--text-secondary)]">
              <p className="podcast-studio-step"><span>1</span>Select your best sources in the sidebar.</p>
              <p className="podcast-studio-step"><span>2</span>Choose mode, language, and voices.</p>
              <p className="podcast-studio-step"><span>3</span>Generate and jump into playback instantly.</p>
            </div>
          </div>

          <div className="mt-4 space-y-2">
            <button
              onClick={onRequestNew}
              disabled={selectedSources.length === 0}
              className="podcast-play-btn w-full h-11 rounded-xl inline-flex items-center justify-center gap-2 text-sm font-semibold disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <Mic className="w-4 h-4" />
              Create New Podcast
            </button>
            <div className="text-[11px] text-[var(--text-muted)] inline-flex items-center gap-1.5">
              <Radio className="w-3.5 h-3.5" />
              {playableSessions.length} playable session{playableSessions.length === 1 ? '' : 's'}
            </div>
            {error && (
              <div className="text-[11px] text-red-400 rounded-lg border border-red-500/30 bg-red-500/10 px-2.5 py-2">
                {error}
              </div>
            )}
            {onClose && (
              <button
                onClick={onClose}
                className="podcast-pill-btn w-full justify-center text-[var(--text-secondary)]"
              >
                Back to Studio
              </button>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}

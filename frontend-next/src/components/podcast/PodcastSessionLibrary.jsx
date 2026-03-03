'use client';

import { useEffect } from 'react';
import { Mic, Plus, Trash2, Radio, Clock, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import usePodcastStore, { SESSION_STATUS } from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import { useConfirm } from '@/stores/useConfirmStore';
import { formatRelativeDate } from '@/lib/utils/helpers';

const STATUS_CONFIG = {
  [SESSION_STATUS.CREATED]: { icon: Clock, color: 'text-[var(--text-muted)]', label: 'Created' },
  [SESSION_STATUS.SCRIPT_GEN]: { icon: Loader2, color: 'text-yellow-400', label: 'Generating script...' },
  [SESSION_STATUS.AUDIO_GEN]: { icon: Loader2, color: 'text-blue-400', label: 'Generating audio...' },
  [SESSION_STATUS.READY]: { icon: CheckCircle2, color: 'text-green-400', label: 'Ready' },
  [SESSION_STATUS.PLAYING]: { icon: Radio, color: 'text-[var(--accent)]', label: 'Playing' },
  [SESSION_STATUS.PAUSED]: { icon: Clock, color: 'text-yellow-400', label: 'Paused' },
  [SESSION_STATUS.COMPLETED]: { icon: CheckCircle2, color: 'text-green-400', label: 'Completed' },
  [SESSION_STATUS.FAILED]: { icon: AlertCircle, color: 'text-red-400', label: 'Failed' },
};

export default function PodcastSessionLibrary({ onNewPodcast, onSelectSession }) {
  const sessions = usePodcastStore((s) => s.sessions);
  const loadSessions = usePodcastStore((s) => s.loadSessions);
  const removeSession = usePodcastStore((s) => s.removeSession);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const draftMode = useAppStore((s) => s.draftMode);
  const confirm = useConfirm();

  useEffect(() => {
    if (currentNotebook?.id && !draftMode) {
      loadSessions(currentNotebook.id, draftMode);
    }
  }, [currentNotebook?.id, draftMode, loadSessions]);

  const handleDelete = async (session) => {
    const confirmed = await confirm({
      title: 'Delete Podcast',
      message: `Delete "${session.title || 'this podcast'}"? This cannot be undone.`,
      variant: 'danger',
      confirmLabel: 'Delete',
    });
    if (confirmed) {
      await removeSession(session.id);
    }
  };

  const hasSources = selectedSources.size > 0;

  return (
    <div className="space-y-4 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Podcasts</h3>
          <p className="text-[10px] text-[var(--text-muted)] mt-0.5">AI-generated audio discussions</p>
        </div>
        <button
          onClick={onNewPodcast}
          disabled={!hasSources}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Plus className="w-3.5 h-3.5" /> New
        </button>
      </div>

      {!hasSources && (
        <p className="text-xs text-[var(--text-muted)] px-1">
          Select sources in the sidebar to create a podcast
        </p>
      )}

      {/* Session list */}
      {sessions.length === 0 ? (
        <div className="flex flex-col items-center py-8 text-center">
          <Mic className="w-8 h-8 text-[var(--text-muted)] mb-3 opacity-40" />
          <p className="text-xs text-[var(--text-muted)]">No podcasts yet</p>
          <p className="text-[10px] text-[var(--text-muted)] mt-1">Generate your first AI podcast</p>
        </div>
      ) : (
        <div className="space-y-1">
          {sessions.map((s) => {
            const statusInfo = STATUS_CONFIG[s.status] || STATUS_CONFIG[SESSION_STATUS.CREATED];
            const StatusIcon = statusInfo.icon;
            const isClickable = [SESSION_STATUS.READY, SESSION_STATUS.PLAYING, SESSION_STATUS.PAUSED, SESSION_STATUS.COMPLETED].includes(s.status);

            return (
              <div
                key={s.id}
                onClick={() => isClickable && onSelectSession?.(s.id)}
                className={`group relative flex items-center gap-3 px-3 py-3 rounded-xl border border-transparent transition-all ${
                  isClickable
                    ? 'cursor-pointer hover:bg-[var(--surface-overlay)] hover:border-[var(--border)]'
                    : 'opacity-70'
                }`}
              >
                <div className="shrink-0">
                  <StatusIcon className={`w-4 h-4 ${statusInfo.color} ${
                    [SESSION_STATUS.SCRIPT_GEN, SESSION_STATUS.AUDIO_GEN].includes(s.status) ? 'animate-spin' : ''
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs font-medium text-[var(--text-primary)] truncate">
                    {s.title || `Podcast ${s.id?.slice(0, 6)}`}
                  </p>
                  <p className="text-[10px] text-[var(--text-muted)] mt-0.5">
                    {statusInfo.label} · {formatRelativeDate(s.created_at)}
                  </p>
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(s);
                  }}
                  className="p-1 rounded hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                >
                  <Trash2 className="w-3.5 h-3.5 text-[var(--text-muted)] hover:text-red-400" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

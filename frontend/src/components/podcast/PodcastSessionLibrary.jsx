'use client';

import { useMemo } from 'react';
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
  const removeSession = usePodcastStore((s) => s.removeSession);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const confirm = useConfirm();

  const orderedSessions = useMemo(() => {
    const getStamp = (s) => s.updated_at || s.updatedAt || s.created_at || s.createdAt || 0;
    return [...(sessions || [])].sort((a, b) => new Date(getStamp(b)) - new Date(getStamp(a)));
  }, [sessions]);

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

  const hasSources = selectedSources.length > 0;

  return (
    <div className="space-y-4 animate-fade-in">
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-[14px] font-semibold text-[var(--text-primary)]">Podcast Sessions</h3>
          <p className="text-[11px] text-[var(--text-muted)] mt-0.5">Open any ready session to continue listening</p>
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

      {orderedSessions.length === 0 ? (
        <div className="podcast-studio-empty flex flex-col items-center py-8 text-center">
          <Mic className="w-8 h-8 text-[var(--text-muted)] mb-3 opacity-40" />
          <p className="text-xs text-[var(--text-muted)]">No podcasts yet</p>
          <p className="text-[10px] text-[var(--text-muted)] mt-1">Generate your first AI podcast from selected sources</p>
        </div>
      ) : (
        <div className="space-y-1.5">
          {orderedSessions.map((s) => {
            const statusInfo = STATUS_CONFIG[s.status] || STATUS_CONFIG[SESSION_STATUS.CREATED];
            const StatusIcon = statusInfo.icon;
            const isClickable = [SESSION_STATUS.READY, SESSION_STATUS.PLAYING, SESSION_STATUS.PAUSED, SESSION_STATUS.COMPLETED].includes(s.status);

            return (
              <div
                key={s.id}
                onClick={() => isClickable && onSelectSession?.(s.id)}
                className={`podcast-session-item group relative flex items-center gap-3 px-3.5 py-3 rounded-xl border transition-all ${
                  isClickable
                    ? 'cursor-pointer hover:bg-[var(--surface-overlay)] hover:border-[var(--accent-border)]'
                    : 'opacity-70'
                }`}
              >
                <div className="shrink-0">
                  <StatusIcon className={`w-4 h-4 ${statusInfo.color} ${
                    [SESSION_STATUS.SCRIPT_GEN, SESSION_STATUS.AUDIO_GEN].includes(s.status) ? 'animate-spin' : ''
                  }`} />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-[12px] font-semibold text-[var(--text-primary)] truncate">
                    {s.title || `Podcast ${s.id?.slice(0, 6)}`}
                  </p>
                  <div className="mt-1 flex items-center gap-2">
                    <span className="podcast-session-status text-[10px]">{statusInfo.label}</span>
                    <span className="text-[10px] text-[var(--text-muted)]">{formatRelativeDate(s.created_at || s.createdAt)}</span>
                  </div>
                </div>
                {isClickable && <span className="text-[10px] text-[var(--text-muted)] hidden sm:block">Open</span>}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    handleDelete(s);
                  }}
                  className="p-1 rounded hover:bg-red-500/10 transition-colors opacity-0 group-hover:opacity-100"
                  aria-label="Delete session"
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

'use client';

import { Loader2, Radio, FileText, Mic, CheckCircle2 } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';

export default function PodcastGenerating() {
  const progress = usePodcastStore((s) => s.generationProgress);
  const error = usePodcastStore((s) => s.error);
  const setPhase = usePodcastStore((s) => s.setPhase);

  const stage = progress?.stage || 'script';
  const pct = progress?.pct || 0;
  const message = progress?.message || 'Starting...';

  const stageIndex = stage === 'audio' ? 1 : 0;

  if (error) {
    return (
      <div className="flex items-center gap-3 px-4 py-3 rounded-xl border border-red-500/30 bg-red-500/10 animate-fade-in">
        <Radio className="w-4 h-4 text-red-400 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-red-400 truncate">Generation failed</p>
          <p className="text-[10px] text-red-400/70 truncate">{error}</p>
        </div>
        <button
          onClick={() => setPhase('idle')}
          className="shrink-0 px-2.5 py-1 rounded-lg text-[10px] bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] hover:bg-[var(--surface-overlay)] transition-colors"
        >
          Back
        </button>
      </div>
    );
  }

  return (
    <div className="px-1 py-2 space-y-2 animate-fade-in">
      {/* Stage + status row */}
      <div className="flex items-center gap-2">
        <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin shrink-0" />
        <div className="flex items-center gap-1.5 flex-1 min-w-0">
          {/* Script */}
          <span className={`flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
            stageIndex > 0 ? 'text-green-400' : stage === 'script' ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'
          }`}>
            {stageIndex > 0 ? <CheckCircle2 className="w-2.5 h-2.5" /> : <FileText className="w-2.5 h-2.5" />}
            Script
          </span>
          <div className="w-4 h-px bg-[var(--border)]" />
          {/* Audio */}
          <span className={`flex items-center gap-1 text-[10px] font-medium px-1.5 py-0.5 rounded-full ${
            stage === 'audio' ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'
          }`}>
            <Mic className="w-2.5 h-2.5" />
            Audio
          </span>
        </div>
        <span className="text-[10px] tabular-nums text-[var(--text-muted)] shrink-0">{Math.round(pct)}%</span>
      </div>

      {/* Thin progress bar */}
      <div className="h-1 rounded-full bg-[var(--surface)] overflow-hidden">
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      {/* Status message */}
      <p className="text-[10px] text-[var(--text-muted)] truncate">{message}</p>
    </div>
  );
}

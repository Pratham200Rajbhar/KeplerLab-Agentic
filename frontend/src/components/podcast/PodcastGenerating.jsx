'use client';

import { CheckCircle2, Loader2, Mic, Radio, Sparkles } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';

export default function PodcastGenerating() {
  const progress = usePodcastStore((s) => s.generationProgress);
  const error = usePodcastStore((s) => s.error);
  const setPhase = usePodcastStore((s) => s.setPhase);

  const stage = (progress?.stage || 'script').toLowerCase();
  const pct = Math.max(0, Math.min(progress?.pct || 0, 100));
  const message = progress?.message || 'Preparing your podcast...';

  const scriptDone = stage === 'audio';
  const scriptActive = stage === 'script';
  const audioActive = stage === 'audio';

  if (error) {
    return (
      <div className="podcast-gen-shell animate-fade-in border-red-500/35 bg-red-500/10">
        <div className="flex items-center gap-3">
          <Radio className="w-4 h-4 text-red-400 shrink-0" />
          <div className="flex-1 min-w-0">
            <p className="text-xs font-semibold text-red-300">Generation failed</p>
            <p className="text-[11px] text-red-200/80 mt-0.5">{error}</p>
          </div>
        </div>
        <button
          onClick={() => setPhase('idle')}
          className="mt-3 w-full podcast-pill-btn justify-center text-[var(--text-secondary)]"
        >
          Back to Library
        </button>
      </div>
    );
  }

  return (
    <div className="podcast-gen-shell animate-fade-in">
      <div className="flex items-start gap-3">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center border border-[var(--accent-border)] bg-[var(--accent-subtle)]">
          <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin" />
        </div>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-[var(--text-primary)] inline-flex items-center gap-1.5">
            <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
            Building your AI podcast
          </p>
          <p className="text-[11px] text-[var(--text-muted)] mt-1">{message}</p>
        </div>
        <span className="text-[11px] tabular-nums text-[var(--text-muted)] shrink-0">{Math.round(pct)}%</span>
      </div>

      <div className="h-1.5 rounded-full bg-[var(--surface)] overflow-hidden mt-3">
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>

      <div className="mt-3 grid grid-cols-2 gap-2">
        <div className={`podcast-gen-step ${scriptDone ? 'done' : scriptActive ? 'active' : ''}`}>
          {scriptDone ? <CheckCircle2 className="w-3.5 h-3.5" /> : <Radio className="w-3.5 h-3.5" />}
          Script
        </div>
        <div className={`podcast-gen-step ${audioActive ? 'active' : ''}`}>
          <Mic className="w-3.5 h-3.5" />
          Audio
        </div>
      </div>
    </div>
  );
}

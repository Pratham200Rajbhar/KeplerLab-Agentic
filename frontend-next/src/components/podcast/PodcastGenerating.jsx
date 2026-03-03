'use client';

import { Loader2, Radio, FileText, Mic } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';

export default function PodcastGenerating() {
  const progress = usePodcastStore((s) => s.generationProgress);
  const error = usePodcastStore((s) => s.error);
  const setPhase = usePodcastStore((s) => s.setPhase);

  const stage = progress?.stage || 'script';
  const pct = progress?.pct || 0;
  const message = progress?.message || 'Starting...';

  const STAGES = [
    { id: 'script', label: 'Script', icon: FileText },
    { id: 'audio', label: 'Audio', icon: Mic },
  ];

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center animate-fade-in">
        <div className="w-12 h-12 rounded-full bg-red-500/20 flex items-center justify-center mb-4">
          <Radio className="w-6 h-6 text-red-400" />
        </div>
        <p className="text-sm font-medium text-red-400 mb-1">Generation Failed</p>
        <p className="text-xs text-(--text-muted) mb-4">{error}</p>
        <button
          onClick={() => setPhase('idle')}
          className="px-4 py-2 rounded-lg text-xs bg-(--surface) border border-(--border) text-(--text-primary) hover:bg-(--surface-overlay) transition-colors"
        >
          Go Back
        </button>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center py-12 px-4 animate-fade-in">
      {/* Animated icon */}
      <div className="relative mb-6">
        <div className="w-16 h-16 rounded-full bg-(--accent)/10 flex items-center justify-center">
          <Loader2 className="w-8 h-8 text-(--accent) animate-spin" />
        </div>
        <div className="absolute -bottom-1 -right-1 w-6 h-6 rounded-full bg-(--surface-raised) border border-(--border) flex items-center justify-center">
          {stage === 'script' ? (
            <FileText className="w-3 h-3 text-(--accent)" />
          ) : (
            <Mic className="w-3 h-3 text-purple-400" />
          )}
        </div>
      </div>

      {/* Stage indicators */}
      <div className="flex items-center gap-3 mb-4">
        {STAGES.map((s, i) => (
          <div key={s.id} className="flex items-center gap-1.5">
            <div className={`flex items-center gap-1 px-2 py-1 rounded-full text-[10px] font-medium ${
              stage === s.id
                ? 'bg-(--accent)/10 text-(--accent)'
                : STAGES.findIndex((st) => st.id === stage) > i
                ? 'text-green-400'
                : 'text-(--text-muted)'
            }`}>
              <s.icon className="w-3 h-3" />
              {s.label}
            </div>
            {i < STAGES.length - 1 && (
              <div className="w-6 h-px bg-(--border)" />
            )}
          </div>
        ))}
      </div>

      {/* Progress */}
      <p className="text-sm font-medium text-(--text-primary) mb-2">{message}</p>
      <div className="w-48 h-1.5 rounded-full bg-(--surface) overflow-hidden">
        <div
          className="h-full rounded-full bg-(--accent) transition-all duration-500"
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="text-[10px] text-(--text-muted) mt-2 tabular-nums">{Math.round(pct)}%</p>
    </div>
  );
}

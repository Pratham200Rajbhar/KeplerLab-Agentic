'use client';

import { useState, useRef, useEffect } from 'react';
import { HelpCircle, Play, Pause } from 'lucide-react';
import { fetchAudioObjectUrl } from '@/lib/api/config';

export default function PodcastDoubtHistory({ doubts = [], playSegment }) {
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(typeof window !== 'undefined' ? new Audio() : null);

  // Cleanup audio on unmount
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause();
        audioRef.current.src = '';
      }
    };
  }, []);

  const handlePlay = async (doubt) => {
    if (playingId === doubt.id) {
      audioRef.current?.pause();
      setPlayingId(null);
      return;
    }
    if (doubt.audioPath) {
      try {
        const blobUrl = await fetchAudioObjectUrl(doubt.audioPath);
        audioRef.current.src = blobUrl;
        audioRef.current.play().catch(() => {});
        setPlayingId(doubt.id);
        audioRef.current.onended = () => {
          setPlayingId(null);
          URL.revokeObjectURL(blobUrl);
        };
      } catch (err) {
        console.error('Failed to load doubt audio:', err);
      }
    }
  };

  if (!doubts.length) {
    return (
      <div className="px-4 py-8 text-center">
        <HelpCircle className="w-5 h-5 text-(--text-muted) mx-auto mb-2 opacity-40" />
        <p className="text-xs text-(--text-muted)">No questions asked yet</p>
        <p className="text-[10px] text-(--text-muted) mt-1">Use the Ask button to interrupt the podcast</p>
      </div>
    );
  }

  return (
    <div className="px-3 py-2 space-y-2">
      {doubts.map((d, i) => (
        <div key={d.id || i} className="p-2.5 rounded-lg border border-(--border)">
          {/* Question */}
          <div className="flex items-start gap-2 mb-2">
            <HelpCircle className="w-3.5 h-3.5 text-(--accent) mt-0.5 shrink-0" />
            <p className="text-xs text-(--text-primary) leading-relaxed">{d.questionText || d.question_text}</p>
          </div>

          {/* Answer */}
          <div className="pl-5">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-[9px] font-bold uppercase px-1 py-0.5 rounded bg-purple-500/15 text-purple-400">
                ANSWER
              </span>
              {d.audioPath && (
                <button
                  onClick={() => handlePlay(d)}
                  className="p-0.5 rounded hover:bg-(--surface-overlay) transition-colors"
                >
                  {playingId === d.id ? (
                    <Pause className="w-3 h-3 text-(--accent)" fill="currentColor" />
                  ) : (
                    <Play className="w-3 h-3 text-(--text-muted)" fill="currentColor" />
                  )}
                </button>
              )}
            </div>
            <p className="text-xs text-(--text-secondary) leading-relaxed">{d.answerText || d.answer_text}</p>
          </div>

          {/* Jump to context */}
          {(d.pausedAtSegment != null || d.paused_at_segment != null) && (
            <button
              onClick={() => playSegment?.(d.pausedAtSegment ?? d.paused_at_segment)}
              className="mt-1.5 text-[9px] text-(--text-muted) hover:text-(--accent) transition-colors"
            >
              Asked at segment {(d.pausedAtSegment ?? d.paused_at_segment) + 1} →
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

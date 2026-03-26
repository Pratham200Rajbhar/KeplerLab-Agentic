'use client';

import { useState, useRef, useEffect } from 'react';
import { HelpCircle, Play, Pause } from 'lucide-react';
import { fetchAudioObjectUrl } from '@/lib/api/config';

export default function PodcastDoubtHistory({ doubts = [], playSegment }) {
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(typeof window !== 'undefined' ? new Audio() : null);

  
  useEffect(() => {
    
    
    const audio = audioRef.current;
    return () => {
      if (audio) {
        audio.pause();
        audio.src = '';
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
        <HelpCircle className="w-5 h-5 text-[var(--text-muted)] mx-auto mb-2 opacity-40" />
        <p className="text-xs text-[var(--text-muted)]">No questions asked yet</p>
        <p className="text-[10px] text-[var(--text-muted)] mt-1">Use the Ask button to interrupt the podcast</p>
      </div>
    );
  }

  return (
    <div className="podcast-list">
      {doubts.map((d, i) => (
        <div
          key={d.id || i}
          className="podcast-answer-card podcast-fade-in-item"
          style={{ animationDelay: `${Math.min(i * 18, 180)}ms` }}
        >
          <div className="flex items-start gap-2 mb-2">
            <HelpCircle className="w-3.5 h-3.5 text-[var(--accent)] mt-0.5 shrink-0" />
            <p className="text-xs text-[var(--text-primary)] leading-relaxed">{d.questionText || d.question_text}</p>
          </div>

          <div className="pl-5">
            <div className="flex items-center gap-2 mb-1">
              <span className="podcast-answer-chip">
                ANSWER
              </span>
              {d.audioPath && (
                <button
                  onClick={() => handlePlay(d)}
                  className="p-0.5 rounded hover:bg-[var(--surface-overlay)] transition-colors"
                >
                  {playingId === d.id ? (
                    <Pause className="w-3 h-3 text-[var(--accent)]" fill="currentColor" />
                  ) : (
                    <Play className="w-3 h-3 text-[var(--text-muted)]" fill="currentColor" />
                  )}
                </button>
              )}
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{d.answerText || d.answer_text}</p>
          </div>

          {(d.pausedAtSegment != null || d.paused_at_segment != null) && (
            <button
              onClick={() => playSegment?.(d.pausedAtSegment ?? d.paused_at_segment)}
              className="mt-1.5 text-[9px] text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors"
            >
              Asked at segment {(d.pausedAtSegment ?? d.paused_at_segment) + 1} →
            </button>
          )}
        </div>
      ))}
    </div>
  );
}

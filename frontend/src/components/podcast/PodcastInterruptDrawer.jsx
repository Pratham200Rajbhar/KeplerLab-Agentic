'use client';

import { useState, useRef, useEffect } from 'react';
import { X, Mic, MicOff, Send, Loader2, Play, Pause } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';
import useMicInput from '@/hooks/useMicInput';
import { fetchAudioObjectUrl } from '@/lib/api/config';

export default function PodcastInterruptDrawer() {
  const setInterruptOpen = usePodcastStore((s) => s.setInterruptOpen);
  const askQuestion = usePodcastStore((s) => s.askQuestion);
  const resume = usePodcastStore((s) => s.resume);

  const [question, setQuestion] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [answer, setAnswer] = useState(null);
  const [playingAnswer, setPlayingAnswer] = useState(false);
  const answerAudioRef = useRef(typeof window !== 'undefined' ? new Audio() : null);
  const inputRef = useRef(null);

  const { isRecording, start: startMic, stop: stopMic, cancel: cancelMic } = useMicInput({
    onTranscript: (text) => {
      setQuestion((prev) => (prev ? `${prev} ${text}` : text));
    },
  });

  useEffect(() => {
    inputRef.current?.focus();
    
    const answerAudio = answerAudioRef.current;
    return () => {
      answerAudio?.pause();
      if (answerAudio?.src) {
        URL.revokeObjectURL(answerAudio.src);
      }
    };
  }, []);

  const handleSubmit = async () => {
    if (!question.trim() || submitting) return;
    setSubmitting(true);
    try {
      const result = await askQuestion(question.trim());
      setAnswer(result);
      setQuestion('');

      
      if (result?.audioPath) {
        try {
          const url = await fetchAudioObjectUrl(result.audioPath);
          answerAudioRef.current.src = url;
          answerAudioRef.current.play().catch(() => {});
          setPlayingAnswer(true);
          answerAudioRef.current.onended = () => {
            setPlayingAnswer(false);
            URL.revokeObjectURL(url);
          };
        } catch {
          
        }
      }
    } catch (err) {
      console.error('Failed to ask question:', err);
    } finally {
      setSubmitting(false);
    }
  };

  const toggleAnswerAudio = () => {
    if (playingAnswer) {
      answerAudioRef.current.pause();
      setPlayingAnswer(false);
    } else if (answerAudioRef.current.src) {
      answerAudioRef.current.play().catch(() => {});
      setPlayingAnswer(true);
    }
  };

  const handleClose = () => {
    answerAudioRef.current.pause();
    setInterruptOpen(false);
    resume();
  };

  return (
    <div className="absolute inset-x-0 bottom-0 z-30 animate-slide-up">
      <div className="podcast-drawer p-4">
        <div className="flex items-center justify-between mb-3">
          <h4 className="text-sm font-semibold text-[var(--text-primary)]">Ask a Question</h4>
          <button onClick={handleClose} className="podcast-icon-btn">
            <X className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>

        {answer && (
          <div className="mb-3 podcast-answer-card animate-fade-in">
            <div className="flex items-center gap-2 mb-1.5">
              <span className="podcast-answer-chip">
                ANSWER
              </span>
              {answer.audioPath && (
                <button onClick={toggleAnswerAudio} className="p-0.5 rounded hover:bg-[var(--surface-overlay)]">
                  {playingAnswer ? (
                    <Pause className="w-3 h-3 text-[var(--accent)]" fill="currentColor" />
                  ) : (
                    <Play className="w-3 h-3 text-[var(--text-muted)]" fill="currentColor" />
                  )}
                </button>
              )}
            </div>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed">{answer.answerText}</p>
          </div>
        )}

        <div className="flex items-center gap-2">
          <button
            onClick={isRecording ? stopMic : startMic}
            className={`p-2.5 rounded-xl shrink-0 transition-colors ${
              isRecording
                ? 'bg-red-500/20 text-red-400 animate-pulse'
                : 'bg-[var(--surface)] text-[var(--text-muted)] hover:bg-[var(--surface-overlay)]'
            }`}
          >
            {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
          </button>

          <input
            ref={inputRef}
            type="text"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleSubmit()}
            placeholder="Type your question..."
            className="podcast-drawer-field flex-1 px-3 py-2.5 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />

          <button
            onClick={handleSubmit}
            disabled={!question.trim() || submitting}
            className="podcast-play-btn h-10 w-10 rounded-xl disabled:opacity-40 shrink-0"
          >
            {submitting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Send className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </div>
  );
}

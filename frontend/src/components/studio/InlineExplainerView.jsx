'use client';

import { useState, useEffect, useRef } from 'react';
import { Play, Pause, SkipBack, SkipForward, List, Loader2 } from 'lucide-react';
import { fetchExplainerVideoBlob } from '@/lib/api/explainer';
import { useToast } from '@/stores/useToastStore';

export default function InlineExplainerView({ explainer, onClose }) {
  const toast = useToast();
  
  const onCloseRef = useRef(onClose);
  onCloseRef.current = onClose;
  const toastRef = useRef(toast);
  toastRef.current = toast;
  const [videoUrl, setVideoUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [isPlaying, setIsPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [showChapters, setShowChapters] = useState(false);
  const videoRef = useRef(null);
  const videoUrlRef = useRef(null); 

  const chapters = explainer?.data?.chapters || [];

  useEffect(() => {
    if (!explainer?.data?.explainer_id) return;
    let cancelled = false;

    async function loadVideo() {
      try {
        setLoading(true);
        const url = await fetchExplainerVideoBlob(explainer.data.explainer_id);
        if (!cancelled) {
          videoUrlRef.current = url;
          setVideoUrl(url);
        } else {
          URL.revokeObjectURL(url);
        }
      } catch (err) {
        if (!cancelled) {
          toastRef.current.error(err.message || 'Failed to load video');
          onCloseRef.current?.();
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadVideo();
    return () => {
      cancelled = true;
      if (videoUrlRef.current) {
        URL.revokeObjectURL(videoUrlRef.current);
        videoUrlRef.current = null;
      }
    };
  }, [explainer?.data?.explainer_id]);

  const togglePlay = () => {
    const vid = videoRef.current;
    if (!vid) return;
    if (vid.paused) {
      vid.play();
      setIsPlaying(true);
    } else {
      vid.pause();
      setIsPlaying(false);
    }
  };

  const jumpToChapter = (chapter) => {
    const vid = videoRef.current;
    if (!vid) return;
    vid.currentTime = chapter.startTime || 0;
    vid.play();
    setIsPlaying(true);
    setShowChapters(false);
  };

  const skip = (delta) => {
    const vid = videoRef.current;
    if (!vid) return;
    vid.currentTime = Math.max(0, Math.min(vid.currentTime + delta, vid.duration));
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-[var(--accent)] animate-spin" />
        <span className="ml-2 text-sm text-[var(--text-muted)]">Loading video...</span>
      </div>
    );
  }

  return (
    <div className="space-y-3 animate-fade-in">
      {}
      <div className="relative rounded-xl overflow-hidden bg-black aspect-video">
        <video
          ref={videoRef}
          src={videoUrl}
          className="w-full h-full"
          onTimeUpdate={() => setCurrentTime(videoRef.current?.currentTime || 0)}
          onLoadedMetadata={() => setDuration(videoRef.current?.duration || 0)}
          onEnded={() => setIsPlaying(false)}
          onPlay={() => setIsPlaying(true)}
          onPause={() => setIsPlaying(false)}
        />
      </div>

      {}
      <div className="flex items-center gap-3 px-2">
        <button onClick={() => skip(-10)} className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors" aria-label="Skip back 10 seconds">
          <SkipBack className="w-4 h-4 text-[var(--text-secondary)]" />
        </button>
        <button onClick={togglePlay} className="p-2 rounded-xl bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors" aria-label={isPlaying ? 'Pause' : 'Play'}>
          {isPlaying ? <Pause className="w-4 h-4" fill="currentColor" /> : <Play className="w-4 h-4" fill="currentColor" />}
        </button>
        <button onClick={() => skip(10)} className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors" aria-label="Skip forward 10 seconds">
          <SkipForward className="w-4 h-4 text-[var(--text-secondary)]" />
        </button>

        {}
        <div className="flex-1 mx-2">
          <div
            className="h-1 rounded-full bg-[var(--surface)] cursor-pointer"
            onClick={(e) => {
              const rect = e.currentTarget.getBoundingClientRect();
              const pct = (e.clientX - rect.left) / rect.width;
              if (videoRef.current) videoRef.current.currentTime = pct * duration;
            }}
          >
            <div
              className="h-full rounded-full bg-[var(--accent)] transition-all"
              style={{ width: `${duration ? (currentTime / duration) * 100 : 0}%` }}
            />
          </div>
        </div>

        <span className="text-[10px] text-[var(--text-muted)] tabular-nums">
          {formatTime(currentTime)} / {formatTime(duration)}
        </span>

        {chapters.length > 0 && (
          <button
            onClick={() => setShowChapters(!showChapters)}
            className={`p-1.5 rounded-lg transition-colors ${showChapters ? 'bg-[var(--accent)] text-[var(--accent)]' : 'hover:bg-[var(--surface-overlay)] text-[var(--text-muted)]'}`}
            aria-label={showChapters ? 'Hide chapters' : 'Show chapters'}
          >
            <List className="w-4 h-4" />
          </button>
        )}
      </div>

      {}
      {showChapters && chapters.length > 0 && (
        <div className="space-y-1 px-2 animate-fade-in">
          {chapters.map((ch, i) => (
            <button
              key={ch.title || i}
              onClick={() => jumpToChapter(ch)}
              className="w-full flex items-center gap-2 px-3 py-2 rounded-lg text-left hover:bg-[var(--surface-overlay)] transition-colors"
            >
              <span className="text-[10px] text-[var(--text-muted)] tabular-nums w-10">{formatTime(ch.startTime || 0)}</span>
              <span className="text-xs text-[var(--text-primary)] truncate">{ch.title || `Chapter ${i + 1}`}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function formatTime(seconds) {
  if (!seconds || isNaN(seconds)) return '0:00';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return `${m}:${s.toString().padStart(2, '0')}`;
}

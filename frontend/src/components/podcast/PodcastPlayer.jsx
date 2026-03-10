'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play, Pause, SkipBack, SkipForward,
  MessageCircle, BookOpen, HelpCircle, Bookmark, ChevronLeft
} from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';
import usePodcastPlayer from '@/hooks/usePodcastPlayer';
import PodcastTranscript from './PodcastTranscript';
import PodcastChapterBar from './PodcastChapterBar';
import PodcastInterruptDrawer from './PodcastInterruptDrawer';
import PodcastDoubtHistory from './PodcastDoubtHistory';
import PodcastExportBar from './PodcastExportBar';

const SPEEDS = [0.5, 0.75, 1, 1.25, 1.5, 2];

function formatTime(seconds) {
  if (!seconds || isNaN(seconds) || seconds < 0) return '0:00';
  const s = Math.floor(seconds);
  const m = Math.floor(s / 60);
  return `${m}:${(s % 60).toString().padStart(2, '0')}`;
}

function buildTabs(doubtsCount) {
  return [
    { id: 'transcript', label: 'Transcript', icon: BookOpen },
    { id: 'chapters',   label: 'Chapters',   icon: BookOpen },
    { id: 'doubts',     label: doubtsCount > 0 ? `Q&A (${doubtsCount})` : 'Q&A', icon: HelpCircle },
  ];
}

export default function PodcastPlayer() {
  const session      = usePodcastStore((s) => s.session);
  const segments     = usePodcastStore((s) => s.segments);
  const chapters     = usePodcastStore((s) => s.chapters);
  const doubts       = usePodcastStore((s) => s.doubts);
  const bookmarks    = usePodcastStore((s) => s.bookmarks);
  const interruptOpen   = usePodcastStore((s) => s.interruptOpen);
  const setInterruptOpen = usePodcastStore((s) => s.setInterruptOpen);
  const setPhase     = usePodcastStore((s) => s.setPhase);
  const addBookmark  = usePodcastStore((s) => s.addBookmark);

  const {
    isPlaying,
    currentSegmentIndex,
    playbackSpeed,
    seekTo,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    playSegment,
  } = usePodcastPlayer();

  const [activeTab, setActiveTab]       = useState('transcript');
  const [currentTime, setCurrentTime]   = useState(0);
  const [duration, setDuration]         = useState(0);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);

  
  const getAudio = () => usePodcastStore.getState()._audioEl;

  
  useEffect(() => {
    const audio = getAudio();
    if (!audio) return;

    const onTimeUpdate    = () => setCurrentTime(audio.currentTime || 0);
    const onDurationChange = () => setDuration(audio.duration && isFinite(audio.duration) ? audio.duration : 0);
    const onLoadedMeta    = () => setDuration(audio.duration && isFinite(audio.duration) ? audio.duration : 0);

    audio.addEventListener('timeupdate',     onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);
    audio.addEventListener('loadedmetadata', onLoadedMeta);

    return () => {
      audio.removeEventListener('timeupdate',     onTimeUpdate);
      audio.removeEventListener('durationchange', onDurationChange);
      audio.removeEventListener('loadedmetadata', onLoadedMeta);
    };
    
  }, [currentSegmentIndex]);

  
  const seekbarRef = useRef(null);
  const handleSeekbarClick = useCallback((e) => {
    const bar = seekbarRef.current;
    if (!bar || !duration) return;
    const { left, width } = bar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - left) / width));
    seekTo(pct * duration);
  }, [duration, seekTo]);

  
  const completedMs    = segments.slice(0, currentSegmentIndex).reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const totalDurationMs = segments.reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const overallPct     = totalDurationMs > 0 ? (completedMs / totalDurationMs) * 100 : 0;

  
  const segPct = duration > 0 ? Math.min((currentTime / duration) * 100, 100) : 0;

  const currentSeg = segments[currentSegmentIndex];
  const isBookmarked = bookmarks.some((b) => b.segmentIndex === currentSegmentIndex);

  const handleBookmark = async () => {
    if (!isBookmarked) {
      try { await addBookmark(currentSegmentIndex, `Bookmark at segment ${currentSegmentIndex + 1}`); }
      catch (err) { console.error('Failed to bookmark:', err); }
    }
  };

  return (
    <div className="flex flex-col h-full animate-fade-in">

      {}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-[var(--border)] shrink-0">
        <button onClick={() => setPhase('idle')} className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors">
          <ChevronLeft className="w-4 h-4 text-[var(--text-muted)]" />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-[var(--text-primary)] truncate">{session?.title || 'Podcast'}</p>
          <p className="text-[10px] text-[var(--text-muted)]">{segments.length} segments</p>
        </div>
        <PodcastExportBar />
      </div>

      {}
      <div className="px-3 pt-2 shrink-0">
        <div className="h-0.5 rounded-full bg-[var(--surface-overlay)] overflow-hidden">
          <div className="h-full bg-[var(--accent)] rounded-full transition-all duration-500" style={{ width: `${overallPct}%` }} />
        </div>
      </div>

      {}
      {currentSeg && (
        <div className="mx-3 mt-2.5 p-3 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] shrink-0">
          <div className="flex items-center gap-2 mb-1.5">
            <span className={`text-[9px] font-bold uppercase tracking-wide px-1.5 py-0.5 rounded-md ${
              (currentSeg.speaker === 'host' || currentSeg.speaker === 'HOST')
                ? 'bg-blue-500/15 text-blue-400'
                : 'bg-purple-500/15 text-purple-400'
            }`}>
              {currentSeg.speaker || 'Speaker'}
            </span>
            <span className="text-[10px] text-[var(--text-muted)] ml-auto">
              {currentSegmentIndex + 1} / {segments.length}
            </span>
          </div>
          <p className="text-xs text-[var(--text-secondary)] line-clamp-2 leading-relaxed">
            {currentSeg.text}
          </p>
        </div>
      )}

      {}
      <div className="px-3 mt-3 shrink-0">
        {}
        <div
          ref={seekbarRef}
          onClick={handleSeekbarClick}
          className="relative h-2 rounded-full bg-[var(--surface-overlay)] cursor-pointer group"
        >
          {}
          <div
            className="h-full rounded-full bg-[var(--accent)] transition-none"
            style={{ width: `${segPct}%` }}
          />
          {}
          <div
            className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full bg-white border-2 border-[var(--accent)] shadow opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none"
            style={{ left: `calc(${segPct}% - 6px)` }}
          />
        </div>
        {}
        <div className="flex justify-between mt-1">
          <span className="text-[9px] text-[var(--text-muted)] tabular-nums">{formatTime(currentTime)}</span>
          <span className="text-[9px] text-[var(--text-muted)] tabular-nums">{formatTime(duration)}</span>
        </div>
      </div>

      {}
      <div className="flex items-center justify-center gap-4 px-3 py-2 shrink-0">
        <button
          onClick={prevSegment}
          disabled={currentSegmentIndex === 0}
          className="p-2 rounded-xl hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-30"
        >
          <SkipBack className="w-5 h-5 text-[var(--text-secondary)]" />
        </button>

        <button
          onClick={togglePlayPause}
          className="w-11 h-11 rounded-2xl bg-[var(--accent)] text-white flex items-center justify-center hover:opacity-90 transition-opacity shadow-lg"
        >
          {isPlaying
            ? <Pause className="w-5 h-5" fill="currentColor" />
            : <Play  className="w-5 h-5 ml-0.5" fill="currentColor" />
          }
        </button>

        <button
          onClick={nextSegment}
          disabled={currentSegmentIndex >= segments.length - 1}
          className="p-2 rounded-xl hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-30"
        >
          <SkipForward className="w-5 h-5 text-[var(--text-secondary)]" />
        </button>
      </div>

      {}
      <div className="flex items-center justify-center gap-3 px-3 pb-3 shrink-0">
        {}
        <div className="relative">
          <button
            onClick={() => setShowSpeedMenu((v) => !v)}
            className="px-2.5 py-1 rounded-lg text-[10px] font-bold text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors tabular-nums border border-[var(--border)]"
          >
            {playbackSpeed}×
          </button>
          {showSpeedMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowSpeedMenu(false)} />
              <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 z-50 py-1 min-w-[64px] rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] shadow-lg overflow-hidden">
                {SPEEDS.map((s) => (
                  <button
                    key={s}
                    onClick={() => { changeSpeed(s); setShowSpeedMenu(false); }}
                    className={`w-full px-3 py-1.5 text-xs text-center transition-colors ${
                      playbackSpeed === s
                        ? 'text-[var(--accent)] bg-[var(--accent-subtle)]'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)]'
                    }`}
                  >
                    {s}×
                  </button>
                ))}
              </div>
            </>
          )}
        </div>

        <button
          onClick={handleBookmark}
          title="Bookmark"
          className={`p-1.5 rounded-lg transition-colors ${isBookmarked ? 'text-[var(--accent)]' : 'text-[var(--text-muted)] hover:bg-[var(--surface-overlay)]'}`}
        >
          <Bookmark className={`w-4 h-4 ${isBookmarked ? 'fill-current' : ''}`} />
        </button>

        <button
          onClick={() => setInterruptOpen(true)}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold border border-[var(--accent)] text-[var(--accent)] hover:bg-[var(--accent-subtle)] transition-colors"
        >
          <MessageCircle className="w-3.5 h-3.5" /> Ask
        </button>
      </div>

      {}
      <div className="flex border-b border-[var(--border)] shrink-0">
        {buildTabs(doubts.length).map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-medium transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'border-[var(--accent)] text-[var(--accent)]'
                : 'border-transparent text-[var(--text-muted)] hover:text-[var(--text-secondary)]'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {}
      <div className="flex-1 overflow-y-auto min-h-0">
        {activeTab === 'transcript' && (
          <PodcastTranscript segments={segments} currentIndex={currentSegmentIndex} onSegmentClick={(i) => playSegment(i)} />
        )}
        {activeTab === 'chapters' && (
          <PodcastChapterBar chapters={chapters} currentSegmentIndex={currentSegmentIndex} bookmarks={bookmarks} onChapterClick={(ch) => playSegment(ch.startSegment)} />
        )}
        {activeTab === 'doubts' && (
          <PodcastDoubtHistory doubts={doubts} playSegment={playSegment} />
        )}
      </div>

      {interruptOpen && <PodcastInterruptDrawer />}
    </div>
  );
}

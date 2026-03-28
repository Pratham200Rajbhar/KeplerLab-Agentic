'use client';

import { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import {
  Play, Pause, SkipBack, SkipForward,
  MessageCircle, BookOpen, HelpCircle, Bookmark, ChevronLeft, List, Waves
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
    { id: 'chapters', label: 'Chapters', icon: List },
    { id: 'doubts',     label: doubtsCount > 0 ? `Q&A (${doubtsCount})` : 'Q&A', icon: HelpCircle },
  ];
}

export default function PodcastPlayer({ onClose }) {
  const session = usePodcastStore((s) => s.session);
  const segments = usePodcastStore((s) => s.segments);
  const chapters = usePodcastStore((s) => s.chapters);
  const doubts = usePodcastStore((s) => s.doubts);
  const bookmarks = usePodcastStore((s) => s.bookmarks);
  const audioElRef = usePodcastStore((s) => s._audioElRef);
  const interruptOpen = usePodcastStore((s) => s.interruptOpen);
  const setInterruptOpen = usePodcastStore((s) => s.setInterruptOpen);
  const addBookmark = usePodcastStore((s) => s.addBookmark);

  const {
    isPlaying,
    currentSegmentIndex,
    playbackSpeed,
    seekToOverall,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    playSegment,
  } = usePodcastPlayer();

  const [activeTab, setActiveTab]       = useState('transcript');
  const [currentTime, setCurrentTime]   = useState(0);
  const [showSpeedMenu, setShowSpeedMenu] = useState(false);
  const lastUiTimeRef = useRef(0);

  useEffect(() => {
    const audio = audioElRef?.current;
    if (!audio) return;

    const throttledTimeUpdate = () => {
      const next = audio.currentTime || 0;
      if (Math.abs(next - lastUiTimeRef.current) >= 0.2 || audio.paused || next === 0) {
        lastUiTimeRef.current = next;
        setCurrentTime(next);
      }
    };

    audio.addEventListener('timeupdate',     throttledTimeUpdate);

    return () => {
      audio.removeEventListener('timeupdate',     throttledTimeUpdate);
    };

  }, [audioElRef]);

  const { totalDurationSec, overallCurrentSec, overallPct } = useMemo(() => {
    const completedBeforeCurrentSec = segments
      .slice(0, currentSegmentIndex)
      .reduce((sum, seg) => sum + ((seg.durationMs || 0) / 1000), 0);
    const total = segments.reduce((sum, seg) => sum + ((seg.durationMs || 0) / 1000), 0);
    const current = completedBeforeCurrentSec + Math.max(0, currentTime || 0);
    return {
      totalDurationSec: total,
      overallCurrentSec: current,
      overallPct: total > 0 ? Math.min((current / total) * 100, 100) : 0,
    };
  }, [segments, currentSegmentIndex, currentTime]);

  const seekbarRef = useRef(null);
  const handleSeekbarClick = useCallback((e) => {
    const bar = seekbarRef.current;
    if (!bar || !totalDurationSec) return;
    const { left, width } = bar.getBoundingClientRect();
    const pct = Math.max(0, Math.min(1, (e.clientX - left) / width));
    seekToOverall(pct * totalDurationSec);
  }, [totalDurationSec, seekToOverall]);

  const currentSeg = segments[currentSegmentIndex];
  const isBookmarked = useMemo(
    () => bookmarks.some((b) => b.segmentIndex === currentSegmentIndex),
    [bookmarks, currentSegmentIndex],
  );
  const tabs = useMemo(() => buildTabs(doubts.length), [doubts.length]);

  const handleBookmark = useCallback(async () => {
    if (!isBookmarked) {
      try { await addBookmark(currentSegmentIndex, `Bookmark at segment ${currentSegmentIndex + 1}`); }
      catch (err) { console.error('Failed to bookmark:', err); }
    }
  }, [isBookmarked, addBookmark, currentSegmentIndex]);

  if (!session) {
    return null;
  }

  return (
    <div className="podcast-shell podcast-player-shell flex flex-col h-full animate-fade-in">
      <div className="podcast-hero shrink-0">
        <div className="flex items-start gap-2.5">
          <button
            onClick={onClose}
            className="podcast-icon-btn mt-0.5"
            aria-label="Back to podcast library"
          >
            <ChevronLeft className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
          <div className="flex-1 min-w-0">
            <p className="podcast-eyebrow">Studio / AI Podcast</p>
            <p className="podcast-title truncate">{session?.title || 'Podcast Session'}</p>
            <div className="podcast-subline">
              <span>{segments.length} segments</span>
              <span className="podcast-dot" />
              <span>{chapters.length} chapters</span>
            </div>
          </div>
          <PodcastExportBar />
        </div>

        <div className="mt-3">
          <div className="podcast-overall-track">
            <div className="podcast-overall-fill" style={{ width: `${overallPct}%` }} />
          </div>
          <p className="podcast-overall-meta">Session progress {Math.round(overallPct)}%</p>
        </div>
      </div>

      {!segments.length && (
        <div className="mx-3 mt-3 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] px-4 py-5 text-center">
          <p className="text-sm font-medium text-[var(--text-primary)]">Preparing audio segments...</p>
          <p className="text-xs text-[var(--text-muted)] mt-1">The player will unlock as soon as generation completes.</p>
        </div>
      )}

      {currentSeg && (
        <div className="podcast-now-card mx-3 mt-2 shrink-0">
          <div className="flex items-center gap-2 mb-1.5">
            <Waves className="w-3.5 h-3.5 text-[var(--accent)]" />
            <span className="podcast-mini-label">Now playing</span>
            <span className="text-[10px] text-[var(--text-muted)] ml-auto tabular-nums">
              {currentSegmentIndex + 1} / {segments.length}
            </span>
          </div>

          <div className="flex items-start gap-2">
            <span className={`podcast-speaker-chip ${(currentSeg.speaker === 'host' || currentSeg.speaker === 'HOST') ? 'host' : 'guest'}`}>
              {currentSeg.speaker || 'Speaker'}
            </span>
            <p className="text-xs text-[var(--text-secondary)] leading-relaxed line-clamp-3">
              {currentSeg.text}
            </p>
          </div>
        </div>
      )}

      <div className="podcast-player-controls px-3 mt-2.5 shrink-0">
        <div
          ref={seekbarRef}
          onClick={handleSeekbarClick}
          className="podcast-seekbar"
          role="slider"
          aria-valuemin={0}
          aria-valuemax={totalDurationSec || 0}
          aria-valuenow={overallCurrentSec || 0}
          aria-label="Seek full podcast timeline"
        >
          <div
            className="podcast-seekbar-fill"
            style={{ width: `${overallPct}%` }}
          />
          <div
            className="podcast-seekbar-thumb"
            style={{ left: `calc(${overallPct}% - 7px)` }}
          />
        </div>

        <div className="flex justify-between mt-1.5">
          <span className="text-[10px] text-[var(--text-muted)] tabular-nums">{formatTime(overallCurrentSec)}</span>
          <span className="text-[10px] text-[var(--text-muted)] tabular-nums">{formatTime(totalDurationSec)}</span>
        </div>
      </div>

      <div className="podcast-transport shrink-0">
        <button
          onClick={prevSegment}
          disabled={currentSegmentIndex === 0}
          className="podcast-icon-btn"
          aria-label="Previous segment"
        >
          <SkipBack className="w-5 h-5 text-[var(--text-secondary)]" />
        </button>

        <button
          onClick={togglePlayPause}
          className="podcast-play-btn"
          aria-label={isPlaying ? 'Pause' : 'Play'}
        >
          {isPlaying
            ? <Pause className="w-5 h-5" fill="currentColor" />
            : <Play  className="w-5 h-5 ml-0.5" fill="currentColor" />
          }
        </button>

        <button
          onClick={nextSegment}
          disabled={currentSegmentIndex >= segments.length - 1}
          className="podcast-icon-btn"
          aria-label="Next segment"
        >
          <SkipForward className="w-5 h-5 text-[var(--text-secondary)]" />
        </button>
      </div>

      <div className="podcast-tools shrink-0">
        <div className="relative">
          <button
            onClick={() => setShowSpeedMenu((v) => !v)}
            className="podcast-pill-btn"
            aria-label="Playback speed"
          >
            {playbackSpeed}×
          </button>
          {showSpeedMenu && (
            <>
              <div className="fixed inset-0 z-40" onClick={() => setShowSpeedMenu(false)} />
              <div className="absolute bottom-full mb-1 left-1/2 -translate-x-1/2 z-50 py-1 min-w-[72px] rounded-xl border border-[var(--border)] bg-[var(--surface-raised)] shadow-lg overflow-hidden">
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
          className={`podcast-pill-btn ${isBookmarked ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`}
        >
          <Bookmark className={`w-4 h-4 ${isBookmarked ? 'fill-current' : ''}`} />
        </button>

        <button
          onClick={() => setInterruptOpen(true)}
          className="podcast-ask-btn"
        >
          <MessageCircle className="w-3.5 h-3.5" /> Ask
        </button>
      </div>

      <div className="podcast-tab-rail shrink-0">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`podcast-tab-btn ${
              activeTab === tab.id
                ? 'active'
                : ''
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto min-h-0 px-2 pb-2">
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

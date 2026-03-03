'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  Play, Pause, SkipBack, SkipForward, Volume2, VolumeX,
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
const TABS = [
  { id: 'transcript', label: 'Transcript', icon: BookOpen },
  { id: 'chapters', label: 'Chapters', icon: BookOpen },
  { id: 'doubts', label: 'Q&A', icon: HelpCircle },
];

export default function PodcastPlayer() {
  const session = usePodcastStore((s) => s.session);
  const segments = usePodcastStore((s) => s.segments);
  const chapters = usePodcastStore((s) => s.chapters);
  const doubts = usePodcastStore((s) => s.doubts);
  const bookmarks = usePodcastStore((s) => s.bookmarks);
  const interruptOpen = usePodcastStore((s) => s.interruptOpen);
  const setInterruptOpen = usePodcastStore((s) => s.setInterruptOpen);
  const setPhase = usePodcastStore((s) => s.setPhase);
  const addBookmark = usePodcastStore((s) => s.addBookmark);

  const {
    isPlaying,
    currentSegmentIndex,
    playbackSpeed,
    togglePlayPause,
    nextSegment,
    prevSegment,
    changeSpeed,
    playSegment,
  } = usePodcastPlayer();

  const [activeTab, setActiveTab] = useState('transcript');
  const [currentTime, setCurrentTime] = useState(0);
  const [segmentDuration, setSegmentDuration] = useState(0);
  const audioRef = useRef(usePodcastStore.getState()._audioEl);

  // Track time updates
  useEffect(() => {
    const audio = audioRef.current;
    if (!audio) return;

    const onTimeUpdate = () => setCurrentTime(audio.currentTime);
    const onDurationChange = () => setSegmentDuration(audio.duration || 0);

    audio.addEventListener('timeupdate', onTimeUpdate);
    audio.addEventListener('durationchange', onDurationChange);

    return () => {
      audio.removeEventListener('timeupdate', onTimeUpdate);
      audio.removeEventListener('durationchange', onDurationChange);
    };
  }, []);

  // Total progress
  const totalDuration = segments.reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const elapsed = segments.slice(0, currentSegmentIndex).reduce((s, seg) => s + (seg.durationMs || 0), 0);
  const totalPct = totalDuration > 0 ? (elapsed / totalDuration) * 100 : 0;

  const currentSeg = segments[currentSegmentIndex];

  const handleSpeedCycle = () => {
    const idx = SPEEDS.indexOf(playbackSpeed);
    const next = SPEEDS[(idx + 1) % SPEEDS.length];
    changeSpeed(next);
  };

  const handleBookmark = async () => {
    try {
      await addBookmark(currentSegmentIndex, `Bookmark at segment ${currentSegmentIndex + 1}`);
    } catch (err) {
      console.error('Failed to bookmark:', err);
    }
  };

  return (
    <div className="flex flex-col h-full animate-fade-in">
      {/* Header */}
      <div className="flex items-center gap-2 px-3 py-2.5 border-b border-(--border)">
        <button
          onClick={() => setPhase('idle')}
          className="p-1 rounded-lg hover:bg-(--surface-overlay) transition-colors"
        >
          <ChevronLeft className="w-4 h-4 text-(--text-muted)" />
        </button>
        <div className="flex-1 min-w-0">
          <p className="text-xs font-medium text-(--text-primary) truncate">
            {session?.title || 'Podcast'}
          </p>
          <p className="text-[10px] text-(--text-muted)">
            {segments.length} segments
          </p>
        </div>
        <PodcastExportBar />
      </div>

      {/* Progress bar */}
      <div className="px-3 pt-2">
        <div className="h-1 rounded-full bg-(--surface) overflow-hidden">
          <div
            className="h-full bg-(--accent) rounded-full transition-all"
            style={{ width: `${totalPct}%` }}
          />
        </div>
      </div>

      {/* Now playing */}
      {currentSeg && (
        <div className="px-3 py-2">
          <div className="flex items-center gap-2">
            <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
              currentSeg.speaker === 'host'
                ? 'bg-(--accent)/15 text-(--accent)'
                : 'bg-purple-500/15 text-purple-400'
            }`}>
              {currentSeg.speaker || 'Speaker'}
            </span>
            <p className="text-xs text-(--text-secondary) truncate flex-1">
              {currentSeg.text?.slice(0, 80)}...
            </p>
          </div>
        </div>
      )}

      {/* Transport controls */}
      <div className="flex items-center justify-center gap-4 px-3 py-3">
        <button onClick={prevSegment} className="p-2 rounded-xl hover:bg-(--surface-overlay) transition-colors">
          <SkipBack className="w-5 h-5 text-(--text-secondary)" />
        </button>

        <button
          onClick={togglePlayPause}
          className="p-3 rounded-2xl bg-(--accent) text-white hover:bg-(--accent-light) transition-colors shadow-lg shadow-(--accent)/20"
        >
          {isPlaying ? <Pause className="w-6 h-6" fill="currentColor" /> : <Play className="w-6 h-6" fill="currentColor" />}
        </button>

        <button onClick={nextSegment} className="p-2 rounded-xl hover:bg-(--surface-overlay) transition-colors">
          <SkipForward className="w-5 h-5 text-(--text-secondary)" />
        </button>
      </div>

      {/* Secondary controls */}
      <div className="flex items-center justify-center gap-3 px-3 pb-3">
        <button
          onClick={handleSpeedCycle}
          className="px-2 py-1 rounded-lg text-[10px] font-bold text-(--text-muted) hover:bg-(--surface-overlay) transition-colors tabular-nums"
        >
          {playbackSpeed}x
        </button>
        <button
          onClick={handleBookmark}
          className="p-1.5 rounded-lg text-(--text-muted) hover:bg-(--surface-overlay) hover:text-(--accent) transition-colors"
        >
          <Bookmark className="w-4 h-4" />
        </button>
        <button
          onClick={() => setInterruptOpen(true)}
          className="flex items-center gap-1 px-2.5 py-1 rounded-lg text-[10px] font-medium text-(--accent) hover:bg-(--accent)/10 transition-colors"
        >
          <MessageCircle className="w-3.5 h-3.5" /> Ask
        </button>
      </div>

      {/* Tab bar */}
      <div className="flex border-b border-(--border)">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-medium transition-colors border-b-2 ${
              activeTab === tab.id
                ? 'border-(--accent) text-(--accent)'
                : 'border-transparent text-(--text-muted) hover:text-(--text-secondary)'
            }`}
          >
            <tab.icon className="w-3.5 h-3.5" />
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto">
        {activeTab === 'transcript' && (
          <PodcastTranscript
            segments={segments}
            currentIndex={currentSegmentIndex}
            onSegmentClick={(i) => playSegment(i)}
          />
        )}
        {activeTab === 'chapters' && (
          <PodcastChapterBar
            chapters={chapters}
            currentSegmentIndex={currentSegmentIndex}
            bookmarks={bookmarks}
            onChapterClick={(ch) => playSegment(ch.startSegment)}
          />
        )}
        {activeTab === 'doubts' && (
          <PodcastDoubtHistory
            doubts={doubts}
            playSegment={playSegment}
          />
        )}
      </div>

      {/* QA Drawer */}
      {interruptOpen && <PodcastInterruptDrawer />}
    </div>
  );
}

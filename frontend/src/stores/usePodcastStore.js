import { create } from 'zustand';
import { fetchAudioObjectUrl } from '@/lib/api/config';
import {
  createPodcastSession,
  getPodcastSession,
  listPodcastSessions,
  startPodcastGeneration,
  submitPodcastQuestion,
  getPodcastDoubts,
  addPodcastBookmark,
  deletePodcastBookmark,
  addPodcastAnnotation,
  deletePodcastAnnotation,
  deletePodcastSession,
  triggerPodcastExport,
  generatePodcastSummary,
} from '@/lib/api/podcast';

export const SESSION_STATUS = {
  CREATED: 'created',
  SCRIPT_GEN: 'script_generating',
  AUDIO_GEN: 'audio_generating',
  READY: 'ready',
  PLAYING: 'playing',
  PAUSED: 'paused',
  COMPLETED: 'completed',
  FAILED: 'failed',
};

const usePodcastStore = create((set, get) => ({
  // ── Session state ──
  session: null,
  sessions: [],
  segments: [],
  chapters: [],
  doubts: [],
  bookmarks: [],
  annotations: [],

  // ── Playback state ──
  currentSegmentIndex: 0,
  isPlaying: false,
  playbackSpeed: 1,
  currentTime: 0,
  totalElapsed: 0,

  // ── UI state ──
  phase: 'idle', // idle | generating | player
  interruptOpen: false,
  generationProgress: null,
  error: null,
  loading: false,

  // ── Audio refs (not serialized) ──
  _audioEl: typeof window !== 'undefined' ? new Audio() : null,
  _audioCache: new Map(),
  _eventsBound: false,

  // ── Cleanup ──
  resetPodcast: () => {
    const { _audioEl, _audioCache } = get();
    if (_audioEl) {
      _audioEl.pause();
      _audioEl.src = '';
    }
    _audioCache.forEach(url => URL.revokeObjectURL(url));
    _audioCache.clear();
    set({
      session: null,
      sessions: [],
      segments: [],
      chapters: [],
      doubts: [],
      bookmarks: [],
      annotations: [],
      currentSegmentIndex: 0,
      isPlaying: false,
      phase: 'idle',
      generationProgress: null,
      error: null,
    });
  },

  // ── Load sessions ──
  loadSessions: async (notebookId, isDraft) => {
    if (!notebookId || isDraft) return;
    try {
      const data = await listPodcastSessions(notebookId);
      set({ sessions: data || [] });
    } catch (err) {
      console.error('Failed to load podcast sessions:', err);
    }
  },

  // ── Load session ──
  loadSession: async (sessionId) => {
    try {
      set({ loading: true });
      const data = await getPodcastSession(sessionId);
      const status = data.status;
      let phase = 'idle';
      if ([SESSION_STATUS.READY, SESSION_STATUS.PLAYING, SESSION_STATUS.PAUSED, SESSION_STATUS.COMPLETED].includes(status)) {
        phase = 'player';
      } else if ([SESSION_STATUS.SCRIPT_GEN, SESSION_STATUS.AUDIO_GEN].includes(status)) {
        phase = 'generating';
      }
      set({
        session: data,
        segments: data.segments || [],
        chapters: data.chapters || [],
        doubts: data.doubts || [],
        bookmarks: data.bookmarks || [],
        annotations: data.annotations || [],
        currentSegmentIndex: data.currentSegment || 0,
        phase,
      });
    } catch (err) {
      set({ error: err.message });
    } finally {
      set({ loading: false });
    }
  },

  // ── Create session ──
  _creating: false,
  create: async ({ mode, topic, language, hostVoice, guestVoice }, notebookId, selectedSources) => {
    if (!notebookId || get()._creating) return;
    set({ _creating: true, loading: true, error: null });
    try {
      const data = await createPodcastSession({
        notebook_id: notebookId,
        material_ids: [...selectedSources],
        mode,
        topic: topic || undefined,
        language: language || 'en',
        host_voice: hostVoice || undefined,
        guest_voice: guestVoice || undefined,
      });
      set({ session: data });
      return data;
    } catch (err) {
      set({ error: err.message });
      throw err;
    } finally {
      set({ loading: false, _creating: false });
    }
  },

  // ── Start generation ──
  startGeneration: async (sessionId) => {
    try {
      set({
        error: null,
        phase: 'generating',
        generationProgress: { stage: 'script', pct: 0, message: 'Starting generation…' },
      });
      await startPodcastGeneration(sessionId || get().session?.id);
    } catch (err) {
      set({ error: err.message, phase: 'idle' });
    }
  },

  // ── Playback ──
  playSegment: async (index) => {
    const { segments, playbackSpeed, _audioEl, _audioCache } = get();
    if (!segments[index]) return;
    const seg = segments[index];
    if (!seg.audioPath) return;

    set({ currentSegmentIndex: index, currentTime: 0 });

    try {
      let blobUrl = _audioCache.get(seg.audioPath);
      if (!blobUrl) {
        blobUrl = await fetchAudioObjectUrl(seg.audioPath);
        _audioCache.set(seg.audioPath, blobUrl);
      }

      _audioEl.pause();
      _audioEl.src = blobUrl;
      _audioEl.playbackRate = playbackSpeed;
      await _audioEl.play();
      set({ isPlaying: true });
    } catch (err) {
      console.error('Failed to play segment', index, err);
      set({ isPlaying: false });
    }
  },

  prefetchSegment: async (index) => {
    const { segments, _audioCache } = get();
    if (!segments[index]) return;
    const seg = segments[index];
    if (!seg.audioPath || _audioCache.has(seg.audioPath)) return;
    try {
      const blobUrl = await fetchAudioObjectUrl(seg.audioPath);
      _audioCache.set(seg.audioPath, blobUrl);
    } catch { /* non-fatal */ }
  },

  pause: () => {
    get()._audioEl?.pause();
    set({ isPlaying: false });
  },

  resume: () => {
    const { _audioEl, currentSegmentIndex, playSegment } = get();
    if (!_audioEl?.src || _audioEl.src === window.location.href) {
      playSegment(currentSegmentIndex);
      return;
    }
    _audioEl.play().catch(() => {});
    set({ isPlaying: true });
  },

  togglePlayPause: () => {
    if (get().isPlaying) get().pause();
    else get().resume();
  },

  nextSegment: () => {
    const { currentSegmentIndex, segments, playSegment } = get();
    if (currentSegmentIndex < segments.length - 1) {
      playSegment(currentSegmentIndex + 1);
    }
  },

  prevSegment: () => {
    const { currentSegmentIndex, playSegment } = get();
    if (currentSegmentIndex > 0) {
      playSegment(currentSegmentIndex - 1);
    }
  },

  changeSpeed: (speed) => {
    set({ playbackSpeed: speed });
    const { _audioEl } = get();
    if (_audioEl) _audioEl.playbackRate = speed;
  },

  // ── Q&A ──
  askQuestion: async (questionText) => {
    const { session, currentSegmentIndex, pause: pauseFn } = get();
    if (!session?.id) return;
    try {
      pauseFn();
      set({ interruptOpen: true });
      const result = await submitPodcastQuestion(session.id, {
        question_text: questionText,
        paused_at_segment: currentSegmentIndex,
      });
      set((s) => ({ doubts: [result, ...s.doubts] }));
      return result;
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  loadDoubts: async () => {
    const { session } = get();
    if (!session?.id) return;
    try {
      const data = await getPodcastDoubts(session.id);
      set({ doubts: data || [] });
    } catch (err) {
      console.error('Failed to load doubts:', err);
    }
  },

  // ── Bookmarks ──
  addBookmark: async (segmentIndex, label) => {
    const { session } = get();
    if (!session?.id) return;
    const data = await addPodcastBookmark(session.id, { segment_index: segmentIndex, label });
    set((s) => ({ bookmarks: [...s.bookmarks, data] }));
    return data;
  },

  removeBookmark: async (bookmarkId) => {
    const { session } = get();
    if (!session?.id) return;
    await deletePodcastBookmark(session.id, bookmarkId);
    set((s) => ({ bookmarks: s.bookmarks.filter(b => b.id !== bookmarkId) }));
  },

  // ── Annotations ──
  addAnnotation: async (segmentIndex, text) => {
    const { session } = get();
    if (!session?.id) return;
    const data = await addPodcastAnnotation(session.id, { segment_index: segmentIndex, note: text });
    set((s) => ({ annotations: [...s.annotations, data] }));
    return data;
  },

  removeAnnotation: async (annotationId) => {
    const { session } = get();
    if (!session?.id) return;
    await deletePodcastAnnotation(session.id, annotationId);
    set((s) => ({ annotations: s.annotations.filter(a => a.id !== annotationId) }));
  },

  // ── Delete session ──
  removeSession: async (sessionId) => {
    await deletePodcastSession(sessionId);
    set((s) => ({
      sessions: s.sessions.filter(s2 => s2.id !== sessionId),
      ...(s.session?.id === sessionId ? { session: null, phase: 'idle' } : {}),
    }));
  },

  // ── Export ──
  exportSession: async (format) => {
    const { session } = get();
    if (!session?.id) return;
    return triggerPodcastExport(session.id, format);
  },

  generateSummary: async () => {
    const { session } = get();
    if (!session?.id) return;
    return generatePodcastSummary(session.id);
  },

  // ── WS event handler ──
  handleWsEvent: (event) => {
    const { type, ...rest } = event;
    switch (type) {
      case 'podcast_progress': {
        const pct = (rest.progress ?? 0) * 100;
        set({
          generationProgress: {
            stage: rest.phase || 'script',
            pct,
            message: rest.message || 'Generating…',
          },
        });
        if (rest.phase === 'error') {
          set({ error: rest.message || 'Generation failed', phase: 'idle' });
        }
        break;
      }
      case 'podcast_ready':
        get().loadSession(rest.session_id || event.session_id);
        break;
      case 'podcast_segment_ready':
        if (rest.segment) {
          set((s) => {
            const exists = s.segments.some(seg => seg.index === rest.segment.index);
            if (exists) return {};
            return { segments: [...s.segments, rest.segment].sort((a, b) => a.index - b.index) };
          });
        }
        break;
      case 'podcast_paused':
        get().pause();
        break;
      case 'podcast_answer':
        set((s) => ({ doubts: [rest, ...s.doubts] }));
        break;
      case 'podcast_auto_resume':
        set({ interruptOpen: false });
        get().resume();
        break;
      default:
        break;
    }
  },

  // Setters
  setPhase: (phase) => set({ phase }),
  setSession: (session) => set({ session }),
  setInterruptOpen: (open) => set({ interruptOpen: open }),
  setError: (error) => set({ error }),
  setGenerationProgress: (progress) => set({ generationProgress: progress }),
  setCurrentSegmentIndex: (idx) => set({ currentSegmentIndex: idx }),
  setSegments: (segments) => set({ segments }),
  setBookmarks: (bookmarks) => set({ bookmarks }),
  setAnnotations: (annotations) => set({ annotations }),
  setDoubts: (doubts) => set({ doubts }),
  setCurrentTime: (time) => set({ currentTime: time }),

  // ── Computed ──
  get totalDuration() {
    return get().segments.reduce((sum, s) => sum + (s.durationMs || 0), 0);
  },

  getCurrentChapter: () => {
    const { chapters, currentSegmentIndex } = get();
    if (!chapters.length) return null;
    for (let i = chapters.length - 1; i >= 0; i--) {
      if (currentSegmentIndex >= chapters[i].startSegment) return chapters[i];
    }
    return chapters[0];
  },
}));

export default usePodcastStore;

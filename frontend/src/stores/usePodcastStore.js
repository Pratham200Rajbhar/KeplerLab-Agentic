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
  
  session: null,
  sessions: [],
  segments: [],
  chapters: [],
  doubts: [],
  bookmarks: [],
  annotations: [],

  
  currentSegmentIndex: 0,
  isPlaying: false,
  playbackSpeed: 1,
  currentTime: 0,
  totalElapsed: 0,

  
  phase: 'idle', 
  interruptOpen: false,
  generationProgress: null,
  error: null,
  loading: false,

  
  _audioElRef: { current: null },
  _audioCacheRef: { current: new Map() },

  setAudioRefs: (audioElRef, audioCacheRef) => {
    set({ _audioElRef: audioElRef, _audioCacheRef: audioCacheRef });
  },

  
  resetPodcast: () => {
    const { _audioElRef, _audioCacheRef } = get();
    if (_audioElRef.current) {
      _audioElRef.current.pause();
      _audioElRef.current.src = '';
    }
    if (_audioCacheRef.current) {
      _audioCacheRef.current.forEach(url => URL.revokeObjectURL(url));
      _audioCacheRef.current.clear();
    }
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

  
  loadSessions: async (notebookId, isDraft) => {
    if (!notebookId || isDraft) return;
    try {
      const data = await listPodcastSessions(notebookId);
      set({ sessions: data || [] });
    } catch (err) {
      console.error('Failed to load podcast sessions:', err);
    }
  },

  
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

  
  playSegment: async (index) => {
    const { segments, playbackSpeed, _audioElRef, _audioCacheRef } = get();
    if (!segments[index]) return;
    const seg = segments[index];
    if (!seg.audioPath) return;
    const audioEl = _audioElRef.current;
    const audioCache = _audioCacheRef.current;
    if (!audioEl) return;

    set({ currentSegmentIndex: index, currentTime: 0 });

    try {
      let blobUrl = audioCache.get(seg.audioPath);
      if (!blobUrl) {
        blobUrl = await fetchAudioObjectUrl(seg.audioPath);
        audioCache.set(seg.audioPath, blobUrl);
      }

      audioEl.pause();
      audioEl.src = blobUrl;
      audioEl.playbackRate = playbackSpeed;
      await audioEl.play();
      set({ isPlaying: true });
    } catch (err) {
      console.error('Failed to play segment', index, err);
      set({ isPlaying: false });
    }
  },

  prefetchSegment: async (index) => {
    const { segments, _audioCacheRef } = get();
    if (!segments[index]) return;
    const seg = segments[index];
    const audioCache = _audioCacheRef.current;
    if (!seg.audioPath || !audioCache || audioCache.has(seg.audioPath)) return;
    try {
      const blobUrl = await fetchAudioObjectUrl(seg.audioPath);
      audioCache.set(seg.audioPath, blobUrl);
    } catch {  }
  },

  pause: () => {
    get()._audioElRef.current?.pause();
    set({ isPlaying: false });
  },

  resume: () => {
    const { _audioElRef, currentSegmentIndex, playSegment } = get();
    const audioEl = _audioElRef.current;
    if (!audioEl?.src || audioEl.src === window.location.href) {
      playSegment(currentSegmentIndex);
      return;
    }
    audioEl.play().catch(() => {});
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
    const { _audioElRef } = get();
    if (_audioElRef.current) _audioElRef.current.playbackRate = speed;
  },

  
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

  
  removeSession: async (sessionId) => {
    await deletePodcastSession(sessionId);
    set((s) => ({
      sessions: s.sessions.filter(s2 => s2.id !== sessionId),
      ...(s.session?.id === sessionId ? { session: null, phase: 'idle' } : {}),
    }));
  },

  
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

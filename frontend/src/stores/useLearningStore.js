import { create } from 'zustand';

import {
  askLearningAssist,
  completeLearningDay,
  createLearningPath,
  getLearningProgress,
  getLearningReview,
  listLearningDays,
  listLearningPaths,
  openLearningDay,
  submitLearningGame,
  submitLearningInteraction,
  submitLearningQuiz,
  submitLearningTask,
} from '@/lib/api/learning';

const useLearningStore = create((set, get) => ({
  paths: [],
  activePath: null,
  days: [],
  activeDay: null,
  session: null,
  dayContent: null,
  progress: null,
  review: [],
  mentorByDay: {},
  mentorMessages: [],
  lastStageResult: null,
  openingDayId: null,
  lastActiveDayByPath: {},
  dayCache: {},
  loading: {
    paths: false,
    createPath: false,
    days: false,
    openDay: false,
    submitStage: false,
    completeDay: false,
    askMentor: false,
    progress: false,
    review: false,
  },
  error: null,

  setError: (error) => set({ error }),

  _setLoading: (key, value) =>
    set((state) => ({
      loading: { ...state.loading, [key]: value },
    })),

  reset: () =>
    set({
      paths: [],
      activePath: null,
      days: [],
      activeDay: null,
      session: null,
      dayContent: null,
      progress: null,
      review: [],
      mentorByDay: {},
      mentorMessages: [],
      lastStageResult: null,
      openingDayId: null,
      lastActiveDayByPath: {},
      dayCache: {},
      error: null,
      loading: {
        paths: false,
        createPath: false,
        days: false,
        openDay: false,
        submitStage: false,
        completeDay: false,
        askMentor: false,
        progress: false,
        review: false,
      },
    }),

  loadPaths: async () => {
    get()._setLoading('paths', true);
    try {
      const paths = await listLearningPaths();
      set({ paths, error: null });

      const state = get();
      if (!state.activePath && paths.length > 0) {
        await state.selectPath(paths[0]);
      }
    } catch (err) {
      set({ error: err.message || 'Failed to load learning paths' });
    } finally {
      get()._setLoading('paths', false);
    }
  },

  createPath: async (payload) => {
    get()._setLoading('createPath', true);
    try {
      const created = await createLearningPath(payload);
      set((state) => ({
        paths: [created, ...state.paths],
        activePath: created,
        error: null,
      }));
      await get().loadDays(created.id);
      await get().loadProgress(created.id);
      await get().loadReview(created.id);
      return created;
    } catch (err) {
      set({ error: err.message || 'Failed to create path' });
      throw err;
    } finally {
      get()._setLoading('createPath', false);
    }
  },

  selectPath: async (path) => {
    const pathObj = typeof path === 'string'
      ? get().paths.find((p) => p.id === path)
      : path;
    if (!pathObj) return;

    const state = get();
    const cachedDayId = state.lastActiveDayByPath[pathObj.id];
    const cachedPayload = cachedDayId ? state.dayCache[cachedDayId] : null;
    const cachedMentorMessages = cachedDayId ? (state.mentorByDay[cachedDayId] || []) : [];

    set({
      activePath: pathObj,
      activeDay: cachedPayload?.day || null,
      session: cachedPayload?.session || null,
      dayContent: cachedPayload?.content || null,
      mentorMessages: cachedMentorMessages,
      lastStageResult: null,
    });

    await Promise.all([
      get().loadDays(pathObj.id),
      get().loadProgress(pathObj.id),
      get().loadReview(pathObj.id),
    ]);
  },

  loadDays: async (pathId) => {
    get()._setLoading('days', true);
    try {
      const days = await listLearningDays(pathId);
      const state = get();
      const preferredDayId = state.lastActiveDayByPath[pathId];
      let activeDay = state.activeDay;
      if (!activeDay || !days.some((d) => d.id === activeDay.id)) {
        activeDay =
          (preferredDayId && days.find((d) => d.id === preferredDayId)) ||
          days.find((d) => d.is_unlocked && d.status !== 'completed') ||
          days[0] ||
          null;
      }

      const sameDay = Boolean(activeDay?.id && state.activeDay?.id === activeDay.id);
      const cachedPayload = activeDay ? state.dayCache[activeDay.id] : null;
      const mentorMessages = activeDay ? (state.mentorByDay[activeDay.id] || []) : [];

      set({
        days,
        activeDay,
        session: cachedPayload?.session ?? (sameDay ? state.session : null),
        dayContent: cachedPayload?.content ?? (sameDay ? state.dayContent : null),
        mentorMessages,
        lastActiveDayByPath: activeDay
          ? { ...state.lastActiveDayByPath, [pathId]: activeDay.id }
          : state.lastActiveDayByPath,
        error: null,
      });
    } catch (err) {
      set({ error: err.message || 'Failed to load days' });
    } finally {
      get()._setLoading('days', false);
    }
  },

  openDay: async (dayId, forceRegenerate = false) => {
    const state = get();

    if (!forceRegenerate && state.dayCache[dayId]) {
      const cached = state.dayCache[dayId];
      set((prev) => ({
        activeDay: cached.day,
        session: cached.session,
        dayContent: cached.content,
        mentorMessages: prev.mentorByDay[dayId] || [],
        lastStageResult: null,
        error: null,
        lastActiveDayByPath: prev.activePath?.id
          ? { ...prev.lastActiveDayByPath, [prev.activePath.id]: dayId }
          : prev.lastActiveDayByPath,
      }));
      return cached;
    }

    if (!forceRegenerate) {
      if (state.openingDayId === dayId) {
        return {
          day: state.activeDay,
          session: state.session,
          content: state.dayContent,
        };
      }

      if (state.activeDay?.id === dayId && state.dayContent) {
        return {
          day: state.activeDay,
          session: state.session,
          content: state.dayContent,
        };
      }
    }

    set({ openingDayId: dayId });
    get()._setLoading('openDay', true);
    try {
      const payload = await openLearningDay(dayId, forceRegenerate);
      set((prev) => ({
        activeDay: payload.day,
        session: payload.session,
        dayContent: payload.content,
        mentorMessages: prev.mentorByDay[dayId] || [],
        lastStageResult: null,
        error: null,
        openingDayId: null,
        dayCache: {
          ...prev.dayCache,
          [dayId]: {
            day: payload.day,
            session: payload.session,
            content: payload.content,
            cachedAt: Date.now(),
          },
        },
        lastActiveDayByPath: prev.activePath?.id
          ? { ...prev.lastActiveDayByPath, [prev.activePath.id]: dayId }
          : prev.lastActiveDayByPath,
      }));
      return payload;
    } catch (err) {
      set({ error: err.message || 'Failed to open learning day', openingDayId: null });
      throw err;
    } finally {
      get()._setLoading('openDay', false);
    }
  },

  submitInteraction: async (answers) => {
    const dayId = get().activeDay?.id;
    if (!dayId) return null;
    get()._setLoading('submitStage', true);
    try {
      const result = await submitLearningInteraction(dayId, answers);
      set((state) => ({
        session: result.session,
        lastStageResult: result,
        error: null,
        dayCache: state.activeDay?.id
          ? {
            ...state.dayCache,
            [state.activeDay.id]: {
              day: state.activeDay,
              session: result.session,
              content: state.dayContent,
              cachedAt: Date.now(),
            },
          }
          : state.dayCache,
      }));
      await Promise.all([get().loadProgress(get().activePath?.id), get().loadReview(get().activePath?.id)]);
      return result;
    } catch (err) {
      set({ error: err.message || 'Interaction submission failed' });
      throw err;
    } finally {
      get()._setLoading('submitStage', false);
    }
  },

  submitTask: async (submission) => {
    const dayId = get().activeDay?.id;
    if (!dayId) return null;
    get()._setLoading('submitStage', true);
    try {
      const result = await submitLearningTask(dayId, submission);
      set((state) => ({
        session: result.session,
        lastStageResult: result,
        error: null,
        dayCache: state.activeDay?.id
          ? {
            ...state.dayCache,
            [state.activeDay.id]: {
              day: state.activeDay,
              session: result.session,
              content: state.dayContent,
              cachedAt: Date.now(),
            },
          }
          : state.dayCache,
      }));
      await get().loadProgress(get().activePath?.id);
      return result;
    } catch (err) {
      set({ error: err.message || 'Task submission failed' });
      throw err;
    } finally {
      get()._setLoading('submitStage', false);
    }
  },

  submitQuiz: async (answers) => {
    const dayId = get().activeDay?.id;
    if (!dayId) return null;
    get()._setLoading('submitStage', true);
    try {
      const result = await submitLearningQuiz(dayId, answers);
      set((state) => ({
        session: result.session,
        lastStageResult: result,
        error: null,
        dayCache: state.activeDay?.id
          ? {
            ...state.dayCache,
            [state.activeDay.id]: {
              day: state.activeDay,
              session: result.session,
              content: state.dayContent,
              cachedAt: Date.now(),
            },
          }
          : state.dayCache,
      }));
      await Promise.all([get().loadProgress(get().activePath?.id), get().loadReview(get().activePath?.id)]);
      return result;
    } catch (err) {
      set({ error: err.message || 'Quiz submission failed' });
      throw err;
    } finally {
      get()._setLoading('submitStage', false);
    }
  },

  submitGame: async (moves) => {
    const dayId = get().activeDay?.id;
    if (!dayId) return null;
    get()._setLoading('submitStage', true);
    try {
      const result = await submitLearningGame(dayId, moves);
      set((state) => ({
        session: result.session,
        lastStageResult: result,
        error: null,
        dayCache: state.activeDay?.id
          ? {
            ...state.dayCache,
            [state.activeDay.id]: {
              day: state.activeDay,
              session: result.session,
              content: state.dayContent,
              cachedAt: Date.now(),
            },
          }
          : state.dayCache,
      }));
      await get().loadProgress(get().activePath?.id);
      return result;
    } catch (err) {
      set({ error: err.message || 'Game submission failed' });
      throw err;
    } finally {
      get()._setLoading('submitStage', false);
    }
  },

  completeDay: async () => {
    const dayId = get().activeDay?.id;
    const pathId = get().activePath?.id;
    if (!dayId || !pathId) return null;

    get()._setLoading('completeDay', true);
    try {
      const result = await completeLearningDay(dayId);
      const progress = result?.progress;
      set((state) => {
        const nextDayCache = { ...state.dayCache };
        delete nextDayCache[dayId];

        const updatedPaths = state.paths.map((path) =>
          path.id === pathId
            ? {
              ...path,
              completion_percentage: progress?.completion_percentage ?? path.completion_percentage,
              current_day: progress?.current_day ?? path.current_day,
              streak: progress?.streak ?? path.streak,
              status: progress?.completion_percentage >= 100 ? 'completed' : path.status,
            }
            : path
        );
        const updatedActivePath =
          state.activePath?.id === pathId
            ? updatedPaths.find((path) => path.id === pathId) || state.activePath
            : state.activePath;

        return {
          lastStageResult: result,
          error: null,
          dayCache: nextDayCache,
          paths: updatedPaths,
          activePath: updatedActivePath,
        };
      });
      await Promise.all([
        get().loadDays(pathId),
        get().loadProgress(pathId),
        get().loadReview(pathId),
      ]);

      const nextDayId = result?.unlocked_next_day_id;
      if (nextDayId) {
        await get().openDay(nextDayId, false);
      }

      return result;
    } catch (err) {
      set({ error: err.message || 'Failed to complete day' });
      throw err;
    } finally {
      get()._setLoading('completeDay', false);
    }
  },

  askMentor: async (question) => {
    const dayId = get().activeDay?.id;
    if (!dayId) {
      throw new Error('Open a learning day before asking for help');
    }

    const cleanedQuestion = String(question || '').trim();
    if (!cleanedQuestion) {
      throw new Error('Question is required');
    }

    const userMessage = {
      id: `u_${Date.now()}`,
      role: 'user',
      text: cleanedQuestion,
      created_at: new Date().toISOString(),
    };

    set((state) => {
      const currentThread = state.mentorByDay[dayId] || [];
      const nextThread = [...currentThread, userMessage].slice(-50);
      return {
        mentorByDay: {
          ...state.mentorByDay,
          [dayId]: nextThread,
        },
        mentorMessages: state.activeDay?.id === dayId ? nextThread : state.mentorMessages,
        error: null,
      };
    });

    get()._setLoading('askMentor', true);
    try {
      const payload = await askLearningAssist(dayId, cleanedQuestion);
      const assistantMessage = {
        id: `a_${Date.now()}`,
        role: 'assistant',
        text: payload?.answer || 'I could not generate an answer right now. Please try again.',
        understanding_check: payload?.understanding_check || '',
        next_steps: Array.isArray(payload?.next_steps) ? payload.next_steps : [],
        related_concepts: Array.isArray(payload?.related_concepts) ? payload.related_concepts : [],
        created_at: new Date().toISOString(),
      };

      set((state) => {
        const currentThread = state.mentorByDay[dayId] || [];
        const nextThread = [...currentThread, assistantMessage].slice(-50);
        return {
          mentorByDay: {
            ...state.mentorByDay,
            [dayId]: nextThread,
          },
          mentorMessages: state.activeDay?.id === dayId ? nextThread : state.mentorMessages,
          error: null,
        };
      });

      return payload;
    } catch (err) {
      set({ error: err.message || 'AI mentor request failed' });
      throw err;
    } finally {
      get()._setLoading('askMentor', false);
    }
  },

  loadProgress: async (pathId) => {
    if (!pathId) return;
    get()._setLoading('progress', true);
    try {
      const progress = await getLearningProgress(pathId);
      set((state) => {
        const updatedPaths = state.paths.map((path) =>
          path.id === pathId
            ? {
              ...path,
              completion_percentage: progress.completion_percentage,
              current_day: progress.current_day,
              streak: progress.streak,
            }
            : path
        );

        const updatedActivePath =
          state.activePath?.id === pathId
            ? updatedPaths.find((path) => path.id === pathId) || state.activePath
            : state.activePath;

        return {
          progress,
          paths: updatedPaths,
          activePath: updatedActivePath,
          error: null,
        };
      });
    } catch (err) {
      set({ error: err.message || 'Failed to load progress' });
    } finally {
      get()._setLoading('progress', false);
    }
  },

  loadReview: async (pathId) => {
    if (!pathId) return;
    get()._setLoading('review', true);
    try {
      const reviewPayload = await getLearningReview(pathId);
      set({ review: reviewPayload?.recommendations || [], error: null });
    } catch (err) {
      set({ error: err.message || 'Failed to load review recommendations' });
    } finally {
      get()._setLoading('review', false);
    }
  },
}));

export default useLearningStore;

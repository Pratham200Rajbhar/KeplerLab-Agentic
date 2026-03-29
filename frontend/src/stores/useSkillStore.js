/**
 * Zustand store for Agent Skills state management.
 */
import { create } from 'zustand';
import { generateId } from '@/lib/utils/helpers';
import useChatStore from '@/stores/useChatStore';
import {
  getSkills,
  getSkill,
  createSkill,
  updateSkill,
  deleteSkill,
  getSkillTemplates,
  validateSkillMarkdown,
  suggestSkillTags as suggestSkillTagsApi,
  generateSkillDraft as generateSkillDraftApi,
  runSkill,
  getSkillRuns,
  getSkillRun,
} from '@/lib/api/skills';

function mergeStepState(steps = [], stepIndex, patch = {}) {
  if (typeof stepIndex !== 'number') return steps;
  let found = false;
  const next = steps.map((step) => {
    if (step.index !== stepIndex) return step;
    found = true;
    return { ...step, ...patch };
  });
  if (!found) next.push({ index: stepIndex, ...patch });
  return [...next].sort((a, b) => (a.index || 0) - (b.index || 0));
}

const useSkillStore = create((set, get) => ({
  // ── State ───────────────────────────────────────────────
  skills: [],
  templates: [],
  activeSkill: null,
  skillRuns: [],
  isLoading: false,
  isRunning: false,
  isSuggestingTags: false,
  isGeneratingDraft: false,
  editorContent: '',
  editorValid: null,    // null | { valid: true, parsed } | { valid: false, error }
  currentRun: null,     // { run_id, status, steps: [], artifacts: [], progress: 0 }
  error: null,

  // ── Skill CRUD ──────────────────────────────────────────

  loadSkills: async (notebookId) => {
    set({ isLoading: true, error: null });
    try {
      const skills = await getSkills(notebookId, true);
      set({ skills, isLoading: false });
    } catch (err) {
      set({ error: err.message, isLoading: false });
    }
  },

  loadTemplates: async () => {
    try {
      const templates = await getSkillTemplates();
      set({ templates });
    } catch (err) {
      console.error('Failed to load templates:', err);
    }
  },

  setActiveSkill: (skill) => {
    set({
      activeSkill: skill,
      editorContent: skill?.markdown || '',
      editorValid: null,
    });
  },

  createSkill: async ({ markdown, notebookId, isGlobal, tags }) => {
    set({ isLoading: true, error: null });
    try {
      const skill = await createSkill({ markdown, notebookId, isGlobal, tags });
      set((state) => ({
        skills: [skill, ...state.skills],
        activeSkill: skill,
        isLoading: false,
      }));
      return skill;
    } catch (err) {
      set({ error: err.message, isLoading: false });
      throw err;
    }
  },

  updateSkill: async (skillId, { markdown, tags }) => {
    set({ isLoading: true, error: null });
    try {
      const updated = await updateSkill(skillId, { markdown, tags });
      set((state) => ({
        skills: state.skills.map((s) => (s.id === skillId ? updated : s)),
        activeSkill: state.activeSkill?.id === skillId ? updated : state.activeSkill,
        isLoading: false,
      }));
      return updated;
    } catch (err) {
      set({ error: err.message, isLoading: false });
      throw err;
    }
  },

  deleteSkill: async (skillId) => {
    try {
      await deleteSkill(skillId);
      set((state) => ({
        skills: state.skills.filter((s) => s.id !== skillId),
        activeSkill: state.activeSkill?.id === skillId ? null : state.activeSkill,
      }));
    } catch (err) {
      set({ error: err.message });
      throw err;
    }
  },

  // ── Editor ──────────────────────────────────────────────

  setEditorContent: (content) => set({ editorContent: content, editorValid: null }),

  validateEditor: async () => {
    const { editorContent } = get();
    if (!editorContent.trim()) {
      set({ editorValid: { valid: false, error: 'Skill markdown is empty' } });
      return false;
    }
    try {
      const result = await validateSkillMarkdown(editorContent);
      set({ editorValid: result });
      return result.valid;
    } catch (err) {
      set({ editorValid: { valid: false, error: err.message } });
      return false;
    }
  },

  suggestTags: async (markdown, maxTags = 6) => {
    set({ isSuggestingTags: true, error: null });
    try {
      const tags = await suggestSkillTagsApi(markdown, maxTags);
      return tags;
    } catch (err) {
      set({ error: err.message || 'Failed to suggest tags' });
      throw err;
    } finally {
      set({ isSuggestingTags: false });
    }
  },

  generateDraft: async (prompt) => {
    set({ isGeneratingDraft: true, error: null });
    try {
      return await generateSkillDraftApi(prompt);
    } catch (err) {
      set({ error: err.message || 'Failed to generate skill draft' });
      throw err;
    } finally {
      set({ isGeneratingDraft: false });
    }
  },

  // ── Execution ───────────────────────────────────────────

  executeSkill: async (skillId, { variables, notebookId, sessionId, materialIds, streamToChat = true } = {}) => {
    const skillRecord = get().skills.find((s) => s.id === skillId) || get().activeSkill;
    const chatMessageId = streamToChat ? generateId() : null;

    const updateChatSkill = (updater, contentOverride = null) => {
      if (!chatMessageId) return;
      useChatStore.getState().updateMessageById(chatMessageId, (msg) => {
        const prevSkillState = msg.skillState || {};
        const nextSkillState = typeof updater === 'function' ? updater(prevSkillState) : { ...prevSkillState, ...updater };
        return {
          ...msg,
          ...(typeof contentOverride === 'string' ? { content: contentOverride } : {}),
          skillState: nextSkillState,
        };
      });
    };

    if (chatMessageId) {
      useChatStore.getState().addMessage({
        id: chatMessageId,
        role: 'assistant',
        content: '',
        createdAt: Date.now(),
        intentOverride: 'SKILL_EXECUTION',
        skillState: {
          runId: null,
          skillId,
          skillTitle: skillRecord?.title || 'Skill Run',
          status: 'starting',
          message: `Starting ${skillRecord?.title || 'skill'}...`,
          progress: 0,
          plan: [],
          steps: [],
          artifacts: [],
          startedAt: Date.now(),
        },
      });
    }

    set({
      isRunning: true,
      error: null,
      currentRun: {
        run_id: null,
        status: 'starting',
        steps: [],
        artifacts: [],
        progress: 0,
        plan: [],
      },
    });

    try {
      await runSkill(skillId, {
        variables,
        notebookId,
        sessionId,
        materialIds,
        onEvent: (eventName, data) => {
          set((state) => {
            const run = { ...state.currentRun };

            switch (eventName) {
              case 'skill_status':
                run.status = data.status || run.status;
                run.run_id = data.run_id || run.run_id;
                run.message = data.message;
                if (data.plan) run.plan = data.plan;
                updateChatSkill((prev) => ({
                  ...prev,
                  runId: data.run_id || prev.runId || null,
                  status: data.status || prev.status || 'running',
                  message: data.message || prev.message,
                  plan: Array.isArray(data.plan) ? data.plan : (prev.plan || []),
                }));
                break;

              case 'skill_step_start':
                run.steps = mergeStepState(run.steps, data.step_index, {
                  instruction: data.instruction,
                  tool: data.tool,
                  status: 'running',
                });
                run.progress = data.progress || run.progress;
                updateChatSkill((prev) => ({
                  ...prev,
                  progress: data.progress ?? prev.progress ?? 0,
                  steps: mergeStepState(prev.steps, data.step_index, {
                    instruction: data.instruction,
                    tool: data.tool,
                    status: 'running',
                  }),
                }));
                break;

              case 'skill_step_result':
                run.steps = mergeStepState(run.steps, data.step_index, {
                  status: 'completed',
                  content: data.content,
                  elapsed: data.elapsed,
                });
                run.progress = data.progress || run.progress;
                updateChatSkill((prev) => ({
                  ...prev,
                  progress: data.progress ?? prev.progress ?? 0,
                  steps: mergeStepState(prev.steps, data.step_index, {
                    status: 'completed',
                    content: data.content,
                    elapsed: data.elapsed,
                  }),
                }));
                break;

              case 'skill_step_error':
                run.steps = mergeStepState(run.steps, data.step_index, {
                  status: 'failed',
                  error: data.error,
                });
                run.progress = data.progress || run.progress;
                updateChatSkill((prev) => ({
                  ...prev,
                  progress: data.progress ?? prev.progress ?? 0,
                  steps: mergeStepState(prev.steps, data.step_index, {
                    status: 'failed',
                    error: data.error,
                  }),
                }));
                break;

              case 'skill_step_skipped':
                run.steps = mergeStepState(run.steps, data.step_index, {
                  instruction: data.instruction,
                  tool: data.tool,
                  status: 'skipped',
                  reason: data.reason,
                });
                run.progress = data.progress || run.progress;
                updateChatSkill((prev) => ({
                  ...prev,
                  progress: data.progress ?? prev.progress ?? 0,
                  steps: mergeStepState(prev.steps, data.step_index, {
                    instruction: data.instruction,
                    tool: data.tool,
                    status: 'skipped',
                    reason: data.reason,
                  }),
                }));
                break;

              case 'skill_artifact':
                run.artifacts = [...run.artifacts, data];
                updateChatSkill((prev) => ({
                  ...prev,
                  artifacts: [...(prev.artifacts || []), data],
                }));
                break;
            }

            return { currentRun: run };
          });
        },
        onError: (error) => {
          set((state) => ({
            currentRun: { ...state.currentRun, status: 'failed', error },
            isRunning: false,
            error,
          }));
          updateChatSkill((prev) => ({
            ...prev,
            status: 'failed',
            message: error || 'Skill execution failed',
            error,
            completedAt: Date.now(),
          }));
        },
        onDone: (data) => {
          set((state) => ({
            currentRun: {
              ...state.currentRun,
              status: data.status || 'completed',
              progress: 100,
              elapsed: data.elapsed_seconds,
              finalOutput: data.final_output,
            },
            isRunning: false,
          }));
          updateChatSkill((prev) => ({
            ...prev,
            status: data.status || 'completed',
            progress: 100,
            elapsed: data.elapsed_seconds,
            finalOutput: data.final_output,
            completedAt: Date.now(),
            steps: Array.isArray(data.step_logs) && data.step_logs.length > 0
              ? data.step_logs.map((s) => ({
                  index: s.step_index,
                  instruction: s.instruction,
                  tool: s.tool,
                  status: s.skipped ? 'skipped' : (s.success ? 'completed' : 'failed'),
                  content: s.content,
                  error: s.error,
                  reason: s.skip_reason,
                  elapsed: s.elapsed_seconds,
                }))
              : prev.steps,
          }), data.final_output || 'Skill run completed.');
        },
      });
    } catch (err) {
      set({
        isRunning: false,
        error: err.message,
        currentRun: { ...get().currentRun, status: 'failed', error: err.message },
      });
      updateChatSkill((prev) => ({
        ...prev,
        status: 'failed',
        message: err.message || 'Skill execution failed',
        error: err.message,
        completedAt: Date.now(),
      }));
    }
  },

  clearRun: () => set({ currentRun: null, isRunning: false }),

  // ── Run History ─────────────────────────────────────────

  loadRuns: async (skillId) => {
    try {
      const runs = await getSkillRuns(skillId);
      set({ skillRuns: runs });
    } catch (err) {
      console.error('Failed to load skill runs:', err);
    }
  },

  loadRunDetail: async (runId) => {
    try {
      return await getSkillRun(runId);
    } catch (err) {
      console.error('Failed to load run detail:', err);
      return null;
    }
  },

  // ── Reset ───────────────────────────────────────────────

  reset: () =>
    set({
      skills: [],
      activeSkill: null,
      skillRuns: [],
      isLoading: false,
      isRunning: false,
      isSuggestingTags: false,
      isGeneratingDraft: false,
      editorContent: '',
      editorValid: null,
      currentRun: null,
      error: null,
    }),
}));

export default useSkillStore;

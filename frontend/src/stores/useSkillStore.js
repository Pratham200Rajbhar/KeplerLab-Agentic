/**
 * Zustand store for Agent Skills state management.
 */
import { create } from 'zustand';
import {
  getSkills,
  getSkill,
  createSkill,
  updateSkill,
  deleteSkill,
  getSkillTemplates,
  validateSkillMarkdown,
  runSkill,
  getSkillRuns,
  getSkillRun,
} from '@/lib/api/skills';

const useSkillStore = create((set, get) => ({
  // ── State ───────────────────────────────────────────────
  skills: [],
  templates: [],
  activeSkill: null,
  skillRuns: [],
  isLoading: false,
  isRunning: false,
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

  // ── Execution ───────────────────────────────────────────

  executeSkill: async (skillId, { variables, notebookId, sessionId, materialIds } = {}) => {
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
                break;

              case 'skill_step_start':
                run.steps = [
                  ...run.steps,
                  {
                    index: data.step_index,
                    instruction: data.instruction,
                    tool: data.tool,
                    status: 'running',
                  },
                ];
                run.progress = data.progress || run.progress;
                break;

              case 'skill_step_result':
                run.steps = run.steps.map((s) =>
                  s.index === data.step_index
                    ? { ...s, status: 'completed', content: data.content, elapsed: data.elapsed }
                    : s
                );
                run.progress = data.progress || run.progress;
                break;

              case 'skill_step_error':
                run.steps = run.steps.map((s) =>
                  s.index === data.step_index
                    ? { ...s, status: 'failed', error: data.error }
                    : s
                );
                run.progress = data.progress || run.progress;
                break;

              case 'skill_step_skipped':
                run.steps = [
                  ...run.steps,
                  {
                    index: data.step_index,
                    instruction: data.instruction,
                    tool: data.tool,
                    status: 'skipped',
                    reason: data.reason,
                  },
                ];
                run.progress = data.progress || run.progress;
                break;

              case 'skill_artifact':
                run.artifacts = [...run.artifacts, data];
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
        },
      });
    } catch (err) {
      set({
        isRunning: false,
        error: err.message,
        currentRun: { ...get().currentRun, status: 'failed', error: err.message },
      });
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
      editorContent: '',
      editorValid: null,
      currentRun: null,
      error: null,
    }),
}));

export default useSkillStore;

'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { useRouter } from 'next/navigation';
import {
  ArrowLeft,
  BarChart3,
  BookOpen,
  Bot,
  Check,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  CircleDashed,
  Flame,
  HelpCircle,
  Layers,
  ListChecks,
  Lock,
  MessageSquareText,
  Plus,
  Puzzle,
  RefreshCw,
  Send,
  Sparkles,
  Target,
  Trophy,
  Zap,
} from 'lucide-react';

import useAuthStore from '@/stores/useAuthStore';
import useLearningStore from '@/stores/useLearningStore';
import { useToast } from '@/stores/useToastStore';

const LEVEL_OPTIONS = [
  { label: 'Beginner', value: 'beginner' },
  { label: 'Intermediate', value: 'intermediate' },
  { label: 'Advanced', value: 'advanced' },
];

const GOAL_OPTIONS = [
  { label: 'Concept Mastery', value: 'concept_mastery' },
  { label: 'Career Switch', value: 'career_switch' },
  { label: 'Project Build', value: 'project_build' },
  { label: 'Exam Prep', value: 'exam_prep' },
];

const PATH_FILTERS = [
  { id: 'all', label: 'All' },
  { id: 'active', label: 'Active' },
  { id: 'completed', label: 'Completed' },
];

const STAGE_FLOW = [
  {
    id: 'LESSON',
    title: 'Lesson',
    hint: 'Understand concepts and examples.',
    icon: BookOpen,
  },
  {
    id: 'INTERACTION',
    title: 'Interaction',
    hint: 'Respond to guided reflection prompts.',
    icon: HelpCircle,
  },
  {
    id: 'TASK',
    title: 'Task',
    hint: 'Apply concepts to practical work.',
    icon: ListChecks,
  },
  {
    id: 'QUIZ',
    title: 'Quiz',
    hint: 'Validate understanding with MCQs.',
    icon: Zap,
  },
  {
    id: 'GAME',
    title: 'Game',
    hint: 'Reinforce memory with challenge rounds.',
    icon: Puzzle,
  },
  {
    id: 'COMPLETE',
    title: 'Complete',
    hint: 'Finish day and unlock progression.',
    icon: Trophy,
  },
];

function toPercent(value) {
  const num = Number(value || 0);
  if (!Number.isFinite(num)) return 0;
  return Math.min(100, Math.max(0, num));
}

function titleCase(value) {
  return String(value || '')
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function ProgressBar({ value }) {
  return (
    <div className="h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--surface-overlay)' }}>
      <div
        className="h-full rounded-full"
        style={{
          width: `${toPercent(value)}%`,
          background: 'linear-gradient(90deg, #0ea5e9, var(--accent), var(--accent-light))',
        }}
      />
    </div>
  );
}

function PathStatusBadge({ status }) {
  const normalized = String(status || 'active');
  const config = {
    active: {
      color: 'var(--accent)',
      background: 'var(--accent-subtle)',
      border: '1px solid var(--accent-border)',
      label: 'Active',
    },
    completed: {
      color: 'var(--success)',
      background: 'var(--success-subtle)',
      border: '1px solid var(--success-border)',
      label: 'Completed',
    },
    paused: {
      color: 'var(--warning)',
      background: 'var(--warning-subtle)',
      border: '1px solid var(--warning-border)',
      label: 'Paused',
    },
    archived: {
      color: 'var(--text-muted)',
      background: 'var(--surface-overlay)',
      border: '1px solid var(--border)',
      label: 'Archived',
    },
  };

  const style = config[normalized] || config.active;

  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full"
      style={{ color: style.color, background: style.background, border: style.border }}
    >
      {style.label}
    </span>
  );
}

function DayStateBadge({ day }) {
  if (day.status === 'completed') {
    return (
      <span
        className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full"
        style={{
          color: 'var(--success)',
          background: 'var(--success-subtle)',
          border: '1px solid var(--success-border)',
        }}
      >
        <Check className="w-3 h-3" />
        Done
      </span>
    );
  }

  if (!day.is_unlocked) {
    return (
      <span
        className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full"
        style={{
          color: 'var(--text-muted)',
          background: 'var(--surface-overlay)',
          border: '1px solid var(--border)',
        }}
      >
        <Lock className="w-3 h-3" />
        Locked
      </span>
    );
  }

  return (
    <span
      className="inline-flex items-center gap-1 text-[11px] font-semibold px-2 py-1 rounded-full"
      style={{
        color: 'var(--accent)',
        background: 'var(--accent-subtle)',
        border: '1px solid var(--accent-border)',
      }}
    >
      <Sparkles className="w-3 h-3" />
      Ready
    </span>
  );
}

function StagePipeline({ stage }) {
  const currentIndex = Math.max(
    0,
    STAGE_FLOW.findIndex((item) => item.id === stage)
  );

  return (
    <div className="grid sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
      {STAGE_FLOW.map((item, index) => {
        const Icon = item.icon;
        const isDone = index < currentIndex;
        const isActive = index === currentIndex;

        return (
          <div
            key={item.id}
            className="rounded-xl p-2.5"
            style={{
              background: isActive ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
              border: isActive ? '1px solid var(--accent-border)' : '1px solid var(--border)',
            }}
          >
            <div className="flex items-start gap-2">
              <div
                className="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
                style={{
                  color: isDone || isActive ? 'var(--accent)' : 'var(--text-muted)',
                  background: 'color-mix(in srgb, var(--surface) 75%, transparent)',
                }}
              >
                {isDone ? <Check className="w-4 h-4" /> : <Icon className="w-4 h-4" />}
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
                  {item.title}
                </p>
                <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                  {item.hint}
                </p>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}

function MetricTile({ icon: Icon, label, value, hint }) {
  return (
    <div
      className="rounded-xl p-3"
      style={{
        background: 'color-mix(in srgb, var(--surface-raised) 88%, transparent)',
        border: '1px solid var(--border)',
      }}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-[11px] uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
            {label}
          </p>
          <p className="text-xl font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>
            {value}
          </p>
          {hint ? (
            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
              {hint}
            </p>
          ) : null}
        </div>
        <div
          className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{
            background: 'var(--surface-overlay)',
            border: '1px solid var(--border)',
            color: 'var(--accent)',
          }}
        >
          <Icon className="w-4 h-4" />
        </div>
      </div>
    </div>
  );
}

function MentorMessage({ message }) {
  const isAssistant = message.role === 'assistant';

  return (
    <div className={`rounded-xl p-2.5 ${isAssistant ? '' : 'ml-6'}`} style={{
      background: isAssistant ? 'color-mix(in srgb, var(--surface-raised) 90%, transparent)' : 'var(--accent-subtle)',
      border: isAssistant ? '1px solid var(--border)' : '1px solid var(--accent-border)',
    }}>
      <div className="flex items-center gap-1.5 mb-1.5">
        <span
          className="text-[10px] font-semibold uppercase tracking-wide"
          style={{ color: isAssistant ? 'var(--text-secondary)' : 'var(--accent)' }}
        >
          {isAssistant ? 'AI Mentor' : 'You'}
        </span>
      </div>
      <p className="text-xs whitespace-pre-wrap" style={{ color: 'var(--text-primary)' }}>
        {message.text}
      </p>

      {isAssistant && message.understanding_check ? (
        <div className="mt-2 rounded-lg px-2 py-1.5" style={{
          background: 'var(--surface-overlay)',
          border: '1px solid var(--border)',
        }}>
          <p className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
            Check Yourself
          </p>
          <p className="text-xs mt-0.5" style={{ color: 'var(--text-primary)' }}>
            {message.understanding_check}
          </p>
        </div>
      ) : null}

      {isAssistant && message.next_steps?.length ? (
        <div className="mt-2">
          <p className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
            Next Steps
          </p>
          <ul className="mt-1 space-y-1">
            {message.next_steps.slice(0, 3).map((step, index) => (
              <li key={`${message.id}_step_${index}`} className="text-xs" style={{ color: 'var(--text-primary)' }}>
                {index + 1}. {step}
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </div>
  );
}

export default function LearningPage() {
  const router = useRouter();
  const { success: toastSuccess, error: toastError, info: toastInfo, warning: toastWarning } = useToast();
  const autoOpenInFlightRef = useRef(null);

  const { isAuthenticated, isLoading: authLoading } = useAuthStore();
  const {
    paths,
    activePath,
    days,
    activeDay,
    session,
    dayContent,
    progress,
    review,
    mentorMessages,
    lastStageResult,
    loading,
    error,
    loadPaths,
    createPath,
    selectPath,
    openDay,
    askMentor,
    submitInteraction,
    submitTask,
    submitQuiz,
    submitGame,
    completeDay,
    setError,
  } = useLearningStore();

  const [pathFilter, setPathFilter] = useState('all');
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState({
    title: '',
    topic: '',
    duration_days: 30,
    level: 'beginner',
    goal_type: 'concept_mastery',
  });

  const [workspaceTab, setWorkspaceTab] = useState('practice');
  const [showFullLesson, setShowFullLesson] = useState(false);
  const [mentorQuestion, setMentorQuestion] = useState('');

  const [interactionAnswers, setInteractionAnswers] = useState({});
  const [taskSubmission, setTaskSubmission] = useState('');
  const [quizAnswers, setQuizAnswers] = useState({});
  const [gameMoves, setGameMoves] = useState({});

  const resetWorkspaceState = () => {
    setMentorQuestion('');
    setShowFullLesson(false);
    setWorkspaceTab('practice');
  };

  const resetStageInputs = () => {
    setInteractionAnswers({});
    setTaskSubmission('');
    setQuizAnswers({});
    setGameMoves({});
  };

  useEffect(() => {
    if (authLoading) return;
    if (!isAuthenticated) {
      router.replace('/auth');
      return;
    }
    loadPaths();
  }, [authLoading, isAuthenticated, loadPaths, router]);

  useEffect(() => {
    if (!activeDay?.id || dayContent || loading.openDay) return;
    if (autoOpenInFlightRef.current === activeDay.id) return;

    autoOpenInFlightRef.current = activeDay.id;
    openDay(activeDay.id)
      .catch((err) => {
        toastError(err.message || 'Failed to open day');
      })
      .finally(() => {
        if (autoOpenInFlightRef.current === activeDay.id) {
          autoOpenInFlightRef.current = null;
        }
      });
  }, [activeDay?.id, dayContent, loading.openDay, openDay, toastError]);

  const stage = session?.stage || 'LESSON';
  const stageMeta = useMemo(
    () => STAGE_FLOW.find((item) => item.id === stage) || STAGE_FLOW[0],
    [stage]
  );

  const filteredPaths = useMemo(() => {
    if (pathFilter === 'all') return paths;
    return paths.filter((path) => path.status === pathFilter);
  }, [pathFilter, paths]);

  const activePathCompletion = toPercent(
    progress?.completion_percentage ?? activePath?.completion_percentage ?? 0
  );
  const activePathStreak = Number(progress?.streak ?? activePath?.streak ?? 0);
  const activePathCurrentDay = Number(progress?.current_day ?? activePath?.current_day ?? 1);

  const completedDays = days.filter((day) => day.status === 'completed').length;
  const nextUnlockedDay = days.find((day) => day.is_unlocked && day.status !== 'completed');
  const activeDayIndex = activeDay ? days.findIndex((day) => day.id === activeDay.id) : -1;
  const previousDay = activeDayIndex > 0 ? days[activeDayIndex - 1] : null;
  const nextDay = activeDayIndex >= 0 && activeDayIndex < days.length - 1 ? days[activeDayIndex + 1] : null;

  const totalTracks = paths.length;
  const activeTracks = paths.filter((path) => path.status === 'active').length;
  const completedTracks = paths.filter((path) => path.status === 'completed').length;
  const averageCompletion = paths.length
    ? Math.round(
      paths.reduce((acc, path) => acc + Number(path.completion_percentage || 0), 0) /
          paths.length
    )
    : 0;

  const confidenceAverage = review.length
    ? review.reduce((acc, item) => acc + Number(item.confidence || 0), 0) / review.length
    : null;

  const reviewTopicSuggestions = useMemo(
    () => (review || []).map((item) => String(item.topic || '').trim()).filter(Boolean).slice(0, 4),
    [review]
  );

  const mentorQuickPrompts = useMemo(() => {
    const prompts = [];
    if (stageMeta?.title) {
      prompts.push(`I am stuck at ${stageMeta.title}. Explain what I should do first.`);
    }
    if (activeDay?.title) {
      prompts.push(`Give me a simple explanation for ${activeDay.title}.`);
    }
    if (reviewTopicSuggestions.length > 0) {
      prompts.push(`Help me revise ${reviewTopicSuggestions[0]} with a practical example.`);
    }
    prompts.push('Ask me one check question to verify I understood this lesson.');
    return prompts.slice(0, 4);
  }, [activeDay?.title, reviewTopicSuggestions, stageMeta?.title]);

  if (authLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--surface)' }}>
        <div className="loading-spinner w-8 h-8" />
      </div>
    );
  }

  if (!isAuthenticated) return null;

  const handleCreatePath = async (e) => {
    e.preventDefault();

    const topic = String(createForm.topic || '').trim();
    const title = String(createForm.title || '').trim();
    const durationDays = Number(createForm.duration_days);

    if (!topic) {
      toastError('Topic is required');
      return;
    }
    if (!Number.isFinite(durationDays) || durationDays < 7 || durationDays > 90) {
      toastError('Duration must be between 7 and 90 days');
      return;
    }

    try {
      await createPath({
        topic,
        title: title || undefined,
        duration_days: durationDays,
        level: createForm.level,
        goal_type: createForm.goal_type,
      });
      resetStageInputs();
      resetWorkspaceState();
      setShowCreateForm(false);
      toastSuccess('Learning track created');
    } catch (err) {
      toastError(err.message || 'Failed to create learning track');
    }
  };

  const handleSelectPath = async (path) => {
    try {
      resetStageInputs();
      resetWorkspaceState();
      await selectPath(path);
    } catch (err) {
      toastError(err.message || 'Failed to switch learning track');
    }
  };

  const handleOpenDay = async (day) => {
    if (!day?.id) return;
    if (!day.is_unlocked) {
      toastInfo('This day is locked. Complete previous day first.');
      return;
    }

    try {
      resetStageInputs();
      resetWorkspaceState();
      await openDay(day.id);
    } catch (err) {
      toastError(err.message || 'Failed to open day');
    }
  };

  const handleRegenerateDay = async () => {
    if (!activeDay?.id) return;
    try {
      await openDay(activeDay.id, true);
      toastSuccess('Day content regenerated by AI');
    } catch (err) {
      toastError(err.message || 'Failed to refresh day content');
    }
  };

  const onAskMentor = async (e) => {
    e.preventDefault();
    const question = mentorQuestion.trim();
    if (!question) return;

    setMentorQuestion('');
    try {
      await askMentor(question);
    } catch (err) {
      toastError(err.message || 'AI mentor request failed');
    }
  };

  const handleQuickPrompt = async (promptText) => {
    try {
      await askMentor(promptText);
    } catch (err) {
      toastError(err.message || 'AI mentor request failed');
    }
  };

  const onSubmitInteraction = async (e) => {
    e.preventDefault();
    const questions = dayContent?.interaction?.questions || [];
    const answers = questions.map((question) => ({
      question_id: question.id,
      response: interactionAnswers[question.id] || '',
    }));

    try {
      const result = await submitInteraction(answers);
      (result.passed ? toastSuccess : toastWarning)(result.feedback);
    } catch (err) {
      toastError(err.message || 'Interaction submission failed');
    }
  };

  const onSubmitTask = async (e) => {
    e.preventDefault();
    try {
      const result = await submitTask(taskSubmission);
      (result.passed ? toastSuccess : toastWarning)(result.feedback);
    } catch (err) {
      toastError(err.message || 'Task submission failed');
    }
  };

  const onSubmitQuiz = async (e) => {
    e.preventDefault();
    const questions = dayContent?.quiz?.questions || [];
    const answers = questions.map((question) => ({
      question_id: question.id,
      selected_option: quizAnswers[question.id] || '',
    }));

    try {
      const result = await submitQuiz(answers);
      (result.passed ? toastSuccess : toastWarning)(result.feedback);
    } catch (err) {
      toastError(err.message || 'Quiz submission failed');
    }
  };

  const onSubmitGame = async (e) => {
    e.preventDefault();
    const rounds = dayContent?.game?.rounds || [];
    const moves = rounds.map((round) => ({
      round_id: round.id,
      answer: gameMoves[round.id] || '',
    }));

    try {
      const result = await submitGame(moves);
      (result.passed ? toastSuccess : toastWarning)(result.feedback);
    } catch (err) {
      toastError(err.message || 'Game submission failed');
    }
  };

  const onCompleteDay = async () => {
    try {
      const result = await completeDay();
      toastSuccess('Day completed and progress updated');
      if (!result?.unlocked_next_day_id) {
        toastSuccess('Learning track completed. Excellent work.');
      }
    } catch (err) {
      toastError(err.message || 'Failed to complete day');
    }
  };

  return (
    <div className="min-h-screen" style={{ background: 'var(--surface)' }}>
      <header
        className="sticky top-0 z-20 border-b"
        style={{
          borderColor: 'var(--border)',
          background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
          backdropFilter: 'blur(10px)',
        }}
      >
        <div className="max-w-[1440px] mx-auto px-4 md:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button onClick={() => router.push('/')} className="btn-secondary px-3 py-2">
              <ArrowLeft className="w-4 h-4" />
              Dashboard
            </button>
            <div>
              <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                AI Learning Studio
              </p>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                Learn, ask questions, and progress across multiple AI-generated tracks
              </p>
            </div>
          </div>

          <button
            onClick={() => setShowCreateForm((value) => !value)}
            className="btn-primary px-4 py-2"
          >
            <Plus className="w-4 h-4" />
            New Learning Track
          </button>
        </div>
      </header>

      <main className="max-w-[1440px] mx-auto px-4 md:px-8 py-6">
        {error ? (
          <div
            className="mb-4 p-3 rounded-xl flex items-center justify-between gap-3"
            style={{
              background: 'var(--danger-subtle)',
              border: '1px solid var(--danger-border)',
              color: 'var(--danger)',
            }}
          >
            <p className="text-sm">{error}</p>
            <button className="btn-secondary px-3 py-1.5 text-xs" onClick={() => setError(null)}>
              Dismiss
            </button>
          </div>
        ) : null}

        {showCreateForm ? (
          <section
            className="mb-5 rounded-2xl p-4 md:p-5"
            style={{
              background: 'color-mix(in srgb, var(--surface-raised) 92%, transparent)',
              border: '1px solid var(--border)',
            }}
          >
            <div className="flex items-center justify-between gap-3 mb-4">
              <div>
                <h2 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Create Learning Track
                </h2>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Every day, lesson, quiz, and game is generated by AI for your track.
                </p>
              </div>
              <span
                className="inline-flex items-center gap-1 text-xs px-2 py-1 rounded-full"
                style={{
                  color: 'var(--accent)',
                  background: 'var(--accent-subtle)',
                  border: '1px solid var(--accent-border)',
                }}
              >
                <Sparkles className="w-3 h-3" />
                AI Generated
              </span>
            </div>

            <form onSubmit={handleCreatePath} className="space-y-4">
              <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-3">
                <div className="sm:col-span-2">
                  <label className="form-label">Topic</label>
                  <input
                    className="input"
                    value={createForm.topic}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, topic: e.target.value }))}
                    placeholder="e.g. System Design"
                    required
                  />
                </div>

                <div className="sm:col-span-2">
                  <label className="form-label">Title (optional)</label>
                  <input
                    className="input"
                    value={createForm.title}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, title: e.target.value }))}
                    placeholder="e.g. Backend Interview Sprint"
                  />
                </div>

                <div>
                  <label className="form-label">Duration (days)</label>
                  <input
                    type="number"
                    min={7}
                    max={90}
                    className="input"
                    value={createForm.duration_days}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, duration_days: e.target.value }))}
                    required
                  />
                </div>

                <div>
                  <label className="form-label">Level</label>
                  <select
                    className="input"
                    value={createForm.level}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, level: e.target.value }))}
                  >
                    {LEVEL_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="form-label">Goal</label>
                  <select
                    className="input"
                    value={createForm.goal_type}
                    onChange={(e) => setCreateForm((prev) => ({ ...prev, goal_type: e.target.value }))}
                  >
                    {GOAL_OPTIONS.map((option) => (
                      <option key={option.value} value={option.value}>
                        {option.label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="flex justify-end gap-2">
                <button type="button" onClick={() => setShowCreateForm(false)} className="btn-secondary px-4 py-2">
                  Cancel
                </button>
                <button type="submit" disabled={loading.createPath} className="btn-primary px-4 py-2">
                  {loading.createPath ? 'Creating...' : 'Create Track'}
                </button>
              </div>
            </form>
          </section>
        ) : null}

        <div className="grid xl:grid-cols-[340px_minmax(0,1fr)] gap-5">
          <aside className="space-y-4">
            <div
              className="rounded-2xl p-4"
              style={{
                background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                border: '1px solid var(--border)',
              }}
            >
              <div className="flex items-center justify-between gap-2 mb-3">
                <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                  My Learning Tracks
                </h3>
                <span
                  className="text-xs font-semibold px-2 py-1 rounded-full"
                  style={{
                    color: 'var(--text-secondary)',
                    background: 'var(--surface-overlay)',
                    border: '1px solid var(--border)',
                  }}
                >
                  {paths.length}
                </span>
              </div>

              <div className="grid grid-cols-3 gap-1 mb-3">
                {PATH_FILTERS.map((filter) => (
                  <button
                    key={filter.id}
                    className="text-xs font-medium rounded-lg py-1.5"
                    style={{
                      color: pathFilter === filter.id ? 'var(--accent)' : 'var(--text-secondary)',
                      background: pathFilter === filter.id ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                      border:
                        pathFilter === filter.id
                          ? '1px solid var(--accent-border)'
                          : '1px solid var(--border)',
                    }}
                    onClick={() => setPathFilter(filter.id)}
                  >
                    {filter.label}
                  </button>
                ))}
              </div>

              {loading.paths ? (
                <div className="py-8 flex justify-center">
                  <div className="loading-spinner w-6 h-6" />
                </div>
              ) : null}

              <div className="space-y-2 max-h-[460px] overflow-auto pr-1">
                {filteredPaths.map((path) => {
                  const isActivePath = activePath?.id === path.id;
                  const completion = toPercent(path.completion_percentage || 0);

                  return (
                    <button
                      key={path.id}
                      onClick={() => handleSelectPath(path)}
                      className="w-full text-left rounded-xl p-3"
                      style={{
                        background: isActivePath ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                        border: isActivePath ? '1px solid var(--accent-border)' : '1px solid var(--border)',
                      }}
                    >
                      <div className="flex items-start justify-between gap-2">
                        <p className="text-sm font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
                          {path.title}
                        </p>
                        <PathStatusBadge status={path.status} />
                      </div>

                      <p className="text-xs mt-1 truncate" style={{ color: 'var(--text-muted)' }}>
                        {path.topic}
                      </p>

                      <div className="mt-2">
                        <ProgressBar value={completion} />
                      </div>

                      <div className="mt-2 flex items-center justify-between">
                        <p className="text-[11px]" style={{ color: 'var(--text-secondary)' }}>
                          Day {path.current_day || 1} / {path.duration_days}
                        </p>
                        <p className="text-[11px] font-semibold" style={{ color: 'var(--text-secondary)' }}>
                          {Math.round(completion)}%
                        </p>
                      </div>
                    </button>
                  );
                })}

                {!loading.paths && !filteredPaths.length ? (
                  <div
                    className="rounded-xl p-3 text-center text-xs"
                    style={{
                      color: 'var(--text-muted)',
                      background: 'var(--surface-overlay)',
                      border: '1px dashed var(--border)',
                    }}
                  >
                    No tracks found for this filter.
                  </div>
                ) : null}
              </div>
            </div>

            <div
              className="rounded-2xl p-4"
              style={{
                background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                border: '1px solid var(--border)',
              }}
            >
              <h3 className="text-sm font-semibold mb-3" style={{ color: 'var(--text-primary)' }}>
                Portfolio Summary
              </h3>
              <div className="space-y-2 text-xs" style={{ color: 'var(--text-secondary)' }}>
                <div className="flex items-center justify-between">
                  <span>Total tracks</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{totalTracks}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Active tracks</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{activeTracks}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Completed tracks</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{completedTracks}</span>
                </div>
                <div className="flex items-center justify-between">
                  <span>Avg completion</span>
                  <span className="font-semibold" style={{ color: 'var(--text-primary)' }}>{averageCompletion}%</span>
                </div>
              </div>
            </div>
          </aside>

          <section className="space-y-4 min-w-0">
            {!activePath ? (
              <div
                className="rounded-2xl p-10 text-center"
                style={{
                  background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                  border: '1px solid var(--border)',
                }}
              >
                <div className="flex justify-center mb-3">
                  <CircleDashed className="w-6 h-6" style={{ color: 'var(--text-muted)' }} />
                </div>
                <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                  Start your first learning track
                </h2>
                <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                  Create a track from the button above and begin with AI-generated daily learning.
                </p>
              </div>
            ) : (
              <>
                <div
                  className="rounded-2xl p-4"
                  style={{
                    background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                    border: '1px solid var(--border)',
                  }}
                >
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div>
                      <p className="text-xs font-semibold uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
                        Active Track
                      </p>
                      <h1 className="text-2xl font-semibold mt-0.5" style={{ color: 'var(--text-primary)' }}>
                        {activePath.title}
                      </h1>
                      <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                        {activePath.topic} • {titleCase(activePath.level)} • {titleCase(activePath.goal_type)}
                      </p>
                    </div>
                    <PathStatusBadge status={activePath.status} />
                  </div>

                  <div className="grid sm:grid-cols-2 xl:grid-cols-4 gap-3 mt-4">
                    <MetricTile
                      icon={BarChart3}
                      label="Completion"
                      value={`${Math.round(activePathCompletion)}%`}
                      hint={`${completedDays}/${activePath.duration_days} days`}
                    />
                    <MetricTile
                      icon={Flame}
                      label="Streak"
                      value={`${activePathStreak}`}
                      hint="Consecutive active days"
                    />
                    <MetricTile
                      icon={Layers}
                      label="Current Day"
                      value={`${activePathCurrentDay}`}
                      hint={nextUnlockedDay ? nextUnlockedDay.title : 'No pending day'}
                    />
                    <MetricTile
                      icon={Target}
                      label="Confidence"
                      value={
                        confidenceAverage === null
                          ? '--'
                          : `${Math.round(Math.max(0, Math.min(100, confidenceAverage * 100)))}%`
                      }
                      hint={
                        confidenceAverage === null
                          ? 'No review signals yet'
                          : 'Average topic confidence'
                      }
                    />
                  </div>
                </div>

                <div className="grid 2xl:grid-cols-[290px_minmax(0,1fr)_360px] gap-4 min-w-0">
                  <aside
                    className="rounded-2xl p-4"
                    style={{
                      background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    <div className="flex items-center justify-between mb-3">
                      <h3 className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                        Day Navigator
                      </h3>
                      <span
                        className="text-[11px] px-2 py-1 rounded-full"
                        style={{
                          color: 'var(--text-secondary)',
                          background: 'var(--surface-overlay)',
                          border: '1px solid var(--border)',
                        }}
                      >
                        {days.length} days
                      </span>
                    </div>

                    <div className="space-y-2 max-h-[calc(100vh-280px)] overflow-auto pr-1">
                      {days.map((day) => {
                        const isSelected = activeDay?.id === day.id;

                        return (
                          <button
                            key={day.id}
                            onClick={() => handleOpenDay(day)}
                            className="w-full text-left rounded-xl p-2.5"
                            style={{
                              background: isSelected ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                              border: isSelected ? '1px solid var(--accent-border)' : '1px solid var(--border)',
                              opacity: day.is_unlocked ? 1 : 0.72,
                            }}
                          >
                            <div className="flex items-start justify-between gap-2">
                              <div className="min-w-0">
                                <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
                                  Day {day.day_number}
                                </p>
                                <p className="text-xs mt-0.5 truncate" style={{ color: 'var(--text-secondary)' }}>
                                  {day.title}
                                </p>
                              </div>
                              <ChevronRight className="w-4 h-4 shrink-0" style={{ color: 'var(--text-muted)' }} />
                            </div>

                            <div className="mt-2">
                              <DayStateBadge day={day} />
                            </div>
                          </button>
                        );
                      })}

                      {!days.length ? (
                        <div
                          className="rounded-xl p-3 text-center text-xs"
                          style={{
                            color: 'var(--text-muted)',
                            background: 'var(--surface-overlay)',
                            border: '1px dashed var(--border)',
                          }}
                        >
                          This track has no scheduled days.
                        </div>
                      ) : null}
                    </div>
                  </aside>

                  <section
                    className="rounded-2xl p-4 max-h-[calc(100vh-220px)] overflow-auto min-w-0"
                    style={{
                      background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    {activeDay ? (
                      <>
                        <div className="flex flex-wrap items-start justify-between gap-3 mb-3">
                          <div>
                            <p className="text-xs uppercase tracking-wide" style={{ color: 'var(--text-muted)' }}>
                              Current Session
                            </p>
                            <h2 className="text-lg font-semibold" style={{ color: 'var(--text-primary)' }}>
                              Day {activeDay.day_number}: {activeDay.title}
                            </h2>
                            <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>
                              Stage: {stageMeta.title}
                            </p>
                          </div>

                          <div className="flex items-center gap-2">
                            <button
                              className="btn-secondary px-2.5 py-2"
                              disabled={!previousDay || !previousDay.is_unlocked}
                              onClick={() => handleOpenDay(previousDay)}
                            >
                              <ChevronLeft className="w-4 h-4" />
                              Prev
                            </button>
                            <button
                              className="btn-secondary px-2.5 py-2"
                              disabled={!nextDay || !nextDay.is_unlocked}
                              onClick={() => handleOpenDay(nextDay)}
                            >
                              Next
                              <ChevronRight className="w-4 h-4" />
                            </button>
                            <button
                              onClick={handleRegenerateDay}
                              disabled={loading.openDay}
                              className="btn-secondary px-3 py-2"
                            >
                              <RefreshCw className={`w-4 h-4 ${loading.openDay ? 'animate-spin' : ''}`} />
                              Regenerate
                            </button>
                          </div>
                        </div>

                        <StagePipeline stage={stage} />

                        {lastStageResult?.feedback ? (
                          <div
                            className="mt-4 rounded-xl p-3 flex items-start gap-2"
                            style={{
                              background: lastStageResult.passed
                                ? 'var(--success-subtle)'
                                : 'var(--warning-subtle)',
                              border: lastStageResult.passed
                                ? '1px solid var(--success-border)'
                                : '1px solid var(--warning-border)',
                            }}
                          >
                            {lastStageResult.passed ? (
                              <CheckCircle2 className="w-4 h-4 mt-0.5" style={{ color: 'var(--success)' }} />
                            ) : (
                              <Target className="w-4 h-4 mt-0.5" style={{ color: 'var(--warning)' }} />
                            )}
                            <div>
                              <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
                                {lastStageResult.passed ? 'Stage passed' : 'Retry recommended'}
                              </p>
                              <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                                {lastStageResult.feedback}
                              </p>
                            </div>
                          </div>
                        ) : null}

                        <div className="mt-4 flex items-center gap-2">
                          <button
                            className="text-xs px-3 py-1.5 rounded-lg"
                            style={{
                              color: workspaceTab === 'practice' ? 'var(--accent)' : 'var(--text-secondary)',
                              background: workspaceTab === 'practice' ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                              border:
                                workspaceTab === 'practice'
                                  ? '1px solid var(--accent-border)'
                                  : '1px solid var(--border)',
                            }}
                            onClick={() => setWorkspaceTab('practice')}
                          >
                            Practice Workspace
                          </button>
                          <button
                            className="text-xs px-3 py-1.5 rounded-lg"
                            style={{
                              color: workspaceTab === 'lesson' ? 'var(--accent)' : 'var(--text-secondary)',
                              background: workspaceTab === 'lesson' ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                              border:
                                workspaceTab === 'lesson'
                                  ? '1px solid var(--accent-border)'
                                  : '1px solid var(--border)',
                            }}
                            onClick={() => setWorkspaceTab('lesson')}
                          >
                            Lesson View
                          </button>
                        </div>
                      </>
                    ) : (
                      <div
                        className="rounded-xl p-8 text-center"
                        style={{ background: 'var(--surface-overlay)', border: '1px dashed var(--border)' }}
                      >
                        <CircleDashed className="w-6 h-6 mx-auto mb-2" style={{ color: 'var(--text-muted)' }} />
                        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                          Select a day from the left to start learning.
                        </p>
                      </div>
                    )}

                    {loading.openDay && activeDay ? (
                      <div className="py-16 flex justify-center">
                        <div className="loading-spinner w-8 h-8" />
                      </div>
                    ) : null}

                    {!loading.openDay && activeDay && dayContent ? (
                      <div className="mt-4">
                        {workspaceTab === 'lesson' ? (
                          <div
                            className="rounded-xl p-3"
                            style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}
                          >
                            <div className="flex items-center justify-between gap-2 mb-2">
                              <div className="flex items-center gap-2" style={{ color: 'var(--text-primary)' }}>
                                <BookOpen className="w-4 h-4" />
                                <h3 className="text-sm font-semibold">AI Lesson</h3>
                              </div>
                              <button
                                className="text-xs px-2.5 py-1 rounded-lg"
                                style={{
                                  background: 'var(--surface-raised)',
                                  border: '1px solid var(--border)',
                                  color: 'var(--text-secondary)',
                                }}
                                onClick={() => setShowFullLesson((value) => !value)}
                              >
                                {showFullLesson ? 'Show Summary' : 'Show Full Lesson'}
                              </button>
                            </div>

                            <div className="space-y-2">
                              {(showFullLesson
                                ? dayContent.lesson?.sections || []
                                : (dayContent.lesson?.sections || []).slice(0, 1)
                              ).map((section, index) => (
                                <div
                                  key={`lesson_${index}`}
                                  className="rounded-lg p-3"
                                  style={{
                                    background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                                    border: '1px solid var(--border)',
                                  }}
                                >
                                  <p className="text-xs font-semibold" style={{ color: 'var(--text-primary)' }}>
                                    {section.heading}
                                  </p>
                                  <p className="text-sm mt-1" style={{ color: 'var(--text-secondary)' }}>
                                    {section.text}
                                  </p>
                                </div>
                              ))}
                            </div>
                          </div>
                        ) : (
                          <div className="space-y-4">
                            {(stage === 'LESSON' || stage === 'INTERACTION') && (
                              <form
                                onSubmit={onSubmitInteraction}
                                className="rounded-xl p-3"
                                style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}
                              >
                                <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                  Interaction
                                </h3>
                                <div className="space-y-3">
                                  {(dayContent.interaction?.questions || []).map((question, index) => (
                                    <div
                                      key={question.id}
                                      className="rounded-lg p-3"
                                      style={{
                                        background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                                        border: '1px solid var(--border)',
                                      }}
                                    >
                                      <label
                                        className="text-xs font-semibold block mb-2"
                                        style={{ color: 'var(--text-primary)' }}
                                      >
                                        Q{index + 1}. {question.prompt}
                                      </label>
                                      <textarea
                                        className="textarea"
                                        rows={3}
                                        value={interactionAnswers[question.id] || ''}
                                        onChange={(e) =>
                                          setInteractionAnswers((prev) => ({
                                            ...prev,
                                            [question.id]: e.target.value,
                                          }))
                                        }
                                        required
                                      />
                                    </div>
                                  ))}
                                </div>

                                <div className="mt-3 flex justify-end">
                                  <button type="submit" disabled={loading.submitStage} className="btn-primary px-4 py-2">
                                    <Send className="w-4 h-4" />
                                    {loading.submitStage ? 'Submitting...' : 'Submit Interaction'}
                                  </button>
                                </div>
                              </form>
                            )}

                            {stage === 'TASK' && (
                              <form
                                onSubmit={onSubmitTask}
                                className="rounded-xl p-3"
                                style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}
                              >
                                <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                  Practical Task
                                </h3>

                                <ul className="space-y-2 mb-3">
                                  {(dayContent.task?.instructions || []).map((instruction, index) => (
                                    <li
                                      key={`task_instruction_${index}`}
                                      className="text-sm rounded-lg px-3 py-2"
                                      style={{
                                        color: 'var(--text-secondary)',
                                        background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                                        border: '1px solid var(--border)',
                                      }}
                                    >
                                      <span className="font-semibold mr-1" style={{ color: 'var(--text-primary)' }}>
                                        {index + 1}.
                                      </span>
                                      {instruction}
                                    </li>
                                  ))}
                                </ul>

                                <textarea
                                  className="textarea"
                                  rows={6}
                                  value={taskSubmission}
                                  onChange={(e) => setTaskSubmission(e.target.value)}
                                  placeholder="Describe your solution clearly and practically..."
                                  required
                                />

                                <div className="mt-3 flex justify-end">
                                  <button type="submit" disabled={loading.submitStage} className="btn-primary px-4 py-2">
                                    <ListChecks className="w-4 h-4" />
                                    {loading.submitStage ? 'Submitting...' : 'Submit Task'}
                                  </button>
                                </div>
                              </form>
                            )}

                            {stage === 'QUIZ' && (
                              <form
                                onSubmit={onSubmitQuiz}
                                className="rounded-xl p-3"
                                style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}
                              >
                                <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                  Quiz
                                </h3>

                                <div className="space-y-3">
                                  {(dayContent.quiz?.questions || []).map((question, index) => (
                                    <div
                                      key={question.id}
                                      className="rounded-lg p-3"
                                      style={{
                                        background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                                        border: '1px solid var(--border)',
                                      }}
                                    >
                                      <p className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                        {index + 1}. {question.stem}
                                      </p>

                                      <div className="grid sm:grid-cols-2 gap-2">
                                        {(question.options || []).map((option) => {
                                          const isSelected = quizAnswers[question.id] === option.label;
                                          return (
                                            <label
                                              key={`${question.id}_${option.label}`}
                                              className="rounded-lg p-2 text-sm cursor-pointer"
                                              style={{
                                                background: isSelected ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                                                border: isSelected
                                                  ? '1px solid var(--accent-border)'
                                                  : '1px solid var(--border)',
                                              }}
                                            >
                                              <input
                                                type="radio"
                                                name={question.id}
                                                value={option.label}
                                                checked={isSelected}
                                                onChange={(e) =>
                                                  setQuizAnswers((prev) => ({
                                                    ...prev,
                                                    [question.id]: e.target.value,
                                                  }))
                                                }
                                                className="mr-2"
                                              />
                                              {option.label}. {option.text}
                                            </label>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  ))}
                                </div>

                                <div className="mt-3 flex justify-end">
                                  <button type="submit" disabled={loading.submitStage} className="btn-primary px-4 py-2">
                                    <Zap className="w-4 h-4" />
                                    {loading.submitStage ? 'Submitting...' : 'Submit Quiz'}
                                  </button>
                                </div>
                              </form>
                            )}

                            {stage === 'GAME' && (
                              <form
                                onSubmit={onSubmitGame}
                                className="rounded-xl p-3"
                                style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}
                              >
                                <h3 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                  Learning Game
                                </h3>

                                <div className="space-y-3">
                                  {(dayContent.game?.rounds || []).map((round, index) => (
                                    <div
                                      key={round.id}
                                      className="rounded-lg p-3"
                                      style={{
                                        background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                                        border: '1px solid var(--border)',
                                      }}
                                    >
                                      <p className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
                                        Round {index + 1}. {round.prompt}
                                      </p>

                                      <div className="grid sm:grid-cols-3 gap-2">
                                        {(round.choices || []).map((choice) => {
                                          const isSelected = gameMoves[round.id] === choice.label;
                                          return (
                                            <label
                                              key={`${round.id}_${choice.label}`}
                                              className="rounded-lg p-2 text-sm cursor-pointer"
                                              style={{
                                                background: isSelected ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
                                                border: isSelected
                                                  ? '1px solid var(--accent-border)'
                                                  : '1px solid var(--border)',
                                              }}
                                            >
                                              <input
                                                type="radio"
                                                name={round.id}
                                                value={choice.label}
                                                checked={isSelected}
                                                onChange={(e) =>
                                                  setGameMoves((prev) => ({
                                                    ...prev,
                                                    [round.id]: e.target.value,
                                                  }))
                                                }
                                                className="mr-2"
                                              />
                                              {choice.label}. {choice.text}
                                            </label>
                                          );
                                        })}
                                      </div>
                                    </div>
                                  ))}
                                </div>

                                <div className="mt-3 flex justify-end">
                                  <button type="submit" disabled={loading.submitStage} className="btn-primary px-4 py-2">
                                    <Puzzle className="w-4 h-4" />
                                    {loading.submitStage ? 'Submitting...' : 'Submit Game'}
                                  </button>
                                </div>
                              </form>
                            )}

                            {stage === 'COMPLETE' && (
                              <div
                                className="rounded-xl p-4"
                                style={{
                                  background: 'var(--success-subtle)',
                                  border: '1px solid var(--success-border)',
                                }}
                              >
                                <div className="flex items-center gap-2 mb-2" style={{ color: 'var(--success)' }}>
                                  <Trophy className="w-4 h-4" />
                                  <p className="text-sm font-semibold">Ready to complete this day</p>
                                </div>
                                <p className="text-sm mb-3" style={{ color: 'var(--text-secondary)' }}>
                                  Finish this day to unlock your next mission and keep momentum.
                                </p>
                                <button
                                  onClick={onCompleteDay}
                                  disabled={loading.completeDay}
                                  className="btn-primary px-4 py-2"
                                >
                                  {loading.completeDay ? (
                                    <>
                                      <RefreshCw className="w-4 h-4 animate-spin" />
                                      Completing...
                                    </>
                                  ) : (
                                    <>
                                      <Trophy className="w-4 h-4" />
                                      Complete Day
                                    </>
                                  )}
                                </button>
                              </div>
                            )}
                          </div>
                        )}
                      </div>
                    ) : null}
                  </section>

                  <aside className="space-y-4 min-w-0">
                    <section
                      className="rounded-2xl p-4"
                      style={{
                        background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <div className="flex items-center gap-2 mb-3" style={{ color: 'var(--text-primary)' }}>
                        <Bot className="w-4 h-4" />
                        <h3 className="text-sm font-semibold">AI Mentor</h3>
                      </div>

                      <div className="flex flex-wrap gap-1.5 mb-3">
                        {mentorQuickPrompts.map((prompt, index) => (
                          <button
                            key={`mentor_prompt_${index}`}
                            className="text-[11px] px-2 py-1 rounded-lg"
                            style={{
                              background: 'var(--surface-overlay)',
                              border: '1px solid var(--border)',
                              color: 'var(--text-secondary)',
                            }}
                            onClick={() => handleQuickPrompt(prompt)}
                            disabled={loading.askMentor}
                          >
                            {prompt}
                          </button>
                        ))}
                      </div>

                      <div
                        className="space-y-2 max-h-[280px] overflow-auto pr-1 mb-3"
                        style={{
                          background: 'color-mix(in srgb, var(--surface-overlay) 70%, transparent)',
                          border: '1px solid var(--border)',
                          borderRadius: '0.75rem',
                          padding: '0.5rem',
                        }}
                      >
                        {!mentorMessages.length ? (
                          <div className="rounded-lg p-3 text-center" style={{ color: 'var(--text-muted)' }}>
                            <MessageSquareText className="w-4 h-4 mx-auto mb-1" />
                            <p className="text-xs">Ask anything you missed. AI Mentor will explain with steps.</p>
                          </div>
                        ) : (
                          mentorMessages.map((message) => (
                            <MentorMessage key={message.id} message={message} />
                          ))
                        )}
                      </div>

                      <form onSubmit={onAskMentor} className="space-y-2">
                        <textarea
                          className="textarea"
                          rows={3}
                          value={mentorQuestion}
                          onChange={(e) => setMentorQuestion(e.target.value)}
                          placeholder="Ask what you missed, ask for examples, or ask for simpler explanation..."
                        />
                        <button
                          type="submit"
                          disabled={loading.askMentor || !mentorQuestion.trim()}
                          className="btn-primary px-4 py-2 w-full"
                        >
                          {loading.askMentor ? (
                            <>
                              <RefreshCw className="w-4 h-4 animate-spin" />
                              Thinking...
                            </>
                          ) : (
                            <>
                              <Send className="w-4 h-4" />
                              Ask AI Mentor
                            </>
                          )}
                        </button>
                      </form>
                    </section>

                    <section
                      className="rounded-2xl p-4"
                      style={{
                        background: 'color-mix(in srgb, var(--surface-raised) 90%, transparent)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      <div className="flex items-center gap-2 mb-3" style={{ color: 'var(--text-primary)' }}>
                        <Target className="w-4 h-4" />
                        <h3 className="text-sm font-semibold">Review Recommendations</h3>
                      </div>

                      {!review.length ? (
                        <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>
                          No weak topics detected yet. Keep progressing and recommendations will adapt.
                        </p>
                      ) : (
                        <div className="space-y-2">
                          {review.map((item) => {
                            const confidence = Math.round(
                              Math.max(0, Math.min(100, Number(item.confidence || 0) * 100))
                            );
                            return (
                              <div
                                key={item.topic}
                                className="rounded-xl p-3"
                                style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}
                              >
                                <p className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                                  {item.topic}
                                </p>
                                <p className="text-xs mt-0.5" style={{ color: 'var(--text-secondary)' }}>
                                  {item.reason}
                                </p>
                                <div className="mt-2">
                                  <ProgressBar value={confidence} />
                                </div>
                                <p className="text-[11px] mt-1" style={{ color: 'var(--text-muted)' }}>
                                  Confidence: {confidence}%
                                </p>
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </section>
                  </aside>
                </div>
              </>
            )}
          </section>
        </div>
      </main>
    </div>
  );
}

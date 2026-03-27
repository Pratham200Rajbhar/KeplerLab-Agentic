'use client';

import { useState, useRef, useCallback, useEffect, useMemo, memo } from 'react';
import dynamic from 'next/dynamic';
import {
  Layers,
  ClipboardCheck,
  Monitor,
  Video,
  Mic,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Brain,
} from 'lucide-react';

import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import { useConfirm } from '@/stores/useConfirmStore';
import usePodcastStore from '@/stores/usePodcastStore';
import { generateFlashcards, generateQuiz, downloadBlob } from '@/lib/api/generation';
import { generateMindMap } from '@/lib/api/mindmap';
import {
  generatePresentation as generatePresentationApi,
  getPresentation,
  updatePresentation as updatePresentationApi,
  downloadPresentation,
} from '@/lib/api/presentation';
import {
  saveGeneratedContent,
  getGeneratedContent,
  deleteGeneratedContent,
  updateGeneratedContent,
  rateGeneratedContent,
} from '@/lib/api/notebooks';
import { PANEL } from '@/lib/utils/constants';

import FeatureCard from './FeatureCard';
import ExplainerDialog from './ExplainerDialog';
import PresentationDialog from '@/components/presentation/PresentationDialog';
import PresentationEditor from '@/components/presentation/PresentationEditor';
import PodcastConfigDialog from '@/components/podcast/PodcastConfigDialog';

import {
  InlineFlashcardsView,
  InlineQuizView,
  InlineExplainerView,
  FlashcardConfigDialog,
  QuizConfigDialog,
  HistoryRenameModal,
  ContentHistory,
} from './index';

const PodcastStudio = dynamic(
  () => import('@/components/podcast/PodcastStudio'),
  { ssr: false, loading: () => <LoadingSpinner /> }
);
const MindMapCanvas = dynamic(
  () => import('@/components/mindmap/MindMapCanvas'),
  { ssr: false, loading: () => <LoadingSpinner /> }
);

function LoadingSpinner() {
  return (
    <div className="flex items-center justify-center py-12">
      <div className="loading-spinner w-8 h-8" />
    </div>
  );
}


const PodcastProgress = memo(function PodcastProgress({ phase, progress }) {
  if (phase !== 'generating' || !progress) return null;
  return (
    <div className="mt-3 p-3 rounded-xl border border-[var(--accent-border,var(--accent))] bg-[var(--accent-subtle)] animate-fade-in">
      <div className="flex items-center gap-2 mb-2">
        <div className="loading-spinner w-3.5 h-3.5" />
        <span className="text-xs font-medium text-[var(--text-primary)] flex-1 truncate">
          {progress.message || 'Generating podcast\u2026'}
        </span>
        <span className="text-[10px] text-[var(--text-muted)] tabular-nums shrink-0">
          {Math.round(progress.pct || 0)}%
        </span>
      </div>
      <div
        className="h-1.5 rounded-full bg-[var(--surface-overlay)] overflow-hidden"
        role="progressbar"
        aria-valuenow={Math.round(progress.pct || 0)}
        aria-valuemax={100}
      >
        <div
          className="h-full rounded-full bg-[var(--accent)] transition-all duration-700 ease-out"
          style={{ width: `${Math.max(progress.pct || 0, 3)}%` }}
        />
      </div>
    </div>
  );
});

export default function StudioPanel() {

  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const draftMode = useAppStore((s) => s.draftMode);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);
  const loading = useAppStore((s) => s.loading);
  const setFlashcards = useAppStore((s) => s.setFlashcards);
  const setQuiz = useAppStore((s) => s.setQuiz);
  const setPresentation = useAppStore((s) => s.setPresentation);
  const setLoadingState = useAppStore((s) => s.setLoadingState);

  const podcastPhase = usePodcastStore((s) => s.phase);
  const podcastSessions = usePodcastStore((s) => s.sessions);
  const podcastProgress = usePodcastStore((s) => s.generationProgress);
  const podcastError = usePodcastStore((s) => s.error);
  const loadPodcastSessions = usePodcastStore((s) => s.loadSessions);
  const loadPodcastSession = usePodcastStore((s) => s.loadSession);
  const removePodcastSession = usePodcastStore((s) => s.removeSession);
  const createPodcast = usePodcastStore((s) => s.create);
  const startPodcastGeneration = usePodcastStore((s) => s.startGeneration);
  const setPodcastError = usePodcastStore((s) => s.setError);

  const toast = useToast();
  const confirm = useConfirm();

  const effectiveMaterial =
    selectedSources.length > 0
      ? materials.find((m) => selectedSources.includes(m.id)) || null
      : null;

  const selectedMaterialIds = selectedSources;


  const [activeView, setActiveView] = useState(null);


  const [flashcardsData, setFlashcardsData] = useState(null);
  const [quizData, setQuizData] = useState(null);
  const [presentationData, setPresentationData] = useState(null);
  const [explainerData, setExplainerData] = useState(null);
  const [mindmapData, setMindmapData] = useState(null);
  const [mindmapFullscreen, setMindmapFullscreen] = useState(false);
  const [mindmapRating, setMindmapRating] = useState(null);
  const [mindmapContentId, setMindmapContentId] = useState(null);
  const [activePresentationSlide, setActivePresentationSlide] = useState(0);
  const [isPresentationUpdating, setIsPresentationUpdating] = useState(false);
  const [isPresentationDownloading, setIsPresentationDownloading] = useState(false);


  const [showPresentationConfig, setShowPresentationConfig] = useState(false);
  const [showQuizConfig, setShowQuizConfig] = useState(false);
  const [showFlashcardConfig, setShowFlashcardConfig] = useState(false);
  const [showExplainerDialog, setShowExplainerDialog] = useState(false);
  const [showPodcastConfig, setShowPodcastConfig] = useState(false);


  const [contentHistory, setContentHistory] = useState([]);
  const [activeHistoryMenu, setActiveHistoryMenu] = useState(null);
  const [showRenameHistoryModal, setShowRenameHistoryModal] = useState(false);
  const [renamingHistoryItem, setRenamingHistoryItem] = useState(null);
  const [newHistoryTitle, setNewHistoryTitle] = useState('');


  const [width, setWidth] = useState(PANEL.STUDIO.DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef(null);
  const abortControllerRef = useRef({});

  const handleCancelGeneration = useCallback((type) => {
    abortControllerRef.current[type]?.abort();
  }, []);


  const prevNotebookId = useRef(null);

  useEffect(() => {
    const notebookId = currentNotebook?.id;
    if (notebookId === prevNotebookId.current) return;
    prevNotebookId.current = notebookId;

    setFlashcardsData(null);
    setQuizData(null);
    setPresentationData(null);
    setActivePresentationSlide(0);
    setMindmapData(null);
    setMindmapFullscreen(false);
    setMindmapContentId(null);
    setMindmapRating(null);
    setShowPresentationConfig(false);
    setShowQuizConfig(false);
    setShowFlashcardConfig(false);
    setShowExplainerDialog(false);
    setContentHistory([]);
    setFlashcards(null);
    setQuiz(null);
    setPresentation(null);
    setActiveView(null);

    // Use notebook ID and draft state to control loading
    if (currentNotebook?.id) {
      loadPodcastSessions(currentNotebook.id, currentNotebook.isDraft || draftMode);
    }

    const loadSavedContent = async () => {
      if (currentNotebook?.id && !currentNotebook.isDraft && !draftMode) {
        try {
          const contents = await getGeneratedContent(currentNotebook.id);
          setContentHistory(contents.map((c) => ({ ...c })));
          const seen = new Set();
          for (const c of contents) {
            if (seen.has(c.content_type)) continue;
            seen.add(c.content_type);
            switch (c.content_type) {
              case 'flashcards':
                setFlashcardsData(c.data);
                setFlashcards(c.data);
                break;
              case 'quiz':
                setQuizData(c.data);
                setQuiz(c.data);
                break;
              case 'presentation':
                setPresentationData(c);
                setPresentation(c.data);
                break;
              case 'mindmap':
                setMindmapData(c.data);
                setMindmapContentId(c.id);
                setMindmapRating(c.rating || null);
                break;
            }
          }
        } catch (error) {
          console.error('Failed to load saved content:', error);
        }
      }
    };
    loadSavedContent();
  }, [
    currentNotebook?.id,
    currentNotebook?.isDraft,
    draftMode,
    loadPodcastSessions,
    setFlashcards,
    setQuiz,
    setPresentation
  ]);


  const handleMouseMove = useCallback(
    (e) => {
      if (isResizing && panelRef.current) {
        const rect = panelRef.current.getBoundingClientRect();
        const newWidth = rect.right - e.clientX;
        if (newWidth >= PANEL.STUDIO.MIN_WIDTH) {
          setWidth(newWidth);
        }
      }
    },
    [isResizing]
  );

  const handleMouseUp = useCallback(() => setIsResizing(false), []);

  useEffect(() => {
    if (isResizing) {
      document.addEventListener('mousemove', handleMouseMove);
      document.addEventListener('mouseup', handleMouseUp);
    }
    return () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };
  }, [isResizing, handleMouseMove, handleMouseUp]);

  const canSave = currentNotebook?.id && !currentNotebook.isDraft && !draftMode;

  const trySave = async (contentType, data, title) => {
    if (!canSave) return null;
    try {
      const saved = await saveGeneratedContent(
        currentNotebook.id,
        contentType,
        data,
        title,
        effectiveMaterial?.id
      );
      return { ...saved, data };
    } catch (error) {
      console.error(`Failed to save ${contentType}:`, error);
      return null;
    }
  };


  const handleFlashcardsClick = () => {
    setShowFlashcardConfig(true);
  };

  const handleGenerateFlashcards = async (options = {}) => {
    if (!effectiveMaterial) return;
    setShowFlashcardConfig(false);
    setLoadingState('flashcards', true);
    const ac = new AbortController();
    abortControllerRef.current.flashcards = ac;
    try {
      const data = await generateFlashcards(effectiveMaterial.id, {
        ...options,
        materialIds: selectedMaterialIds,
        signal: ac.signal,
      });
      setFlashcardsData(data);
      setFlashcards(data);
      const saved = await trySave(
        'flashcards',
        data,
        data.title || `${data.flashcards?.length || 0} Flashcards`
      );
      if (saved) {
        setContentHistory((prev) => [saved, ...prev]);
        toast.success(`Flashcards saved to Created`);
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to generate flashcards. Please try again.');
    } finally {
      setLoadingState('flashcards', false);
    }
  };

  const handleQuizClick = () => {
    setShowQuizConfig(true);
  };

  const handleGenerateQuiz = async (options = {}) => {
    if (!effectiveMaterial) return;
    setShowQuizConfig(false);
    setLoadingState('quiz', true);
    const ac = new AbortController();
    abortControllerRef.current.quiz = ac;
    try {
      const data = await generateQuiz(effectiveMaterial.id, {
        ...options,
        materialIds: selectedMaterialIds,
        signal: ac.signal,
      });
      setQuizData(data);
      setQuiz(data);
      const saved = await trySave(
        'quiz',
        data,
        data.title || `${data.questions?.length || 0} Questions`
      );
      if (saved) {
        setContentHistory((prev) => [saved, ...prev]);
        toast.success(`Quiz saved to Created`);
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to generate quiz. Please try again.');
    } finally {
      setLoadingState('quiz', false);
    }
  };

  const handlePresentationClick = () => {
    setShowPresentationConfig(true);
  };

  const handleGeneratePresentation = async (options = {}) => {
    if (!effectiveMaterial) return;
    setShowPresentationConfig(false);
    setLoadingState('presentation', true);
    const ac = new AbortController();
    abortControllerRef.current.presentation = ac;
    try {
      const data = await generatePresentationApi(
        {
          notebookId: currentNotebook?.id,
          materialIds: selectedMaterialIds,
          title: options.title,
          instruction: options.instruction,
        },
        { signal: ac.signal }
      );
      setPresentationData(data);
      setPresentation(data?.data || null);
      setActivePresentationSlide(0);
      setContentHistory((prev) => [data, ...prev.filter((item) => item.id !== data.id)]);
      setActiveView('presentation');
      toast.success('Presentation generated');
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to generate presentation. Please try again.');
    } finally {
      setLoadingState('presentation', false);
    }
  };

  const handleUpdatePresentation = async (instruction) => {
    if (!presentationData?.id) return;
    setIsPresentationUpdating(true);
    try {
      const updated = await updatePresentationApi({
        presentationId: presentationData.id,
        instruction,
        active_slide_index: activePresentationSlide,
      });
      setPresentationData(updated);
      setPresentation(updated?.data || null);
      setContentHistory((prev) => prev.map((item) => (item.id === updated.id ? updated : item)));
      toast.success('Presentation updated');
    } catch (error) {
      toast.error(error.message || 'Failed to update presentation');
    } finally {
      setIsPresentationUpdating(false);
      useAppStore.getState().setPresentationUpdateProgress('');
    }
  };

  const handleDownloadPresentation = async (format = 'pptx') => {
    if (!presentationData?.id) return;
    const normalizedFormat = String(format || 'pptx').toLowerCase();
    const extension = normalizedFormat === 'pdf' || normalizedFormat === 'html' ? normalizedFormat : 'pptx';
    const safeBase = String(presentationData?.title || 'presentation')
      .replace(/[\\/:*?"<>|]+/g, '_')
      .trim() || 'presentation';
    setIsPresentationDownloading(true);
    try {
      const { blob, filename } = await downloadPresentation(presentationData.id, { format: normalizedFormat });
      const finalName = filename || `${safeBase}.${extension}`;
      downloadBlob(blob, finalName);
    } catch (error) {
      toast.error(error.message || 'Failed to download presentation');
    } finally {
      setIsPresentationDownloading(false);
    }
  };

  const handleMindMapClick = async () => {
    if (!effectiveMaterial) return;
    setLoadingState('mindmap', true);
    const ac = new AbortController();
    abortControllerRef.current.mindmap = ac;
    try {
      const res = await generateMindMap(currentNotebook?.id, selectedMaterialIds);

      setMindmapData(res.data);
      setMindmapContentId(res.id);
      setMindmapRating(null);
      setActiveView('mindmap');
      setMindmapFullscreen(false);

      if (res.id) {
        setContentHistory((prev) => [res, ...prev]);
        toast.success(`Mind Map saved to Created`);
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to generate mind map. Please try again.');
    } finally {
      setLoadingState('mindmap', false);
    }
  };

  const handleCancelMindMap = () => {
    abortControllerRef.current.mindmap?.abort();
    setLoadingState('mindmap', false);
  };

  const handleToggleMindmapFullscreen = () => {
    setMindmapFullscreen((prev) => !prev);
  };

  const handleMindMapRate = async (contentId, rating) => {
    if (!currentNotebook?.id) return;
    try {
      await rateGeneratedContent(currentNotebook.id, contentId, rating);
      setMindmapRating(rating);
      setContentHistory((prev) =>
        prev.map((item) =>
          item.id === contentId ? { ...item, rating } : item
        )
      );
      toast.success('Rating saved');
    } catch (error) {
      toast.error('Failed to save rating');
    }
  };


  const handleViewHistoryItem = async (item) => {
    switch (item.content_type) {
      case 'flashcards':
        setFlashcardsData(item.data);
        setFlashcards(item.data);
        setActiveView('flashcards');
        break;
      case 'quiz':
        setQuizData(item.data);
        setQuiz(item.data);
        setActiveView('quiz');
        break;
      case 'presentation':
        try {
          const data = await getPresentation(item.id);
          setPresentationData(data);
          setPresentation(data?.data || null);
          setActivePresentationSlide(0);
        } catch (error) {
          toast.error(error.message || 'Failed to load presentation');
          return;
        }
        setActiveView('presentation');
        break;
      case 'explainer':
        setExplainerData(item.data);
        setActiveView('explainer');
        break;
      case 'podcast':
        loadPodcastSession(item.id);
        setActiveView('podcast');
        break;
      case 'mindmap':
        setMindmapData(item.data);
        setMindmapContentId(item.id);
        setMindmapRating(item.rating);
        setActiveView('mindmap');
        setMindmapFullscreen(false);
        break;
    }
  };

  const handleHistoryRename = async (newTitle) => {
    if (!newTitle?.trim() || !renamingHistoryItem || !currentNotebook) return;
    try {
      if (renamingHistoryItem.content_type === 'podcast') {
        const { updateSessionTitle } = usePodcastStore.getState();
        await updateSessionTitle(renamingHistoryItem.id, newTitle.trim());
        // Podcast title update is reflected via store reload or local state update
        loadPodcastSessions(currentNotebook.id);
      } else {
        const updated = await updateGeneratedContent(
          currentNotebook.id,
          renamingHistoryItem.id,
          newTitle.trim()
        );
        setContentHistory((prev) =>
          prev.map((item) => (item.id === renamingHistoryItem.id ? updated : item))
        );
      }
      setShowRenameHistoryModal(false);
      setRenamingHistoryItem(null);
      setNewHistoryTitle('');
    } catch (err) {
      toast.error('Failed to rename content. Please try again.');
    }
  };

  const handleHistoryDelete = async (item, e) => {
    e?.stopPropagation();
    setActiveHistoryMenu(null);
    const ok = await confirm({
      title: 'Delete content?',
      message: `"${item.title || item.content_type}" will be permanently deleted.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok || !currentNotebook) return;

    try {
      if (item.content_type === 'podcast') {
        await removePodcastSession(item.id);
      } else {
        await deleteGeneratedContent(currentNotebook.id, item.id);
        setContentHistory((prev) => prev.filter((c) => c.id !== item.id));
      }

      if (activeView === item.content_type) {
        switch (item.content_type) {
          case 'flashcards':
            if (flashcardsData?.id === item.id) {
              setFlashcardsData(null);
              setFlashcards(null);
              setActiveView(null);
            }
            break;
          case 'quiz':
            if (quizData?.id === item.id) {
              setQuizData(null);
              setQuiz(null);
              setActiveView(null);
            }
            break;
          case 'presentation':
            if (presentationData?.id === item.id) {
              setPresentationData(null);
              setPresentation(null);
              setActiveView(null);
            }
            break;
          case 'mindmap':
            if (mindmapContentId === item.id) {
              setMindmapData(null);
              setMindmapContentId(null);
              setMindmapRating(null);
              setMindmapFullscreen(false);
            }
            break;
        }
      }
    } catch (err) {
      toast.error('Failed to delete content. Please try again.');
    }
  };

  const handleHistoryShare = async (item, e) => {
    e.stopPropagation();
    setActiveHistoryMenu(null);
    try {
      await navigator.clipboard.writeText(JSON.stringify(item.data, null, 2));
      toast.success('Content copied to clipboard');
    } catch {
      toast.error('Failed to copy to clipboard');
    }
  };

  const handleHistoryDownload = (item, e) => {
    e.stopPropagation();
    setActiveHistoryMenu(null);
    try {
      const contentStr = JSON.stringify(item.data, null, 2);
      const blob = new Blob([contentStr], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${item.title || item.content_type}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      toast.error('Failed to export content');
    }
  };

  const openHistoryRenameModal = (item, e) => {
    e?.stopPropagation();
    setActiveHistoryMenu(null);
    setRenamingHistoryItem(item);
    setNewHistoryTitle(item.title || item.content_type);
    setShowRenameHistoryModal(true);
  };

  const combinedHistory = useMemo(() => {
    const podcastItems = (podcastSessions || []).map((s) => ({
      id: s.id,
      content_type: 'podcast',
      title: s.title || 'AI Podcast',
      created_at: s.createdAt,
      data: s,
    }));
    return [...contentHistory, ...podcastItems].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
  }, [contentHistory, podcastSessions]);


  const podcastGeneratingRef = useRef(false);

  const handlePodcastGenerate = async (config) => {
    if (podcastGeneratingRef.current) return;
    podcastGeneratingRef.current = true;
    setShowPodcastConfig(false);
    setLoadingState('podcast', true);
    try {
      const session = await createPodcast(config, currentNotebook?.id, selectedSources);
      if (session?.id) {
        await startPodcastGeneration(session.id);
      }
    } catch (err) {
      toast.error(err.message || 'Failed to start podcast generation.');
      setLoadingState('podcast', false);
      podcastGeneratingRef.current = false;
    }
  };

  useEffect(() => {
    if (podcastPhase === 'generating') {
      setLoadingState('podcast', true);
    } else {
      setLoadingState('podcast', false);
      podcastGeneratingRef.current = false;
    }
    if (podcastPhase === 'player' && !activeView) {
      loadPodcastSessions(currentNotebook?.id);
    }
  }, [podcastPhase, loadPodcastSessions, setLoadingState, activeView, currentNotebook?.id]);


  const outputs = [
    {
      id: 'flashcards',
      title: 'Flashcards',
      description: 'Study with spaced repetition',
      icon: <Layers className="w-5 h-5" />,
      onClick: handleFlashcardsClick,
      onCancel: () => handleCancelGeneration('flashcards'),
    },
    {
      id: 'quiz',
      title: 'Practice Quiz',
      description: 'Test your understanding',
      icon: <ClipboardCheck className="w-5 h-5" />,
      onClick: handleQuizClick,
      onCancel: () => handleCancelGeneration('quiz'),
    },
    {
      id: 'presentation',
      title: 'Presentation',
      description: 'Generate a slide deck from content',
      icon: <Monitor className="w-5 h-5" />,
      onClick: handlePresentationClick,
      onCancel: () => handleCancelGeneration('presentation'),
    },
    {
      id: 'explainer',
      title: 'Explainer Video',
      description: 'Create a narrated video from slides',
      icon: <Video className="w-5 h-5" />,
      onClick: () => setShowExplainerDialog(true),
    },
    {
      id: 'podcast',
      title: 'AI Podcast',
      description:
        podcastPhase === 'generating'
          ? podcastProgress?.message || 'Generating…'
          : 'Two-host AI podcast from your sources',
      icon: <Mic className="w-5 h-5" />,
      onClick: () => {
        if (podcastPhase !== 'generating') setShowPodcastConfig(true);
      },
    },
    {
      id: 'mindmap',
      title: 'Mind Map',
      description: 'Visualize concepts as a connected diagram',
      icon: <Brain className="w-5 h-5" />,
      onClick: handleMindMapClick,
      onCancel: handleCancelMindMap,
    },
  ];

  const completedPodcastSessions = (podcastSessions || []).filter(
    (s) =>
      s.status === 'ready' ||
      s.status === 'playing' ||
      s.status === 'paused' ||
      s.status === 'completed'
  );

  const viewTitles = {
    flashcards: 'Flashcards',
    quiz: 'Quiz',
    presentation: 'Presentation',
    explainer: 'Explainer Video',
    podcast: 'AI Podcast',
    mindmap: 'Mind Map',
  };


  const renderInlineContent = () => {
    switch (activeView) {
      case 'flashcards':
        return <InlineFlashcardsView flashcards={flashcardsData} onClose={() => setActiveView(null)} />;
      case 'quiz':
        return <InlineQuizView quiz={quizData} onClose={() => setActiveView(null)} />;
      case 'presentation':
        return loading['presentation'] ? (
          <div className="flex flex-col items-center justify-center py-12 gap-3" role="status">
            <div className="loading-spinner w-8 h-8" />
            <p className="text-sm text-[var(--text-muted)]">Generating presentation...</p>
            <p className="text-xs text-[var(--text-muted)]">This may take a minute</p>
            <button
              onClick={() => handleCancelGeneration('presentation')}
              className="mt-2 btn-secondary text-[var(--danger)] text-sm flex items-center gap-2"
            >
              Cancel
            </button>
          </div>
        ) : (
          <PresentationEditor
            presentation={presentationData}
            activeSlide={activePresentationSlide}
            onSelectSlide={setActivePresentationSlide}
            onUpdate={handleUpdatePresentation}
            onDownload={handleDownloadPresentation}
            updating={isPresentationUpdating}
            downloading={isPresentationDownloading}
          />
        );
      case 'explainer':
        return <InlineExplainerView explainer={explainerData} onClose={() => setActiveView(null)} />;
      case 'podcast':
        return <PodcastStudio onClose={() => setActiveView(null)} onRequestNew={() => setShowPodcastConfig(true)} />;

      case 'mindmap':
        if (mindmapFullscreen && mindmapData) {
          return (
            <div className="fixed inset-x-0 bottom-0 top-[86px] z-[220] flex flex-col bg-surface-50 animate-fade-in shadow-2xl">
              <div className="flex-1 min-h-0 relative">
                <MindMapCanvas
                  mindmapData={mindmapData}
                  onClose={() => {
                    setMindmapFullscreen(false);
                    setActiveView(null);
                  }}
                  onRate={handleMindMapRate}
                  contentId={mindmapContentId}
                  isFullscreen={true}
                  onToggleFullscreen={handleToggleMindmapFullscreen}
                  savedRating={mindmapRating}
                />
              </div>
            </div>
          );
        } else if (mindmapData) {
          return (
            <div className="flex-1 h-full min-h-0 relative">
              <MindMapCanvas
                mindmapData={mindmapData}
                onClose={() => setActiveView(null)}
                onRate={handleMindMapRate}
                contentId={mindmapContentId}
                isFullscreen={false}
                onToggleFullscreen={handleToggleMindmapFullscreen}
                savedRating={mindmapRating}
              />
            </div>
          );
        }
        return null; // Fallback if mindmapData is null but activeView is 'mindmap'

      default:
        return null;
    }
  };


  return (
    <>
      {/* History Rename Modal */}
      {showRenameHistoryModal && (
        <HistoryRenameModal
          item={renamingHistoryItem}
          onConfirm={handleHistoryRename}
          onClose={() => {
            setShowRenameHistoryModal(false);
            setRenamingHistoryItem(null);
            setNewHistoryTitle('');
          }}
        />
      )}

      {/* Configuration Dialogs */}
      {showPresentationConfig && (
        <PresentationDialog
          onGenerate={handleGeneratePresentation}
          onClose={() => setShowPresentationConfig(false)}
          loading={loading['presentation']}
          materialIds={selectedMaterialIds}
        />
      )}

      {showQuizConfig && (
        <QuizConfigDialog
          onGenerate={handleGenerateQuiz}
          onCancel={() => setShowQuizConfig(false)}
          loading={loading['quiz']}
          materialIds={selectedMaterialIds}
        />
      )}

      {showFlashcardConfig && (
        <FlashcardConfigDialog
          onGenerate={handleGenerateFlashcards}
          onCancel={() => setShowFlashcardConfig(false)}
          loading={loading['flashcards']}
          materialIds={selectedMaterialIds}
        />
      )}

      {showExplainerDialog && (
        <ExplainerDialog
          onClose={() => setShowExplainerDialog(false)}
          materialIds={selectedMaterialIds}
          notebookId={currentNotebook?.id}
        />
      )}

      {showPodcastConfig && (
        <PodcastConfigDialog
          onClose={() => setShowPodcastConfig(false)}
        />
      )}

      <aside
        ref={panelRef}
        className="glass-light workspace-studio-shell h-full overflow-hidden flex flex-col relative"
        style={{ width: `${width}px`, minWidth: `${PANEL.STUDIO.MIN_WIDTH}px` }}
        aria-label="Studio panel"
      >
        { }
        <div
          className={`absolute top-0 left-0 w-1.5 h-full cursor-col-resize transition-colors z-10 group ${isResizing ? 'bg-[var(--accent)]' : 'hover:bg-[var(--accent)]'
            }`}
          onMouseDown={() => setIsResizing(true)}
          role="separator"
          aria-orientation="vertical"
          aria-label="Resize studio panel"
        >
          <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-1 h-8 rounded-full bg-[var(--text-muted)] opacity-0 group-hover:opacity-100 transition-opacity" />
        </div>

        { }
        <div className="panel-header workspace-studio-header">
          <div className="flex items-center gap-2">
            {activeView ? (
              <>
                <button
                  onClick={() => setActiveView(null)}
                  className="btn-icon-sm -ml-1"
                  aria-label="Back to studio grid"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="text-[var(--text-muted)] text-sm">Studio</span>
                <ChevronRight className="w-4 h-4 text-[var(--text-muted)]" />
                <span className="panel-title">{viewTitles[activeView]}</span>
              </>
            ) : (
              <>
                <span className="material-symbols-outlined text-[18px] text-[var(--text-muted)]">labs</span>
                <span className="panel-title">Studio</span>
              </>
            )}
          </div>
          {!activeView && (
            <div className="workspace-studio-chip text-[10px] font-semibold uppercase tracking-wider">
              {selectedSources.length > 0 ? `${selectedSources.length} source${selectedSources.length === 1 ? '' : 's'}` : 'Ready'}
            </div>
          )}
        </div>

        { }
        <div className="workspace-studio-body flex-1 overflow-hidden flex flex-col">
          <div className={`flex-1 relative flex flex-col ${activeView === 'mindmap' ? '' : 'overflow-y-auto p-4'}`}>
            {activeView ? (
              renderInlineContent()
            ) : effectiveMaterial ? (
              <>
                <p className="workspace-studio-lead text-[11.5px] text-text-muted mb-4 leading-relaxed">
                  {selectedSources.length > 1 ? (
                    <>
                      Generating from{' '}
                      <span className="text-text-primary font-semibold px-1.5 py-0.5 rounded-md" style={{ background: 'var(--accent-subtle)' }}>
                        {selectedSources.length} sources
                      </span>
                    </>
                  ) : (
                    <>
                      Create from{' '}
                      <span className="text-text-primary font-semibold">
                        {effectiveMaterial.title || effectiveMaterial.filename}
                      </span>
                    </>
                  )}
                </p>

                <div className="workspace-studio-actions space-y-2">
                  {outputs.map((output, i) => (
                    <div
                      key={output.id}
                      className="animate-fade-up"
                      style={{
                        animationDelay: `${i * 50}ms`,
                        animationFillMode: 'backwards',
                      }}
                    >
                      <FeatureCard
                        icon={output.icon}
                        label={output.title}
                        description={output.description}
                        onClick={output.onClick}
                        loading={loading[output.id]}
                        disabled={!effectiveMaterial}
                        onCancel={output.onCancel}
                      />
                    </div>
                  ))}
                </div>

                { }
                <PodcastProgress phase={podcastPhase} progress={podcastProgress} />

                { }
                {podcastError && podcastPhase === 'idle' && (
                  <div className="mt-3 p-3 rounded-xl bg-[var(--danger-subtle)] border border-[var(--danger-border)] animate-fade-in">
                    <div className="flex items-center gap-2">
                      <AlertTriangle className="w-4 h-4 text-[var(--danger)] shrink-0" />
                      <span className="text-xs text-[var(--danger)]">{podcastError}</span>
                    </div>
                    <button
                      onClick={() => {
                        setPodcastError(null);
                        setShowPodcastConfig(true);
                      }}
                      className="mt-2 text-xs text-[var(--danger)] hover:underline"
                    >
                      Try Again
                    </button>
                  </div>
                )}

                { }
                {combinedHistory.length > 0 && (
                  <div className="workspace-studio-history mt-10 flex flex-col">
                    { }
                    <div className="flex items-center gap-3 py-2 shrink-0">
                      <div className="flex-1 h-px bg-[var(--border)]" />
                      <span className="text-[10px] font-semibold text-[var(--text-muted)] tracking-widest uppercase px-1">
                        Created
                      </span>
                      <div className="flex-1 h-px bg-[var(--border)]" />
                    </div>
                    <div className="pb-2">
                      <ContentHistory
                        items={combinedHistory}
                        onSelect={handleViewHistoryItem}
                        onRename={openHistoryRenameModal}
                        onDelete={handleHistoryDelete}
                      />
                    </div>
                  </div>
                )}

              </>
            ) : (
              <div className="flex flex-col items-center justify-center h-full text-center px-6 py-12">
                <div className="rounded-2xl px-8 py-8 max-w-[280px]" style={{
                  background:
                    'radial-gradient(120% 130% at 0% 0%, color-mix(in srgb, var(--accent) 16%, transparent), transparent 58%), linear-gradient(160deg, color-mix(in srgb, var(--surface-raised) 86%, transparent), color-mix(in srgb, var(--surface-overlay) 62%, transparent))',
                  border: '1px solid color-mix(in srgb, var(--border-strong) 85%, transparent)',
                }}>
                  <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 mx-auto relative" style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}>
                    <div className="absolute inset-0 rounded-2xl" style={{ background: 'var(--gradient-glow, transparent)' }} />
                    <span className="material-symbols-outlined text-[26px] text-accent relative z-10">labs</span>
                  </div>
                  <p className="text-sm font-semibold text-text-primary mb-1.5">No source selected</p>
                  <p className="text-xs text-text-muted max-w-[180px] mx-auto leading-relaxed mb-4">
                    Select a source from the panel to generate study materials
                  </p>
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-2xs font-medium"
                    style={{ background: 'var(--accent-subtle)', color: 'var(--accent)', border: '1px solid var(--accent-border)' }}>
                    Studio will activate automatically
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}

'use client';

import { useState, useRef, useCallback, useEffect, useMemo, memo } from 'react';
import dynamic from 'next/dynamic';
import {
  Layers,
  ClipboardCheck,
  Mic,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  Brain,
  Wand2,
  Presentation,
  Clapperboard,
} from 'lucide-react';

import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import { useConfirm } from '@/stores/useConfirmStore';
import usePodcastStore from '@/stores/usePodcastStore';
import usePresentationStore from '@/stores/usePresentationStore';
import { generateFlashcards, generateQuiz, downloadBlob } from '@/lib/api/generation';
import { generatePresentation, generateVideo } from '@/lib/api/presentation';
import { generateMindMap } from '@/lib/api/mindmap';
import {
  saveGeneratedContent,
  getGeneratedContent,
  deleteGeneratedContent,
  updateGeneratedContent,
  rateGeneratedContent,
} from '@/lib/api/notebooks';
import { PANEL } from '@/lib/utils/constants';

import FeatureCard from './FeatureCard';
import PodcastConfigDialog from '@/components/podcast/PodcastConfigDialog';

import {
  InlineFlashcardsView,
  InlineQuizView,
  FlashcardConfigDialog,
  QuizConfigDialog,
  PresentationConfigDialog,
  ExplainerConfigDialog,
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
const SkillsPanel = dynamic(
  () => import('@/components/skills/SkillsPanel'),
  { ssr: false, loading: () => <LoadingSpinner /> }
);
const PresentationGenerator = dynamic(
  () => import('./PresentationGenerator'),
  { ssr: false, loading: () => <LoadingSpinner /> }
);
const ExplainerGenerator = dynamic(
  () => import('./ExplainerGenerator'),
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

  const presentationId = usePresentationStore((s) => s.presentationId);
  const presentationPhase = usePresentationStore((s) => s.phase);
  const presentationProgress = usePresentationStore((s) => s.progress);
  const presentationError = usePresentationStore((s) => s.error);
  const videoPhase = usePresentationStore((s) => s.videoPhase);
  const videoProgress = usePresentationStore((s) => s.videoProgress);
  const videoError = usePresentationStore((s) => s.videoError);
  const resetPresentation = usePresentationStore((s) => s.reset);
  const setPresentationPhase = usePresentationStore((s) => s.setPhase);
  const setVideoPhase = usePresentationStore((s) => s.setVideoPhase);
  const setPresentationId = usePresentationStore((s) => s.setPresentationId);
  const setPresentationError = usePresentationStore((s) => s.setError);
  const setVideoError = usePresentationStore((s) => s.setVideoError);
  const setPresentationData = usePresentationStore((s) => s.setPresentationData);
  const setPresentationVideoData = usePresentationStore((s) => s.setVideoData);

  const toast = useToast();
  const confirm = useConfirm();

  const effectiveMaterial =
    selectedSources.length > 0
      ? materials.find((m) => selectedSources.includes(m.id)) || null
      : null;

  // ─ Generate contextual descriptions based on materials ─
  const materialContext = useMemo(() => {
    if (selectedSources.length === 0) return {};
    const allMaterials = materials.filter((m) => selectedSources.includes(m.id));
    const hasVideo = allMaterials.some((m) => m.material_type === 'video');
    const hasAudio = allMaterials.some((m) => m.material_type === 'audio');
    const hasDocument = allMaterials.some((m) => m.material_type === 'document');
    const hasImage = allMaterials.some((m) => m.material_type === 'image');
    
    return {
      sourceCount: selectedSources.length,
      hasVideo,
      hasAudio,
      hasDocument,
      hasImage,
    };
  }, [selectedSources, materials]);

  // ─ Generate dynamic feature descriptions ─
  const getFeatureDescription = useCallback((featureId) => {
    const baseDesc = {
      flashcards: 'Study with spaced repetition learning',
      quiz: 'Assess your comprehension interactively',
      podcast: 'Engaging dual-host audio exploration',
      mindmap: 'Interactive concept visualization',
      presentation: 'Professional AI-crafted slide narratives',
      explainer: 'AI-narrated visual storytelling',
      skills: 'Design and execute intelligent automation',
    };

    if (loading[featureId]) return 'Generating…';
    return baseDesc[featureId] || '';
  }, [loading]);

  const selectedMaterialIds = selectedSources;


  const [activeView, setActiveView] = useState(null);


  const [flashcardsData, setFlashcardsData] = useState(null);
  const [quizData, setQuizData] = useState(null);
  const [mindmapData, setMindmapData] = useState(null);
  const [mindmapFullscreen, setMindmapFullscreen] = useState(false);
  const [mindmapRating, setMindmapRating] = useState(null);
  const [mindmapContentId, setMindmapContentId] = useState(null);

  const [showQuizConfig, setShowQuizConfig] = useState(false);
  const [showFlashcardConfig, setShowFlashcardConfig] = useState(false);
  const [showPresentationConfig, setShowPresentationConfig] = useState(false);
  const [showExplainerConfig, setShowExplainerConfig] = useState(false);
  const [showPodcastConfig, setShowPodcastConfig] = useState(false);


  const [contentHistory, setContentHistory] = useState([]);
  const [activeHistoryMenu, setActiveHistoryMenu] = useState(null);
  const [showRenameHistoryModal, setShowRenameHistoryModal] = useState(false);
  const [renamingHistoryItem, setRenamingHistoryItem] = useState(null);
  const [newHistoryTitle, setNewHistoryTitle] = useState('');
  const [selectedCreatedItem, setSelectedCreatedItem] = useState(null);


  const [width, setWidth] = useState(PANEL.STUDIO.DEFAULT_WIDTH);
  const [isResizing, setIsResizing] = useState(false);
  const panelRef = useRef(null);
  const abortControllerRef = useRef({});

  const handleCancelGeneration = useCallback((type) => {
    abortControllerRef.current[type]?.abort();
  }, []);


  const prevNotebookId = useRef(null);
  const prevPresentationPhaseRef = useRef(presentationPhase);
  const prevVideoPhaseRef = useRef(videoPhase);

  const refreshGeneratedContentHistory = useCallback(async () => {
    if (!currentNotebook?.id || currentNotebook.isDraft || draftMode) {
      return;
    }

    try {
      const contents = await getGeneratedContent(currentNotebook.id);
      const normalized = contents.map((c) => ({ ...c }));
      setContentHistory(normalized);

      const seen = new Set();
      let latestPresentation = null;

      for (const c of normalized) {
        if (c.content_type === 'presentation' && !latestPresentation) {
          latestPresentation = c;
        }

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
          case 'mindmap':
            setMindmapData(c.data);
            setMindmapContentId(c.id);
            setMindmapRating(c.rating || null);
            break;
          default:
            break;
        }
      }

      if (latestPresentation?.id) {
        setPresentationData({ id: latestPresentation.id, data: latestPresentation.data });
        if (latestPresentation.data?.video) {
          setPresentationVideoData(latestPresentation.data.video);
        }
      }
    } catch (error) {
      console.error('Failed to load saved content:', error);
    }
  }, [
    currentNotebook?.id,
    currentNotebook?.isDraft,
    draftMode,
    setFlashcards,
    setPresentationData,
    setPresentationVideoData,
    setQuiz,
  ]);

  useEffect(() => {
    const notebookId = currentNotebook?.id;
    if (notebookId === prevNotebookId.current) return;
    prevNotebookId.current = notebookId;

    setFlashcardsData(null);
    setQuizData(null);
    setMindmapFullscreen(false);
    setMindmapContentId(null);
    setMindmapRating(null);
    setShowQuizConfig(false);
    setShowFlashcardConfig(false);
    setShowPresentationConfig(false);
    setShowExplainerConfig(false);
    setContentHistory([]);
    setSelectedCreatedItem(null);
    setFlashcards(null);
    setQuiz(null);
    resetPresentation();
    setActiveView(null);

    // Use notebook ID and draft state to control loading
    if (currentNotebook?.id) {
      loadPodcastSessions(currentNotebook.id, currentNotebook.isDraft || draftMode);
    }

    refreshGeneratedContentHistory();
  }, [
    currentNotebook?.id,
    currentNotebook?.isDraft,
    draftMode,
    loadPodcastSessions,
    refreshGeneratedContentHistory,
    resetPresentation,
    setFlashcards,
    setQuiz
  ]);

  useEffect(() => {
    const isActive = presentationPhase === 'planning' || presentationPhase === 'generating';
    setLoadingState('presentation', isActive);

    const previous = prevPresentationPhaseRef.current;
    const wasActive = previous === 'planning' || previous === 'generating';
    if (previous !== presentationPhase) {
      if (presentationPhase === 'done' && wasActive) {
        refreshGeneratedContentHistory();
        toast.success('Presentation saved to Created');
      } else if (presentationPhase === 'error' && presentationError && wasActive) {
        toast.error(presentationError);
      }
    }

    prevPresentationPhaseRef.current = presentationPhase;
  }, [presentationPhase, presentationError, refreshGeneratedContentHistory, setLoadingState, toast]);

  useEffect(() => {
    const isActive = ['scripting', 'audio', 'rendering'].includes(videoPhase);
    setLoadingState('explainer', isActive);

    const previous = prevVideoPhaseRef.current;
    const wasActive = ['scripting', 'audio', 'rendering'].includes(previous);
    if (previous !== videoPhase) {
      if (videoPhase === 'done' && wasActive) {
        refreshGeneratedContentHistory();
        toast.success('Explain video saved to Created');
      } else if (videoPhase === 'error' && videoError && wasActive) {
        toast.error(videoError);
      }
    }

    prevVideoPhaseRef.current = videoPhase;
  }, [videoPhase, videoError, refreshGeneratedContentHistory, setLoadingState, toast]);

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

  const buildPresentationPayload = useCallback((options = {}) => {
    const topic = String(options.topic || '').trim();
    const themePrompt = String(options.theme || '').trim();
    const argumentationNotes = String(options.additionalNotes || '').trim();
    const numericSlideCount = Number(options.slideCount);

    return {
      topic: topic || null,
      themePrompt: themePrompt || undefined,
      slideCount: Number.isFinite(numericSlideCount) ? numericSlideCount : undefined,
      argumentationNotes: argumentationNotes || undefined,
    };
  }, []);

  const handlePresentationClick = useCallback(() => {
    setShowPresentationConfig(true);
  }, []);

  const handleGeneratePresentation = useCallback(async (options = {}) => {
    if (!currentNotebook?.id || selectedMaterialIds.length === 0) {
      toast.error('Select at least one source to generate a presentation');
      return;
    }

    setShowPresentationConfig(false);
    resetPresentation();
    setPresentationError(null);
    setPresentationPhase('planning');
    setLoadingState('presentation', true);

    try {
      const presentationPayload = buildPresentationPayload(options);
      const started = await generatePresentation(
        currentNotebook.id,
        selectedMaterialIds,
        presentationPayload,
      );

      if (started?.id) {
        setPresentationId(started.id);
      }

      toast.success('Presentation generation started');
    } catch (error) {
      setPresentationError(error.message || 'Failed to start presentation generation');
      setLoadingState('presentation', false);
      toast.error(error.message || 'Failed to start presentation generation');
    }
  }, [
    buildPresentationPayload,
    currentNotebook?.id,
    resetPresentation,
    selectedMaterialIds,
    setLoadingState,
    setPresentationError,
    setPresentationId,
    setPresentationPhase,
    toast,
  ]);

  const handleExplainerClick = useCallback(() => {
    setShowExplainerConfig(true);
  }, []);

  const handleGenerateExplainer = useCallback(async (options = {}) => {
    if (!options.presentationId) {
      toast.error('Choose a presentation first');
      return;
    }

    setShowExplainerConfig(false);
    setLoadingState('explainer', true);
    setPresentationId(options.presentationId);
    setVideoError(null);

    try {
      await generateVideo(options.presentationId, {
        voiceId: options.voiceId,
        narrationLanguage: options.narrationLanguage,
        presentationLanguage: options.presentationLanguage,
        narrationStyle: options.narrationStyle?.trim() || undefined,
        narrationNotes: options.additionalNotes?.trim() || undefined,
        autoGenerateSlides: true,
        notebookId: currentNotebook?.id || undefined,
        materialIds: selectedMaterialIds,
      });

      toast.success('Explain video generation started');
    } catch (error) {
      setLoadingState('explainer', false);
      toast.error(error.message || 'Failed to start explain video generation');
    }
  }, [
    currentNotebook?.id,
    selectedMaterialIds,
    setLoadingState,
    setPresentationId,
    setVideoError,
    toast,
  ]);

  const handleExplainUpload = useCallback(async (options = {}) => {
    if (!options.file) {
      toast.error('Please provide a file to upload');
      return;
    }

    setShowExplainerConfig(false);
    setLoadingState('explainer', true);
    setVideoError(null);

    try {
      const { explainPptxUpload } = await import('@/lib/api/presentation');
      const result = await explainPptxUpload({
        file: options.file,
        voiceId: options.voiceId,
        narrationLanguage: options.narrationLanguage,
        narrationStyle: options.narrationStyle?.trim() || undefined,
        narrationNotes: options.additionalNotes?.trim() || undefined,
        notebookId: currentNotebook?.id,
      });
      
      setPresentationId(result.videoId);
      setVideoPhase('scripting');
      toast.success('Explain video generation started from uploaded file');
    } catch (error) {
      setLoadingState('explainer', false);
      toast.error(error.message || 'Failed to upload and start explain video');
    }
  }, [setLoadingState, setPresentationId, setVideoError, toast]);


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
    setSelectedCreatedItem(item);

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
        if (item.processing) {
          setActiveView(null);
          break;
        }
        setPresentationData({ id: item.id, data: item.data });
        if (item.data?.video) {
          setPresentationVideoData(item.data.video);
        }
        setActiveView('presentation');
        break;
      case 'explainer':
        if (item.processing) {
          setActiveView(null);
          break;
        }
        if (item.parentId) {
          setPresentationId(item.parentId);
        }
        if (item.data?.videoUrl) {
          setPresentationVideoData(item.data);
        }
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
          prev.map((item) => (
            item.id === renamingHistoryItem.id
              ? { ...item, ...updated, data: item.data, rating: item.rating, content_type: item.content_type }
              : item
          ))
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
    if (item.readOnly || item.processing || item.content_type === 'explainer') return;
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
        setSelectedCreatedItem((prev) => {
          if (!prev) return prev;
          if (prev.id === item.id) return null;
          if (prev.parentId && prev.parentId === item.id) return null;
          return prev;
        });
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
          case 'mindmap':
            if (mindmapContentId === item.id) {
              setMindmapData(null);
              setMindmapContentId(null);
              setMindmapRating(null);
              setMindmapFullscreen(false);
            }
            break;
          case 'presentation':
            if (presentationId === item.id) {
              resetPresentation();
              setActiveView(null);
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
    const derivedExplainers = (contentHistory || [])
      .filter((item) => item.content_type === 'presentation' && item.data?.video)
      .map((item) => ({
        id: `explainer:${item.id}`,
        parentId: item.id,
        readOnly: true,
        content_type: 'explainer',
        title:
          item.data?.video?.title ||
          item.data?.video?.aiTitle ||
          item.title ||
          'Untitled',
        created_at: item.data?.video?.createdAt || item.updated_at || item.created_at,
        data: {
          ...(item.data?.video || {}),
          presentationId: item.id,
          presentationTitle: item.title || 'Untitled',
          slideCount: item.data?.slideCount || item.data?.slides?.length || 0,
        },
      }));

    const podcastItems = (podcastSessions || []).map((s) => ({
      id: s.id,
      content_type: 'podcast',
      title: s.title || 'AI Podcast',
      created_at: s.createdAt,
      data: s,
    }));

    const pendingItems = [];
    if (presentationId && ['planning', 'generating'].includes(presentationPhase)) {
      pendingItems.push({
        id: `pending:presentation:${presentationId}`,
        content_type: 'presentation',
        title: 'Presentation (in progress)',
        processing: true,
        created_at: new Date().toISOString(),
        data: {
          status: presentationPhase,
          message: presentationProgress?.message || 'Generating presentation',
        },
      });
    }

    if (presentationId && ['scripting', 'audio', 'rendering'].includes(videoPhase)) {
      pendingItems.push({
        id: `pending:explainer:${presentationId}`,
        parentId: presentationId,
        content_type: 'explainer',
        title: 'Explain Video (in progress)',
        processing: true,
        created_at: new Date().toISOString(),
        data: {
          status: videoPhase,
          message: videoProgress?.message || 'Generating explain video',
        },
      });
    }

    return [...pendingItems, ...contentHistory, ...derivedExplainers, ...podcastItems].sort(
      (a, b) => new Date(b.created_at) - new Date(a.created_at)
    );
  }, [
    contentHistory,
    podcastSessions,
    presentationId,
    presentationPhase,
    presentationProgress?.message,
    videoPhase,
    videoProgress?.message,
  ]);

  const presentationHistoryItems = useMemo(
    () => contentHistory.filter((item) => item.content_type === 'presentation'),
    [contentHistory]
  );


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
      description: getFeatureDescription('flashcards'),
      icon: <Layers className="w-5 h-5" />,
      onClick: handleFlashcardsClick,
      onCancel: () => handleCancelGeneration('flashcards'),
      accent: '59 130 246',
    },
    {
      id: 'quiz',
      title: 'Practice Quiz',
      description: getFeatureDescription('quiz'),
      icon: <ClipboardCheck className="w-5 h-5" />,
      onClick: handleQuizClick,
      onCancel: () => handleCancelGeneration('quiz'),
      accent: '34 197 94',
    },
    {
      id: 'podcast',
      title: 'AI Podcast',
      description:
        podcastPhase === 'generating'
          ? podcastProgress?.message || 'Generating…'
          : getFeatureDescription('podcast'),
      icon: <Mic className="w-5 h-5" />,
      onClick: () => {
        if (podcastPhase !== 'generating') setShowPodcastConfig(true);
      },
      onSettings: () => setShowPodcastConfig(true),
      accent: '236 72 153',
    },
    {
      id: 'mindmap',
      title: 'Mind Map',
      description: getFeatureDescription('mindmap'),
      icon: <Brain className="w-5 h-5" />,
      onClick: handleMindMapClick,
      onCancel: handleCancelMindMap,
      accent: '14 165 233',
    },
    {
      id: 'presentation',
      title: 'Presentation',
      description:
        loading['presentation']
          ? presentationProgress?.message || 'Generating slides…'
          : getFeatureDescription('presentation'),
      icon: <Presentation className="w-5 h-5" />,
      onClick: handlePresentationClick,
      onSettings: handlePresentationClick,
      accent: '255 159 28',
    },
    {
      id: 'explainer',
      title: 'Explain Video',
      description:
        loading['explainer']
          ? videoProgress?.message || 'Generating…'
          : getFeatureDescription('explainer'),
      icon: <Clapperboard className="w-5 h-5" />,
      onClick: handleExplainerClick,
      onSettings: handleExplainerClick,
      accent: '34 197 94',
    },
    {
      id: 'skills',
      title: 'Agent Skills',
      description: getFeatureDescription('skills'),
      icon: <Wand2 className="w-5 h-5" />,
      onClick: () => setActiveView('skills'),
      onSettings: () => setActiveView('skills'),
      accent: '59 130 246',
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
    explainer: 'Explain Video',
    podcast: 'AI Podcast',
    mindmap: 'Mind Map',
    skills: 'Agent Skills',
  };


  const renderInlineContent = () => {
    switch (activeView) {
      case 'flashcards':
        return <InlineFlashcardsView flashcards={flashcardsData} onClose={() => setActiveView(null)} />;
      case 'quiz':
        return <InlineQuizView quiz={quizData} onClose={() => setActiveView(null)} />;
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
        return null;

      case 'presentation':
        return (
          <PresentationGenerator
            onClose={() => setActiveView(null)}
            onSaved={refreshGeneratedContentHistory}
          />
        );

      case 'explainer':
        return (
          <ExplainerGenerator
            onOpenPresentation={() => setActiveView('presentation')}
            onSaved={refreshGeneratedContentHistory}
            historyItems={combinedHistory}
            onStartVideo={(opts) => {
              // Route through the existing handleGenerateExplainer flow
              // so we get proper job management, WS streaming and history updates
              handleGenerateExplainer({
                presentationId: opts.presentationId || presentationId,
                voiceId: opts.voiceId,
                narrationLanguage: opts.narrationLanguage || 'en',
                narrationStyle: opts.narrationStyle,
                additionalNotes: opts.narrationNotes,
                presentationLanguage: opts.narrationLanguage || 'en',
              });
            }}
          />
        );

      case 'skills':
        return <SkillsPanel onClose={() => setActiveView(null)} />;

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

      {showPresentationConfig && (
        <PresentationConfigDialog
          onGenerate={handleGeneratePresentation}
          onCancel={() => setShowPresentationConfig(false)}
          loading={loading['presentation']}
          sourceCount={selectedMaterialIds.length}
        />
      )}

      {showExplainerConfig && (
        <ExplainerConfigDialog
          onGenerate={handleGenerateExplainer}
          onUpload={handleExplainUpload}
          onCancel={() => setShowExplainerConfig(false)}
          onOpenPresentation={() => setShowPresentationConfig(true)}
          presentations={presentationHistoryItems}
          loading={loading['explainer']}
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
                <div className="workspace-studio-actions space-y-2">
                  {outputs.map((output, i) => (
                    <div
                      key={output.id}
                      className="animate-fade-up"
                      style={{
                        animationDelay: `${i * 40}ms`,
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
                        onSettings={output.onSettings}
                        accent={output.accent}
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
                  <div className="workspace-studio-history mt-5 flex flex-col">
                    <div className="workspace-studio-history-head py-1.5 shrink-0">
                      <span className="text-[11px] font-semibold text-[var(--text-secondary)] tracking-[0.14em] uppercase">
                        Created
                      </span>
                    </div>
                    <div className="pb-1">
                      <ContentHistory
                        items={combinedHistory}
                        activeId={selectedCreatedItem?.id}
                        onSelect={handleViewHistoryItem}
                        onRename={openHistoryRenameModal}
                        onDelete={handleHistoryDelete}
                      />
                    </div>
                  </div>
                )}

              </>
            ) : (
              <div className="workspace-studio-empty-layout flex flex-col min-h-full">
                <div className="workspace-studio-empty-simple flex flex-col items-center justify-center text-center px-6 py-12">
                  <div className="workspace-studio-empty-icon w-14 h-14 rounded-2xl flex items-center justify-center mb-4 mx-auto bg-[var(--accent-subtle)]">
                    <span className="material-symbols-outlined text-[28px] text-[var(--accent)]">lightbulb</span>
                  </div>
                  <p className="workspace-studio-empty-title text-base font-bold text-[var(--text-primary)] mb-2">Ready to create?</p>
                  <p className="workspace-studio-empty-subtitle text-xs text-[var(--text-muted)] max-w-[240px] mx-auto leading-relaxed mb-4">
                    Select a source material to unlock powerful AI-driven content generation across flashcards, quizzes, presentations, and more.
                  </p>
                  <div className="text-[10px] text-[var(--text-muted)] font-medium bg-[var(--surface-overlay)] px-3 py-1.5 rounded-full">
                    💡 Tip: Select multiple sources for richer content
                  </div>
                </div>

                {combinedHistory.length > 0 && (
                  <div className="workspace-studio-history mt-2 flex flex-col">
                    <div className="workspace-studio-history-head py-1.5 shrink-0">
                      <span className="text-[11px] font-semibold text-[var(--text-secondary)] tracking-[0.14em] uppercase">
                        Created
                      </span>
                    </div>
                    <div className="pb-1">
                      <ContentHistory
                        items={combinedHistory}
                        activeId={selectedCreatedItem?.id}
                        onSelect={handleViewHistoryItem}
                        onRename={openHistoryRenameModal}
                        onDelete={handleHistoryDelete}
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </aside>
    </>
  );
}

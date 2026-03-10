'use client';

import { useState, useRef, useCallback, useEffect } from 'react';
import dynamic from 'next/dynamic';
import {
  Layers,
  ClipboardCheck,
  Monitor,
  Video,
  Mic,
  ChevronLeft,
  ChevronRight,
  FlaskConical,
  AlertTriangle,
  Network,
} from 'lucide-react';

import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import { useConfirm } from '@/stores/useConfirmStore';
import usePodcast from '@/hooks/usePodcast';
import { generateFlashcards, generateQuiz, generatePresentation } from '@/lib/api/generation';
import { generateMindMap } from '@/lib/api/mindmap';
import {
  saveGeneratedContent,
  getGeneratedContent,
  deleteGeneratedContent,
  updateGeneratedContent,
} from '@/lib/api/notebooks';
import { PANEL } from '@/lib/utils/constants';

import FeatureCard from './FeatureCard';
import ExplainerDialog from './ExplainerDialog';
import { PresentationConfigDialog } from '@/components/presentation/PresentationView';
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


const InlinePresentationView = dynamic(
  () => import('@/components/presentation/PresentationView'),
  { ssr: false, loading: () => <LoadingSpinner /> }
);
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


export default function StudioPanel() {
  
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const draftMode = useAppStore((s) => s.draftMode);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);
  const loading = useAppStore((s) => s.loading);
  const setFlashcards = useAppStore((s) => s.setFlashcards);
  const setQuiz = useAppStore((s) => s.setQuiz);
  const setLoadingState = useAppStore((s) => s.setLoadingState);

  const podcast = usePodcast();
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
  const [showMindmapCanvas, setShowMindmapCanvas] = useState(false);

  
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

  
  useEffect(() => {
    setFlashcardsData(null);
    setQuizData(null);
    setPresentationData(null);
    setMindmapData(null);
    setShowPresentationConfig(false);
    setShowQuizConfig(false);
    setShowFlashcardConfig(false);
    setShowExplainerDialog(false);
    setContentHistory([]);
    setFlashcards(null);
    setQuiz(null);
    setActiveView(null);

    podcast.loadSessions();

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
                setPresentationData(c.data);
                break;
              case 'mindmap':
                setMindmapData(c.data);
                break;
            }
          }
        } catch (error) {
          console.error('Failed to load saved content:', error);
        }
      }
    };
    loadSavedContent();
    
  }, [currentNotebook?.id]);

  
  const handleMouseMove = useCallback(
    (e) => {
      if (isResizing && panelRef.current) {
        const rect = panelRef.current.getBoundingClientRect();
        const newWidth = rect.right - e.clientX;
        if (newWidth >= PANEL.STUDIO.MIN_WIDTH && newWidth <= PANEL.STUDIO.MAX_WIDTH) {
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
      const data = await generatePresentation(effectiveMaterial.id, {
        ...options,
        materialIds: selectedMaterialIds,
        signal: ac.signal,
      });
      setPresentationData(data);
      const saved = await trySave('presentation', data, data.title || 'Presentation');
      if (saved) {
        setContentHistory((prev) => [saved, ...prev]);
        toast.success(`Presentation saved to Created`);
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to generate presentation. Please try again.');
    } finally {
      setLoadingState('presentation', false);
    }
  };

  const handleMindmapClick = async () => {
    if (!effectiveMaterial) return;
    if (mindmapData) {
      setShowMindmapCanvas(true);
      return;
    }
    setLoadingState('mindmap', true);
    const ac = new AbortController();
    abortControllerRef.current.mindmap = ac;
    try {
      const data = await generateMindMap({
        notebookId: currentNotebook.id,
        materialIds: selectedMaterialIds,
        signal: ac.signal,
      });
      setMindmapData(data);
      const saved = await trySave('mindmap', data, data.title || 'Mind Map');
      if (saved) {
        setContentHistory((prev) => [saved, ...prev]);
        toast.success('Mind map saved to Created');
      }
      setShowMindmapCanvas(true);
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to generate mind map. Please try again.');
    } finally {
      setLoadingState('mindmap', false);
    }
  };

  const handleMindmapRegenerate = async () => {
    if (!currentNotebook?.id || !selectedMaterialIds.length) return;
    setLoadingState('mindmap', true);
    const ac = new AbortController();
    abortControllerRef.current.mindmap = ac;
    try {
      const data = await generateMindMap({
        notebookId: currentNotebook.id,
        materialIds: selectedMaterialIds,
        signal: ac.signal,
      });
      setMindmapData(data);
      const saved = await trySave('mindmap', data, data.title || 'Mind Map');
      if (saved) {
        setContentHistory((prev) => {
          const exists = prev.find((c) => c.content_type === 'mindmap' && c.id === saved.id);
          return exists ? prev.map((c) => (c.id === saved.id ? saved : c)) : [saved, ...prev];
        });
      }
    } catch (error) {
      if (error.name === 'AbortError') return;
      toast.error(error.message || 'Failed to regenerate mind map.');
    } finally {
      setLoadingState('mindmap', false);
    }
  };

  
  const handleViewHistoryItem = (item) => {
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
        setPresentationData(item.data);
        setActiveView('presentation');
        break;
      case 'explainer':
        setExplainerData(item.data);
        setActiveView('explainer');
        break;
      case 'mindmap':
        setMindmapData(item.data);
        setShowMindmapCanvas(true);
        break;
    }
  };

  const handleHistoryRename = async (newTitle) => {
    if (!newTitle?.trim() || !renamingHistoryItem || !currentNotebook) return;
    try {
      const updated = await updateGeneratedContent(
        currentNotebook.id,
        renamingHistoryItem.id,
        newTitle.trim()
      );
      setContentHistory((prev) =>
        prev.map((item) => (item.id === renamingHistoryItem.id ? updated : item))
      );
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
      await deleteGeneratedContent(currentNotebook.id, item.id);
      setContentHistory((prev) => prev.filter((c) => c.id !== item.id));

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
              setActiveView(null);
            }
            break;
          case 'mindmap':
            setMindmapData(null);
            setShowMindmapCanvas(false);
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

  
  const podcastGeneratingRef = useRef(false);

  const handlePodcastGenerate = async (config) => {
    if (podcastGeneratingRef.current) return;
    podcastGeneratingRef.current = true;
    setShowPodcastConfig(false);
    setLoadingState('podcast', true);
    try {
      const session = await podcast.create(config);
      if (session?.id) {
        await podcast.startGeneration(session.id);
      }
    } catch (err) {
      toast.error(err.message || 'Failed to start podcast generation.');
      setLoadingState('podcast', false);
      podcastGeneratingRef.current = false;
    }
  };

  useEffect(() => {
    const { phase: podPhase } = podcast;
    if (podPhase === 'generating') {
      setLoadingState('podcast', true);
    } else {
      setLoadingState('podcast', false);
      podcastGeneratingRef.current = false;
    }
    if (podPhase === 'player') {
      podcast.loadSessions();
      setActiveView('podcast');
    }
    
  }, [podcast.phase]);

  
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
        podcast.phase === 'generating'
          ? podcast.generationProgress?.message || 'Generating\u2026'
          : 'Two-host AI podcast from your sources',
      icon: <Mic className="w-5 h-5" />,
      onClick: () => {
        if (podcast.phase !== 'generating') setShowPodcastConfig(true);
      },
    },
    {
      id: 'mindmap',
      title: 'Mind Map',
      description: 'Visualize concept relationships',
      icon: <Network className="w-5 h-5" />,
      onClick: handleMindmapClick,
      onCancel: () => handleCancelGeneration('mindmap'),
    },
  ];

  const completedPodcastSessions = (podcast.sessions || []).filter(
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
          <InlinePresentationView
            presentation={presentationData}
            onClose={() => setActiveView(null)}
          />
        );
      case 'explainer':
        return <InlineExplainerView explainer={explainerData} onClose={() => setActiveView(null)} />;
      case 'podcast':
        return <PodcastStudio onRequestNew={() => setShowPodcastConfig(true)} />;

      default:
        return null;
    }
  };

  
  return (
    <>
      {}
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

      {}
      {showPresentationConfig && (
        <PresentationConfigDialog
          onConfirm={handleGeneratePresentation}
          onClose={() => setShowPresentationConfig(false)}
        />
      )}

      {showQuizConfig && (
        <QuizConfigDialog
          onGenerate={handleGenerateQuiz}
          onCancel={() => setShowQuizConfig(false)}
          loading={loading['quiz']}
        />
      )}

      {showFlashcardConfig && (
        <FlashcardConfigDialog
          onGenerate={handleGenerateFlashcards}
          onCancel={() => setShowFlashcardConfig(false)}
          loading={loading['flashcards']}
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

      {showMindmapCanvas && mindmapData && (
        <MindMapCanvas
          mapData={mindmapData}
          onClose={() => setShowMindmapCanvas(false)}
          onRegenerate={handleMindmapRegenerate}
        />
      )}

      <aside
        ref={panelRef}
        className="glass-light h-full overflow-hidden flex flex-col relative"
        style={{ width: `${width}px`, minWidth: `${PANEL.STUDIO.MIN_WIDTH}px` }}
        aria-label="Studio panel"
      >
        {}
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

        {}
        <div className="panel-header">
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
                <FlaskConical className="w-5 h-5 text-[var(--text-muted)]" />
                <span className="panel-title">Studio</span>
              </>
            )}
          </div>
        </div>

        {}
        <div className="flex-1 overflow-hidden flex flex-col">
          {}
          <div className="flex-1 overflow-y-auto p-4 relative">
          {activeView ? (
            renderInlineContent()
          ) : effectiveMaterial ? (
            <>
              <p className="text-[11.5px] text-text-muted mb-4 leading-relaxed">
                {selectedSources.size > 1 ? (
                  <>
                    Generating from{' '}
                    <span className="text-text-primary font-semibold px-1.5 py-0.5 rounded-md" style={{ background: 'var(--accent-subtle)' }}>
                      {selectedSources.size} sources
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

              <div className="space-y-1.5">
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

              {}
              {podcast.phase === 'generating' && podcast.generationProgress && (
                <div className="mt-3 p-3 rounded-xl border border-[var(--accent-border,var(--accent))] bg-[var(--accent-subtle)] animate-fade-in">
                  <div className="flex items-center gap-2 mb-2">
                    <div className="loading-spinner w-3.5 h-3.5" />
                    <span className="text-xs font-medium text-[var(--text-primary)] flex-1 truncate">
                      {podcast.generationProgress.message || 'Generating podcast…'}
                    </span>
                    <span className="text-[10px] text-[var(--text-muted)] tabular-nums shrink-0">
                      {Math.round(podcast.generationProgress.pct || 0)}%
                    </span>
                  </div>
                  <div
                    className="h-1.5 rounded-full bg-[var(--surface-overlay)] overflow-hidden"
                    role="progressbar"
                    aria-valuenow={Math.round(podcast.generationProgress.pct || 0)}
                    aria-valuemax={100}
                  >
                    <div
                      className="h-full rounded-full bg-[var(--accent)] transition-all duration-700 ease-out"
                      style={{ width: `${Math.max(podcast.generationProgress.pct || 0, 3)}%` }}
                    />
                  </div>
                </div>
              )}

              {}
              {podcast.error && podcast.phase === 'idle' && (
                <div className="mt-3 p-3 rounded-xl bg-[var(--danger-subtle)] border border-[var(--danger-border)] animate-fade-in">
                  <div className="flex items-center gap-2">
                    <AlertTriangle className="w-4 h-4 text-[var(--danger)] shrink-0" />
                    <span className="text-xs text-[var(--danger)]">{podcast.error}</span>
                  </div>
                  <button
                    onClick={() => {
                      podcast.setError(null);
                      setShowPodcastConfig(true);
                    }}
                    className="mt-2 text-xs text-[var(--danger)] hover:underline"
                  >
                    Try Again
                  </button>
                </div>
              )}

            </>
          ) : (
            <div className="flex flex-col items-center justify-center h-full text-center px-6 py-12">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center mb-4 relative" style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}>
                <div className="absolute inset-0 rounded-2xl" style={{ background: 'var(--gradient-glow, transparent)' }} />
                <FlaskConical className="w-6 h-6 text-accent relative z-10" />
              </div>
              <p className="text-sm font-semibold text-text-secondary mb-1.5">No source selected</p>
              <p className="text-xs text-text-muted max-w-[180px] leading-relaxed">
                Select a source from the panel to generate study materials
              </p>
            </div>
          )}
          </div>{}

          {}
          {contentHistory.length > 0 && (
            <div
              className="border-t border-[var(--border)] flex flex-col shrink-0"
              style={{ maxHeight: '42%' }}
            >
              {}
              <div className="flex items-center gap-3 px-4 py-2 shrink-0">
                <div className="flex-1 h-px bg-[var(--border)]" />
                <span className="text-[10px] font-semibold text-[var(--text-muted)] tracking-widest uppercase px-1">
                  Created
                </span>
                <div className="flex-1 h-px bg-[var(--border)]" />
              </div>
              <div className="overflow-y-auto px-2 pb-2">
                <ContentHistory
                  items={contentHistory}
                  onSelect={handleViewHistoryItem}
                  onRename={openHistoryRenameModal}
                  onDelete={handleHistoryDelete}
                />
              </div>
            </div>
          )}
        </div>{}
      </aside>
    </>
  );
}

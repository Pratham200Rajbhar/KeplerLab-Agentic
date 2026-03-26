'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/stores/useAuthStore';
import useAppStore from '@/stores/useAppStore';
import { getNotebook } from '@/lib/api/notebooks';
import Header from '@/components/layout/Header';
import { PanelErrorBoundary } from '@/components/ui/ErrorBoundary';
import { X, Menu, Sparkles, BookOpen, CheckCircle2 } from 'lucide-react';


const Sidebar = dynamic(() => import('@/components/layout/Sidebar'), { ssr: false });
const ChatPanel = dynamic(() => import('@/components/chat/ChatPanel'), { ssr: false });
const StudioPanel = dynamic(() => import('@/components/studio/StudioPanel'), { ssr: false });

export default function NotebookPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id;
  const { user } = useAuthStore();

  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const setCurrentNotebook = useAppStore((s) => s.setCurrentNotebook);
  const setDraftMode = useAppStore((s) => s.setDraftMode);
  const resetForNotebookSwitch = useAppStore((s) => s.resetForNotebookSwitch);
  const newlyCreatedNotebookId = useAppStore((s) => s.newlyCreatedNotebookId);
  const setNewlyCreatedNotebookId = useAppStore((s) => s.setNewlyCreatedNotebookId);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const selectedCount = selectedSources.length;

  const completedSelectedCount = selectedSources.filter((sourceId) => {
    const material = materials.find((m) => m.id === sourceId);
    return material?.status === 'completed';
  }).length;

  
  useEffect(() => {
    let cancelled = false;

    const loadNotebook = async () => {
      
      if (newlyCreatedNotebookId) {
        if (id === 'draft') {
          setLoaded(true);
          return;
        }
        if (id === newlyCreatedNotebookId) {
          setNewlyCreatedNotebookId(null);
          
        }
      }

      if (id === 'draft') {
        if (!currentNotebook?.isDraft) {
          resetForNotebookSwitch();
          setCurrentNotebook({ id: 'draft', name: 'New Notebook', isDraft: true });
          setDraftMode(true);
        }
        setLoaded(true);
        return;
      }

      if (id && currentNotebook?.id !== id) {
        resetForNotebookSwitch();
        try {
          const notebook = await getNotebook(id);
          if (cancelled) return;
          setCurrentNotebook(notebook);
          setDraftMode(false);
        } catch (error) {
          console.error('Failed to load notebook:', error);
          if (!cancelled) router.replace('/');
          return;
        }
      }
      if (!cancelled) setLoaded(true);
    };

    loadNotebook();
    return () => { cancelled = true; };
  }, [id, currentNotebook?.id, currentNotebook?.isDraft, resetForNotebookSwitch, setCurrentNotebook, setDraftMode, router, newlyCreatedNotebookId, setNewlyCreatedNotebookId]);

  const handleBack = () => {
    resetForNotebookSwitch();
    router.push('/');
  };

  if (!loaded) {
    return (
      <div className="h-screen flex items-center justify-center bg-surface">
        <div className="loading-spinner w-8 h-8" />
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden bg-surface notebook-workspace-shell">
      <div className="notebook-workspace-atmosphere" aria-hidden="true" />
      <Header user={user} onBack={handleBack} />
      <div className="workspace-meta-strip workspace-meta-strip-elevated">
        <div className="workspace-meta-chip">
          <BookOpen className="w-3.5 h-3.5" />
          <span>{currentNotebook?.name || 'Notebook'}</span>
        </div>
        <div className="workspace-meta-chip">
          <CheckCircle2 className="w-3.5 h-3.5" />
          <span>{completedSelectedCount} ready source{completedSelectedCount === 1 ? '' : 's'}</span>
        </div>
        <div className="workspace-meta-chip">
          <span>{selectedCount} selected</span>
        </div>
        <div className="workspace-meta-chip workspace-meta-chip-glow">
          <Sparkles className="w-3.5 h-3.5" />
          <span>AI Studio Live</span>
        </div>
      </div>
      <div className="flex-1 flex overflow-hidden workspace-panels workspace-panels-shell">
        {}
        <div
          className={`sidebar-overlay${sidebarOpen ? ' visible' : ''}`}
          onClick={() => setSidebarOpen(false)}
        />

        <PanelErrorBoundary panelName="Sidebar">
          <div className={`sidebar-mobile${sidebarOpen ? ' sidebar-open' : ''}`}>
            <Sidebar onNavigate={() => setSidebarOpen(false)} />
          </div>
        </PanelErrorBoundary>

        <PanelErrorBoundary panelName="Chat">
          <ChatPanel />
        </PanelErrorBoundary>

        <PanelErrorBoundary panelName="Studio">
          <StudioPanel />
        </PanelErrorBoundary>
      </div>

      {}
      <button
        className="sidebar-toggle"
        onClick={() => setSidebarOpen((v) => !v)}
        aria-label="Toggle sources panel"
      >
        {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
      </button>
    </div>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import dynamic from 'next/dynamic';
import useAuthStore from '@/stores/useAuthStore';
import useAppStore from '@/stores/useAppStore';
import { getNotebook } from '@/lib/api/notebooks';
import Header from '@/components/layout/Header';
import { PanelErrorBoundary } from '@/components/ui/ErrorBoundary';
import { X, Menu } from 'lucide-react';

// Lazy-load heavy panels
const Sidebar = dynamic(() => import('@/components/layout/Sidebar'), { ssr: false });
const ChatPanel = dynamic(() => import('@/components/chat/ChatPanel'), { ssr: false });
const StudioPanel = dynamic(() => import('@/components/studio/StudioPanel'), { ssr: false });

export default function NotebookPage() {
  const params = useParams();
  const router = useRouter();
  const id = params.id;
  const { user } = useAuthStore();

  const {
    currentNotebook,
    setCurrentNotebook,
    setDraftMode,
    resetForNotebookSwitch,
  } = useAppStore();

  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [loaded, setLoaded] = useState(false);

  // Load notebook data from URL param
  useEffect(() => {
    let cancelled = false;

    const loadNotebook = async () => {
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
  }, [id, currentNotebook?.id, currentNotebook?.isDraft, resetForNotebookSwitch, setCurrentNotebook, setDraftMode, router]);

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
    <div className="h-screen flex flex-col overflow-hidden bg-surface">
      <Header user={user} onBack={handleBack} />
      <div className="flex-1 flex overflow-hidden workspace-panels">
        {/* Mobile sidebar overlay */}
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

      {/* Mobile sidebar toggle */}
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

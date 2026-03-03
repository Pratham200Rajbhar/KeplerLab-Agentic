'use client';

import { Loader2, RefreshCw, Maximize2, AlertTriangle, Brain } from 'lucide-react';
import useMindMap from '@/hooks/useMindMap';
import useAppStore from '@/stores/useAppStore';
import dynamic from 'next/dynamic';

const MindMapCanvas = dynamic(() => import('./MindMapCanvas'), {
  ssr: false,
  loading: () => (
    <div className="flex items-center justify-center h-full">
      <Loader2 className="w-6 h-6 text-(--accent) animate-spin" />
    </div>
  ),
});

export default function MindMapView({ notebookId }) {
  const selectedSources = useAppStore((s) => s.selectedSources);
  const sourcesArray = [...selectedSources];

  const {
    status,
    mapData,
    isCanvasOpen,
    errorMessage,
    regenerate,
    openCanvas,
    closeCanvas,
  } = useMindMap({
    notebookId,
    selectedSources: sourcesArray,
  });

  if (!sourcesArray.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <Brain className="w-8 h-8 text-(--text-muted) mb-3 opacity-40" />
        <p className="text-sm text-(--text-muted)">Select sources to generate a mind map</p>
      </div>
    );
  }

  if (status === 'checking' || status === 'generating') {
    return (
      <div className="flex flex-col items-center justify-center py-12">
        <Loader2 className="w-6 h-6 text-(--accent) animate-spin mb-3" />
        <p className="text-sm text-(--text-muted)">
          {status === 'checking' ? 'Checking for existing map...' : 'Generating mind map...'}
        </p>
      </div>
    );
  }

  if (status === 'error') {
    return (
      <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
        <AlertTriangle className="w-6 h-6 text-red-400 mb-3" />
        <p className="text-sm text-red-400 mb-3">{errorMessage || 'Failed to generate mind map'}</p>
        <button
          onClick={regenerate}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-(--accent) text-white hover:bg-(--accent-light) transition-colors"
        >
          <RefreshCw className="w-3.5 h-3.5" /> Retry
        </button>
      </div>
    );
  }

  if (status === 'ready' && mapData) {
    return (
      <div className="space-y-3 animate-fade-in">
        {/* Preview card */}
        <div className="p-4 rounded-xl border border-(--border) bg-(--surface)">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-(--text-primary)">Mind Map</h4>
            <div className="flex items-center gap-1">
              <button
                onClick={regenerate}
                className="p-1.5 rounded-lg text-(--text-muted) hover:bg-(--surface-overlay) transition-colors"
                title="Regenerate"
              >
                <RefreshCw className="w-3.5 h-3.5" />
              </button>
              <button
                onClick={openCanvas}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-(--accent) text-white hover:bg-(--accent-light) transition-colors"
              >
                <Maximize2 className="w-3.5 h-3.5" /> Open Canvas
              </button>
            </div>
          </div>

          {/* Mini preview */}
          <div className="text-xs text-(--text-secondary)">
            {mapData.title && <p className="font-medium mb-1">{mapData.title}</p>}
            {mapData.nodes && <p className="text-(--text-muted)">{mapData.nodes.length} nodes</p>}
          </div>
        </div>

        {/* Canvas overlay */}
        {isCanvasOpen && (
          <div className="fixed inset-0 z-50 bg-(--bg-primary)">
            <MindMapCanvas mapData={mapData} onClose={closeCanvas} />
          </div>
        )}
      </div>
    );
  }

  return null;
}

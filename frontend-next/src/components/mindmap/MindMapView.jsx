'use client';

import { Loader2, RefreshCw, Maximize2, AlertTriangle, Network, X, Brain } from 'lucide-react';
import useMindMap from '@/hooks/useMindMap';
import useAppStore from '@/stores/useAppStore';
import dynamic from 'next/dynamic';

const MindMapCanvas = dynamic(() => import('./MindMapCanvas'), { ssr: false, loading: () => null });

/* Mini skeleton that mimics a node-tree structure */
function MindMapSkeleton() {
  return (
    <div className="py-3 px-1 select-none pointer-events-none" aria-hidden>
      {/* Root */}
      <div className="flex justify-center mb-3">
        <div className="w-20 h-6 rounded-lg bg-[var(--accent)] opacity-60 animate-pulse" />
      </div>
      {/* Level 1 */}
      <div className="flex justify-around mb-3">
        {[70, 80, 65].map((w, i) => (
          <div key={i} className="h-5 rounded-md bg-[var(--surface-overlay)] animate-pulse" style={{ width: `${w}px`, animationDelay: `${i * 150}ms` }} />
        ))}
      </div>
      {/* Level 2 */}
      <div className="flex justify-around">
        {[55, 60, 50, 58, 52].map((w, i) => (
          <div key={i} className="h-4 rounded-md bg-[var(--surface-overlay)] opacity-60 animate-pulse" style={{ width: `${w}px`, animationDelay: `${i * 100}ms` }} />
        ))}
      </div>
    </div>
  );
}
export default function MindMapView({ notebookId, onGenerated }) {
  const selectedSources = useAppStore((s) => s.selectedSources);
  const sourcesArray = [...selectedSources];

  const {
    status,
    mapData,
    isCanvasOpen,
    errorMessage,
    cancel,
    regenerate,
    openCanvas,
    closeCanvas,
  } = useMindMap({
    notebookId,
    selectedSources: sourcesArray,
    onGenerated,
  });

  /* ── Preview card content by status ── */
  const renderCardBody = () => {
    if (!sourcesArray.length) {
      return (
        <div className="flex flex-col items-center justify-center py-6 px-4 text-center">
          <Brain className="w-7 h-7 text-[var(--text-muted)] mb-2 opacity-40" />
          <p className="text-xs text-[var(--text-muted)]">Select sources to generate a mind map</p>
        </div>
      );
    }

    if (status === 'checking') {
      return (
        <div className="flex items-center gap-3 py-4 px-2">
          <Loader2 className="w-5 h-5 text-[var(--accent)] animate-spin shrink-0" />
          <p className="text-xs text-[var(--text-muted)]">Checking for saved map…</p>
        </div>
      );
    }

    if (status === 'generating') {
      return (
        <div className="space-y-3 py-2">
          {/* Skeleton preview */}
          <div className="flex items-start gap-3">
            <div className="w-20 h-8 rounded-lg bg-[var(--surface-overlay)] animate-pulse" />
            <div className="flex flex-col gap-1.5 pt-1">
              <div className="w-28 h-5 rounded bg-[var(--surface-overlay)] animate-pulse" />
              <div className="w-20 h-5 rounded bg-[var(--surface-overlay)] animate-pulse" />
              <div className="w-24 h-5 rounded bg-[var(--surface-overlay)] animate-pulse" />
            </div>
          </div>
          <p className="text-[11px] text-[var(--text-muted)] animate-pulse">
            Analysing materials and building concept graph…
          </p>
          <button
            onClick={cancel}
            className="flex items-center gap-1.5 px-3 py-1 rounded-lg text-xs border border-[var(--border)] text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors"
          >
            <X className="w-3 h-3" /> Cancel
          </button>
        </div>
      );
    }

    if (status === 'error') {
      return (
        <div className="flex flex-col items-center py-4 px-2 gap-2 text-center">
          <AlertTriangle className="w-5 h-5 text-red-400" />
          <p className="text-xs text-red-400">{errorMessage || 'Failed to generate mind map'}</p>
          <button
            onClick={regenerate}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
          >
            <RefreshCw className="w-3 h-3" /> Retry
          </button>
        </div>
      );
    }

    if (status === 'ready' && mapData) {
      return (
        <div
          className="cursor-pointer group"
          onClick={openCanvas}
          title="Click to open canvas"
        >
          {/* Blurred node count preview */}
          <div className="flex items-center gap-2 px-1 mb-3">
            <Network className="w-4 h-4 text-[var(--accent)]" />
            <p className="text-xs font-medium text-[var(--text-primary)]">
              {mapData.title || 'Mind Map'}
            </p>
            <span className="ml-auto text-[10px] text-[var(--text-muted)] bg-[var(--surface-overlay)] px-1.5 py-0.5 rounded-full">
              {mapData.nodes?.length || 0} nodes
            </span>
          </div>
          <div className="flex items-center justify-center py-3 rounded-lg border border-dashed border-[var(--border)] group-hover:border-[var(--accent)] transition-colors">
            <span className="text-xs text-[var(--text-muted)] group-hover:text-[var(--accent)] transition-colors flex items-center gap-1.5">
              <Maximize2 className="w-3.5 h-3.5" /> Open Canvas
            </span>
          </div>
        </div>
      );
    }

    return null;
  };

  return (
    <>
      {/* Inline preview card always visible in the panel */}
      <div className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 animate-fade-in">
        {/* Card header */}
        <div className="flex items-center gap-2 mb-3">
          <Network className="w-4 h-4 text-[var(--text-muted)]" />
          <h4 className="text-sm font-semibold text-[var(--text-primary)]">Mind Map</h4>
          {status === 'ready' && (
            <span className="ml-auto flex items-center gap-1 text-[10px] text-green-400 font-medium">
              <span className="w-1.5 h-1.5 rounded-full bg-green-400 inline-block" /> Ready
            </span>
          )}
          {status === 'ready' && (
            <button
              onClick={(e) => { e.stopPropagation(); regenerate(); }}
              className="p-1 rounded-md text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors"
              title="Regenerate"
            >
              <RefreshCw className="w-3.5 h-3.5" />
            </button>
          )}
        </div>

        {renderCardBody()}
      </div>

      {/* Full-screen canvas dialog — rendered as fixed overlay, outside panel DOM flow */}
      {isCanvasOpen && mapData && (
        <MindMapCanvas
          mapData={mapData}
          onClose={closeCanvas}
          onRegenerate={regenerate}
        />
      )}
    </>
  );
}

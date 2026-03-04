'use client';

import { BookOpen, RefreshCw, Sparkles } from 'lucide-react';
import { QUICK_ACTIONS } from '@/lib/utils/constants';

export default function ChatEmptyState({ hasSource, isSourceProcessing, selectedSources, materials, onQuickAction }) {
  if (hasSource) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-6 py-12">
        <div className="max-w-lg text-center">
          <div className="inline-flex items-center gap-2 px-3.5 py-2 rounded-full mb-6"
            style={{ background: 'var(--accent-subtle)' }}>
            <div className="w-2 h-2 bg-success rounded-full animate-pulse" />
            <span className="text-sm text-text-secondary">
              {selectedSources.length > 1 ? (
                <><span className="text-accent font-medium">{selectedSources.length} sources</span> selected</>
              ) : (
                <>Ready to explore <span className="text-accent font-medium">{materials.find(m => selectedSources.includes(m.id))?.filename}</span></>
              )}
            </span>
          </div>
          <h2 className="text-2xl font-display font-semibold text-text-primary mb-3 tracking-tight">What would you like to know?</h2>
          <p className="text-text-muted text-sm mb-8">Ask questions, run code, research topics, generate study materials — all inline.</p>
          <div className="flex flex-wrap justify-center gap-2">
            {QUICK_ACTIONS.map(action => (
              <button key={action.id} className="quick-action-chip" onClick={() => onQuickAction(action)}>
                <span>{action.icon}</span><span>{action.label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isSourceProcessing) {
    return (
      <div className="flex flex-col items-center justify-center h-full px-6 py-12">
        <div className="max-w-lg text-center">
          <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-6"
            style={{ background: 'var(--accent-subtle)' }}>
            <RefreshCw className="w-6 h-6 text-accent animate-spin" />
          </div>
          <h2 className="text-xl font-display font-semibold text-text-primary mb-2 tracking-tight">Processing your source...</h2>
          <p className="text-text-muted text-sm">Hold tight while we index your file. Chat will unlock automatically when it&apos;s ready.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col items-center justify-center h-full px-6 py-12">
      <div className="max-w-lg text-center">
        <div className="w-14 h-14 rounded-2xl flex items-center justify-center mx-auto mb-6"
          style={{ background: 'var(--surface-overlay)' }}>
          <Sparkles className="w-6 h-6 text-text-muted" />
        </div>
        <h2 className="text-xl font-display font-semibold text-text-primary mb-2 tracking-tight">Welcome to KeplerLab</h2>
        <p className="text-text-muted text-sm max-w-sm mx-auto">Add sources from the sidebar to start exploring with AI-powered research assistance.</p>
      </div>
    </div>
  );
}

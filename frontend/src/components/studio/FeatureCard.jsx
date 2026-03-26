'use client';

import { memo } from 'react';
import { Loader2, X, ArrowRight } from 'lucide-react';

const MATERIAL_ICON_BY_LABEL = {
  Flashcards: 'layers',
  'Practice Quiz': 'checklist',
  Presentation: 'slideshow',
  'Explainer Video': 'video_camera_front',
  'AI Podcast': 'mic',
  'Mind Map': 'account_tree',
};


export default memo(function FeatureCard({ icon, label, description, onClick, loading, onCancel, disabled, accent }) {
  const materialIcon = MATERIAL_ICON_BY_LABEL[label] || 'auto_awesome';

  return (
    <button
      onClick={loading ? undefined : onClick}
      disabled={disabled && !loading}
      className={`workspace-studio-feature-card group relative w-full text-left p-3.5 rounded-xl transition-all duration-200 overflow-hidden border ${
        loading
          ? 'border-[var(--accent)] bg-[var(--accent-subtle)] cursor-default'
          : disabled
            ? 'border-[var(--border)] opacity-40 cursor-not-allowed'
            : 'border-[var(--border)] hover:border-[var(--accent)] cursor-pointer'
      }`}
    >
      {}
      {loading && (
        <div className="absolute top-0 left-0 h-0.5 w-full overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent animate-[shimmer_1.5s_ease-in-out_infinite]" />
        </div>
      )}

      <div className="flex items-center gap-3 relative z-10">
        {}
        <div className={`workspace-studio-feature-icon shrink-0 w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-200 ${
          loading
            ? 'bg-[var(--accent-subtle)]'
            : 'bg-[var(--surface-overlay)] group-hover:bg-[var(--accent-subtle)]'
        }`}>
          {loading ? (
            <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin" />
          ) : (
            <span className="material-symbols-outlined text-[18px] text-[var(--text-muted)] group-hover:text-[var(--accent)] transition-colors duration-200">
              {materialIcon}
            </span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[15px] font-semibold text-[var(--text-primary)] leading-tight tracking-tight">
            {label}
          </p>
          {description && (
            <p className={`text-[11px] mt-0.5 leading-snug transition-colors duration-200 ${
              loading
                ? 'text-[var(--accent)] animate-pulse'
                : 'text-[var(--text-muted)] group-hover:text-[var(--text-secondary)]'
            }`}>
              {loading ? 'Generating…' : description}
            </p>
          )}
        </div>

        {}
        <div className="shrink-0 flex items-center gap-1">
          {loading && onCancel ? (
            <div
              role="button"
              tabIndex={0}
              onClick={(e) => { e.stopPropagation(); onCancel(); }}
              onKeyDown={(e) => { if (e.key === 'Enter' || e.key === ' ') { e.stopPropagation(); onCancel(); } }}
              className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] text-[var(--text-muted)] hover:text-red-400 transition-colors cursor-pointer"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </div>
          ) : !loading && !disabled && (
            <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)] opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
          )}
        </div>
      </div>
    </button>
  );
});

'use client';

import { Loader2, X, ArrowRight } from 'lucide-react';

/**
 * A card button for triggering content generation in the studio panel.
 * Shows loading spinner + cancel when generating.
 */
export default function FeatureCard({ icon, label, description, onClick, loading, onCancel, disabled, accent }) {
  // accent can be a CSS color string like 'var(--accent)' or a tailwind-compatible color
  const accentStyle = accent || 'var(--accent)';

  return (
    <button
      onClick={loading ? undefined : onClick}
      disabled={disabled && !loading}
      className={`group relative w-full text-left p-3 rounded-xl transition-all duration-200 overflow-hidden border ${
        loading
          ? 'border-[var(--accent)] bg-[var(--accent-subtle)] cursor-default'
          : disabled
            ? 'border-[var(--border)] opacity-40 cursor-not-allowed'
            : 'border-[var(--border)] hover:border-[var(--accent)] hover:bg-[var(--surface-overlay)] cursor-pointer'
      }`}
    >
      {/* Loading shimmer bar */}
      {loading && (
        <div className="absolute top-0 left-0 h-0.5 w-full overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-[var(--accent)] to-transparent animate-[shimmer_1.5s_ease-in-out_infinite]" />
        </div>
      )}

      <div className="flex items-center gap-3 relative z-10">
        {/* Icon badge */}
        <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center transition-all duration-200 ${
          loading
            ? 'bg-[var(--accent-subtle)]'
            : 'bg-[var(--surface-overlay)] group-hover:bg-[var(--accent-subtle)]'
        }`}>
          {loading ? (
            <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin" />
          ) : (
            <div className="text-[var(--text-muted)] group-hover:text-[var(--accent)] transition-colors duration-200">
              {icon}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[13px] font-semibold text-[var(--text-primary)] leading-tight">
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

        {/* Right side actions */}
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
}

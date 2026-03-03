'use client';

import { Loader2, X, ArrowRight } from 'lucide-react';

/**
 * A card button for triggering content generation in the studio panel.
 * Shows loading spinner + cancel when generating.
 */
export default function FeatureCard({ icon, label, description, onClick, loading, onCancel, disabled }) {
  return (
    <button
      onClick={loading ? undefined : onClick}
      disabled={disabled && !loading}
      className={`group relative w-full text-left p-3.5 rounded-xl transition-all duration-200 overflow-hidden ${loading
        ? 'bg-accent/5 cursor-default'
        : disabled
          ? 'opacity-40 cursor-not-allowed'
          : 'hover:bg-surface-overlay cursor-pointer'
        }`}
    >
      {/* Hover glow effect */}
      {!loading && !disabled && (
        <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-300 pointer-events-none"
          style={{ background: 'radial-gradient(ellipse at 0% 50%, rgba(16,185,129,0.04) 0%, transparent 70%)' }}
        />
      )}

      {/* Loading shimmer bar */}
      {loading && (
        <div className="absolute top-0 left-0 h-0.5 w-full overflow-hidden">
          <div className="h-full w-1/3 bg-gradient-to-r from-transparent via-accent to-transparent animate-[shimmer_1.5s_ease-in-out_infinite]" />
        </div>
      )}

      <div className="flex items-center gap-3 relative z-10">
        {/* Icon badge */}
        <div className={`shrink-0 w-9 h-9 rounded-lg flex items-center justify-center transition-all duration-200 ${loading
          ? 'bg-accent/15'
          : 'bg-surface-overlay group-hover:bg-accent/12'
          }`}>
          {loading ? (
            <Loader2 className="w-4.5 h-4.5 text-accent animate-spin" />
          ) : (
            <div className="text-text-muted group-hover:text-accent transition-colors duration-200 scale-90">
              {icon}
            </div>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className={`text-sm font-semibold transition-colors duration-200 ${loading ? 'text-text-primary' : 'text-text-primary group-hover:text-text-primary'}`}>
            {label}
          </p>
          {description && (
            <p className={`text-[11.5px] mt-0.5 transition-colors duration-200 ${loading ? 'text-accent animate-pulse' : 'text-text-muted group-hover:text-text-secondary'}`}>
              {loading ? 'Generating…' : description}
            </p>
          )}
        </div>

        {/* Right side actions */}
        <div className="shrink-0 flex items-center gap-1">
          {loading && onCancel ? (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCancel();
              }}
              className="p-1.5 rounded-lg hover:bg-surface-overlay text-text-muted hover:text-danger transition-colors"
              title="Cancel"
            >
              <X className="w-3.5 h-3.5" />
            </button>
          ) : !disabled && (
            <ArrowRight className="w-4 h-4 text-text-muted opacity-0 group-hover:opacity-100 group-hover:translate-x-0.5 transition-all duration-200" />
          )}
        </div>
      </div>
    </button>
  );
}

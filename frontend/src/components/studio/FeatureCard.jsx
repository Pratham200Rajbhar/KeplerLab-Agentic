'use client';

import { memo, useState } from 'react';
import { Loader2, X, ArrowRight, MoreVertical } from 'lucide-react';

const MATERIAL_ICON_BY_LABEL = {
  Flashcards: 'layers',
  'Practice Quiz': 'checklist',
  Presentation: 'slideshow',
  'Explainer Video': 'video_camera_front',
  'Explain Video': 'video_camera_front',
  'AI Podcast': 'mic',
  'Mind Map': 'account_tree',
  'Agent Skills': 'auto_awesome',
};

export default memo(function FeatureCard({
  icon,
  label,
  description,
  onClick,
  loading,
  onCancel,
  disabled,
  accent,
  onSettings,
  menuItems = [],
}) {
  const [menuOpen, setMenuOpen] = useState(false);
  const materialIcon = MATERIAL_ICON_BY_LABEL[label] || 'auto_awesome';
  const hasMenu = Boolean(onSettings) || menuItems.length > 0;
  const accentRgb = accent || '16 185 129';

  return (
    <div
      className={`relative w-full rounded-xl border bg-[var(--surface-raised)] transition-colors ${
        loading
          ? 'border-[var(--accent)]'
          : disabled
            ? 'border-[var(--border)] opacity-45 cursor-not-allowed'
            : 'border-[var(--border)] hover:border-[rgb(var(--feature-accent-rgb))]'
      }`}
      style={{ '--feature-accent-rgb': accentRgb }}
      data-loading={loading ? 'true' : 'false'}
    >
      <button
        onClick={loading ? undefined : onClick}
        disabled={disabled && !loading}
        className="w-full text-left p-3 pr-10 flex items-center gap-3"
      >
        <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
          loading ? 'bg-[var(--accent-subtle)]' : 'bg-[var(--surface-overlay)]'
        }`}>
          {loading ? (
            <Loader2 className="w-4 h-4 text-[var(--accent)] animate-spin" />
          ) : icon ? (
            <span className="text-[var(--text-muted)]">
              {icon}
            </span>
          ) : (
            <span className="material-symbols-outlined text-[17px] text-[var(--text-muted)]">
              {materialIcon}
            </span>
          )}
        </div>

        <div className="flex-1 min-w-0">
          <p className="text-[14px] font-semibold text-[var(--text-primary)] leading-tight tracking-tight">
            {label}
          </p>
          {description && (
            <p className={`text-[11px] mt-0.5 leading-snug ${loading ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'}`}>
              {loading ? 'Generating…' : description}
            </p>
          )}
        </div>

        {!loading && !disabled && (
          <ArrowRight className="w-3.5 h-3.5 text-[var(--text-muted)]" />
        )}
      </button>

      {loading && onCancel && (
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onCancel();
          }}
          className="absolute top-2 right-2 z-20 p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] text-[var(--text-muted)] hover:text-red-400 transition-colors"
          title="Cancel"
          aria-label="Cancel"
        >
          <X className="w-3.5 h-3.5" />
        </button>
      )}

      {hasMenu && !loading && !disabled && (
        <div className="absolute top-2 right-2 z-20">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              setMenuOpen((prev) => !prev);
            }}
            className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] text-[var(--text-muted)] transition-colors"
            title="More options"
            aria-label="More options"
          >
            <MoreVertical className="w-3.5 h-3.5" />
          </button>

          {menuOpen && (
            <>
              <div className="fixed inset-0 z-30" onClick={() => setMenuOpen(false)} />
              <div className="absolute right-0 top-full mt-1 z-40 min-w-[140px] overflow-hidden rounded-lg border border-[var(--border)] bg-[var(--surface-raised)] shadow-lg">
                {onSettings && (
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpen(false);
                      onSettings();
                    }}
                    className="w-full px-3 py-2 text-left text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)]"
                  >
                    Settings
                  </button>
                )}

                {menuItems.map((item, idx) => (
                  <button
                    key={idx}
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation();
                      setMenuOpen(false);
                      item.onClick?.();
                    }}
                    className={`w-full px-3 py-2 text-left text-xs ${
                      item.danger
                        ? 'text-red-400 hover:bg-red-500/10'
                        : 'text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)]'
                    }`}
                  >
                    {item.label}
                  </button>
                ))}
              </div>
            </>
          )}
        </div>
      )}
    </div>
  );
});

'use client';

import { useEffect, useRef } from 'react';
import { AlertTriangle } from 'lucide-react';
import useConfirmStore from '@/stores/useConfirmStore';

export default function ConfirmDialog() {
  const state = useConfirmStore((s) => s.state);
  const inputValue = useConfirmStore((s) => s.inputValue);
  const setInputValue = useConfirmStore((s) => s.setInputValue);
  const handleClose = useConfirmStore((s) => s.handleClose);
  const handleConfirm = useConfirmStore((s) => s.handleConfirm);
  const inputRef = useRef(null);

  useEffect(() => {
    if (state?.prompt && inputRef.current) {
      inputRef.current.focus();
    }
  }, [state]);

  if (!state) return null;

  const isDanger = state.variant === 'danger';

  return (
    <div className="fixed inset-0 z-[9998] flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-(--backdrop) animate-fade-in"
        onClick={handleClose}
      />

      {/* Dialog */}
      <div className="relative bg-(--surface-raised) border border-(--border) rounded-2xl shadow-(--shadow-glass) max-w-sm w-full mx-4 animate-slide-up">
        <div className="p-6">
          {/* Header */}
          <div className="flex items-start gap-4 mb-4">
            {(state.icon || isDanger) && (
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                  isDanger
                    ? 'bg-(--danger-subtle) text-(--danger)'
                    : 'bg-(--accent-subtle) text-(--accent)'
                }`}
              >
                {state.icon || <AlertTriangle className="w-5 h-5" />}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-(--text-primary)">
                {state.title}
              </h3>
              {state.message && (
                <p className="mt-1.5 text-sm text-(--text-secondary) leading-relaxed">
                  {state.message}
                </p>
              )}
            </div>
          </div>

          {/* Prompt input */}
          {state.prompt && (
            <div className="mb-5">
              <input
                ref={inputRef}
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && inputValue.trim()) handleConfirm();
                }}
                placeholder={state.placeholder}
                className="w-full px-3 py-2.5 rounded-xl bg-(--surface) border border-(--border) text-(--text-primary) text-sm placeholder:text-(--text-muted) focus:outline-none focus:ring-2 focus:ring-(--focus-ring) transition-all"
                aria-label={state.title}
              />
            </div>
          )}

          {/* Actions */}
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={handleClose}
              className="px-4 py-2 text-sm rounded-lg border border-(--border) text-(--text-secondary) hover:bg-(--surface-overlay) transition-colors"
            >
              {state.cancelLabel}
            </button>
            <button
              onClick={handleConfirm}
              disabled={state.prompt && !inputValue.trim()}
              className={`px-4 py-2 text-sm rounded-lg text-white font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed ${
                isDanger
                  ? 'bg-(--danger) hover:bg-(--danger-dark)'
                  : 'bg-(--accent) hover:bg-(--accent-dark)'
              }`}
              autoFocus={!state.prompt}
            >
              {state.confirmLabel}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

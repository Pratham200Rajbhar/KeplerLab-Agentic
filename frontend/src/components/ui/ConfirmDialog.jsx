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
  const dialogRef = useRef(null);

  useEffect(() => {
    if (state?.prompt && inputRef.current) {
      inputRef.current.focus();
    }
  }, [state]);

  
  useEffect(() => {
    if (!state) return;
    const handleKey = (e) => { if (e.key === 'Escape') handleClose(); };
    document.addEventListener('keydown', handleKey);
    return () => document.removeEventListener('keydown', handleKey);
  }, [state, handleClose]);

  
  useEffect(() => {
    if (!state) return;
    const dialog = dialogRef.current;
    if (!dialog) return;
    const trap = (e) => {
      if (e.key !== 'Tab') return;
      const focusable = dialog.querySelectorAll('button, input, [tabindex]:not([tabindex="-1"])');
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) { if (document.activeElement === first) { e.preventDefault(); last.focus(); } }
      else { if (document.activeElement === last) { e.preventDefault(); first.focus(); } }
    };
    dialog.addEventListener('keydown', trap);
    return () => dialog.removeEventListener('keydown', trap);
  }, [state]);

  if (!state) return null;

  const isDanger = state.variant === 'danger';

  return (
    <div className="modal-v2-root fixed inset-0 z-[9998] flex items-center justify-center" role="dialog" aria-modal="true" aria-label={state.title || 'Confirm'} ref={dialogRef}>
      {}
      <div
        className="modal-v2-backdrop absolute inset-0 animate-fade-in"
        onClick={handleClose}
      />

      {}
      <div className="modal-v2-shell relative max-w-sm w-full mx-4 animate-slide-up">
        <div className="p-6">
          {}
          <div className="flex items-start gap-4 mb-4">
            {(state.icon || isDanger) && (
              <div
                className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${
                  isDanger
                    ? 'bg-[var(--danger-subtle)] text-[var(--danger)]'
                    : 'bg-[var(--accent-subtle)] text-[var(--accent)]'
                }`}
              >
                {state.icon || <AlertTriangle className="w-5 h-5" />}
              </div>
            )}
            <div className="flex-1 min-w-0">
              <h3 className="text-base font-semibold text-[var(--text-primary)]">
                {state.title}
              </h3>
              {state.message && (
                <p className="mt-1.5 text-sm text-[var(--text-secondary)] leading-relaxed">
                  {state.message}
                </p>
              )}
            </div>
          </div>

          {}
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
                className="w-full px-3 py-2.5 rounded-xl bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] text-sm placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-2 focus:ring-[var(--focus-ring)] transition-all"
                aria-label={state.title}
              />
            </div>
          )}

          {}
          <div className="flex items-center justify-end gap-2">
            <button
              onClick={handleClose}
              className="workspace-dialog-btn ghost px-4 py-2 text-sm rounded-lg border text-[var(--text-secondary)]"
            >
              {state.cancelLabel}
            </button>
            <button
              onClick={handleConfirm}
              disabled={state.prompt && !inputValue.trim()}
              className={`workspace-dialog-btn px-4 py-2 text-sm rounded-lg text-white font-medium disabled:opacity-40 disabled:cursor-not-allowed ${
                isDanger
                  ? 'danger'
                  : 'primary'
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

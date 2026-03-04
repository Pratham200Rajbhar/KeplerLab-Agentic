'use client';

import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

export default function Modal({
  children,
  onClose,
  maxWidth = 'md',
  size,       // alias for maxWidth (backward compat)
  isOpen,
  title,
  icon,
  footer,
}) {
  // Allow callers to control visibility via isOpen (undefined = always render)
  if (isOpen === false) return null;

  const effectiveMaxWidth = size || maxWidth;

  const widthClass = {
    sm: 'max-w-sm',
    md: 'max-w-md',
    lg: 'max-w-lg',
    xl: 'max-w-xl',
    '2xl': 'max-w-2xl',
    '3xl': 'max-w-3xl',
    full: 'max-w-[90vw]',
  }[effectiveMaxWidth] || (effectiveMaxWidth?.startsWith('max-w-') ? effectiveMaxWidth : 'max-w-md');

  return (
    <ModalInner
      onClose={onClose}
      widthClass={widthClass}
      title={title}
      icon={icon}
      footer={footer}
    >
      {children}
    </ModalInner>
  );
}

function ModalInner({ children, onClose, widthClass, title, icon, footer }) {
  const dialogRef = useRef(null);

  // ESC key to close
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  // Focus trap
  useEffect(() => {
    const dialog = dialogRef.current;
    if (!dialog) return;
    const focusable = dialog.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    if (focusable.length > 0) focusable[0].focus();

    const trapFocus = (e) => {
      if (e.key !== 'Tab' || focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey) {
        if (document.activeElement === first) { e.preventDefault(); last.focus(); }
      } else {
        if (document.activeElement === last) { e.preventDefault(); first.focus(); }
      }
    };
    dialog.addEventListener('keydown', trapFocus);
    return () => dialog.removeEventListener('keydown', trapFocus);
  }, []);

  return (
    <div
      className="fixed inset-0 z-[9990] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-label={title || 'Dialog'}
      ref={dialogRef}
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/60 backdrop-blur-[2px] animate-fade-in"
        onClick={onClose}
        role="presentation"
      />
      {/* Content */}
      <div
        className={`relative ${widthClass} w-full bg-surface-raised rounded-2xl shadow-glow-sm animate-slide-up overflow-hidden flex flex-col max-h-[90vh] mx-auto`}
        style={{ border: '1px solid rgba(255,255,255,0.06)' }}
      >
        {/* Header */}
        {(title || icon) && (
          <div className="flex items-center gap-3 px-6 py-4 shrink-0" style={{ borderBottom: '1px solid rgba(255,255,255,0.04)' }}>
            {icon && <span className="text-accent">{icon}</span>}
            {title && <h2 className="text-lg font-semibold text-text-primary flex-1">{title}</h2>}
            {onClose && (
              <button
                onClick={onClose}
                className="p-1.5 rounded-lg hover:bg-surface-overlay transition-colors text-text-muted hover:text-text-primary"
                aria-label="Close dialog"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

        {/* Body */}
        <div className={`flex-1 overflow-auto ${title ? 'px-6 py-4' : ''}`}>
          {children}
        </div>

        {/* Footer */}
        {footer && (
          <div className="px-6 py-4 shrink-0" style={{ borderTop: '1px solid rgba(255,255,255,0.04)' }}>
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

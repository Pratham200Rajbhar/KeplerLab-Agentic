'use client';

import { useEffect, useRef, useCallback } from 'react';
import { X } from 'lucide-react';

export default function Modal({
  children,
  onClose,
  maxWidth = 'md',
  size,       
  isOpen,
  title,
  icon,
  footer,
}) {
  
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

  
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === 'Escape') onClose?.();
    };
    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  
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
      className="modal-v2-root fixed inset-0 z-[9990] flex items-start sm:items-center justify-center p-3 sm:p-4 overflow-y-auto"
      role="dialog"
      aria-modal="true"
      aria-label={title || 'Dialog'}
      ref={dialogRef}
    >
      {}
      <div
        className="modal-v2-backdrop absolute inset-0 animate-fade-in"
        onClick={onClose}
        role="presentation"
      />
      {}
      <div
        className={`modal-v2-shell relative ${widthClass} w-full rounded-2xl animate-slide-up overflow-hidden flex flex-col max-h-[92vh] sm:max-h-[90vh] mx-auto my-2 sm:my-0`}
      >
        {}
        {(title || icon) && (
          <div className="modal-v2-header flex items-center gap-3 px-6 py-4 shrink-0">
            {icon && <span className="text-accent">{icon}</span>}
            {title && <h2 className="text-lg font-semibold text-text-primary flex-1">{title}</h2>}
            {onClose && (
              <button
                onClick={onClose}
                className="modal-v2-close p-1.5 rounded-lg transition-colors text-text-muted hover:text-text-primary"
                aria-label="Close dialog"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>
        )}

        {}
        <div className={`modal-v2-body flex-1 overflow-auto ${title ? 'px-6 py-4' : ''}`}>
          {children}
        </div>

        {}
        {footer && (
          <div className="modal-v2-footer px-6 py-4 shrink-0">
            {footer}
          </div>
        )}
      </div>
    </div>
  );
}

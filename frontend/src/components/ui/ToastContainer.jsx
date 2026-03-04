'use client';

import { X, CheckCircle, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import useToastStore from '@/stores/useToastStore';

const ICONS = {
  success: CheckCircle,
  error: AlertCircle,
  info: Info,
  warning: AlertTriangle,
};

const STYLES = {
  success: 'border-success-border bg-success-subtle',
  error: 'border-danger-border bg-danger-subtle',
  info: 'border-info-border bg-info-subtle',
  warning: 'border-[rgba(255,159,67,0.2)] bg-warning-subtle',
};

const TEXT_COLORS = {
  success: 'text-success',
  error: 'text-danger',
  info: 'text-accent',
  warning: 'text-warning',
};

export default function ToastContainer() {
  const toasts = useToastStore((s) => s.toasts);
  const removeToast = useToastStore((s) => s.removeToast);

  if (!toasts.length) return null;

  return (
    <div
      className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 pointer-events-none"
      aria-live="polite"
      role="status"
    >
      {
        toasts.map((t) => {
          const Icon = ICONS[t.type] || Info;
          return (
            <div
              key={t.id}
              className={`
              pointer-events-auto flex items-center gap-3 px-4 py-3 rounded-xl
              border shadow-lg backdrop-blur-sm max-w-sm
              bg-surface-raised
              ${t.exiting ? 'animate-fade-out' : 'animate-fade-in'}
              ${STYLES[t.type] || STYLES.info}
            `}
              role="alert"
            >
              <Icon className={`w-4 h-4 shrink-0 ${TEXT_COLORS[t.type] || ''}`} />
              <p className="text-sm flex-1 text-text-primary">{t.message}</p>
              <button
                onClick={() => removeToast(t.id)}
                className="shrink-0 p-0.5 rounded hover:bg-surface-overlay transition-colors"
                aria-label="Dismiss notification"
              >
                <X className="w-3.5 h-3.5 opacity-60 text-text-secondary" />
              </button>
            </div>
          );
        })
      }
    </div >
  );
}

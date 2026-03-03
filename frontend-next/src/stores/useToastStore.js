import { create } from 'zustand';
import { TIMERS } from '@/lib/utils/constants';

let toastIdCounter = 0;

const useToastStore = create((set, get) => ({
  toasts: [],
  _timers: {},

  removeToast: (id) => {
    // Mark as exiting for animation
    set((state) => ({
      toasts: state.toasts.map((t) =>
        t.id === id ? { ...t, exiting: true } : t
      ),
    }));
    // Remove after animation
    setTimeout(() => {
      set((state) => ({
        toasts: state.toasts.filter((t) => t.id !== id),
      }));
      const timers = get()._timers;
      if (timers[id]) {
        clearTimeout(timers[id]);
        delete timers[id];
      }
    }, 200);
  },

  addToast: (message, type = 'info', duration = TIMERS.TOAST_DURATION) => {
    // Normalise: Error objects, non-strings → readable string
    if (message instanceof Error) message = message.message || 'An error occurred';
    else if (typeof message !== 'string') message = String(message);

    const id = ++toastIdCounter;
    set((state) => ({
      toasts: [...state.toasts.slice(-4), { id, message, type, exiting: false }],
    }));
    if (duration > 0) {
      const timer = setTimeout(() => get().removeToast(id), duration);
      get()._timers[id] = timer;
    }
    return id;
  },

  // Convenience methods
  success: (msg, duration) => get().addToast(msg, 'success', duration),
  error: (msg, duration) => get().addToast(msg, 'error', duration),
  info: (msg, duration) => get().addToast(msg, 'info', duration),
  warning: (msg, duration) => get().addToast(msg, 'warning', duration),
}));

// Create a toast function with convenience methods for backward compat
export function useToast() {
  const store = useToastStore();
  const toast = (message, type, duration) => store.addToast(message, type, duration);
  toast.success = store.success;
  toast.error = store.error;
  toast.info = store.info;
  toast.warning = store.warning;
  return toast;
}

export default useToastStore;

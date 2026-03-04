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

// Hook that returns a plain object with all toast methods.
// Usage: const toast = useToast(); then call toast.success('msg'), toast.error('msg'), etc.
export function useToast() {
  const store = useToastStore();
  // Return a new object — never mutate the value returned from the hook.
  return {
    toast: (message, type, duration) => store.addToast(message, type, duration),
    success: store.success,
    error: store.error,
    info: store.info,
    warning: store.warning,
  };
}

export default useToastStore;

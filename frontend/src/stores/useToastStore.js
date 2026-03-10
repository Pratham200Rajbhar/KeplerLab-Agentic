import { create } from 'zustand';
import { TIMERS } from '@/lib/utils/constants';

let toastIdCounter = 0;

const useToastStore = create((set, get) => ({
  toasts: [],
  _timers: {},

  removeToast: (id) => {
    
    set((state) => ({
      toasts: state.toasts.map((t) =>
        t.id === id ? { ...t, exiting: true } : t
      ),
    }));
    
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

  
  success: (msg, duration) => get().addToast(msg, 'success', duration),
  error: (msg, duration) => get().addToast(msg, 'error', duration),
  info: (msg, duration) => get().addToast(msg, 'info', duration),
  warning: (msg, duration) => get().addToast(msg, 'warning', duration),
}));


export function useToast() {
  const store = useToastStore();
  
  return {
    toast: (message, type, duration) => store.addToast(message, type, duration),
    success: store.success,
    error: store.error,
    info: store.info,
    warning: store.warning,
  };
}

export default useToastStore;

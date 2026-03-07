import { create } from 'zustand';
import { generateId } from '@/lib/utils/helpers';

const useChatStore = create((set, get) => ({
  // ── State ──
  messages: [],
  sessionId: null,
  isStreaming: false,
  abortController: null,
  pendingChatMessage: null,

  // ── Actions ──
  addMessage: (role, content, extra = null) => {
    const message = {
      id: generateId(),
      role,
      content,
      citations: extra?.citations || (Array.isArray(extra) ? extra : null),
      slashCommand: extra?.slashCommand || null,
      timestamp: new Date(),
    };
    set((state) => ({ messages: [...state.messages, message] }));
    return message;
  },

  updateLastMessage: (updater) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const updated = [...state.messages];
      const last = updated[updated.length - 1];
      updated[updated.length - 1] = typeof updater === 'function' ? updater(last) : { ...last, ...updater };
      return { messages: updated };
    }),

  setMessages: (messagesOrUpdater) =>
    set((state) => ({
      messages:
        typeof messagesOrUpdater === 'function'
          ? messagesOrUpdater(state.messages)
          : messagesOrUpdater,
    })),

  clearMessages: () => set({ messages: [], sessionId: null }),

  setSessionId: (id) => set({ sessionId: id }),

  setStreaming: (isStreaming) => set({ isStreaming }),

  setAbortController: (controller) => set({ abortController: controller }),

  setPendingChatMessage: (msg) => set({ pendingChatMessage: msg }),
}));

export default useChatStore;

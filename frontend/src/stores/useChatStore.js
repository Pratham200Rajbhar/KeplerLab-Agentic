import { create } from 'zustand';

const useChatStore = create((set, get) => ({
  
  messages: [],
  sessionId: null,
  isStreaming: false,
  error: null,

  
  addMessage: (message) =>
    set((state) => ({ messages: [...state.messages, message] })),

  updateMessageById: (messageId, updater) =>
    set((state) => ({
      messages: state.messages.map((msg) => {
        if (msg.id !== messageId) return msg;
        return typeof updater === 'function'
          ? updater(msg)
          : { ...msg, ...updater };
      }),
    })),

  updateLastMessage: (updater) =>
    set((state) => {
      if (state.messages.length === 0) return state;
      const updated = [...state.messages];
      const last = updated[updated.length - 1];
      updated[updated.length - 1] =
        typeof updater === 'function' ? updater(last) : { ...last, ...updater };
      return { messages: updated };
    }),

  setStreaming: (isStreaming) => set({ isStreaming }),

  setError: (error) => set({ error }),

  clearMessages: () => set({ messages: [], sessionId: null, error: null }),

  setSessionId: (id) => set({ sessionId: id }),

  setMessages: (messages) => set({ messages }),
}));

export default useChatStore;

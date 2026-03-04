import { create } from 'zustand';

const useConfirmStore = create((set, get) => ({
  state: null,
  inputValue: '',

  show: (options) =>
    new Promise((resolve) => {
      const defaults = {
        title: 'Confirm',
        message: '',
        confirmLabel: 'Confirm',
        cancelLabel: 'Cancel',
        variant: 'default', // 'default' | 'danger'
        prompt: false,
        defaultValue: '',
        placeholder: '',
        icon: null,
      };
      const config = { ...defaults, ...options, resolve };
      set({ state: config, inputValue: config.defaultValue || '' });
    }),

  setInputValue: (value) => set({ inputValue: value }),

  handleClose: () => {
    const { state } = get();
    if (state) {
      state.resolve(state.prompt ? null : false);
      set({ state: null, inputValue: '' });
    }
  },

  handleConfirm: () => {
    const { state, inputValue } = get();
    if (state) {
      state.resolve(state.prompt ? inputValue : true);
      set({ state: null, inputValue: '' });
    }
  },
}));

export function useConfirm() {
  const show = useConfirmStore((s) => s.show);
  return show;
}

export default useConfirmStore;

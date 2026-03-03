import { create } from 'zustand';
import { login as apiLogin, signup as apiSignup, logout as apiLogout, getCurrentUser, refreshToken } from '@/lib/api/auth';
import { setAccessToken as syncTokenToApi } from '@/lib/api/config';
import { TIMERS } from '@/lib/utils/constants';

const useAuthStore = create((set, get) => ({
  user: null,
  accessToken: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,

  _refreshTimerRef: null,
  _accessTokenRef: null,
  _isInitializing: false,

  _syncToken: (token) => {
    syncTokenToApi(token);
    const store = get();
    store._accessTokenRef = token;
  },

  scheduleRefresh: () => {
    const state = get();
    if (state._refreshTimerRef) {
      clearTimeout(state._refreshTimerRef);
    }
    const timer = setTimeout(async () => {
      try {
        const tokens = await refreshToken();
        set({ accessToken: tokens.access_token });
        get()._syncToken(tokens.access_token);
        get().scheduleRefresh();
      } catch {
        set({ accessToken: null, user: null, isAuthenticated: false });
        get()._syncToken(null);
      }
    }, TIMERS.TOKEN_REFRESH_INTERVAL);
    set({ _refreshTimerRef: timer });
  },

  initAuth: async () => {
    const state = get();
    if (state._isInitializing) return;
    set({ _isInitializing: true });

    try {
      const tokens = await refreshToken();
      set({ accessToken: tokens.access_token });
      get()._syncToken(tokens.access_token);

      const userData = await getCurrentUser(tokens.access_token);
      set({ user: userData, isAuthenticated: true });
      get().scheduleRefresh();
    } catch {
      set({ accessToken: null, user: null, isAuthenticated: false });
      get()._syncToken(null);
    } finally {
      set({ isLoading: false, _isInitializing: false });
    }
  },

  login: async (email, password) => {
    set({ error: null });
    try {
      const tokens = await apiLogin(email, password);
      set({ accessToken: tokens.access_token });
      get()._syncToken(tokens.access_token);

      const userData = await getCurrentUser(tokens.access_token);
      set({ user: userData, isAuthenticated: true });
      get().scheduleRefresh();
      return true;
    } catch (err) {
      set({ error: err.message || 'Login failed' });
      return false;
    }
  },

  signup: async (email, username, password) => {
    set({ error: null });
    try {
      await apiSignup(email, username, password);
      return true;
    } catch (err) {
      set({ error: err.message || 'Signup failed' });
      return false;
    }
  },

  logout: async () => {
    const state = get();
    try {
      await apiLogout(state._accessTokenRef || state.accessToken);
    } catch { /* ignore */ }

    if (state._refreshTimerRef) {
      clearTimeout(state._refreshTimerRef);
    }
    set({
      accessToken: null,
      user: null,
      isAuthenticated: false,
      _refreshTimerRef: null,
    });
    get()._syncToken(null);
  },

  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}));

export default useAuthStore;

import { create } from 'zustand';
import {
  login as apiLogin,
  signup as apiSignup,
  logout as apiLogout,
  getCurrentUser,
  refreshToken,
} from '@/lib/api/auth';
import { setAccessToken as syncTokenToApi, onSessionExpired } from '@/lib/api/config';
import { TIMERS } from '@/lib/utils/constants';

// Module-level refs to avoid storing non-serializable values in Zustand state
let _refreshTimer = null;
let _accessTokenRef = null;
let _initPromise = null;

const useAuthStore = create((set, get) => ({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  error: null,

  _syncToken: (token) => {
    _accessTokenRef = token;
    syncTokenToApi(token);
  },

  scheduleRefresh: () => {
    if (_refreshTimer) clearTimeout(_refreshTimer);
    _refreshTimer = setTimeout(async () => {
      // Retry up to 3 times with exponential backoff before giving up.
      // This handles transient network blips without prematurely logging the
      // user out.
      const MAX_RETRIES = 3;
      let attempt = 0;

      while (attempt < MAX_RETRIES) {
        try {
          const tokens = await refreshToken();
          get()._syncToken(tokens.access_token);
          get().scheduleRefresh(); // reschedule on success
          return;
        } catch {
          attempt++;
          if (attempt < MAX_RETRIES) {
            // Exponential back-off: 2s, 4s, 8s …
            await new Promise((r) => setTimeout(r, 2000 * 2 ** (attempt - 1)));
          }
        }
      }

      // All retries exhausted — session is genuinely expired.
      set({ user: null, isAuthenticated: false });
      get()._syncToken(null);
      if (typeof window !== 'undefined') {
        window.location.href = '/auth?reason=expired';
      }
    }, TIMERS.TOKEN_REFRESH_INTERVAL);
  },

  initAuth: async () => {
    // Deduplicate concurrent init calls (React Strict Mode)
    if (_initPromise) return _initPromise;

    _initPromise = (async () => {
      try {
        const tokens = await refreshToken();
        get()._syncToken(tokens.access_token);

        const userData = await getCurrentUser(tokens.access_token);
        set({ user: userData, isAuthenticated: true });
        get().scheduleRefresh();
      } catch {
        set({ user: null, isAuthenticated: false });
        get()._syncToken(null);
      } finally {
        set({ isLoading: false });
        _initPromise = null;
      }
    })();

    return _initPromise;
  },

  login: async (email, password) => {
    set({ error: null });
    try {
      const tokens = await apiLogin(email, password);
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
    try {
      await apiLogout(_accessTokenRef);
    } catch { /* ignore logout API errors */ }

    if (_refreshTimer) {
      clearTimeout(_refreshTimer);
      _refreshTimer = null;
    }

    set({
      user: null,
      isAuthenticated: false,
    });
    get()._syncToken(null);
  },

  setError: (error) => set({ error }),
  clearError: () => set({ error: null }),
}));

// Register session expiry handler for soft redirects
if (typeof window !== 'undefined') {
  onSessionExpired(() => {
    useAuthStore.getState().logout();
    window.location.href = '/auth?reason=expired';
  });
}

export default useAuthStore;

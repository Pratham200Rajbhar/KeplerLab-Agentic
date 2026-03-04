'use client';

import { useEffect } from 'react';
import { ThemeProvider } from 'next-themes';
import useAuthStore from '@/stores/useAuthStore';
import ToastContainer from '@/components/ui/ToastContainer';
import ConfirmDialog from '@/components/ui/ConfirmDialog';

function AuthInitializer({ children }) {
  const initAuth = useAuthStore((s) => s.initAuth);

  useEffect(() => {
    initAuth();
  }, [initAuth]);

  return children;
}

export default function Providers({ children }) {
  return (
    <ThemeProvider
      attribute="class"
      defaultTheme="dark"
      storageKey="kepler-theme"
      disableTransitionOnChange
    >
      <AuthInitializer>
        {children}
        <ToastContainer />
        <ConfirmDialog />
      </AuthInitializer>
    </ThemeProvider>
  );
}

'use client';

import useAuthStore from '@/stores/useAuthStore';
import Dashboard from '@/components/Dashboard';
import LandingPage from '@/components/LandingPage';

export default function RootPage() {
  const { isAuthenticated, isLoading } = useAuthStore();

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--surface)' }}>
        <div className="loading-spinner w-6 h-6" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return <LandingPage />;
  }

  return <Dashboard />;
}

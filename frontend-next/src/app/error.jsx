'use client';

import { useEffect } from 'react';
import { AlertTriangle, RefreshCw, Home } from 'lucide-react';
import Link from 'next/link';

export default function Error({ error, reset }) {
  useEffect(() => {
    console.error('Route error:', error);
  }, [error]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-(--surface) p-6">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="mx-auto w-16 h-16 rounded-2xl bg-(--danger-subtle) border border-(--danger-border) flex items-center justify-center">
          <AlertTriangle className="w-8 h-8 text-(--danger)" />
        </div>
        <div>
          <h2 className="text-xl font-semibold text-(--text-primary) mb-2">
            Something went wrong
          </h2>
          <p className="text-sm text-(--text-muted)">
            {error?.message || 'An unexpected error occurred.'}
          </p>
        </div>
        <div className="flex items-center justify-center gap-3">
          <button
            onClick={() => reset()}
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-(--accent) hover:bg-(--accent-light) text-white text-sm font-medium transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
            Try again
          </button>
          <Link
            href="/"
            className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-(--surface-overlay) hover:bg-(--surface-100) text-(--text-primary) text-sm font-medium transition-colors"
          >
            <Home className="w-4 h-4" />
            Home
          </Link>
        </div>
      </div>
    </div>
  );
}

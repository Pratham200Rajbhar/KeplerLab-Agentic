import Link from 'next/link';
import { Home, Search } from 'lucide-react';

export default function NotFound() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-(--surface) p-6">
      <div className="max-w-md w-full text-center space-y-6">
        <div className="mx-auto w-20 h-20 rounded-2xl bg-(--surface-overlay) border border-(--border) flex items-center justify-center">
          <Search className="w-10 h-10 text-(--text-muted)" />
        </div>
        <div>
          <h2 className="text-3xl font-bold text-(--text-primary) mb-2">404</h2>
          <p className="text-sm text-(--text-muted)">
            The page you&apos;re looking for doesn&apos;t exist or has been moved.
          </p>
        </div>
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-5 py-2.5 rounded-xl bg-(--accent) hover:bg-(--accent-light) text-white text-sm font-medium transition-colors"
        >
          <Home className="w-4 h-4" />
          Back to Home
        </Link>
      </div>
    </div>
  );
}

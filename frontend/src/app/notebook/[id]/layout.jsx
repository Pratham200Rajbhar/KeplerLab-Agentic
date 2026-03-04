import { Suspense } from 'react';

export async function generateMetadata() {
  return { title: 'Notebook — KeplerLab' };
}

export default function NotebookLayout({ children }) {
  return (
    <Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-surface">
          <div className="flex flex-col items-center gap-4">
            <div className="loading-spinner w-10 h-10" />
            <p className="text-text-secondary text-sm">Loading notebook...</p>
          </div>
        </div>
      }
    >
      {children}
    </Suspense>
  );
}

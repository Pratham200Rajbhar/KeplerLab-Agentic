'use client';

import { Suspense } from 'react';
import dynamic from 'next/dynamic';

const FileViewerContent = dynamic(() => import('@/components/viewer/FileViewerContent'), {
  ssr: false,
  loading: () => (
    <div className="h-screen flex items-center justify-center bg-(--surface)">
      <div className="loading-spinner w-10 h-10" />
    </div>
  ),
});

export default function FileViewerPage() {
  return (
    <Suspense
      fallback={
        <div className="h-screen flex items-center justify-center bg-(--surface)">
          <div className="loading-spinner w-10 h-10" />
        </div>
      }
    >
      <FileViewerContent />
    </Suspense>
  );
}

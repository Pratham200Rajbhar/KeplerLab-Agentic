'use client';

import PresentationViewer from './PresentationViewer';

export default function SlideCanvas({ presentationId, slideIndex, version }) {
  return (
    <div className="flex-1 min-h-0 flex flex-col gap-2">
      <div className="text-xs text-[var(--text-muted)]">Preview (HTML 1920x1080) | Slide {slideIndex + 1}</div>
      <div className="flex-1 min-h-[280px]">
        <PresentationViewer presentationId={presentationId} slideIndex={slideIndex} version={version} />
      </div>
    </div>
  );
}

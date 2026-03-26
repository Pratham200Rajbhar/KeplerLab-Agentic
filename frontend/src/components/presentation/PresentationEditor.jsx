'use client';

import { useState, useRef, useEffect } from 'react';
import SlideCanvas from './SlideCanvas';
import SlideInputBox from './SlideInputBox';
import SlideList from './SlideList';

export default function PresentationEditor({
  presentation,
  activeSlide,
  onSelectSlide,
  onUpdate,
  onDownload,
  updating,
  downloading,
}) {
  const slides = presentation?.data?.slides || [];
  const [downloadFormat, setDownloadFormat] = useState('pptx');
  const [htmlVersion, setHtmlVersion] = useState(0);
  const prevUpdating = useRef(updating);

  useEffect(() => {
    if (prevUpdating.current && !updating) {
      setHtmlVersion((v) => v + 1);
    }
    prevUpdating.current = updating;
  }, [updating]);

  return (
    <div className="h-full grid grid-cols-12 gap-3">
      <div className="col-span-3 min-h-0">
        <SlideList slides={slides} activeIndex={activeSlide} onSelect={onSelectSlide} />
      </div>

      <div className="col-span-9 min-h-0 flex flex-col gap-3">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">{presentation?.title || 'Presentation'}</h3>
          <div className="flex items-center gap-2">
            <select
              value={downloadFormat}
              onChange={(e) => setDownloadFormat(e.target.value)}
              disabled={downloading}
              className="px-2.5 py-1.5 rounded-lg border border-[var(--border)] bg-[var(--surface)] text-xs"
              aria-label="Download presentation format"
            >
              <option value="pptx">PPTX</option>
              <option value="pdf">PDF</option>
              <option value="html">HTML</option>
            </select>
            <button
              onClick={() => onDownload(downloadFormat)}
              disabled={downloading}
              className="px-3 py-1.5 rounded-lg bg-[var(--surface-overlay)] text-xs"
            >
              {downloading ? 'Preparing...' : 'Download'}
            </button>
          </div>
        </div>
        <SlideCanvas
          presentationId={presentation?.id}
          slideIndex={activeSlide}
          version={htmlVersion}
        />

        <div className="rounded-xl border border-[var(--border)] p-3 bg-[var(--surface)]">
          <SlideInputBox onSubmit={onUpdate} loading={updating} />
        </div>
      </div>
    </div>
  );
}

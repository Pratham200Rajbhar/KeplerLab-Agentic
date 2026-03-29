'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { fetchPresentationHtml } from '@/lib/api/presentation';

const SLIDE_WIDTH = 1920;
const SLIDE_HEIGHT = 1080;

function extractSlideHtml(fullHtml, slideIndex) {
  const styles = (fullHtml.match(/<style[\s\S]*?<\/style>/gi) || []).join('\n');
  const slides = fullHtml.match(/<slide[\s\S]*?<\/slide>/gi) || [];
  const safeIndex = Math.max(0, Math.min(slideIndex || 0, Math.max(0, slides.length - 1)));
  const selected = slides[safeIndex] || '<slide><div class="slide"><h1>No slide content</h1></div></slide>';

  return `<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=1920" />
  ${styles}
  <style>
    html, body {
      margin: 0;
      padding: 0;
      width: 1920px;
      height: 1080px;
      overflow: hidden;
    }
    slide {
      display: block;
      margin: 0;
      padding: 0;
    }
  </style>
</head>
<body style="margin:0; padding:0; background:#f3f4f6; overflow:hidden; display:flex; align-items:center; justify-content:center;">
  ${selected}
</body>
</html>`;
}

export default function PresentationViewer({ presentationId, slideIndex = 0, version }) {
  const frameWrapRef = useRef(null);
  const [scale, setScale] = useState(1);
  const [htmlText, setHtmlText] = useState('');
  const [loadedKey, setLoadedKey] = useState('');
  const [errorState, setErrorState] = useState({ key: '', message: '' });

  const requestKey = `${presentationId || ''}:${version || 0}`;
  const loading = Boolean(presentationId) && loadedKey !== requestKey;
  const error = errorState.key === requestKey ? errorState.message : '';

  useEffect(() => {
    const el = frameWrapRef.current;
    if (!el) return;

    const updateScale = () => {
      const w = el.clientWidth || SLIDE_WIDTH;
      const h = el.clientHeight || SLIDE_HEIGHT;
      const s = Math.min(w / SLIDE_WIDTH, h / SLIDE_HEIGHT);
      setScale(Math.max(0.1, s));
    };

    const observer = new ResizeObserver(updateScale);
    observer.observe(el);
    updateScale();
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!presentationId) return;
    const controller = new AbortController();

    // Fetch new HTML whenever presentationId or version changes
    fetchPresentationHtml(presentationId, { signal: controller.signal, version })
      .then((html) => {
        setHtmlText(html || '');
        setErrorState({ key: requestKey, message: '' });
        setLoadedKey(requestKey);
      })
      .catch((err) => {
        if (err.name === 'AbortError') return;
        setErrorState({ key: requestKey, message: err.message || 'Failed to load presentation HTML' });
        setLoadedKey(requestKey);
      });

    return () => controller.abort();
  }, [presentationId, requestKey, version]);

  const srcDoc = useMemo(() => extractSlideHtml(htmlText, slideIndex), [htmlText, slideIndex]);

  if (!presentationId) {
    return <div className="text-sm text-[var(--text-muted)]">No preview available.</div>;
  }

  if (loading) {
    return <div className="text-sm text-[var(--text-muted)]">Loading slide preview...</div>;
  }

  if (error) {
    return <div className="text-sm text-red-400">{error}</div>;
  }

  return (
    <div ref={frameWrapRef} className="w-full h-full rounded-xl border border-[var(--border)] bg-[#f3f4f6] overflow-hidden relative">
      <iframe
        title="Presentation HTML Preview"
        srcDoc={srcDoc}
        sandbox="allow-same-origin"
        style={{
          position: 'absolute',
          top: '50%',
          left: '50%',
          width: `${SLIDE_WIDTH}px`,
          height: `${SLIDE_HEIGHT}px`,
          border: 'none',
          transform: `translate(-50%, -50%) scale(${scale})`,
          transformOrigin: 'center center',
        }}
      />
    </div>
  );
}

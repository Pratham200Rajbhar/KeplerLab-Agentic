'use client';

import { useState, useRef } from 'react';
import { Download, Maximize2, X } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

export default function ChartRenderer({ base64Chart, explanation, title = 'Chart' }) {
  const [expanded, setExpanded] = useState(false);
  const imgRef = useRef(null);
  if (!base64Chart) return null;

  const src = base64Chart.startsWith('data:') ? base64Chart : `data:image/png;base64,${base64Chart}`;

  const handleDownload = () => {
    const a = document.createElement('a');
    a.href = src;
    a.download = `${title.replace(/\s+/g, '_')}.png`;
    a.click();
  };

  return (
    <>
      <div className="chart-renderer">
        <div className="chart-header"><span className="chart-icon">📊</span><span className="chart-title">{title}</span></div>
        <div className="chart-image-wrapper">
          {/* eslint-disable-next-line @next/next/no-img-element -- chart image is a dynamic data URL; Next <Image> requires known dimensions */}
          <img ref={imgRef} src={src} alt={title} className="chart-image" onClick={() => setExpanded(true)} />
        </div>
        <div className="chart-actions">
          <button className="chart-btn" onClick={handleDownload} title="Download PNG"><Download className="w-4 h-4" />Download</button>
          <button className="chart-btn" onClick={() => setExpanded(true)} title="Expand"><Maximize2 className="w-4 h-4" />Expand</button>
        </div>
        {explanation && (
          <div className="chart-insight">
            <span className="chart-insight-icon">💡</span>
            <div className="chart-insight-text markdown-content"><MarkdownRenderer content={explanation} /></div>
          </div>
        )}
      </div>
      {expanded && (
        <div className="chart-modal-backdrop" onClick={() => setExpanded(false)}>
          <div className="chart-modal" onClick={e => e.stopPropagation()}>
            <button className="chart-modal-close" onClick={() => setExpanded(false)} aria-label="Close expanded chart"><X size={16} /></button>
            {/* eslint-disable-next-line @next/next/no-img-element -- same dynamic data URL in the modal */}
            <img src={src} alt={title} className="chart-modal-image" />
            {explanation && <div className="chart-modal-insight markdown-content"><MarkdownRenderer content={explanation} /></div>}
          </div>
        </div>
      )}
    </>
  );
}

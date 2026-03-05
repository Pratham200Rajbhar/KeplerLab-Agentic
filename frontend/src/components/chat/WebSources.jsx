'use client';

import { memo } from 'react';
import { ExternalLink, Globe } from 'lucide-react';

/**
 * WebSources — renders a list of clickable source citations.
 *
 * Props:
 *   sources: [{ title, url, domain, snippet, quality_score }]
 */
function WebSources({ sources = [] }) {
  if (!sources.length) return null;

  return (
    <div className="mt-3 space-y-1.5">
      <div className="flex items-center gap-1.5 text-xs text-text-muted mb-1">
        <Globe className="w-3 h-3" />
        <span className="font-medium">Sources</span>
      </div>
      <div className="flex flex-wrap gap-1.5">
        {sources.map((src, idx) => (
          <a
            key={src.url || idx}
            href={src.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg
              bg-surface-overlay/80 border border-border/20
              text-text-secondary hover:text-accent hover:border-accent/30
              transition-all duration-150 group max-w-[260px]"
            title={src.snippet || src.title}
          >
            <span className="inline-flex items-center justify-center w-4 h-4 rounded bg-accent/10 text-accent text-[10px] font-bold shrink-0">
              {idx + 1}
            </span>
            <span className="truncate">{src.title || src.domain || src.url}</span>
            <ExternalLink className="w-3 h-3 shrink-0 opacity-0 group-hover:opacity-100 transition-opacity" />
          </a>
        ))}
      </div>
    </div>
  );
}

export default memo(WebSources);

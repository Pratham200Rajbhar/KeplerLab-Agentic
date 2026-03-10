'use client';

import { memo } from 'react';
import { ExternalLink } from 'lucide-react';


function WebSources({ sources = [] }) {
  if (!sources.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-1.5">
      {sources.map((src, idx) => {
        let domain = '';
        try { domain = new URL(src.url).hostname.replace(/^www\./, ''); } catch {}
        return (
          <a
            key={src.url || idx}
            href={src.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[11px] pl-1.5 pr-2 py-1 rounded-md
              bg-white/[0.04] border border-white/[0.06]
              text-text-muted hover:text-text-primary hover:border-white/[0.12]
              transition-colors group"
            title={src.title || src.url}
          >
            <span className="flex items-center justify-center w-4 h-4 rounded bg-accent/10 text-accent text-[10px] font-bold shrink-0">
              {idx + 1}
            </span>
            <span className="truncate max-w-[140px]">{domain || src.title || 'Source'}</span>
            <ExternalLink className="w-2.5 h-2.5 opacity-0 group-hover:opacity-60 transition-opacity shrink-0" />
          </a>
        );
      })}
    </div>
  );
}

export default memo(WebSources);

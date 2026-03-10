'use client';

import { memo } from 'react';
import { Globe, Loader2, FileText, Sparkles } from 'lucide-react';


function WebSearchStrip({ status, label }) {
  if (status === 'idle' || status === 'done') return null;

  const icons = {
    searching: <Globe className="w-3.5 h-3.5 text-emerald-400" />,
    scraping: <FileText className="w-3.5 h-3.5 text-emerald-400" />,
    streaming: <Sparkles className="w-3.5 h-3.5 text-emerald-400" />,
  };

  return (
    <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-emerald-500/5 border border-emerald-500/15 mb-3">
      <Loader2 className="w-3.5 h-3.5 text-emerald-400 animate-spin shrink-0" />
      {icons[status] || icons.searching}
      <span className="text-sm text-emerald-300">
        {label || 'Searching the web...'}
      </span>
    </div>
  );
}

export default memo(WebSearchStrip);

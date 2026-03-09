'use client';

import { memo, useState, useMemo } from 'react';
import {
  Globe,
  BookOpen,
  Sparkles,
  ChevronDown,
  ChevronUp,
  ExternalLink,
  CheckCircle2,
  Loader2,
  Search,
  Zap,
} from 'lucide-react';

/**
 * Redesigned WebSearchProgressPanel
 * 
 * A modern, state-driven UI for web search progress.
 * Features:
 *  - Glassmorphic look (blur + transparency)
 *  - Ambient glowing indicators
 *  - Unified state handling from backend 'web_search_update' event
 *  - Auto-collapsing sources after completion
 */
function WebSearchProgressPanel({ webSearchState, sources = [], isStreaming }) {
  const [collapsed, setCollapsed] = useState(false);

  // Skip if no search has started
  if (!webSearchState) return null;

  const { status, queries = [], scrapingUrls = [] } = webSearchState;
  
  // Logic to determine if we are fully done
  const isDone = status === 'done' && !isStreaming;

  // Determine the primary phase
  // status: 'searching' | 'reading' | 'done'
  const effectiveStatus = (status === 'done' || sources.length > 0) && isStreaming 
    ? 'generating' 
    : status;

  // Configuration for different phases
  const phaseConfig = {
    searching: {
      label: 'Scanning Web',
      icon: Search,
      color: 'text-blue-400',
      bg: 'bg-blue-400/10',
      glow: 'shadow-[0_0_15px_rgba(96,165,250,0.3)]',
      progress: 33,
    },
    reading: {
      label: 'Reading Sources',
      icon: BookOpen,
      color: 'text-teal-400',
      bg: 'bg-teal-400/10',
      glow: 'shadow-[0_0_15px_rgba(45,212,191,0.3)]',
      progress: 66,
    },
    generating: {
      label: 'Synthesizing Response',
      icon: Sparkles,
      color: 'text-purple-400',
      bg: 'bg-purple-400/10',
      glow: 'shadow-[0_0_15px_rgba(192,132,252,0.3)]',
      progress: 90,
    },
    done: {
      label: 'Research Complete',
      icon: CheckCircle2,
      color: 'text-green-400',
      bg: 'bg-green-400/10',
      glow: 'shadow-none',
      progress: 100,
    },
  }[effectiveStatus] || {
    label: 'Ready',
    icon: Globe,
    color: 'text-text-muted',
    bg: 'bg-transparent',
    glow: 'shadow-none',
    progress: 0,
  };

  const Icon = phaseConfig.icon;

  // Render for completed state (Sources Accordion)
  if (isDone && sources.length > 0) {
    return (
      <div className="mb-4 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-xl overflow-hidden shadow-sm transition-all duration-500">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="w-full flex items-center justify-between px-4 py-3 hover:bg-white/[0.05] transition-colors group"
        >
          <div className="flex items-center gap-3">
            <div className={`p-1.5 rounded-lg bg-green-400/10 text-green-400`}>
              <CheckCircle2 className="w-4 h-4" />
            </div>
            <div className="flex flex-col items-start translate-y-[1px]">
              <span className="text-sm font-medium text-text-primary tracking-tight">Research Details</span>
              <span className="text-[11px] text-text-muted">
                {sources.length} cited source{sources.length !== 1 ? 's' : ''}
              </span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase font-bold tracking-widest text-text-muted opacity-0 group-hover:opacity-100 transition-opacity">
              {collapsed ? 'View' : 'Hide'}
            </span>
            {collapsed ? <ChevronDown className="w-4 h-4 text-text-muted" /> : <ChevronUp className="w-4 h-4 text-text-muted" />}
          </div>
        </button>

        {!collapsed && (
          <div className="px-4 pb-4 pt-1 grid grid-cols-1 sm:grid-cols-2 gap-2 animate-in fade-in slide-in-from-top-2 duration-300">
            {sources.map((src, idx) => (
              <a
                key={src.url || idx}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-3 group text-xs rounded-xl px-3 py-2.5
                  bg-white/[0.02] border border-white/5 hover:border-accent/30
                  hover:bg-accent/5 transition-all duration-200"
              >
                <div className="flex items-center justify-center w-5 h-5 rounded-lg
                  bg-accent/10 text-accent text-[10px] font-bold shrink-0 border border-accent/20">
                  {idx + 1}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="truncate text-text-secondary group-hover:text-accent font-medium transition-colors">
                    {src.title || src.url}
                  </div>
                  <div className="text-[10px] text-text-muted truncate opacity-60">
                    {new URL(src.url).hostname}
                  </div>
                </div>
                <ExternalLink className="w-3.5 h-3.5 text-text-muted opacity-0 group-hover:opacity-100 translate-x-1 group-hover:translate-x-0 transition-all shrink-0" />
              </a>
            ))}
          </div>
        )}
      </div>
    );
  }

  // Render for active research pipeline
  return (
    <div className="mb-4 rounded-2xl border border-white/10 bg-white/[0.03] backdrop-blur-2xl p-4 shadow-xl overflow-hidden relative group">
      {/* Ambient backgrounds */}
      <div className={`absolute top-0 left-0 w-full h-1 ${phaseConfig.bg} opacity-50`} />
      <div className={`absolute -top-10 -right-10 w-32 h-32 blur-[60px] ${phaseConfig.bg} opacity-20 transition-colors duration-1000`} />
      
      <div className="relative z-10 space-y-4">
        {/* Header Area */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className={`p-2.5 rounded-xl ${phaseConfig.bg} ${phaseConfig.color} ${phaseConfig.glow} transition-all duration-500 animate-pulse`}>
              <Icon className="w-5 h-5" />
            </div>
            <div>
              <h4 className="text-sm font-semibold text-text-primary tracking-tight">{phaseConfig.label}</h4>
              <div className="flex items-center gap-2 mt-0.5">
                <p className="text-[11px] text-text-muted">Analyzing real-time intelligence</p>
                {effectiveStatus !== 'done' && (
                  <div className="flex gap-0.5">
                    {[1,2,3].map(i => (
                      <span key={i} className={`w-1 h-1 rounded-full ${phaseConfig.bg} animate-bounce`} style={{ animationDelay: `${i * 0.2}s` }} />
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
          
          <div className="text-right">
             <span className={`text-[10px] font-black tracking-tighter uppercase p-1 px-2 rounded-md ${phaseConfig.bg} ${phaseConfig.color}`}>
               {effectiveStatus}
             </span>
          </div>
        </div>

        {/* Progress Bar Container */}
        <div className="space-y-2">
          <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden">
            <div 
              className={`h-full ${phaseConfig.bg.replace('bg-', 'bg-')} transition-all duration-1000 ease-out`}
              style={{ 
                width: `${phaseConfig.progress}%`,
                backgroundColor: 'currentColor' // Handled by Tailwind mapping or style
              }}
            />
          </div>
          
          <div className="flex justify-between items-center px-0.5">
             <div className="flex gap-2">
                {['searching', 'reading', 'generating'].map(p => {
                  const active = effectiveStatus === p;
                  return (
                    <div key={p} className={`h-1 w-8 rounded-full transition-all duration-500 ${active ? 'bg-accent w-12 shadow-[0_0_8px_rgba(var(--accent-rgb),0.5)]' : 'bg-white/10'}`} />
                  );
                })}
             </div>
             <span className="text-[10px] font-medium text-text-muted tabular-nums">
               {Math.round(phaseConfig.progress)}%
             </span>
          </div>
        </div>

        {/* Active Queries / URLs */}
        {effectiveStatus === 'searching' && queries.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-1">
            {queries.map((q, i) => (
              <span key={i} className="px-2.5 py-1 rounded-lg bg-blue-400/5 border border-blue-400/10 text-[10px] text-blue-300 flex items-center gap-1.5 animate-in fade-in slide-in-from-left-2 transition-all">
                <Search className="w-2.5 h-2.5 opacity-50" />
                {q}
              </span>
            ))}
          </div>
        )}

        {effectiveStatus === 'reading' && scrapingUrls.length > 0 && (
          <div className="grid grid-cols-1 gap-1.5 pt-1">
            {scrapingUrls.slice(-3).map((item, idx) => {
              let domain = item.url;
              try { domain = new URL(item.url).hostname.replace(/^www\./, ''); } catch {}
              return (
                <div key={idx} className="flex items-center justify-between text-[11px] animate-in slide-in-from-bottom-1 fade-in duration-300">
                  <div className="flex items-center gap-2 min-w-0">
                    {item.status === 'done' 
                      ? <CheckCircle2 className="w-3 h-3 text-teal-400" />
                      : item.status === 'failed'
                        ? <Zap className="w-3 h-3 text-red-400" />
                        : <Loader2 className="w-3 h-3 text-teal-400/60 animate-spin" />
                    }
                    <span className="truncate text-text-secondary opacity-80">{domain}</span>
                  </div>
                  <span className="text-[9px] font-bold text-text-muted uppercase ml-2 tabular-nums">
                    {item.status}
                  </span>
                </div>
              );
            })}
          </div>
        )}

        {effectiveStatus === 'generating' && (
          <div className="pt-1 flex items-center gap-2 text-[11px] text-purple-300 animate-in fade-in duration-500">
             <div className="flex -space-x-1">
                <div className="w-6 h-6 rounded-lg bg-purple-400/20 border border-purple-400/30 flex items-center justify-center">
                  <Sparkles className="w-3 h-3" />
                </div>
             </div>
             <span className="font-medium">Synthesizing comprehensive answer...</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default memo(WebSearchProgressPanel);

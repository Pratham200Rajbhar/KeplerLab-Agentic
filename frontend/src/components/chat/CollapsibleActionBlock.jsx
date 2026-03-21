'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Languages, HelpCircle, RefreshCw, BookOpen } from 'lucide-react';
import MarkdownRenderer from './MarkdownRenderer';

const ACTION_MAP = {
  translate: { icon: Languages, label: 'Translation', color: 'text-blue-400', bg: 'bg-blue-400/10' },
  ask: { icon: HelpCircle, label: 'Response', color: 'text-amber-400', bg: 'bg-amber-400/10' },
  simplify: { icon: RefreshCw, label: 'Simplified View', iconClass: 'animate-spin-slow', color: 'text-emerald-400', bg: 'bg-emerald-400/10' },
  explain: { icon: BookOpen, label: 'In-depth Explanation', color: 'text-purple-400', bg: 'bg-purple-400/10' },
};

export default function CollapsibleActionBlock({ content, defaultOpen = true, isOpen: externalOpen, onToggle }) {
  const [internalOpen, setInternalOpen] = useState(defaultOpen);
  
  const isOpen = externalOpen !== undefined ? externalOpen : internalOpen;
  const toggle = () => {
    if (onToggle) onToggle();
    else setInternalOpen(!internalOpen);
  };

  // Parse the prefix like [translate:parent_id:selection] or [ask]
  const match = content.match(/^\[(translate|ask|simplify|explain)(?::([^:]+):?([^\]]*))?\]\s*(.*)/s);
  
  if (!match) {
    return <MarkdownRenderer content={content} />;
  }

  const [, action, parentId, selection, body] = match;
  const config = ACTION_MAP[action] || { icon: HelpCircle, label: action, color: 'text-accent', bg: 'bg-accent/10' };
  const Icon = config.icon;

  return (
    <div className="relative group/action transition-all duration-300 py-1">
      <button
        onClick={toggle}
        className="flex items-center gap-2 text-[10px] font-bold tracking-wider uppercase opacity-60 hover:opacity-100 transition-opacity"
      >
        <div className={`flex items-center justify-center p-1 rounded-md ${config.bg} ${config.color}`}>
          <Icon size={12} className={config.iconClass || ''} />
        </div>
        <span className={config.color}>{config.label}</span>
        <ChevronRight className={`w-3 h-3 transition-transform duration-300 ${isOpen ? 'rotate-90 text-text-muted' : 'text-text-muted/50'}`} />
      </button>

      {isOpen && (
        <div className="mt-2 ml-2 pl-4 border-l-2 border-white/5 animate-in fade-in slide-in-from-left-2 duration-300">
          <div className="prose-chat prose-invert max-w-none text-sm text-text-secondary leading-relaxed">
            <MarkdownRenderer content={body} />
          </div>
        </div>
      )}
    </div>
  );
}

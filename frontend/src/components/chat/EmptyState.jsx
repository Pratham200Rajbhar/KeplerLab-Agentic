'use client';

import { Zap, Globe, Code2, Search } from 'lucide-react';

const COMMAND_HINTS = [
  { cmd: '/agent',    icon: Zap,    title: 'Agent Execution',  desc: 'Multi-step reasoning',  color: 'text-purple-400', bg: 'bg-purple-500/10', border: 'border-purple-500/15' },
  { cmd: '/research', icon: Globe,  title: 'Research Mode',    desc: 'Deep web research',      color: 'text-blue-400',   bg: 'bg-blue-500/10',   border: 'border-blue-500/15' },
  { cmd: '/code',     icon: Code2,  title: 'Code Execution',   desc: 'Python & data analysis', color: 'text-green-400',  bg: 'bg-green-500/10',  border: 'border-green-500/15' },
  { cmd: '/web',      icon: Search, title: 'Web Search',       desc: 'Search the internet',    color: 'text-orange-400', bg: 'bg-orange-500/10', border: 'border-orange-500/15' },
];

export default function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 py-16 select-none">
      <div className="max-w-md w-full text-center">
        <h2 className="text-2xl font-semibold text-text-primary mb-2 tracking-tight">
          How can I help you?
        </h2>
        <p className="text-text-muted text-sm mb-10 leading-relaxed">
          Ask anything, add sources from the sidebar, or use a slash command for advanced modes.
        </p>

        <div className="grid grid-cols-2 gap-2.5">
          {COMMAND_HINTS.map(({ cmd, icon: Icon, title, desc, color, bg, border }) => (
            <div
              key={cmd}
              className={`flex items-start gap-3 px-3.5 py-3 rounded-xl border ${border} text-left`}
              style={{ background: 'var(--surface-raised, rgba(255,255,255,0.03))' }}
            >
              <div className={`shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${bg} mt-0.5`}>
                <Icon size={15} className={color} />
              </div>
              <div className="min-w-0">
                <div className="text-sm font-medium text-text-primary leading-snug">{title}</div>
                <div className="text-xs text-text-muted mt-0.5">{desc}</div>
                <code className="text-[11px] text-text-muted/60 font-mono mt-1 block">{cmd}</code>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

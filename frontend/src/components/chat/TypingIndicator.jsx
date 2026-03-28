'use client';

import { Bot } from 'lucide-react';


export default function TypingIndicator() {
  return (
    <div className="px-4 sm:px-6 py-3.5">
      <div className="max-w-4xl mx-auto flex gap-3.5">
        <div className="shrink-0 mt-0.5">
          <div className="w-8 h-8 rounded-xl flex items-center justify-center bg-gradient-to-br from-accent/20 to-accent/5 text-accent border border-accent/10">
            <Bot size={14} />
          </div>
        </div>
        <div className="chat-assistant-text-shell inline-flex items-center gap-2.5 py-2.5 px-3.5">
          <div className="typing-indicator" aria-hidden="true">
            <span />
            <span />
            <span />
          </div>
          <span className="text-[11px] font-medium text-text-muted tracking-wide">Thinking…</span>
        </div>
      </div>
    </div>
  );
}

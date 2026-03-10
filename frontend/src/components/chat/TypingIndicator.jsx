'use client';

import { Bot } from 'lucide-react';


export default function TypingIndicator() {
  return (
    <div className="px-4 sm:px-6 py-4">
      <div className="max-w-3xl mx-auto flex gap-3.5">
        <div className="shrink-0 mt-0.5">
          <div className="w-7 h-7 rounded-full flex items-center justify-center bg-accent/15 text-accent">
            <Bot size={14} />
          </div>
        </div>
        <div className="flex items-center gap-1.5 py-1.5">
          <span className="w-2 h-2 rounded-full bg-text-muted/30 animate-bounce [animation-delay:0ms]" />
          <span className="w-2 h-2 rounded-full bg-text-muted/30 animate-bounce [animation-delay:150ms]" />
          <span className="w-2 h-2 rounded-full bg-text-muted/30 animate-bounce [animation-delay:300ms]" />
        </div>
      </div>
    </div>
  );
}

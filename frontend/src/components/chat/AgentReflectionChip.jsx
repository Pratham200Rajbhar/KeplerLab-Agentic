'use client';

import { memo } from 'react';

/**
 * AgentReflectionChip — small, italic, muted chip shown between agent steps
 * when an `agent_reflection` SSE event is received.
 *
 * Example: "✦ Goal achieved — composing response"
 *
 * Fades in with CSS opacity transition (no Framer Motion).
 */
function AgentReflectionChip({ text }) {
  if (!text) return null;

  return (
    <div
      className="flex items-center gap-1.5 py-1 px-2 my-1 animate-fade-in"
      style={{ animation: 'reflectionFade 0.4s ease-in forwards' }}
    >
      <span className="text-accent/60 text-xs">✦</span>
      <span className="text-xs italic text-text-muted/70">{text}</span>

      <style jsx>{`
        @keyframes reflectionFade {
          from { opacity: 0; transform: translateY(4px); }
          to   { opacity: 1; transform: translateY(0); }
        }
      `}</style>
    </div>
  );
}

export default memo(AgentReflectionChip);

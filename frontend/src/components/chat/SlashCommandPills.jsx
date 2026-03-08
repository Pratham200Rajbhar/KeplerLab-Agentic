'use client';

import { memo } from 'react';
import { SLASH_COMMANDS } from './slashCommands';

export default memo(function SlashCommandPills({ onSelect, visible }) {
  if (!visible) return null;
  return (
    <div className="slash-pills flex flex-wrap gap-1.5 mb-2 px-1 animate-fade-in">
      {SLASH_COMMANDS.map(cmd => (
        <button key={cmd.command} onClick={() => onSelect(cmd)}
          className="slash-pill inline-flex items-center gap-1 px-2.5 py-1 rounded-lg text-xs font-medium transition-all duration-150 hover:scale-[1.04] active:scale-95 cursor-pointer shadow-sm"
          style={{ backgroundColor: `${cmd.color}15`, color: cmd.color }} title={cmd.description}>
          <span className="opacity-70">{cmd.command}</span>
        </button>
      ))}
    </div>
  );
});

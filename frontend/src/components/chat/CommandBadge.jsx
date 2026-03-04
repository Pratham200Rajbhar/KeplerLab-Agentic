'use client';

import { memo } from 'react';
import { X } from 'lucide-react';

export default memo(function CommandBadge({ command, onRemove, small = false }) {
  if (!command) return null;

  const sizeClass = small
    ? 'text-[10px] px-1.5 py-0.5 gap-1'
    : 'text-xs px-2.5 py-1 gap-1.5';

  return (
    <span
      className={`command-badge inline-flex items-center font-medium rounded-lg border ${sizeClass}`}
      style={{
        borderColor: `${command.color}40`,
        backgroundColor: `${command.color}15`,
        color: command.color,
      }}
    >
      <span className="font-mono">{command.command}</span>
      {onRemove && (
        <button
          onClick={(e) => { e.stopPropagation(); onRemove(); }}
          className="ml-0.5 rounded-full hover:bg-surface-overlay transition-colors w-4 h-4 flex items-center justify-center leading-none"
          style={{ color: command.color }}
          title="Remove command"
        >
          <X size={12} />
        </button>
      )}
    </span>
  );
});

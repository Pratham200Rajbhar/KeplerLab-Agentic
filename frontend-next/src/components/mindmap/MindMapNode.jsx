'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { ChevronDown, ChevronRight } from 'lucide-react';

const DEPTH_COLORS = [
  { bg: 'bg-(--accent)/20', border: 'border-(--accent)/40', text: 'text-(--accent)' },
  { bg: 'bg-blue-500/15', border: 'border-blue-500/30', text: 'text-blue-400' },
  { bg: 'bg-purple-500/15', border: 'border-purple-500/30', text: 'text-purple-400' },
  { bg: 'bg-green-500/15', border: 'border-green-500/30', text: 'text-green-400' },
  { bg: 'bg-orange-500/15', border: 'border-orange-500/30', text: 'text-orange-400' },
  { bg: 'bg-pink-500/15', border: 'border-pink-500/30', text: 'text-pink-400' },
];

function MindMapNode({ id, data }) {
  const depth = Math.min(data.depth || 0, DEPTH_COLORS.length - 1);
  const colors = DEPTH_COLORS[depth];
  const isHighlighted = data.highlighted;
  const isCollapsed = data.collapsed;

  return (
    <div
      className={`group relative px-4 py-2.5 rounded-xl border transition-all cursor-pointer min-w-[120px] max-w-[220px] ${
        isHighlighted
          ? 'border-yellow-400 bg-yellow-400/10 ring-2 ring-yellow-400/30 shadow-lg shadow-yellow-400/10'
          : `${colors.bg} ${colors.border} hover:shadow-md`
      }`}
    >
      <Handle type="target" position={Position.Top} className="!bg-(--border) !w-2 !h-2 !border-0" />

      <div className="flex items-center gap-1.5">
        {/* Collapse toggle */}
        {data.onToggleCollapse && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              data.onToggleCollapse(id);
            }}
            className="shrink-0 p-0.5 rounded hover:bg-white/10 transition-colors"
          >
            {isCollapsed ? (
              <ChevronRight className={`w-3 h-3 ${colors.text}`} />
            ) : (
              <ChevronDown className={`w-3 h-3 ${colors.text}`} />
            )}
          </button>
        )}

        <span
          className={`text-xs font-medium leading-snug ${
            isHighlighted ? 'text-yellow-300' : 'text-(--text-primary)'
          }`}
        >
          {data.label}
        </span>
      </div>

      {data.description && (
        <p className="text-[10px] text-(--text-muted) mt-1 line-clamp-2 leading-relaxed">
          {data.description}
        </p>
      )}

      <Handle type="source" position={Position.Bottom} className="!bg-(--border) !w-2 !h-2 !border-0" />
    </div>
  );
}

export default memo(MindMapNode);

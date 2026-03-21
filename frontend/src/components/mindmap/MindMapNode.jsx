'use client';

import { memo } from 'react';
import { Handle, Position } from '@xyflow/react';
import { ChevronRight, ChevronLeft } from 'lucide-react';

/**
 * MindMapNode (Scratch Redesign)
 * Standardized pill-shaped node with explicitly placed handles as direct children.
 * This ensures React Flow can calculate the connection points accurately.
 */
function MindMapNode({ id, data }) {
  const isHighlighted = data.highlighted;
  const isCollapsed = data.collapsed;
  const hasChildren = data.hasChildren;
  const depth = data.depth || 0;

  return (
    <div
      onClick={() => hasChildren && data.onToggleCollapse?.(id)}
      className={`
        group relative px-6 py-2.5 rounded-full border transition-all duration-300 
        cursor-pointer min-w-[120px] max-w-[320px] flex items-center justify-between gap-3
        ${isHighlighted 
          ? 'bg-[#3b4252] border-blue-400/50 shadow-[0_0_15px_rgba(96,165,250,0.2)]' 
          : 'bg-[#2e3440] border-[#4c566a] hover:border-[#81a1c1]'
        }
      `}
    >
      {/* Target Handle (Input) - Placed as direct child for coordinate accuracy */}
      {depth > 0 && (
        <Handle
          type="target"
          position={Position.Left}
          className="!opacity-0 !w-4 !h-4 !border-0"
          style={{ left: '0px', top: '50%', transform: 'translateY(-50%)' }}
        />
      )}

      {/* Label Container */}
      <div className="flex-1 min-w-0 py-1">
        <span className="text-[13px] font-medium text-[#eceff4] text-center block leading-tight tracking-tight">
          {data.label}
        </span>
      </div>

      {/* Source Handle (Output) - Placed as direct child for coordinate accuracy */}
      {/* It's positioned behind the chevron button hub */}
      {hasChildren && !isCollapsed && (
        <Handle
          type="source"
          position={Position.Right}
          className="!opacity-0 !w-4 !h-4 !border-0"
          style={{ right: '0px', top: '50%', transform: 'translateY(-50%)' }}
        />
      )}

      {/* Visual Hub (Chevron Toggle) */}
      {hasChildren && (
        <div className="relative flex items-center justify-center mr-[-10px] shrink-0 pointer-events-none">
          <div 
            className={`
              w-7 h-7 rounded-full flex items-center justify-center shadow-lg border transition-all duration-300
              ${isCollapsed 
                ? 'bg-[#3b4252] text-[#81a1c1] border-[#4c566a]' 
                : 'bg-[#81a1c1] text-[#2e3440] border-[#81a1c1]'
              }
            `}
          >
            {isCollapsed ? (
              <ChevronRight className="w-4 h-4" />
            ) : (
              <ChevronLeft className="w-4 h-4" />
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default memo(MindMapNode);

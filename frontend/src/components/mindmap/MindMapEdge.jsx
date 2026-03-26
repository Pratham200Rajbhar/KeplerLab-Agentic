import { BaseEdge, getBezierPath } from '@xyflow/react';
import { memo } from 'react';

const MindMapEdge = memo(({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  style = {},
  markerEnd,
}) => {
  const GAP = 12;

  const isSourceRight = sourcePosition === 'right';
  const shiftedSourceX = isSourceRight ? sourceX + GAP : sourceX - GAP;
  const shiftedTargetX = isSourceRight ? targetX - GAP : targetX + GAP;

  const [edgePath] = getBezierPath({
    sourceX: shiftedSourceX,
    sourceY,
    sourcePosition,
    targetX: shiftedTargetX,
    targetY,
    targetPosition,
    curvature: 0.4,
  });

  const color = style.stroke || '#6366f1';

  return (
    <g className="mindmap-edge-group">
      <path
        d={edgePath}
        fill="none"
        stroke={color}
        strokeWidth={2}
        strokeOpacity={0.25}
        strokeLinecap="round"
      />
      <BaseEdge
        path={edgePath}
        markerEnd={markerEnd}
        style={{
          stroke: color,
          strokeWidth: 1.5,
          strokeLinecap: 'round',
          opacity: 0.85,
        }}
      />
      <circle r="2" fill={color} opacity={0.9}>
        <animateMotion
          dur="3s"
          repeatCount="indefinite"
          path={edgePath}
        />
        <animate
          attributeName="opacity"
          values="0;0.9;0"
          dur="3s"
          repeatCount="indefinite"
        />
      </circle>
    </g>
  );
});

MindMapEdge.displayName = 'MindMapEdge';

export default MindMapEdge;

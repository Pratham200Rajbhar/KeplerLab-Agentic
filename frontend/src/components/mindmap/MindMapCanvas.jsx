'use client';

import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
  getBezierPath,
  BaseEdge
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { toPng } from 'html-to-image';
import { X, Search, Download, ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';
import MindMapNode from './MindMapNode';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';

/**
 * Custom HubEdge component for a professional curved look.
 * Originates from the parent's hub and fans out to children.
 */
const HubEdge = ({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, style = {}, markerEnd }) => {
  const [edgePath] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition,
    curvature: 0.6,
  });

  return (
    <BaseEdge 
      id={id}
      path={edgePath} 
      markerEnd={markerEnd} 
      style={{ 
        ...style, 
        stroke: '#94a3b8', 
        strokeWidth: 2.5, 
        opacity: 0.8 
      }} 
    />
  );
};

const nodeTypes = { mindmap: MindMapNode };
const edgeTypes = { hub: HubEdge };

const NODE_WIDTH = 260; 
const NODE_HEIGHT = 44; 

/**
 * Dagre layout engine for consistent Right-to-Left (LR) tree structure.
 */
function generateLayout(mapData) {
  if (!mapData?.nodes?.length) return { nodes: [], edges: [] };

  const edgesList = Array.isArray(mapData.edges) && mapData.edges.length > 0
    ? mapData.edges
    : mapData.nodes
        .filter((n) => n.parent_id)
        .map((n) => ({ source: n.parent_id, target: n.id }));

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'LR', ranksep: 120, nodesep: 30 });

  mapData.nodes.forEach((n) => {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
  });

  edgesList.forEach((e) => {
    g.setEdge(e.source, e.target);
  });

  dagre.layout(g);

  const rfNodes = mapData.nodes.map((n) => {
    const pos = g.node(n.id);
    const hasChildren = edgesList.some((e) => e.source === n.id);
    
    // Find depth by climbing up the parent tree
    let depth = 0;
    let currentParentId = n.parent_id;
    while (currentParentId) {
      depth++;
      const parent = mapData.nodes.find(node => node.id === currentParentId);
      currentParentId = parent?.parent_id;
      if (depth > 20) break; // Infinite loop guard
    }

    return {
      id: n.id,
      type: 'mindmap',
      data: { 
        label: n.label, 
        depth,
        hasChildren 
      },
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
    };
  });

  const rfEdges = edgesList.map((e) => ({
    id: `${e.source}-${e.target}`,
    source: e.source,
    target: e.target,
    type: 'hub',
    animated: true,
  }));

  return { nodes: rfNodes, edges: rfEdges };
}

function MindMapCanvasInner({ mapData, onClose, onRegenerate }) {
  const initialLayout = useMemo(() => generateLayout(mapData), [mapData]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialLayout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialLayout.edges);
  const [searchTerm, setSearchTerm] = useState('');
  
  // Single source of truth for visibility
  const [collapsedIds, setCollapsedIds] = useState(() => {
    const allParentIds = new Set(mapData.nodes.filter(n => n.parent_id).map(n => n.parent_id));
    return allParentIds; 
  });

  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const containerRef = useRef(null);
  const setPendingChatMessage = useAppStore((s) => s.setPendingChatMessage);
  const toast = useToast();

  const toggleCollapse = useCallback((nodeId) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  // Sync visibility whenever collapsedIds change
  useEffect(() => {
    const hiddenSet = new Set();
    const childMap = {};
    initialLayout.edges.forEach((e) => {
      if (!childMap[e.source]) childMap[e.source] = [];
      childMap[e.source].push(e.target);
    });

    const hideDescendants = (parentId) => {
      const children = childMap[parentId] || [];
      children.forEach((childId) => {
        hiddenSet.add(childId);
        hideDescendants(childId);
      });
    };

    collapsedIds.forEach(id => hideDescendants(id));

    setNodes((nds) => nds.map((n) => ({
      ...n,
      hidden: hiddenSet.has(n.id),
      data: { 
        ...n.data, 
        collapsed: collapsedIds.has(n.id), 
        onToggleCollapse: toggleCollapse 
      },
    })));

    setEdges((eds) => eds.map((e) => ({
      ...e,
      hidden: hiddenSet.has(e.target),
    })));

    // Auto-zoom to focus on visible content
    const timer = setTimeout(() => {
      fitView({ padding: 0.25, duration: 400, maxZoom: 1 });
    }, 100);
    return () => clearTimeout(timer);
  }, [collapsedIds, initialLayout.edges, setNodes, setEdges, fitView, toggleCollapse]);

  // Search/Highlight Logic
  useEffect(() => {
    const lower = searchTerm.toLowerCase();
    setNodes((nds) => nds.map((n) => ({
      ...n,
      data: {
        ...n.data,
        highlighted: searchTerm && (n.data.label || '').toLowerCase().includes(lower),
      },
    })));
  }, [searchTerm, setNodes]);

  const onNodeClick = useCallback(
    (_, node) => {
      setPendingChatMessage(`Tell me more about: ${node.data.label}`);
    },
    [setPendingChatMessage]
  );

  const handleExport = useCallback(async () => {
    const el = containerRef.current?.querySelector('.react-flow__viewport');
    if (!el) return;
    try {
      const dataUrl = await toPng(el, { backgroundColor: '#2e3440' });
      const a = document.createElement('a');
      a.href = dataUrl;
      a.download = 'mindmap.png';
      a.click();
      toast.success('Mind map exported');
    } catch (err) {
      console.error('Export failed:', err);
      toast.error('Failed to export mind map');
    }
  }, [toast]);

  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-[#2e3440]">
      {/* Header */}
      <div className="flex flex-col px-8 py-6 bg-[#2e3440] border-b border-[#4c566a] shrink-0">
        <div className="flex items-center justify-between mb-1">
          <h3 className="text-xl font-medium text-[#eceff4] tracking-tight">
            {mapData?.title || 'Mind Map'}
          </h3>
          <div className="flex items-center gap-3 text-[#81a1c1]">
             <button onClick={() => fitView({ padding: 0.2, maxZoom: 1 })} className="p-1.5 rounded-full hover:bg-[#434c5e]" title="Reset View">
              <Maximize2 className="w-4 h-4" />
            </button>
            <button onClick={handleExport} className="p-1.5 rounded-full hover:bg-[#434c5e]" title="Download PNG">
              <Download className="w-4 h-4" />
            </button>
            <button onClick={onClose} className="ml-2 p-1.5 rounded-full hover:bg-[#434c5e] text-[#eceff4] transition-colors">
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>
        <p className="text-xs text-[#4c566a] font-medium uppercase tracking-widest">
          Based on sources
        </p>

        {/* Search */}
        <div className="absolute top-[100px] right-10 z-10">
           <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[#81a1c1] opacity-50" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Find..."
              className="pl-9 pr-4 py-2 text-xs rounded-full bg-[#3b4252]/50 border border-transparent focus:border-[#5e81ac] text-[#eceff4] focus:outline-none transition-all w-48 backdrop-blur-sm"
            />
          </div>
        </div>
      </div>

      {/* Floating Controls */}
      <div className="fixed bottom-10 right-10 z-10 flex flex-col gap-2 scale-110">
         <div className="flex flex-col bg-[#3b4252] rounded-full p-1 shadow-2xl border border-[#4c566a]">
          {onRegenerate && (
            <button onClick={onRegenerate} className="p-2 rounded-full hover:bg-[#434c5e] text-[#81a1c1]" title="Regenerate">
              <RefreshCw className="w-4 h-4" />
            </button>
          )}
          <button onClick={() => zoomIn()} className="p-2 rounded-full hover:bg-[#434c5e] text-[#81a1c1]" title="Zoom in">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={() => zoomOut()} className="p-2 rounded-full hover:bg-[#434c5e] text-[#81a1c1]" title="Zoom out">
            <ZoomOut className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Flow Canvas */}
      <div ref={containerRef} className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.2, maxZoom: 1 }}
          minZoom={0.1}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="#4c566a" gap={24} size={1} />
        </ReactFlow>
      </div>
    </div>
  );
}

export default function MindMapCanvas({ mapData, onClose, onRegenerate }) {
  if (!mapData) return null;
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner mapData={mapData} onClose={onClose} onRegenerate={onRegenerate} />
    </ReactFlowProvider>
  );
}

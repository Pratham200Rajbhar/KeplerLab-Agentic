'use client';

import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { toPng } from 'html-to-image';
import { X, Search, Download, ZoomIn, ZoomOut, Maximize2 } from 'lucide-react';
import MindMapNode from './MindMapNode';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';

const nodeTypes = { mindmap: MindMapNode };

const NODE_WIDTH = 220;
const NODE_HEIGHT = 50;

/* ─── Dagre layout ─── */
function layoutNodes(mapData) {
  if (!mapData?.nodes?.length) return { nodes: [], edges: [] };

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'TB', ranksep: 80, nodesep: 40 });

  const rfNodes = [];
  const rfEdges = [];

  mapData.nodes.forEach((n) => {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    rfNodes.push({
      id: n.id,
      type: 'mindmap',
      data: { label: n.label, depth: n.depth || 0, description: n.description },
      position: { x: 0, y: 0 },
    });
  });

  (mapData.edges || []).forEach((e) => {
    g.setEdge(e.source, e.target);
    rfEdges.push({
      id: `${e.source}-${e.target}`,
      source: e.source,
      target: e.target,
      type: 'smoothstep',
      style: { stroke: 'var(--border)', strokeWidth: 1.5 },
      animated: false,
    });
  });

  dagre.layout(g);

  rfNodes.forEach((n) => {
    const pos = g.node(n.id);
    n.position = { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 };
  });

  return { nodes: rfNodes, edges: rfEdges };
}

/* ─── Inner Canvas (needs ReactFlow provider) ─── */
function MindMapCanvasInner({ mapData, onClose }) {
  const initialLayout = useMemo(() => layoutNodes(mapData), [mapData]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialLayout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialLayout.edges);
  const [searchTerm, setSearchTerm] = useState('');
  const [collapsedIds, setCollapsedIds] = useState(new Set());
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const containerRef = useRef(null);
  const setPendingChatMessage = useAppStore((s) => s.setPendingChatMessage);
  const toast = useToast();

  // Search highlighting
  useEffect(() => {
    if (!searchTerm.trim()) {
      setNodes((nds) =>
        nds.map((n) => ({ ...n, data: { ...n.data, highlighted: false } }))
      );
      return;
    }
    const lower = searchTerm.toLowerCase();
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: {
          ...n.data,
          highlighted: (n.data.label || '').toLowerCase().includes(lower),
        },
      }))
    );
  }, [searchTerm, setNodes]);

  // Collapse/expand
  const toggleCollapse = useCallback(
    (nodeId) => {
      setCollapsedIds((prev) => {
        const next = new Set(prev);
        if (next.has(nodeId)) next.delete(nodeId);
        else next.add(nodeId);
        return next;
      });
    },
    []
  );

  // Apply collapse visibility
  useEffect(() => {
    if (!collapsedIds.size) {
      setNodes((nds) => nds.map((n) => ({ ...n, hidden: false })));
      setEdges((eds) => eds.map((e) => ({ ...e, hidden: false })));
      return;
    }

    // Find all descendants of collapsed nodes
    const hiddenSet = new Set();
    const childMap = {};
    edges.forEach((e) => {
      if (!childMap[e.source]) childMap[e.source] = [];
      childMap[e.source].push(e.target);
    });

    const collectDescendants = (parentId) => {
      (childMap[parentId] || []).forEach((childId) => {
        if (!collapsedIds.has(childId)) {
          hiddenSet.add(childId);
          collectDescendants(childId);
        }
      });
    };

    collapsedIds.forEach(collectDescendants);

    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        hidden: hiddenSet.has(n.id),
        data: { ...n.data, collapsed: collapsedIds.has(n.id), onToggleCollapse: toggleCollapse },
      }))
    );
    setEdges((eds) =>
      eds.map((e) => ({ ...e, hidden: hiddenSet.has(e.target) }))
    );
  }, [collapsedIds, edges, setNodes, setEdges, toggleCollapse]);

  // Pass collapse handler to nodes
  useEffect(() => {
    setNodes((nds) =>
      nds.map((n) => ({
        ...n,
        data: { ...n.data, onToggleCollapse: toggleCollapse },
      }))
    );
  }, [toggleCollapse, setNodes]);

  // Node click → send to chat
  const onNodeClick = useCallback(
    (_, node) => {
      setPendingChatMessage(`Tell me more about: ${node.data.label}`);
    },
    [setPendingChatMessage]
  );

  // Export PNG
  const handleExport = useCallback(async () => {
    const el = containerRef.current?.querySelector('.react-flow__viewport');
    if (!el) return;
    try {
      const dataUrl = await toPng(el, { backgroundColor: '#0f0f23' });
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
    <div ref={containerRef} className="w-full h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-(--border) bg-(--surface-raised)">
        <div className="flex items-center gap-3">
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-(--surface-overlay) transition-colors">
            <X className="w-5 h-5 text-(--text-secondary)" />
          </button>
          <h3 className="text-sm font-semibold text-(--text-primary)">Mind Map</h3>
        </div>

        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-(--text-muted)" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search nodes..."
              className="pl-8 pr-3 py-1.5 text-xs rounded-lg bg-(--surface) border border-(--border) text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus:ring-1 focus:ring-(--accent) w-40"
            />
          </div>

          <button onClick={() => zoomIn()} className="p-1.5 rounded-lg hover:bg-(--surface-overlay) text-(--text-muted)">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={() => zoomOut()} className="p-1.5 rounded-lg hover:bg-(--surface-overlay) text-(--text-muted)">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button onClick={() => fitView({ padding: 0.2 })} className="p-1.5 rounded-lg hover:bg-(--surface-overlay) text-(--text-muted)">
            <Maximize2 className="w-4 h-4" />
          </button>
          <button onClick={handleExport} className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-(--accent) text-white hover:bg-(--accent-light) transition-colors">
            <Download className="w-3.5 h-3.5" /> PNG
          </button>
        </div>
      </div>

      {/* React Flow canvas */}
      <div className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.2}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="var(--border)" gap={20} size={1} />
          <Controls
            position="bottom-left"
            showInteractive={false}
            className="!bg-(--surface-raised) !border-(--border) !rounded-lg !shadow-lg"
          />
        </ReactFlow>
      </div>
    </div>
  );
}

/* ─── Wrapper with Provider ─── */
export default function MindMapCanvas({ mapData, onClose }) {
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner mapData={mapData} onClose={onClose} />
    </ReactFlowProvider>
  );
}

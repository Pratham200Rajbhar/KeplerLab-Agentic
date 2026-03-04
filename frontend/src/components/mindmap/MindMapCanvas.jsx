'use client';

import { useCallback, useEffect, useMemo, useState, useRef } from 'react';
import {
  ReactFlow,
  ReactFlowProvider,
  Controls,
  MiniMap,
  Background,
  useNodesState,
  useEdgesState,
  useReactFlow,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import dagre from 'dagre';
import { toPng } from 'html-to-image';
import { X, Search, Download, ZoomIn, ZoomOut, Maximize2, RefreshCw } from 'lucide-react';
import MindMapNode from './MindMapNode';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';

const nodeTypes = { mindmap: MindMapNode };

const NODE_WIDTH = 220;
const NODE_HEIGHT = 50;

/* ─── Dagre layout ─── */
function layoutNodes(mapData) {
  if (!mapData?.nodes?.length) return { nodes: [], edges: [] };

  // ── Derive edges from parent_id when no explicit edges array provided ──
  const edgesList = Array.isArray(mapData.edges) && mapData.edges.length > 0
    ? mapData.edges
    : mapData.nodes
        .filter((n) => n.parent_id)
        .map((n) => ({ source: n.parent_id, target: n.id }));

  // ── Derive depth from parent_id hierarchy ──
  const depthMap = {};
  const getDepth = (nodeId, visited = new Set()) => {
    if (depthMap[nodeId] !== undefined) return depthMap[nodeId];
    if (visited.has(nodeId)) { depthMap[nodeId] = 0; return 0; } // cycle guard
    visited.add(nodeId);
    const node = mapData.nodes.find((n) => n.id === nodeId);
    if (!node || !node.parent_id) { depthMap[nodeId] = 0; return 0; }
    const parentDepth = getDepth(node.parent_id, visited);
    depthMap[nodeId] = parentDepth + 1;
    return parentDepth + 1;
  };
  mapData.nodes.forEach((n) => getDepth(n.id));

  const g = new dagre.graphlib.Graph();
  g.setDefaultEdgeLabel(() => ({}));
  g.setGraph({ rankdir: 'LR', ranksep: 120, nodesep: 28 });

  const rfNodes = [];
  const rfEdges = [];

  mapData.nodes.forEach((n) => {
    g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT });
    rfNodes.push({
      id: n.id,
      type: 'mindmap',
      data: { label: n.label, depth: depthMap[n.id] ?? (n.depth || 0), description: n.description },
      position: { x: 0, y: 0 },
    });
  });

  edgesList.forEach((e) => {
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
function MindMapCanvasInner({ mapData, onClose, onRegenerate }) {
  const toggleCollapseRef = useRef(null);
  const edgesRef = useRef([]);
  const initialLayout = useMemo(() => layoutNodes(mapData), [mapData]);
  const [nodes, setNodes, onNodesChange] = useNodesState(initialLayout.nodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialLayout.edges);
  const [searchTerm, setSearchTerm] = useState('');
  const [collapsedIds, setCollapsedIds] = useState(new Set());
  const { fitView, zoomIn, zoomOut } = useReactFlow();
  const containerRef = useRef(null);
  const setPendingChatMessage = useAppStore((s) => s.setPendingChatMessage);
  const toast = useToast();

  // Keep edgesRef in sync without adding edges to other effect deps
  useEffect(() => { edgesRef.current = edges; }, [edges]);

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

  // Collapse/expand — stable ref avoids stale closure in effect
  const toggleCollapse = useCallback((nodeId) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(nodeId)) next.delete(nodeId);
      else next.add(nodeId);
      return next;
    });
  }, []);

  // Keep the ref in sync with the latest toggleCollapse callback.
  // Must run in an effect — not during render — to avoid React skipping updates.
  useEffect(() => {
    toggleCollapseRef.current = toggleCollapse;
  }, [toggleCollapse]);

  // Apply collapse visibility — uses edgesRef to avoid edges in dep array
  // so setNodes → onNodesChange → edges change does NOT re-trigger this
  useEffect(() => {
    const currentEdges = edgesRef.current;
    if (!collapsedIds.size) {
      setNodes((nds) =>
        nds.map((n) => ({
          ...n,
          hidden: false,
          data: { ...n.data, collapsed: false, onToggleCollapse: toggleCollapseRef.current },
        }))
      );
      setEdges((eds) => eds.map((e) => ({ ...e, hidden: false })));
      return;
    }

    const hiddenSet = new Set();
    const childMap = {};
    currentEdges.forEach((e) => {
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
        data: { ...n.data, collapsed: collapsedIds.has(n.id), onToggleCollapse: toggleCollapseRef.current },
      }))
    );
    setEdges((eds) => eds.map((e) => ({ ...e, hidden: hiddenSet.has(e.target) })));
  }, [collapsedIds, setNodes, setEdges]); // ← no `edges` dep → breaks infinite loop

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
    /* Always a fixed full-screen dialog — same pattern as original project */
    <div className="fixed inset-0 z-50 flex flex-col" style={{ background: 'var(--surface)' }}>
      {/* Toolbar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-[var(--border)] bg-[var(--surface-raised)] shrink-0">
        {/* Left: close + title */}
        <div className="flex items-center gap-3">
          <button
            onClick={onClose}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors"
          >
            <X className="w-3.5 h-3.5" /> Close
          </button>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">
            {mapData?.title || 'Mind Map'}
          </h3>
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-2">
          {/* Search */}
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)]" />
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              placeholder="Search nodes..."
              className="pl-8 pr-3 py-1.5 text-xs rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] w-44"
            />
          </div>

          {onRegenerate && (
            <button
              onClick={onRegenerate}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs border border-[var(--border)] text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors"
              title="Regenerate"
            >
              <RefreshCw className="w-3.5 h-3.5" /> Regen
            </button>
          )}

          <button onClick={() => zoomIn()} className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] text-[var(--text-muted)]" title="Zoom in">
            <ZoomIn className="w-4 h-4" />
          </button>
          <button onClick={() => zoomOut()} className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] text-[var(--text-muted)]" title="Zoom out">
            <ZoomOut className="w-4 h-4" />
          </button>
          <button onClick={() => fitView({ padding: 0.15 })} className="p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] text-[var(--text-muted)]" title="Fit all nodes">
            <Maximize2 className="w-4 h-4" />
          </button>

          <button
            onClick={handleExport}
            className="flex items-center gap-1 px-3 py-1.5 rounded-lg text-xs bg-[var(--accent)] text-white hover:opacity-90 transition-opacity"
          >
            <Download className="w-3.5 h-3.5" /> PNG
          </button>
        </div>
      </div>

      {/* React Flow canvas — flex-1 so it fills remaining screen */}
      <div ref={containerRef} className="flex-1">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeClick={onNodeClick}
          nodeTypes={nodeTypes}
          fitView
          minZoom={0.1}
          maxZoom={2}
          proOptions={{ hideAttribution: true }}
        >
          <Background color="var(--border)" gap={20} size={1} />
          <Controls
            position="bottom-left"
            showInteractive={false}
            className="!bg-[var(--surface-raised)] !border-[var(--border)] !rounded-lg !shadow-lg"
          />
          <MiniMap
            position="bottom-right"
            nodeColor="var(--accent)"
            maskColor="rgba(0,0,0,0.4)"
            className="!bg-[var(--surface-raised)] !border !border-[var(--border)] !rounded-lg"
          />
        </ReactFlow>
      </div>
    </div>
  );
}

/* ─── Wrapper with Provider ─── */
export default function MindMapCanvas({ mapData, onClose, onRegenerate }) {
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner mapData={mapData} onClose={onClose} onRegenerate={onRegenerate} />
    </ReactFlowProvider>
  );
}

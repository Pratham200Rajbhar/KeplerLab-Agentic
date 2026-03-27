'use client';

import { useCallback, useEffect, useMemo, memo, useRef, useState } from 'react';
import {
  ReactFlow,
  useNodesState,
  useEdgesState,
  useReactFlow,
  ReactFlowProvider,
  Handle,
  Position,
  Background,
  BackgroundVariant,
  MiniMap,
  getNodesBounds,
  getViewportForBounds,
} from '@xyflow/react';
import { toPng } from 'html-to-image';
import { jsPDF } from 'jspdf';
import {
  X,
  Maximize2,
  ChevronRight,
  ArrowLeft,
  Download,
  ThumbsUp,
  ThumbsDown,
  Plus,
  Minus,
  Loader2,
  Check,
  Minimize2,
  Expand,
  ChevronsDown,
  ChevronsUp,
  Brain,
  Target,
} from 'lucide-react';
import { useTheme } from 'next-themes';
import '@xyflow/react/dist/style.css';

import useAppStore from '@/stores/useAppStore';
import useMindMapStore from '@/stores/useMindMapStore';
import useChatStore from '@/stores/useChatStore';
import MindMapEdge from './MindMapEdge';

const NODE_WIDTH = 300;
const NODE_HEIGHT = 44;
const HORIZONTAL_GAP_BASE = 360;
const HORIZONTAL_GAP_STEP = 40;
const VERTICAL_GAP = 48;
const ROW_HEIGHT = NODE_HEIGHT + VERTICAL_GAP;
const DEFAULT_TITLE = 'Mind Map';

const BRANCH_COLORS = [
  '#6366f1', '#14b8a6', '#ec4899', '#f97316',
  '#3b82f6', '#a855f7', '#f43f5e', '#22c55e',
];

function toLabel(value, fallback = 'Untitled') {
  if (typeof value !== 'string') return fallback;
  const trimmed = value.trim();
  return trimmed || fallback;
}

function normalizeNode(node) {
  if (typeof node === 'string') {
    return { label: toLabel(node), children: [] };
  }
  if (!node || typeof node !== 'object') {
    return { label: 'Untitled', children: [] };
  }
  const label = toLabel(node.label || node.title || node.name);
  const children = Array.isArray(node.children)
    ? node.children.map(normalizeNode).filter(Boolean)
    : [];
  return { label, children };
}

function normalizeMindMapData(rawData) {
  const source = rawData && typeof rawData === 'object' && rawData.data && typeof rawData.data === 'object'
    ? rawData.data
    : rawData;

  if (!source || typeof source !== 'object') {
    return {
      title: DEFAULT_TITLE,
      sourceCount: 1,
      root: { label: 'Mind Map', children: [] },
    };
  }

  const title = toLabel(source.title || source.label || source.name, DEFAULT_TITLE);
  const sourceCount = Number(
    source.source_count || source.sourceCount || source.material_count || source.materialCount || 1
  ) || 1;

  const rootNode = normalizeNode({
    label: source.label || source.root_label || source.rootLabel || title,
    children: Array.isArray(source.children) ? source.children : [],
  });

  if (rootNode.children.length === 0) {
    rootNode.children = [{ label: 'No branches generated', children: [] }];
  }

  return { title, sourceCount, root: rootNode };
}

function buildTreeLayout(rootData, expandedIds, isDark) {
  if (!rootData) return { nodes: [], edges: [] };

  const nodes = [];
  const edges = [];
  const childrenMap = new Map();
  const nodeById = new Map();
  const depthMap = new Map();

  function processNode(nodeData, parentId, branchIdx, depth, path = 'root') {
    const nodeId = path;
    const isRoot = depth === 0;
    const nodeChildren = nodeData.children || [];
    const hasChildren = nodeChildren.length > 0;
    const isExpanded = expandedIds.has(nodeId);
    const colorIdx = isRoot ? 0 : branchIdx % BRANCH_COLORS.length;

    depthMap.set(nodeId, depth);

    const node = {
      id: nodeId,
      type: 'mindNode',
      data: {
        label: toLabel(nodeData.label || nodeData.title),
        branchIndex: colorIdx,
        hasChildren,
        isExpanded,
        nodeId,
        isRoot,
        depth,
        childCount: nodeChildren.length,
        childLabels: nodeChildren.map(c => toLabel(c.label || c.title)),
        isDark,
      },
      position: { x: 0, y: 0 },
    };

    nodes.push(node);
    nodeById.set(nodeId, node);

    if (parentId !== null) {
      if (!childrenMap.has(parentId)) childrenMap.set(parentId, []);
      childrenMap.get(parentId).push(nodeId);

      edges.push({
        id: `edge-${parentId}-${nodeId}`,
        source: parentId,
        target: nodeId,
        type: 'mindMapEdge',
        data: { depth, sourceDepth: depthMap.get(parentId) || 0 },
        style: {
          stroke: BRANCH_COLORS[colorIdx],
        },
      });
    }

    if (hasChildren && isExpanded) {
      nodeChildren.forEach((child, idx) => {
        processNode(child, nodeId, isRoot ? idx : branchIdx, depth + 1, `${path}-${idx}`);
      });
    }
  }

  processNode(rootData, null, 0, 0, 'root');

  function getLeafCount(nodeId) {
    const ch = childrenMap.get(nodeId) || [];
    if (ch.length === 0) return 1;
    return ch.reduce((sum, cid) => sum + getLeafCount(cid), 0);
  }

  function getSubtreeHeight(nodeId) {
    return getLeafCount(nodeId) * ROW_HEIGHT;
  }

  function getLevelGap(depth) {
    return HORIZONTAL_GAP_BASE + Math.max(0, depth - 1) * HORIZONTAL_GAP_STEP;
  }

  function positionSubtree(nodeId, x, topY, depth = 0) {
    const node = nodeById.get(nodeId);
    if (!node) return;

    const ch = childrenMap.get(nodeId) || [];

    if (ch.length === 0) {
      node.position = { x, y: topY + ROW_HEIGHT / 2 };
      return;
    }

    let cursor = topY;
    ch.forEach(cid => {
      const h = getSubtreeHeight(cid);
      positionSubtree(cid, x + getLevelGap(depth + 1), cursor, depth + 1);
      cursor += h;
    });

    const totalH = getSubtreeHeight(nodeId);
    node.position = { x, y: topY + totalH / 2 };
  }

  const root = nodes.find(n => n.data.isRoot);
  if (root) {
    const rootH = getSubtreeHeight(root.id);
    positionSubtree(root.id, 0, -rootH / 2, 0);
  }

  return { nodes, edges };
}

const MindNode = memo(({ data }) => {
  const toggle = useMindMapStore(s => s.toggleExpand);
  const color = data.isRoot ? '#6b7280' : BRANCH_COLORS[data.branchIndex];
  const isDark = !!data.isDark;

  return (
    <div className="relative flex items-center mindnode-container">
      <Handle type="target" position={Position.Left} style={{ opacity: 0 }} />
      <Handle type="source" position={Position.Right} style={{ opacity: 0 }} />

      <div
        className={`mindnode-card flex items-center gap-2 px-3 py-2 rounded-xl border shadow-lg cursor-pointer transition-colors ${isDark ? 'bg-[#1a1c1e] hover:bg-white/5' : 'bg-white hover:bg-[#f3f6fa]'}`}
        style={{
          borderColor: `${color}50`,
          minWidth: 100,
          maxWidth: NODE_WIDTH,
          minHeight: NODE_HEIGHT,
        }}
      >
        <div
          className="w-2 h-2 rounded-full flex-shrink-0"
          style={{ backgroundColor: color }}
        />
        <span className={`flex-1 text-sm font-medium whitespace-normal break-words leading-relaxed ${isDark ? 'text-white/90' : 'text-[#1b2737]'}`}>
          {data.label}
        </span>
        {data.hasChildren && (
          <button
            onClick={e => { e.stopPropagation(); toggle(data.nodeId); }}
            className={`mindnode-toggle p-1 rounded-lg transition-transform ${isDark ? 'hover:bg-white/10 text-gray-400' : 'hover:bg-slate-200 text-slate-500'}`}
            style={{
              transform: data.isExpanded ? 'rotate(90deg)' : 'rotate(0deg)',
              color: data.isExpanded ? color : undefined
            }}
          >
            <ChevronRight className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
});
MindNode.displayName = 'MindNode';

const nodeTypes = { mindNode: MindNode };
const edgeTypes = { mindMapEdge: MindMapEdge };

function MindMapCanvasInner({
  mindmapData,
  onClose,
  onRate,
  contentId,
  isFullscreen: externalFullscreen,
  onToggleFullscreen,
  savedRating,
}) {
  const normalized = useMemo(() => normalizeMindMapData(mindmapData), [mindmapData]);
  const { resolvedTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const expandedIds = useMindMapStore(s => s.expandedNodeIds);
  const toggle = useMindMapStore(s => s.toggleExpand);
  const setExpandedNodeIds = useMindMapStore(s => s.setExpandedNodeIds);

  const setChatInputValue = useAppStore(s => s.setChatInputValue);
  const setActivePanel = useAppStore(s => s.setActivePanel);
  const submitChatMessage = useAppStore(s => s.submitChatMessage);
  const messages = useChatStore(s => s.messages);
  const isStreaming = useChatStore(s => s.isStreaming);

  const [selectedNode, setSelectedNode] = useState(null);
  const isFirstRender = useRef(true);
  const timersRef = useRef([]);
  const customPositionsRef = useRef(new Map());
  const mapWrapperRef = useRef(null);
  const [isLoading, setIsLoading] = useState(true);
  const [rating, setRating] = useState(savedRating || null);
  const [ratingLoading, setRatingLoading] = useState(false);
  const [isExporting, setIsExporting] = useState(false);

  const isFullscreen = externalFullscreen !== undefined ? externalFullscreen : false;

  useEffect(() => {
    let mounted = true;
    isFirstRender.current = true;
    customPositionsRef.current = new Map();

    const loadTimer = setTimeout(() => {
      if (mounted) {
        setIsLoading(false);
      }
    }, 150);
    timersRef.current.push(loadTimer);

    return () => {
      mounted = false;
      customPositionsRef.current = new Map();
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };
  }, []); // removed setExpandedNodeIds dependencies to avoid reset on every material/notebook change if not intended, but specifically removed the call.

  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(
    () => buildTreeLayout(normalized.root, expandedIds, isDark),
    [normalized.root, expandedIds, isDark]
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutEdges);
  const { fitView, zoomIn, zoomOut, setCenter, getZoom } = useReactFlow();
  const prevExpandedIds = useRef(new Set());

  useEffect(() => {
    return () => {
      timersRef.current.forEach(clearTimeout);
      timersRef.current = [];
    };
  }, []);

  useEffect(() => {
    const mergedNodes = layoutNodes.map((node) => {
      const custom = customPositionsRef.current.get(node.id);
      return custom ? { ...node, position: custom } : node;
    });
    setNodes(mergedNodes);
    setEdges(layoutEdges);
  }, [layoutNodes, layoutEdges, setNodes, setEdges]);

  const handleNodeDragStop = useCallback((_, node) => {
    const newPos = { x: node.position.x, y: node.position.y };
    customPositionsRef.current.set(node.id, newPos);
    setNodes((prev) => prev.map((n) => (n.id === node.id ? { ...n, position: newPos } : n)));
  }, [setNodes]);

  useEffect(() => {
    if (isFirstRender.current) {
      if (layoutNodes.length > 0) {
        const timeoutId = setTimeout(() => {
          fitView({ padding: 0.3, duration: 400 });
          isFirstRender.current = false;
          prevExpandedIds.current = new Set(expandedIds);
        }, 100);
        timersRef.current.push(timeoutId);
      }
      return;
    }

    const addedId = [...expandedIds].find(id => !prevExpandedIds.current.has(id));

    if (addedId) {
      const timeoutId = setTimeout(() => {
        const targetNode = layoutNodes.find(n => n.id === addedId);
        if (targetNode) {
          setCenter(targetNode.position.x + HORIZONTAL_GAP_BASE / 2, targetNode.position.y, {
            duration: 500,
            zoom: Math.max(0.75, getZoom() < 0.5 ? 0.7 : getZoom()),
          });
        }
      }, 50);
      timersRef.current.push(timeoutId);
    }

    prevExpandedIds.current = new Set(expandedIds);
  }, [expandedIds, layoutNodes, setCenter, getZoom, fitView]);

  const explanation = useMemo(() => {
    if (!selectedNode) return null;
    const searchStr = `Explain about ${selectedNode.label}`;
    // Look for the last user message containing our query
    const lastUserIdx = [...messages].reverse().findIndex(m => 
      m.role === 'user' && m.content.toLowerCase().includes(searchStr.toLowerCase())
    );
    if (lastUserIdx === -1) return null;
    
    const actualIdx = messages.length - 1 - lastUserIdx;
    // The next message (if any) should be the assistant's reply
    const assistantMsg = messages.slice(actualIdx + 1).find(m => m.role === 'assistant');
    return assistantMsg ? assistantMsg.content : null;
  }, [messages, selectedNode]);

  const handleDownload = useCallback(async () => {
    if (isExporting) return;
    setIsExporting(true);

    // Select the React Flow viewport element
    const viewportElement = document.querySelector('.react-flow__viewport');
    if (!viewportElement) {
      setIsExporting(false);
      return;
    }

    try {
      // 1. Calculate the bounding box of all nodes
      const nodesBounds = getNodesBounds(nodes);

      // 2. Determine necessary dimensions and transform
      // We want to capture the entire graph, so we find the viewport that fits everything
      const padding = 100; // Extra padding around the graph
      const viewport = getViewportForBounds(
        nodesBounds,
        nodesBounds.width + padding * 2,
        nodesBounds.height + padding * 2,
        0.5, // minZoom (to keep it readable)
        2,   // maxZoom
        padding
      );

      // 3. Render the entire viewport to PNG at high resolution
      const dataUrl = await toPng(viewportElement, {
        backgroundColor: '#0b0c0d',
        width: nodesBounds.width + padding * 2,
        height: nodesBounds.height + padding * 2,
        style: {
          width: `${nodesBounds.width + padding * 2}px`,
          height: `${nodesBounds.height + padding * 2}px`,
          transform: `translate(${-nodesBounds.x + padding}px, ${-nodesBounds.y + padding}px) scale(1)`,
        },
        pixelRatio: 2, // High resolution for readability
      });

      // 4. Create PDF
      const pdf = new jsPDF({
        orientation: nodesBounds.width > nodesBounds.height ? 'l' : 'p',
        unit: 'px',
        format: [nodesBounds.width + padding * 2, nodesBounds.height + padding * 3], // Extra vertical space for title
      });

      const safeTitle = normalized.title || 'Mind Map';

      // Add Title to PDF
      pdf.setTextColor(255, 255, 255);
      pdf.setFillColor(11, 12, 13);
      pdf.rect(0, 0, nodesBounds.width + padding * 2, nodesBounds.height + padding * 3, 'F');

      pdf.setFontSize(36);
      pdf.text(safeTitle, (nodesBounds.width + padding * 2) / 2, padding / 2 + 20, { align: 'center' });

      // Add the Mind Map Image
      pdf.addImage(
        dataUrl,
        'PNG',
        0,
        padding,
        nodesBounds.width + padding * 2,
        nodesBounds.height + padding * 2
      );

      const filename = `${safeTitle.toLowerCase().replace(/[^a-z0-9]+/g, '-')}.pdf`;
      pdf.save(filename);

      console.log(`Mind map exported as PDF: ${filename}`);
    } catch (error) {
      console.error('Failed to export mind map PDF', error);
    } finally {
      setIsExporting(false);
    }
  }, [nodes, normalized.title, isExporting]);

  const handleExpandAll = useCallback(() => {
    if (expandedIds.size > 0) {
      setExpandedNodeIds([]);
      return;
    }
    function collectAllIds(node, path = 'root') {
      const ids = [path];
      if (node.children) {
        node.children.forEach((child, idx) => {
          ids.push(...collectAllIds(child, `${path}-${idx}`));
        });
      }
      return ids;
    }
    setExpandedNodeIds(collectAllIds(normalized.root));
  }, [normalized.root, setExpandedNodeIds, expandedIds.size]);

  const handleRate = useCallback(async (newRating) => {
    if (!contentId || !onRate) return;

    setRatingLoading(true);
    try {
      await onRate(contentId, newRating);
      setRating(newRating);
    } catch (error) {
      console.error('Failed to save rating', error);
    } finally {
      setRatingLoading(false);
    }
  }, [contentId, onRate]);

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === 'Escape' && isFullscreen) {
        onToggleFullscreen?.();
        return;
      }
      if (event.key === '+' || event.key === '=') {
        event.preventDefault();
        zoomIn();
        return;
      }
      if (event.key === '-') {
        event.preventDefault();
        zoomOut();
        return;
      }
      if (event.key === '0') {
        event.preventDefault();
        fitView({ duration: 300 });
      }
    };

    window.addEventListener('keydown', onKeyDown);
    return () => window.removeEventListener('keydown', onKeyDown);
  }, [fitView, zoomIn, zoomOut, isFullscreen, onToggleFullscreen]);

  return (
    <div
      ref={mapWrapperRef}
      className={`relative overflow-hidden transition-all duration-300 ease-in-out ${isFullscreen ? 'h-full flex flex-col' : 'h-full flex flex-col'}`}
      style={{
        background: isDark
          ? 'radial-gradient(circle at center, #1a1c1e 0%, #0b0c0d 100%)'
          : 'radial-gradient(circle at center, #f7fbff 0%, #edf3f8 100%)',
      }}
    >
      {/* Subtle background glow */}
      <div className="absolute inset-0 pointer-events-none opacity-20"
        style={{
          background: isDark
            ? 'radial-gradient(circle at 50% 50%, rgba(99, 102, 241, 0.05) 0%, transparent 70%)'
            : 'radial-gradient(circle at 50% 50%, rgba(16, 185, 129, 0.08) 0%, transparent 70%)'
        }} />
      <header className={`absolute top-3 left-0 right-0 z-[70] flex justify-center px-3 pointer-events-none ${isFullscreen ? 'sm:top-4' : 'top-2'}`}>
        <div
          className={`pointer-events-auto flex items-center justify-between gap-3 border backdrop-blur-xl shadow-2xl ${isFullscreen
            ? 'w-full max-w-4xl rounded-2xl px-4 py-2.5'
            : 'w-full max-w-3xl rounded-xl px-3 py-2'
            }`}
          style={{
            borderColor: isDark ? 'rgba(255,255,255,0.10)' : 'rgba(148,163,184,0.45)',
            background: isDark ? 'rgba(11,12,13,0.86)' : 'rgba(248,252,255,0.9)',
          }}
        >
          <div className={`flex items-center min-w-0 ${isFullscreen ? 'gap-3' : 'gap-2'}`}>
          {!isFullscreen && (
            <button
              onClick={onClose}
              className={`p-1.5 rounded-lg transition-colors border mr-1 ${isDark ? 'hover:bg-white/10 text-gray-400 hover:text-white border-white/5' : 'hover:bg-slate-200 text-slate-500 hover:text-slate-800 border-slate-300/60'}`}
              title="Back to Studio"
            >
              <ArrowLeft className="w-4 h-4" />
            </button>
          )}
            {isFullscreen && <Brain className="w-4 h-4 text-accent" />}
          <div className="flex flex-col min-w-0">
              <h1 className={`font-bold leading-tight truncate ${isFullscreen ? 'text-sm' : 'text-xs'} ${isDark ? 'text-white' : 'text-[#152234]'}`}>
              {normalized.title || DEFAULT_TITLE}
            </h1>
            {isFullscreen && (
                <p className={`text-[11px] font-medium ${isDark ? 'text-gray-400' : 'text-slate-500'}`}>
                {normalized.sourceCount} source{normalized.sourceCount > 1 ? 's' : ''}
              </p>
            )}
          </div>
        </div>

          <div className={`flex items-center gap-1.5 ${isDark ? 'text-gray-400' : 'text-slate-500'} ${isFullscreen ? 'ml-auto' : ''}`}>
          <button
            onClick={handleExpandAll}
            className={`flex items-center gap-1.5 rounded-lg transition-all border ${isDark ? 'border-white/5' : 'border-slate-300/65'} ${isFullscreen
              ? `px-2.5 py-1.5 text-[11px] font-bold ${isDark ? 'hover:bg-white/10 text-gray-300 hover:text-white' : 'hover:bg-slate-200 text-slate-600 hover:text-slate-900'}`
              : `${isDark ? 'p-1.5 hover:bg-white/10' : 'p-1.5 hover:bg-slate-200'}`
              }`}
            title={expandedIds.size > 0 ? "Collapse All" : "Expand All"}
          >
            {expandedIds.size > 0 ? <ChevronsUp className="w-3.5 h-3.5" /> : <ChevronsDown className="w-3.5 h-3.5" />}
          </button>

          <button
            onClick={handleDownload}
            disabled={isExporting}
            className={`rounded-lg transition-all p-1.5 ${isExporting ? 'opacity-50 cursor-not-allowed' : ''} ${isDark ? 'hover:bg-white/5' : 'hover:bg-slate-200'}`}
            title="Download as PDF"
          >
            {isExporting ? (
              <Loader2 className="w-4 h-4 animate-spin" />
            ) : (
              <Download className="w-4 h-4" />
            )}
          </button>

          {isFullscreen && <div className={`w-px h-4 mx-1 ${isDark ? 'bg-white/10' : 'bg-slate-300/80'}`} />}

          <button
            onClick={onToggleFullscreen}
            className={`flex items-center gap-1.5 rounded-lg transition-all border ${isDark ? 'border-white/5' : 'border-slate-300/65'} ${isFullscreen
              ? `${isDark ? 'p-1.5 hover:bg-white/10 text-gray-400 hover:text-white' : 'p-1.5 hover:bg-slate-200 text-slate-500 hover:text-slate-900'}`
              : 'p-1.5 bg-accent/20 text-accent hover:bg-accent/30 hidden sm:flex'
              }`}
            title={isFullscreen ? "Exit Fullscreen" : "Fullscreen"}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>

          {isFullscreen && (
            <button
              onClick={onClose}
                className={`rounded-lg transition-all ${isFullscreen
                  ? `${isDark ? 'p-1.5 hover:bg-red-500/10 text-gray-400 hover:text-red-400' : 'p-1.5 hover:bg-red-50 text-slate-500 hover:text-red-600'}`
                  : `${isDark ? 'p-1.5 hover:bg-white/10 hover:text-white' : 'p-1.5 hover:bg-slate-200 hover:text-slate-900'}`
                }`}
              title="Close"
            >
              <X className="w-4 h-4" />
            </button>
          )}
        </div>
        </div>
      </header>

      <div className="relative flex-1 min-h-0">
        {(isLoading || isExporting) ? (
          <div className="absolute inset-0 flex items-center justify-center z-[200] backdrop-blur-sm"
            style={{ background: isDark ? 'rgba(11,12,13,0.4)' : 'rgba(239,246,255,0.55)' }}>
            <div className="flex flex-col items-center gap-3">
              <Loader2 className={`text-accent animate-spin ${isFullscreen ? 'w-8 h-8' : 'w-6 h-6'}`} />
              <p className={`text-sm font-medium shadow-sm ${isDark ? 'text-white' : 'text-slate-800'}`}>
                {isExporting ? 'Preparing PDF...' : 'Loading...'}
              </p>
            </div>
          </div>
        ) : null}
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onNodeDragStop={handleNodeDragStop}
          nodeTypes={nodeTypes}
          edgeTypes={edgeTypes}
          fitView
          fitViewOptions={{ padding: 0.3 }}
          colorMode={isDark ? 'dark' : 'light'}
          minZoom={0.35}
          maxZoom={2}
          nodesDraggable
          nodesConnectable={false}
          elementsSelectable={false}
          onNodeClick={(_, node) => {
            if (node.data?.hasChildren) toggle(node.id);
            const label = node.data?.label || 'this topic';
            const subtopics = node.data?.childLabels || [];
            
            let query = `Explain about ${label}`;
            if (subtopics.length > 0) {
              query += ` and its sub-topics: ${subtopics.join(', ')}`;
            }
            
            submitChatMessage(query);
            if (isFullscreen && onToggleFullscreen) onToggleFullscreen();
          }}
          proOptions={{ hideAttribution: true }}
        >
          <Background
            variant={BackgroundVariant.Dots}
            gap={isFullscreen ? 24 : 20}
            size={isFullscreen ? 1.5 : 1}
            color={isDark ? '#ffffff10' : '#0f172221'}
          />
          {/* MiniMap removed as per user request */}
        </ReactFlow>

        <div className={`absolute left-6 flex gap-2.5 transition-all ${isFullscreen ? 'bottom-6' : 'bottom-3 left-3'}`}>
          <button
            onClick={() => handleRate('positive')}
            disabled={ratingLoading || rating === 'positive'}
            className={`flex items-center gap-2 rounded-xl text-xs font-bold transition-all backdrop-blur-md border ${isFullscreen ? 'px-4 py-2' : 'px-2 py-1'
              } ${rating === 'positive'
                ? 'bg-green-500/20 text-green-400 border-green-500/40 shadow-lg shadow-green-500/10'
                : `${isDark ? 'bg-white/5 text-gray-400 border-white/5 hover:bg-green-500/10 hover:text-green-400 hover:border-green-500/20' : 'bg-white text-slate-500 border-slate-300/70 hover:bg-green-50 hover:text-green-700 hover:border-green-300'}`
              }`}
          >
            {rating === 'positive' ? <Check className="w-3.5 h-3.5" /> : <ThumbsUp className="w-3.5 h-3.5" />}
            <span className={isFullscreen ? '' : 'hidden'}>Good</span>
          </button>
          <button
            onClick={() => handleRate('negative')}
            disabled={ratingLoading || rating === 'negative'}
            className={`flex items-center gap-2 rounded-xl text-xs font-bold transition-all backdrop-blur-md border ${isFullscreen ? 'px-4 py-2' : 'px-2 py-1'
              } ${rating === 'negative'
                ? 'bg-red-500/20 text-red-400 border-red-500/40 shadow-lg shadow-red-500/10'
                : `${isDark ? 'bg-white/5 text-gray-400 border-white/5 hover:bg-red-500/10 hover:text-red-400 hover:border-red-500/20' : 'bg-white text-slate-500 border-slate-300/70 hover:bg-red-50 hover:text-red-700 hover:border-red-300'}`
              }`}
          >
            {rating === 'negative' ? <Check className="w-3.5 h-3.5" /> : <ThumbsDown className="w-3.5 h-3.5" />}
            <span className={isFullscreen ? '' : 'hidden'}>Bad</span>
          </button>
        </div>

        <div
          className={`absolute right-6 flex flex-col gap-1 p-1 rounded-2xl border backdrop-blur-xl shadow-2xl transition-all ${isFullscreen ? 'bottom-6' : 'bottom-3 right-3'
            }`}
          style={{
            borderColor: isDark ? 'rgba(255,255,255,0.1)' : 'rgba(148,163,184,0.55)',
            background: isDark ? 'rgba(26,28,30,0.6)' : 'rgba(255,255,255,0.92)',
          }}
        >
          <button
            onClick={() => fitView({ duration: 300 })}
            className={`${isFullscreen ? 'p-2.5' : 'p-2'} rounded-xl transition-all ${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200'}`}
            title="Reset View"
          >
            <Target className="w-4 h-4" />
          </button>
          <div className={`h-px mx-2 ${isDark ? 'bg-white/10' : 'bg-slate-300/80'}`} />
          <button
            onClick={() => zoomIn()}
            className={`${isFullscreen ? 'p-2.5' : 'p-2'} rounded-xl transition-all ${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200'}`}
            title="Zoom In"
          >
            <Plus className="w-4 h-4" />
          </button>
          <button
            onClick={() => zoomOut()}
            className={`${isFullscreen ? 'p-2.5' : 'p-2'} rounded-xl transition-all ${isDark ? 'text-gray-400 hover:text-white hover:bg-white/5' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-200'}`}
            title="Zoom Out"
          >
            <Minus className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}

export default function MindMapCanvas(props) {
  return (
    <ReactFlowProvider>
      <MindMapCanvasInner {...props} />
    </ReactFlowProvider>
  );
}

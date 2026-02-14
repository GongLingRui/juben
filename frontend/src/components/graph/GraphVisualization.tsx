/**
 * 图数据库可视化组件
 * Graph Database Visualization Component
 *
 * 使用 react-force-graph 实现交互式图谱可视化
 */

import { useEffect, useRef, useState, useCallback } from 'react';
import ForceGraph2D from 'react-force-graph-2d';
import type { GraphData, NodeObject, LinkObject } from 'react-force-graph-2d';
import { forceRadial, forceX, forceY } from 'd3-force';
import { useGraphStore } from '@/store/graphStore';
import { GraphToolbar } from './GraphToolbar';
import { GraphNodeDetail } from './GraphNodeDetail';
import { GraphStatistics } from './GraphStatistics';
import { GraphFilter } from './GraphFilter';
import type { NodeType, RelationType } from '@/services/graphService';
import { Loading } from '@/components/common';

interface GraphVisualizationProps {
  className?: string;
  height?: string | number;
}

// 节点颜色配置
const NODE_COLORS: Record<NodeType, string> = {
  Story: '#475569', // slate-600
  Character: '#6366f1', // indigo-500
  PlotNode: '#10b981', // emerald-500
  WorldRule: '#f59e0b', // amber-500
  Location: '#8b5cf6', // violet-500
  Item: '#ec4899', // pink-500
  Conflict: '#ef4444', // red-500
  Theme: '#06b6d4', // cyan-500
  Motivation: '#f97316', // orange-500
};

// 节点大小配置
const NODE_SIZES: Record<NodeType, number> = {
  Story: 18,
  Character: 15,
  PlotNode: 12,
  WorldRule: 10,
  Location: 8,
  Item: 6,
  Conflict: 10,
  Theme: 8,
  Motivation: 8,
};

// 关系颜色配置
const LINK_COLORS: Record<RelationType, string> = {
  SOCIAL_BOND: '#6366f1',
  FAMILY_RELATION: '#7c3aed',
  ROMANTIC_RELATION: '#ec4899',
  INFLUENCES: '#10b981',
  LEADS_TO: '#22c55e',
  NEXT: '#f59e0b',
  RESOLVES: '#0ea5e9',
  COMPLICATES: '#f97316',
  INVOLVED_IN: '#8b5cf6',
  DRIVEN_BY: '#ec4899',
  CONTAINS: '#14b8a6',
  VIOLATES: '#ef4444',
  ENFORCES: '#f59e0b',
  LOCATED_IN: '#06b6d4',
  LOCATED_AT: '#06b6d4',
  OWNS: '#f97316',
  PART_OF: '#14b8a6',
  REPRESENTS: '#a855f7',
  OPPOSES: '#f43f5e',
  SUPPORTS: '#22c55e',
};

export function GraphVisualization({ className = '', height = '100%' }: GraphVisualizationProps) {
  const graphRef = useRef<any>();
  const [filterOpen, setFilterOpen] = useState(false);
  const [detailOpen, setDetailOpen] = useState(false);
  const [zoom, setZoom] = useState(1);

  const {
    nodes,
    relationships,
    statistics,
    loading,
    error,
    selectedNodeId,
    filter,
    viewMode,
    setSelectedNodeId,
    loadStoryElements,
    loadStatistics,
    setViewMode,
  } = useGraphStore();

  // 转换数据为 force-graph 格式
  const graphData = useCallback((): GraphData => {
    // 根据过滤器筛选节点
    const filteredNodes = nodes.filter((node) => {
      if (filter.nodeTypes.length > 0 && !filter.nodeTypes.includes(node.type as NodeType)) {
        return false;
      }
      if (filter.searchQuery) {
        const query = filter.searchQuery.toLowerCase();
        return (
          node.properties.name?.toLowerCase().includes(query) ||
          node.properties.title?.toLowerCase().includes(query) ||
          node.properties.description?.toLowerCase().includes(query)
        );
      }
      return true;
    });

    const nodeIds = new Set(filteredNodes.map((n) => n.id));

    // 根据过滤器筛选关系
    const filteredLinks = relationships.filter((link) => {
      if (filter.relationTypes.length > 0 && !filter.relationTypes.includes(link.type as RelationType)) {
        return false;
      }
      return nodeIds.has(link.source) && nodeIds.has(link.target);
    });

    // 转换为 force-graph 格式
    const nodesData: NodeObject[] = filteredNodes.map((node) => ({
      id: node.id,
      name: node.properties.name || node.properties.title || node.id,
      type: node.type,
      ...node.properties,
      color: NODE_COLORS[node.type as NodeType] || '#94a3b8',
      size: NODE_SIZES[node.type as NodeType] || 10,
    }));

    const linksData: LinkObject[] = filteredLinks.map((link) => ({
      id: link.id,
      source: link.source,
      target: link.target,
      type: link.type,
      color: LINK_COLORS[link.type as RelationType] || '#cbd5e1',
      ...link.properties,
    }));

    return { nodes: nodesData, links: linksData };
  }, [nodes, relationships, filter]);

  useEffect(() => {
    if (!selectedNodeId) return;
    const node = nodes.find((n) => n.id === selectedNodeId);
    if (node && graphRef.current) {
      const graphNodes = graphData().nodes as any[];
      const found = graphNodes.find((n) => n.id === selectedNodeId);
      if (found) {
        setDetailOpen(true);
        graphRef.current.centerAt(found.x, found.y, 300);
        graphRef.current.zoom(1.6, 300);
        setZoom(1.6);
      }
    }
  }, [selectedNodeId, nodes, graphData]);

  // 处理节点点击
  const handleNodeClick = useCallback(
    (node: any) => {
      setSelectedNodeId(node.id);
      setDetailOpen(true);

      // 高亮选中节点
      if (graphRef.current) {
        graphRef.current.centerAt(node.x, node.y, 300);
        graphRef.current.zoom(1.5, 300);
        setZoom(1.5);
      }
    },
    [setSelectedNodeId]
  );

  // 处理背景点击
  const handleBackgroundClick = useCallback(() => {
    setSelectedNodeId(null);
    setDetailOpen(false);
  }, [setSelectedNodeId]);

  // 处理节点右键点击
  const handleNodeRightClick = useCallback((node: any, event: MouseEvent) => {
    // 阻止默认菜单
    event?.preventDefault();

    // 聚焦到节点
    if (graphRef.current) {
      graphRef.current.centerAt(node.x, node.y, 300);
      graphRef.current.zoom(2, 300);
    }
  }, []);

  // 刷新数据
  const handleRefresh = useCallback(async () => {
    const { currentStoryId } = useGraphStore.getState();
    if (currentStoryId) {
      await loadStoryElements(currentStoryId);
      await loadStatistics(currentStoryId);
    }
  }, [loadStoryElements, loadStatistics]);

  // 导出图像
  const handleExportImage = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.downloadImage('graph', 'image/png', {
        backgroundColor: '#ffffff',
        pixelRatio: 2,
      });
    }
  }, []);

  // 重置视图
  const handleResetView = useCallback(() => {
    if (graphRef.current) {
      graphRef.current.zoom(1, 300);
      graphRef.current.centerAt(0, 0, 300);
      setZoom(1);
    }
  }, []);

  const handleZoomIn = useCallback(() => {
    const nextZoom = Math.min(zoom + 0.2, 3);
    setZoom(nextZoom);
    if (graphRef.current) {
      graphRef.current.zoom(nextZoom, 200);
    }
  }, [zoom]);

  const handleZoomOut = useCallback(() => {
    const nextZoom = Math.max(zoom - 0.2, 0.2);
    setZoom(nextZoom);
    if (graphRef.current) {
      graphRef.current.zoom(nextZoom, 200);
    }
  }, [zoom]);

  // 初始加载
  useEffect(() => {
    const { currentStoryId } = useGraphStore.getState();
    if (currentStoryId) {
      loadStoryElements(currentStoryId);
      loadStatistics(currentStoryId);
    }
  }, [loadStoryElements, loadStatistics]);

  // 视图模式切换
  useEffect(() => {
    if (!graphRef.current) return;

    if (viewMode === 'force') {
      graphRef.current.d3Force('radial', null);
      graphRef.current.d3Force('x', null);
      graphRef.current.d3Force('y', null);
    } else if (viewMode === 'radial') {
      graphRef.current.d3Force(
        'radial',
        forceRadial((node: any) => {
          if (node.type === 'PlotNode') return 60;
          if (node.type === 'Character') return 140;
          return 220;
        }, 0, 0).strength(0.9)
      );
    } else if (viewMode === 'circle') {
      graphRef.current.d3Force('radial', forceRadial(180, 0, 0).strength(1));
    } else if (viewMode === 'tree') {
      graphRef.current.d3Force(
        'x',
        forceX((node: any) => {
          if (node.type === 'Character') return -200;
          if (node.type === 'PlotNode') return 0;
          return 200;
        }).strength(0.6)
      );
      graphRef.current.d3Force(
        'y',
        forceY((node: any) => {
          if (node.type === 'PlotNode') return 0;
          return node.type === 'Character' ? -80 : 80;
        }).strength(0.4)
      );
    }

    graphRef.current.d3ReheatSimulation();
  }, [viewMode]);

  // 错误状态
  if (error) {
    return (
      <div className={`flex items-center justify-center bg-red-50 ${className}`} style={{ height }}>
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-red-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-red-800">加载失败</h3>
          <p className="mt-1 text-sm text-red-600">{error}</p>
          <button
            onClick={handleRefresh}
            className="mt-4 inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-red-700 bg-red-100 hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500"
          >
            重试
          </button>
        </div>
      </div>
    );
  }

  // 加载状态
  if (loading && nodes.length === 0) {
    return (
      <div className={`flex items-center justify-center ${className}`} style={{ height }}>
        <Loading size="lg" text="加载中..." />
      </div>
    );
  }

  // 空状态
  if (nodes.length === 0 && !loading) {
    return (
      <div className={`flex items-center justify-center bg-gray-50 ${className}`} style={{ height }}>
        <div className="text-center">
          <svg
            className="mx-auto h-12 w-12 text-gray-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              strokeWidth={2}
              d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"
            />
          </svg>
          <h3 className="mt-2 text-sm font-medium text-gray-900">暂无数据</h3>
          <p className="mt-1 text-sm text-gray-500">请先选择一个故事或创建节点</p>
        </div>
      </div>
    );
  }

  return (
    <div className={`relative flex flex-col ${className}`} style={{ height }}>
      {/* 工具栏 */}
      <GraphToolbar
        onRefresh={handleRefresh}
        onExportImage={handleExportImage}
        onResetView={handleResetView}
        onZoomIn={handleZoomIn}
        onZoomOut={handleZoomOut}
        onOpenFilter={() => setFilterOpen(true)}
        viewMode={viewMode}
        onViewModeChange={setViewMode}
        loading={loading}
        zoom={zoom}
      />

      {/* 过滤器面板 */}
      {filterOpen && <GraphFilter onClose={() => setFilterOpen(false)} />}

      {/* 图谱可视化 */}
      <div className="flex-1 relative">
        <ForceGraph2D
          ref={graphRef}
          graphData={graphData()}
          nodeLabel="name"
          nodeColor={(node: any) => node.color}
          nodeVal={(node: any) => node.size || 10}
          linkColor={(link: any) => link.color || '#cbd5e1'}
          linkWidth={2}
          linkDirectionalParticles={2}
          linkDirectionalParticleWidth={3}
          onNodeClick={handleNodeClick}
          onBackgroundClick={handleBackgroundClick}
          onNodeRightClick={handleNodeRightClick}
          cooldownTicks={100}
          d3AlphaDecay={0.02}
          d3VelocityDecay={0.3}
          enableNodeDrag
          enableZoomPanInteraction
          enablePanInteraction
          width={undefined}
          height={undefined}
        />
      </div>

      {/* 统计信息 */}
      {statistics && <GraphStatistics statistics={statistics} />}

      {/* 节点详情面板 */}
      {detailOpen && selectedNodeId && (
        <GraphNodeDetail nodeId={selectedNodeId} onClose={() => setDetailOpen(false)} />
      )}
    </div>
  );
}

export default GraphVisualization;

/**
 * 图谱过滤器组件
 * Graph Filter Component
 */

import { useState, useEffect } from 'react';
import { X, Check } from 'lucide-react';
import { useGraphStore } from '@/store/graphStore';
import type { NodeType, RelationType } from '@/services/graphService';

interface GraphFilterProps {
  onClose: () => void;
}

const NODE_TYPES: { value: NodeType; label: string; color: string }[] = [
  { value: 'Story', label: '故事', color: 'bg-slate-600' },
  { value: 'Character', label: '角色', color: 'bg-indigo-500' },
  { value: 'PlotNode', label: '情节', color: 'bg-emerald-500' },
  { value: 'WorldRule', label: '世界观', color: 'bg-amber-500' },
  { value: 'Location', label: '地点', color: 'bg-violet-500' },
  { value: 'Item', label: '物品', color: 'bg-pink-500' },
  { value: 'Conflict', label: '冲突', color: 'bg-red-500' },
  { value: 'Theme', label: '主题', color: 'bg-cyan-500' },
  { value: 'Motivation', label: '动机', color: 'bg-orange-500' },
];

const DEFAULT_RELATION_TYPES: { value: RelationType; label: string }[] = [
  { value: 'SOCIAL_BOND', label: '社交关系' },
  { value: 'FAMILY_RELATION', label: '家庭关系' },
  { value: 'ROMANTIC_RELATION', label: '情感关系' },
  { value: 'INFLUENCES', label: '影响' },
  { value: 'LEADS_TO', label: '导致' },
  { value: 'NEXT', label: '后续' },
  { value: 'RESOLVES', label: '解决' },
  { value: 'COMPLICATES', label: '复杂化' },
  { value: 'INVOLVED_IN', label: '参与' },
  { value: 'DRIVEN_BY', label: '驱动' },
  { value: 'CONTAINS', label: '包含' },
  { value: 'VIOLATES', label: '违反' },
  { value: 'ENFORCES', label: '强制' },
  { value: 'LOCATED_IN', label: '位于' },
  { value: 'LOCATED_AT', label: '位置' },
  { value: 'OWNS', label: '拥有' },
  { value: 'PART_OF', label: '属于' },
  { value: 'REPRESENTS', label: '代表' },
  { value: 'OPPOSES', label: '反对' },
  { value: 'SUPPORTS', label: '支持' },
];

export function GraphFilter({ onClose }: GraphFilterProps) {
  const { filter, setFilter, relationTypeOptions } = useGraphStore();
  const [localFilter, setLocalFilter] = useState({
    nodeTypes: [...filter.nodeTypes],
    relationTypes: [...filter.relationTypes],
    searchQuery: filter.searchQuery,
  });

  useEffect(() => {
    setLocalFilter({
      nodeTypes: [...filter.nodeTypes],
      relationTypes: [...filter.relationTypes],
      searchQuery: filter.searchQuery,
    });
  }, [filter]);

  const handleNodeTypeToggle = (nodeType: NodeType) => {
    setLocalFilter((prev) => {
      const newTypes = prev.nodeTypes.includes(nodeType)
        ? prev.nodeTypes.filter((t) => t !== nodeType)
        : [...prev.nodeTypes, nodeType];
      return { ...prev, nodeTypes: newTypes };
    });
  };

  const handleRelationTypeToggle = (relationType: RelationType) => {
    setLocalFilter((prev) => {
      const newTypes = prev.relationTypes.includes(relationType)
        ? prev.relationTypes.filter((t) => t !== relationType)
        : [...prev.relationTypes, relationType];
      return { ...prev, relationTypes: newTypes };
    });
  };

  const handleApply = () => {
    setFilter(localFilter);
    onClose();
  };

  const handleReset = () => {
    setFilter({
      nodeTypes: [],
      relationTypes: [],
      searchQuery: '',
    });
    onClose();
  };

  const isNodeTypeSelected = (nodeType: NodeType) => localFilter.nodeTypes.includes(nodeType);
  const isRelationTypeSelected = (relationType: RelationType) =>
    localFilter.relationTypes.includes(relationType);
  const hasSelection =
    localFilter.nodeTypes.length > 0 ||
    localFilter.relationTypes.length > 0 ||
    localFilter.searchQuery.length > 0;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-start justify-end z-50">
      <div className="w-80 bg-white h-full shadow-xl overflow-y-auto">
        {/* 头部 */}
        <div className="sticky top-0 bg-white border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">过滤器</h2>
          <button
            onClick={onClose}
            className="p-1 rounded-md hover:bg-gray-100 transition-colors"
            title="关闭"
          >
            <X className="w-5 h-5 text-gray-500" />
          </button>
        </div>

        {/* 内容 */}
        <div className="px-6 py-4 space-y-6">
          {/* 搜索框 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">搜索节点</label>
            <input
              type="text"
              value={localFilter.searchQuery}
              onChange={(e) =>
                setLocalFilter((prev) => ({ ...prev, searchQuery: e.target.value }))
              }
              placeholder="搜索名称、标题或描述..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-transparent text-sm"
            />
          </div>

          {/* 节点类型过滤 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">节点类型</label>
              {localFilter.nodeTypes.length > 0 && (
                <button
                  onClick={() => setLocalFilter((prev) => ({ ...prev, nodeTypes: [] }))}
                  className="text-xs text-indigo-600 hover:text-indigo-700"
                >
                  清除
                </button>
              )}
            </div>
            <div className="space-y-2">
              {NODE_TYPES.map(({ value, label, color }) => (
                <button
                  key={value}
                  onClick={() => handleNodeTypeToggle(value)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border transition-colors ${
                    isNodeTypeSelected(value)
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <span className={`w-3 h-3 rounded-full ${color}`} />
                    <span className="text-sm text-gray-700">{label}</span>
                  </div>
                  {isNodeTypeSelected(value) && (
                    <Check className="w-4 h-4 text-indigo-600" />
                  )}
                </button>
              ))}
            </div>
          </div>

          {/* 关系类型过滤 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="block text-sm font-medium text-gray-700">关系类型</label>
              {localFilter.relationTypes.length > 0 && (
                <button
                  onClick={() => setLocalFilter((prev) => ({ ...prev, relationTypes: [] }))}
                  className="text-xs text-indigo-600 hover:text-indigo-700"
                >
                  清除
                </button>
              )}
            </div>
            <div className="space-y-2">
              {(relationTypeOptions.length > 0 ? relationTypeOptions : DEFAULT_RELATION_TYPES).map(
                ({ value, label }) => (
                <button
                  key={value}
                  onClick={() => handleRelationTypeToggle(value)}
                  className={`w-full flex items-center justify-between px-3 py-2 rounded-lg border transition-colors ${
                    isRelationTypeSelected(value)
                      ? 'border-indigo-500 bg-indigo-50'
                      : 'border-gray-200 hover:bg-gray-50'
                  }`}
                >
                  <span className="text-sm text-gray-700">{label}</span>
                  {isRelationTypeSelected(value) && (
                    <Check className="w-4 h-4 text-indigo-600" />
                  )}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* 底部操作按钮 */}
        <div className="sticky bottom-0 bg-white border-t border-gray-200 px-6 py-4">
          <div className="flex space-x-2">
            <button
              onClick={handleReset}
              disabled={!hasSelection}
              className={`flex-1 px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg transition-colors ${
                hasSelection
                  ? 'text-gray-700 hover:bg-gray-50'
                  : 'text-gray-400 cursor-not-allowed'
              }`}
            >
              重置
            </button>
            <button
              onClick={handleApply}
              className="flex-1 px-4 py-2 text-sm font-medium text-white bg-indigo-600 rounded-lg hover:bg-indigo-700 transition-colors"
            >
              应用
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

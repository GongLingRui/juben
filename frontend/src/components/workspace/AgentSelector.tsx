/**
 * Agent 选择器组件
 * 顶部下拉菜单，用于切换当前对话的 Agent
 */

import { useState, useRef, useEffect } from 'react';
import { ChevronDown, Bot } from 'lucide-react';
import { clsx } from 'clsx';
import { useAgentStore } from '@/store/agentStore';

interface AgentSelectorProps {
  /** 当前选中的 Agent ID */
  value: string;
  /** 选择变更回调 */
  onChange: (agentId: string) => void;
  /** 是否禁用 */
  disabled?: boolean;
}

export default function AgentSelector({
  value,
  onChange,
  disabled = false,
}: AgentSelectorProps) {
  const { agents } = useAgentStore();
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // 获取当前选中的 Agent 信息
  const currentAgent = agents.find((a) => a.id === value);

  // 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleSelect = (agentId: string) => {
    onChange(agentId);
    setIsOpen(false);
  };

  // 根据 category 获取颜色
  const getCategoryColor = (category: string) => {
    const colors: Record<string, string> = {
      planning: 'bg-blue-100 text-blue-700',
      creation: 'bg-purple-100 text-purple-700',
      evaluation: 'bg-orange-100 text-orange-700',
      analysis: 'bg-green-100 text-green-700',
      workflow: 'bg-cyan-100 text-cyan-700',
      character: 'bg-pink-100 text-pink-700',
      story: 'bg-indigo-100 text-indigo-700',
      utility: 'bg-gray-100 text-gray-700',
    };
    return colors[category] || 'bg-gray-100 text-gray-700';
  };

  return (
    <div ref={dropdownRef} className="relative">
      {/* 触发按钮 */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled}
        className={clsx(
          'flex items-center gap-2 px-4 py-2 rounded-lg',
          'bg-white border border-gray-200',
          'hover:border-gray-300 hover:shadow-sm',
          'transition-all duration-200',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      >
        {/* 当前 Agent 的 emoji 图标 */}
        <span className="text-lg">
          {currentAgent?.icon || <Bot className="w-5 h-5 text-blue-600" />}
        </span>
        <span className="font-medium text-gray-900">
          {currentAgent?.displayName || '选择 Agent'}
        </span>
        <ChevronDown
          className={clsx(
            'w-4 h-4 text-gray-400 transition-transform',
            isOpen && 'transform rotate-180'
          )}
        />
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div className="absolute top-full left-0 mt-2 w-80 bg-white rounded-lg shadow-lg border border-gray-200 z-50">
          {/* Agent 列表 */}
          <div className="max-h-96 overflow-y-auto py-2">
            {agents.map((agent) => (
              <button
                key={agent.id}
                type="button"
                onClick={() => handleSelect(agent.id)}
                className={clsx(
                  'w-full flex items-start gap-3 px-4 py-3',
                  'hover:bg-gray-50 transition-colors',
                  'text-left'
                )}
              >
                {/* Agent 图标 (emoji) */}
                <span className="text-2xl flex-shrink-0">
                  {agent.icon}
                </span>

                {/* Agent 信息 */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-gray-900 text-sm">
                      {agent.displayName}
                    </span>
                    {agent.id === value && (
                      <span className="px-1.5 py-0.5 text-xs bg-blue-100 text-blue-700 rounded-full">
                        当前
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-1">
                    {agent.description}
                  </p>
                  {/* 分类标签 */}
                  <span
                    className={clsx(
                      'inline-block mt-1 px-2 py-0.5 text-xs rounded',
                      getCategoryColor(agent.category)
                    )}
                  >
                    {agent.category}
                  </span>
                </div>
              </button>
            ))}

            {agents.length === 0 && (
              <div className="px-4 py-8 text-center text-gray-400 text-sm">
                暂无可用 Agent
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

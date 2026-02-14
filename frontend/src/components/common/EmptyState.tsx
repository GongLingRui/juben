/**
 * 空状态组件
 * 用于展示无数据、无搜索结果等场景
 */

import React from 'react';
import { LucideIcon } from 'lucide-react';

interface EmptyStateProps {
  /** 图标组件 */
  icon?: LucideIcon;
  /** 标题 */
  title: string;
  /** 描述 */
  description?: string;
  /** 主要操作按钮文本 */
  actionText?: string;
  /** 主要操作回调 */
  onAction?: () => void;
  /** 次要操作按钮文本 */
  secondaryActionText?: string;
  /** 次要操作回调 */
  onSecondaryAction?: () => void;
  /** 自定义类名 */
  className?: string;
  /** 大小 */
  size?: 'sm' | 'md' | 'lg';
  /** 类型 */
  type?: 'default' | 'search' | 'error' | 'success';
}

export function EmptyState({
  icon: Icon,
  title,
  description,
  actionText,
  onAction,
  secondaryActionText,
  onSecondaryAction,
  className = '',
  size = 'md',
  type = 'default',
}: EmptyStateProps) {
  const sizeClasses = {
    sm: 'p-6',
    md: 'p-8',
    lg: 'p-12',
  };

  const iconSizes = {
    sm: 'w-10 h-10',
    md: 'w-16 h-16',
    lg: 'w-24 h-24',
  };

  const typeStyles = {
    default: 'text-gray-400',
    search: 'text-blue-400',
    error: 'text-red-400',
    success: 'text-green-400',
  };

  return (
    <div className={`flex flex-col items-center justify-center text-center ${sizeClasses[size]} ${className}`}>
      {Icon && (
        <Icon className={`${iconSizes[size]} ${typeStyles[type]} mb-4 mx-auto`} />
      )}

      <h3 className={`font-semibold text-gray-900 mb-2 ${size === 'sm' ? 'text-base' : size === 'md' ? 'text-lg' : 'text-xl'}`}>
        {title}
      </h3>

      {description && (
        <p className={`text-gray-500 mb-6 max-w-sm ${size === 'sm' ? 'text-sm' : 'text-base'}`}>
          {description}
        </p>
      )}

      {(actionText || secondaryActionText) && (
        <div className="flex items-center gap-3">
          {actionText && (
            <button
              onClick={onAction}
              className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors font-medium"
            >
              {actionText}
            </button>
          )}
          {secondaryActionText && (
            <button
              onClick={onSecondaryAction}
              className="px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium"
            >
              {secondaryActionText}
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * 预设的空状态变体
 */
export function EmptyStateNoData({ onAction }: { onAction?: () => void }) {
  return (
    <EmptyState
      icon={require('lucide-react').Database}
      title="暂无数据"
      description="还没有任何数据，开始创建吧"
      actionText="创建数据"
      onAction={onAction}
    />
  );
}

export function EmptyStateNoResults({ onClear }: { onClear?: () => void }) {
  return (
    <EmptyState
      icon={require('lucide-react').Search}
      title="未找到结果"
      description="尝试调整搜索关键词或筛选条件"
      actionText="清除筛选"
      onAction={onClear}
      type="search"
    />
  );
}

export function EmptyStateNoSelection() {
  return (
    <EmptyState
      icon={require('lucide-react').MousePointerClick}
      title="未选择任何项目"
      description="从列表中选择一个项目查看详情"
      size="sm"
    />
  );
}

export function EmptyStateError({ onRetry }: { onRetry?: () => void }) {
  return (
    <EmptyState
      icon={require('lucide-react').AlertCircle}
      title="出错了"
      description="加载数据时出现问题，请稍后重试"
      actionText="重试"
      onAction={onRetry}
      type="error"
    />
  );
}

export function EmptyStateNoMessages({ onNewChat }: { onNewChat?: () => void }) {
  return (
    <EmptyState
      icon={require('lucide-react').MessageSquare}
      title="开始新对话"
      description="选择一个 Agent 并输入消息开始对话"
      actionText="开始对话"
      onAction={onNewChat}
    />
  );
}

export function EmptyStateNoProjects({ onCreate }: { onCreate?: () => void }) {
  return (
    <EmptyState
      icon={require('lucide-react').FolderOpen}
      title="还没有项目"
      description="创建你的第一个项目来开始工作"
      actionText="创建项目"
      onAction={onCreate}
    />
  );
}

export function EmptyStateNoFiles({ onUpload }: { onUpload?: () => void }) {
  return (
    <EmptyState
      icon={require('lucide-react').FileText}
      title="文件夹为空"
      description="上传文件开始协作"
      actionText="上传文件"
      onAction={onUpload}
    />
  );
}

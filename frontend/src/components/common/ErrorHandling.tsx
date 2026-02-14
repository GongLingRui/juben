/**
 * 错误处理组件
 * 提供错误展示和重试机制
 */

import React from 'react';
import { AlertCircle, RefreshCw, X, Home, ArrowLeft, Bug } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export interface ErrorInfo {
  /** 错误类型 */
  type?: 'network' | 'validation' | 'auth' | 'notFound' | 'server' | 'unknown';
  /** 错误消息 */
  message: string;
  /** 错误详情 */
  details?: string;
  /** 错误代码 */
  code?: string | number;
  /** 是否可以重试 */
  retryable?: boolean;
}

/**
 * 错误提示卡片
 */
interface ErrorCardProps {
  error: ErrorInfo | string;
  /** 重试回调 */
  onRetry?: () => void;
  /** 是否正在重试 */
  isRetrying?: boolean;
  /** 自定义类名 */
  className?: string;
  /** 是否可关闭 */
  dismissible?: boolean;
  /** 关闭回调 */
  onDismiss?: () => void;
  /** 显示详情 */
  showDetails?: boolean;
  /** 操作按钮 */
  actions?: React.ReactNode;
}

export function ErrorCard({
  error,
  onRetry,
  isRetrying = false,
  className = '',
  dismissible = false,
  onDismiss,
  showDetails = false,
  actions,
}: ErrorCardProps) {
  const errorInfo: ErrorInfo = typeof error === 'string' ? { message: error } : error;

  const getErrorType = () => {
    switch (errorInfo.type) {
      case 'network':
        return { icon: AlertCircle, color: 'text-orange-500', bg: 'bg-orange-50', border: 'border-orange-200' };
      case 'validation':
        return { icon: AlertCircle, color: 'text-yellow-500', bg: 'bg-yellow-50', border: 'border-yellow-200' };
      case 'auth':
        return { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-200' };
      case 'notFound':
        return { icon: AlertCircle, color: 'text-gray-500', bg: 'bg-gray-50', border: 'border-gray-200' };
      case 'server':
        return { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-200' };
      default:
        return { icon: AlertCircle, color: 'text-red-500', bg: 'bg-red-50', border: 'border-red-200' };
    }
  };

  const { icon: ErrorIcon, color, bg, border } = getErrorType();

  return (
    <div className={`${bg} ${border} border rounded-lg p-4 ${className}`}>
      <div className="flex items-start gap-3">
        <ErrorIcon className={`w-5 h-5 ${color} flex-shrink-0 mt-0.5`} />

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between">
            <p className="text-sm font-medium text-gray-900">{errorInfo.message}</p>

            {dismissible && (
              <button
                onClick={onDismiss}
                className="ml-2 text-gray-400 hover:text-gray-600 transition-colors"
              >
                <X className="w-4 h-4" />
              </button>
            )}
          </div>

          {showDetails && errorInfo.details && (
            <p className="text-sm text-gray-600 mt-1">{errorInfo.details}</p>
          )}

          {errorInfo.code && (
            <p className="text-xs text-gray-500 mt-1">错误代码: {errorInfo.code}</p>
          )}

          <div className="flex items-center gap-2 mt-3">
            {errorInfo.retryable && onRetry && (
              <button
                onClick={onRetry}
                disabled={isRetrying}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm font-medium text-white bg-blue-600 rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
              >
                <RefreshCw className={`w-3 h-3 ${isRetrying ? 'animate-spin' : ''}`} />
                {isRetrying ? '重试中...' : '重试'}
              </button>
            )}

            {actions}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 错误页面组件
 */
interface ErrorPageProps {
  error: ErrorInfo;
  /** 重试回调 */
  onRetry?: () => void;
  /** 返回首页 */
  showHomeButton?: boolean;
  /** 返回上一页 */
  showBackButton?: boolean;
  /** 自定义操作按钮 */
  actions?: React.ReactNode;
}

export function ErrorPage({
  error,
  onRetry,
  showHomeButton = true,
  showBackButton = false,
  actions,
}: ErrorPageProps) {
  const navigate = useNavigate();

  const getErrorConfig = () => {
    switch (error.type) {
      case 'network':
        return {
          title: '网络连接失败',
          description: '请检查您的网络连接后重试',
          illustration: '🌐',
        };
      case 'validation':
        return {
          title: '输入验证失败',
          description: '请检查您的输入是否正确',
          illustration: '✓',
        };
      case 'auth':
        return {
          title: '权限不足',
          description: '您没有访问此页面的权限',
          illustration: '🔒',
        };
      case 'notFound':
        return {
          title: '页面未找到',
          description: '您访问的页面不存在',
          illustration: '🔍',
        };
      case 'server':
        return {
          title: '服务器错误',
          description: '服务器遇到了问题，请稍后重试',
          illustration: '⚠️',
        };
      default:
        return {
          title: '发生错误',
          description: '应用程序遇到了意外错误',
          illustration: '❌',
        };
    }
  };

  const config = getErrorConfig();

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
      <div className="max-w-md w-full bg-white rounded-lg shadow-lg p-8 text-center">
        <div className="text-6xl mb-4">{config.illustration}</div>

        <h1 className="text-2xl font-bold text-gray-900 mb-2">{config.title}</h1>

        <p className="text-gray-600 mb-4">{config.description}</p>

        {error.message && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 mb-6">
            <p className="text-sm text-red-800">{error.message}</p>
            {error.details && <p className="text-xs text-red-600 mt-1">{error.details}</p>}
          </div>
        )}

        <div className="flex flex-col sm:flex-row items-center justify-center gap-3">
          {error.retryable && onRetry && (
            <button
              onClick={onRetry}
              className="w-full sm:w-auto px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors font-medium"
            >
              重试
            </button>
          )}

          {showBackButton && (
            <button
              onClick={() => navigate(-1)}
              className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium flex items-center justify-center gap-2"
            >
              <ArrowLeft className="w-4 h-4" />
              返回上一页
            </button>
          )}

          {showHomeButton && (
            <button
              onClick={() => navigate('/')}
              className="w-full sm:w-auto px-4 py-2 border border-gray-300 text-gray-700 rounded-lg hover:bg-gray-50 transition-colors font-medium flex items-center justify-center gap-2"
            >
              <Home className="w-4 h-4" />
              返回首页
            </button>
          )}

          {actions}
        </div>

        {error.code && (
          <p className="text-xs text-gray-400 mt-6">错误代码: {error.code}</p>
        )}
      </div>
    </div>
  );
}

/**
 * 内联错误消息
 */
interface InlineErrorProps {
  message: string;
  /** 自定义类名 */
  className?: string;
}

export function InlineError({ message, className = '' }: InlineErrorProps) {
  return (
    <p className={`text-sm text-red-600 flex items-center gap-1 ${className}`}>
      <AlertCircle className="w-3 h-3 flex-shrink-0" />
      <span>{message}</span>
    </p>
  );
}

/**
 * 成功提示卡片
 */
interface SuccessCardProps {
  message: string;
  /** 详情 */
  details?: string;
  /** 是否可关闭 */
  dismissible?: boolean;
  /** 关闭回调 */
  onDismiss?: () => void;
}

export function SuccessCard({ message, details, dismissible, onDismiss }: SuccessCardProps) {
  return (
    <div className="bg-green-50 border border-green-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <Check className="w-5 h-5 text-green-500 flex-shrink-0 mt-0.5" />

        <div className="flex-1">
          <p className="text-sm font-medium text-green-900">{message}</p>
          {details && <p className="text-sm text-green-700 mt-1">{details}</p>}
        </div>

        {dismissible && (
          <button
            onClick={onDismiss}
            className="text-green-400 hover:text-green-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * 警告提示卡片
 */
interface WarningCardProps {
  message: string;
  /** 详情 */
  details?: string;
  /** 是否可关闭 */
  dismissible?: boolean;
  /** 关闭回调 */
  onDismiss?: () => void;
}

export function WarningCard({ message, details, dismissible, onDismiss }: WarningCardProps) {
  return (
    <div className="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
      <div className="flex items-start gap-3">
        <AlertCircle className="w-5 h-5 text-yellow-500 flex-shrink-0 mt-0.5" />

        <div className="flex-1">
          <p className="text-sm font-medium text-yellow-900">{message}</p>
          {details && <p className="text-sm text-yellow-700 mt-1">{details}</p>}
        </div>

        {dismissible && (
          <button
            onClick={onDismiss}
            className="text-yellow-400 hover:text-yellow-600 transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>
    </div>
  );
}

/**
 * 调试信息组件（仅开发环境）
 */
interface DebugInfoProps {
  title: string;
  data: unknown;
  /** 是否展开 */
  expanded?: boolean;
}

export function DebugInfo({ title, data, expanded = false }: DebugInfoProps) {
  const [isExpanded, setIsExpanded] = React.useState(expanded);

  if (process.env.NODE_ENV !== 'development') {
    return null;
  }

  return (
    <div className="mt-4">
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="flex items-center gap-2 text-xs text-gray-500 hover:text-gray-700 transition-colors"
      >
        <Bug className="w-3 h-3" />
        {title}
      </button>

      {isExpanded && (
        <pre className="mt-2 p-3 bg-gray-900 text-green-400 text-xs rounded-lg overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      )}
    </div>
  );
}

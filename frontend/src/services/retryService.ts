/**
 * 错误重试机制服务
 * 参考: https://ably.com/blog/token-streaming-for-ai-ux
 *
 * 功能:
 * - 自动重试
 * - 指数退避
 * - 手动重试
 * - 错误分类
 */

interface RetryOptions {
  /** 最大重试次数 */
  maxRetries?: number;
  /** 初始重试延迟（毫秒） */
  initialDelay?: number;
  /** 最大重试延迟（毫秒） */
  maxDelay?: number;
  /** 退避因子 */
  backoffFactor?: number;
  /** 是否启用抖动 */
  enableJitter?: boolean;
  /** 可重试的错误判断函数 */
  isRetriable?: (error: Error) => boolean;
}

export interface RetryResult<T> {
  data: T | null;
  error: Error | null;
  retryCount: number;
  succeeded: boolean;
}

/**
 * 错误分类
 */
export function classifyError(error: Error): {
  type: 'network' | 'timeout' | 'rate_limit' | 'server' | 'client' | 'unknown';
  retriable: boolean;
} {
  const message = error.message.toLowerCase();

  // 网络错误
  if (
    message.includes('network') ||
    message.includes('fetch') ||
    message.includes('connection') ||
    message.includes('econnrefused') ||
    message.includes('enotfound')
  ) {
    return { type: 'network', retriable: true };
  }

  // 超时错误
  if (message.includes('timeout') || message.includes('timed out')) {
    return { type: 'timeout', retriable: true };
  }

  // 限流错误
  if (
    message.includes('rate limit') ||
    message.includes('429') ||
    message.includes('too many requests')
  ) {
    return { type: 'rate_limit', retriable: true };
  }

  // 服务器错误 (5xx)
  if (/5\d\d/.test(message)) {
    return { type: 'server', retriable: true };
  }

  // 客户端错误 (4xx)
  if (/4\d\d/.test(message)) {
    return { type: 'client', retriable: false };
  }

  return { type: 'unknown', retriable: false };
}

/**
 * 计算重试延迟（指数退避 + 抖动）
 */
function calculateRetryDelay(
  retryCount: number,
  options: Required<RetryOptions>
): number {
  const { initialDelay, maxDelay, backoffFactor, enableJitter } = options;

  // 指数退避
  let delay = initialDelay * Math.pow(backoffFactor, retryCount);

  // 限制最大延迟
  delay = Math.min(delay, maxDelay);

  // 添加抖动（避免多个请求同时重试）
  if (enableJitter) {
    delay = delay * (0.5 + Math.random());
  }

  return Math.floor(delay);
}

/**
 * 延迟函数
 */
function delay(ms: number): Promise<void> {
  return new Promise(resolve => setTimeout(resolve, ms));
}

/**
 * 带重试的异步函数执行
 */
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  options: RetryOptions = {}
): Promise<RetryResult<T>> {
  const {
    maxRetries = 3,
    initialDelay = 1000,
    maxDelay = 10000,
    backoffFactor = 2,
    enableJitter = true,
    isRetriable,
  } = options;

  let lastError: Error | null = null;
  let retryCount = 0;

  for (let i = 0; i <= maxRetries; i++) {
    try {
      const data = await fn();

      return {
        data,
        error: null,
        retryCount: i,
        succeeded: true,
      };
    } catch (error) {
      lastError = error as Error;

      // 检查是否可重试
      const classification = classifyError(lastError);
      const shouldRetry =
        i < maxRetries &&
        classification.retriable &&
        (isRetriable ? isRetriable(lastError) : true);

      if (!shouldRetry) {
        break;
      }

      retryCount = i + 1;
      const retryDelay = calculateRetryDelay(i, {
        maxRetries,
        initialDelay,
        maxDelay,
        backoffFactor,
        enableJitter,
        isRetriable: isRetriable || (() => true),
      });

      console.warn(
        `操作失败，${retryDelay}ms 后进行第 ${retryCount} 次重试...`,
        lastError.message
      );

      await delay(retryDelay);
    }
  }

  return {
    data: null,
    error: lastError!,
    retryCount,
    succeeded: false,
  };
}

/**
 * 创建可重试的异步函数包装器
 */
export function createRetryableFn<T extends (...args: any[]) => Promise<any>>(
  fn: T,
  options?: RetryOptions
): T & { retry: (opts?: RetryOptions) => Promise<RetryResult<ReturnType<T>>> } {
  const retryableFn = (async (...args: Parameters<T>) => {
    return retryWithBackoff(() => fn(...args), options);
  }) as T & { retry: (opts?: RetryOptions) => Promise<RetryResult<ReturnType<T>>> };

  retryableFn.retry = (opts?: RetryOptions) => {
    return retryWithBackoff(() => fn(), { ...options, ...opts });
  };

  return retryableFn;
}

/**
 * 重试状态管理
 */
export class RetryManager {
  private retryCount: Map<string, number> = new Map();
  private lastRetryTime: Map<string, number> = new Map();

  /**
   * 获取重试次数
   */
  getRetryCount(key: string): number {
    return this.retryCount.get(key) || 0;
  }

  /**
   * 增加重试次数
   */
  incrementRetryCount(key: string): number {
    const count = this.getRetryCount(key) + 1;
    this.retryCount.set(key, count);
    this.lastRetryTime.set(key, Date.now());
    return count;
  }

  /**
   * 重置重试次数
   */
  resetRetryCount(key: string): void {
    this.retryCount.delete(key);
    this.lastRetryTime.delete(key);
  }

  /**
   * 检查是否应该重试（基于限流）
   */
  shouldAllowRetry(key: string, maxRetries: number = 3): boolean {
    return this.getRetryCount(key) < maxRetries;
  }

  /**
   * 清理过期的重试记录
   */
  cleanup(maxAge: number = 300000): void {
    const now = Date.now();
    for (const [key, time] of this.lastRetryTime.entries()) {
      if (now - time > maxAge) {
        this.retryCount.delete(key);
        this.lastRetryTime.delete(key);
      }
    }
  }
}

// 全局重试管理器实例
export const globalRetryManager = new RetryManager();

// 定期清理
if (typeof window !== 'undefined') {
  setInterval(() => {
    globalRetryManager.cleanup();
  }, 60000); // 每分钟清理一次
}

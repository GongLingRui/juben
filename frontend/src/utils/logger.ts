/**
 * 前端日志工具
 * 提供统一的日志接口，支持日志级别控制
 */

type LogLevel = 'debug' | 'info' | 'warn' | 'error';

interface LogConfig {
  level: LogLevel;
  enableConsole: boolean;
  enableRemote: boolean;
  remoteUrl?: string;
}

class Logger {
  private config: LogConfig;

  constructor() {
    // 从环境变量或默认值获取配置
    const isDev = import.meta.env.MODE === 'development';
    this.config = {
      level: (import.meta.env.VITE_LOG_LEVEL as LogLevel) || (isDev ? 'debug' : 'warn'),
      enableConsole: true,
      enableRemote: false,
    };
  }

  private shouldLog(level: LogLevel): boolean {
    const levels: Record<LogLevel, number> = { debug: 0, info: 1, warn: 2, error: 3 };
    return levels[level] >= levels[this.config.level];
  }

  private formatMessage(level: LogLevel, message: string, context?: string): string {
    const timestamp = new Date().toISOString();
    const prefix = context ? `[${context}]` : '';
    return `${timestamp} [${level.toUpperCase()}] ${prefix} ${message}`;
  }

  debug(message: string, context?: string, ...args: unknown[]): void {
    if (this.shouldLog('debug') && this.config.enableConsole) {
      console.log(this.formatMessage('debug', message, context), ...args);
    }
  }

  info(message: string, context?: string, ...args: unknown[]): void {
    if (this.shouldLog('info') && this.config.enableConsole) {
      console.info(this.formatMessage('info', message, context), ...args);
    }
  }

  warn(message: string, context?: string, ...args: unknown[]): void {
    if (this.shouldLog('warn') && this.config.enableConsole) {
      console.warn(this.formatMessage('warn', message, context), ...args);
    }
  }

  error(message: string, context?: string, ...args: unknown[]): void {
    if (this.shouldLog('error') && this.config.enableConsole) {
      console.error(this.formatMessage('error', message, context), ...args);
    }
    // 错误日志可以考虑发送到远程监控服务
    if (this.config.enableRemote && this.config.remoteUrl) {
      this.sendToRemote('error', message, context, args);
    }
  }

  private sendToRemote(level: LogLevel, message: string, context?: string, args?: unknown[]): void {
    // TODO: 实现远程日志发送（如 Sentry、LogRocket 等）
    if (typeof fetch !== 'undefined') {
      fetch(this.config.remoteUrl!, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          level,
          message: this.formatMessage(level, message, context),
          args,
          timestamp: new Date().toISOString(),
          userAgent: navigator.userAgent,
          url: window.location.href,
        }),
      }).catch(() => {
        // 忽略远程日志发送失败
      });
    }
  }

  /**
   * 创建带有上下文的子logger
   */
  createChild(context: string) {
    const child = {
      debug: (message: string, ...args: unknown[]) => this.debug(message, context, ...args),
      info: (message: string, ...args: unknown[]) => this.info(message, context, ...args),
      warn: (message: string, ...args: unknown[]) => this.warn(message, context, ...args),
      error: (message: string, ...args: unknown[]) => this.error(message, context, ...args),
    };
    return child;
  }
}

// 导出单例
export const logger = new Logger();

// 导出便捷函数
export const log = {
  debug: (message: string, context?: string, ...args: unknown[]) => logger.debug(message, context, ...args),
  info: (message: string, context?: string, ...args: unknown[]) => logger.info(message, context, ...args),
  warn: (message: string, context?: string, ...args: unknown[]) => logger.warn(message, context, ...args),
  error: (message: string, context?: string, ...args: unknown[]) => logger.error(message, context, ...args),
};

// 创建带上下文的logger
export function createLogger(context: string) {
  return logger.createChild(context);
}

export default logger;

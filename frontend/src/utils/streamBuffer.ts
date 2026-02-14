/**
 * 流式输出缓冲处理工具
 * 参考: https://ably.com/blog/token-streaming-for-ai-ux
 *
 * 功能:
 * - 处理不完整代码块
 * - Markdown 渲染缓冲
 * - Chunk 累加和智能刷新
 */

interface StreamBufferOptions {
  /** 最小缓冲区大小（字符数） */
  minBufferSize?: number;
  /** 最大缓冲区大小（字符数） */
  maxBufferSize?: number;
  /** 是否启用 Markdown 优化 */
  enableMarkdownOptimization?: boolean;
}

export class StreamBuffer {
  private buffer: string = '';
  private lastFlushPosition: number = 0;
  private readonly minBufferSize: number;
  private readonly maxBufferSize: number;
  private readonly enableMarkdownOptimization: boolean;

  // 代码块状态跟踪
  private inCodeBlock: boolean = false;
  private codeBlockLanguage: string = '';
  private codeBlockContent: string = '';
  private incompleteCodeBlock: string = '';

  constructor(options: StreamBufferOptions = {}) {
    this.minBufferSize = options.minBufferSize || 50;
    this.maxBufferSize = options.maxBufferSize || 500;
    this.enableMarkdownOptimization = options.enableMarkdownOptimization !== false;
  }

  /**
   * 添加 chunk 到缓冲区
   */
  add(chunk: string): string {
    this.buffer += chunk;

    // 检测代码块边界
    this._trackCodeBlocks(chunk);

    // 检查是否应该刷新缓冲区
    if (this._shouldFlush()) {
      return this.flush();
    }

    return '';
  }

  /**
   * 刷新缓冲区，返回可渲染的内容
   */
  flush(): string {
    if (this.buffer.length === 0) {
      return '';
    }

    let contentToRender = '';

    // 如果在代码块中，只渲染到上一个安全点
    if (this.inCodeBlock) {
      contentToRender = this.buffer.slice(this.lastFlushPosition, this._findSafeRenderPoint());
      this.lastFlushPosition += contentToRender.length;

      // 保存不完整的代码块
      this.incompleteCodeBlock = this.buffer.slice(this.lastFlushPosition);
    } else {
      contentToRender = this.buffer.slice(this.lastFlushPosition);
      this.lastFlushPosition = this.buffer.length;
    }

    return contentToRender;
  }

  /**
   * 获取所有缓冲内容（完成时调用）
   */
  getAll(): string {
    return this.buffer;
  }

  /**
   * 重置缓冲区
   */
  reset(): void {
    this.buffer = '';
    this.lastFlushPosition = 0;
    this.inCodeBlock = false;
    this.codeBlockLanguage = '';
    this.codeBlockContent = '';
    this.incompleteCodeBlock = '';
  }

  /**
   * 获取当前缓冲区大小
   */
  getSize(): number {
    return this.buffer.length;
  }

  /**
   * 判断是否应该刷新缓冲区
   */
  private _shouldFlush(): boolean {
    const bufferSize = this.buffer.length - this.lastFlushPosition;

    // 如果在代码块中，等待代码块完成或达到最大缓冲区
    if (this.inCodeBlock) {
      return bufferSize >= this.maxBufferSize;
    }

    // 普通内容：达到最小缓冲区大小即可刷新
    return bufferSize >= this.minBufferSize;
  }

  /**
   * 跟踪代码块状态
   */
  private _trackCodeBlocks(chunk: string): void {
    if (!this.enableMarkdownOptimization) {
      return;
    }

    // 检查代码块开始
    if (!this.inCodeBlock) {
      const match = chunk.match(/```(\w*)/);
      if (match) {
        this.inCodeBlock = true;
        this.codeBlockLanguage = match[1] || '';
        this.codeBlockContent = '';
      }
    } else {
      // 检查代码块结束
      if (chunk.includes('```')) {
        this.inCodeBlock = false;
        this.codeBlockContent = '';
      }
    }
  }

  /**
   * 查找安全的渲染点（不破坏 Markdown 结构）
   */
  private _findSafeRenderPoint(): number {
    const remaining = this.buffer.slice(this.lastFlushPosition);

    // 查找最后一个安全的断点（行尾、句子尾等）
    const safePoints = [
      /\n\n/g,           // 双换行
      /\n/g,             // 单换行
      /[。！？.!?]\s*/g,  // 句子结尾
      /[,，]\s*/g,       // 逗号
      /\s+/g,            // 空格
    ];

    let bestPoint = remaining.length;

    for (const pattern of safePoints) {
      const matches = [...remaining.matchAll(pattern)];
      if (matches.length > 0) {
        const lastMatch = matches[matches.length - 1];
        const point = (lastMatch.index || 0) + lastMatch[0].length;
        if (point > 0 && point < bestPoint) {
          bestPoint = point;
          break;
        }
      }
    }

    return bestPoint;
  }

  /**
   * 获取不完整的代码块（用于预览）
   */
  getIncompleteCodeBlock(): { language: string; content: string } {
    if (!this.inCodeBlock || this.incompleteCodeBlock.length === 0) {
      return { language: '', content: '' };
    }

    // 提取代码块内容（去掉 ``` 标记）
    const lines = this.incompleteCodeBlock.split('\n');
    const content = lines.slice(1).join('\n'); // 跳过第一行的 ```

    return {
      language: this.codeBlockLanguage,
      content: content,
    };
  }

  /**
   * 判断是否正在渲染代码块
   */
  isInCodeBlock(): boolean {
    return this.inCodeBlock;
  }
}

/**
 * 创建流式缓冲区实例
 */
export function createStreamBuffer(options?: StreamBufferOptions): StreamBuffer {
  return new StreamBuffer(options);
}

/**
 * 流式输出状态管理
 */
export interface StreamState {
  isStreaming: boolean;
  content: string;
  buffer: string;
  hasIncompleteCodeBlock: boolean;
  incompleteBlock?: { language: string; content: string };
}

/**
 * 管理多个流式缓冲区（支持多 Agent 并发）
 */
export class StreamBufferManager {
  private buffers: Map<string, StreamBuffer> = new Map();

  getOrCreate(key: string, options?: StreamBufferOptions): StreamBuffer {
    if (!this.buffers.has(key)) {
      this.buffers.set(key, new StreamBuffer(options));
    }
    return this.buffers.get(key)!;
  }

  remove(key: string): void {
    this.buffers.delete(key);
  }

  clear(): void {
    this.buffers.clear();
  }

  getState(key: string): StreamState {
    const buffer = this.buffers.get(key);
    if (!buffer) {
      return {
        isStreaming: false,
        content: '',
        buffer: '',
        hasIncompleteCodeBlock: false,
      };
    }

    return {
      isStreaming: true,
      content: buffer.getAll(),
      buffer: buffer['buffer'] || '',
      hasIncompleteCodeBlock: buffer.isInCodeBlock(),
      incompleteBlock: buffer.getIncompleteCodeBlock(),
    };
  }
}

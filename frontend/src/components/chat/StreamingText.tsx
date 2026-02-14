/**
 * 流式文本组件 - 优化版
 * 参考: https://codedeepai.com/blog/streaming-vs-non-streaming-ai-responses-building-lightning-fast-chat-interfaces-that-users-love
 *
 * 特性:
 * - 智能缓冲处理，避免渲染不完整的 Markdown
 * - 代码块检测和优化
 * - 平滑的打字机效果
 */

import { useMemo, useState, useEffect, useRef } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import 'highlight.js/styles/github-dark.css';
import { createStreamBuffer } from '@/utils/streamBuffer';

interface StreamingTextProps {
  content: string;
  isStreaming?: boolean;
  onComplete?: () => void;
  enableBuffer?: boolean;
}

export default function StreamingText({
  content,
  isStreaming = false,
  onComplete,
  enableBuffer = true
}: StreamingTextProps) {
  const [displayContent, setDisplayContent] = useState('');
  const [showCursor, setShowCursor] = useState(true);
  const bufferRef = useRef<ReturnType<typeof createStreamBuffer> | null>(null);
  const lastContentRef = useRef('');
  const rafIdRef = useRef<number>();

  // 初始化缓冲区
  useEffect(() => {
    if (enableBuffer && !bufferRef.current) {
      bufferRef.current = createStreamBuffer({
        minBufferSize: 30,
        maxBufferSize: 300,
        enableMarkdownOptimization: true,
      });
    }
  }, [enableBuffer]);

  // 处理内容更新
  useEffect(() => {
    console.log('[StreamingText] Content updated:', content.substring(0, 50), 'isStreaming:', isStreaming);

    if (!enableBuffer) {
      // 不使用缓冲区，直接显示
      setDisplayContent(content);
      return;
    }

    const buffer = bufferRef.current;
    if (!buffer) return;

    // 检测新增的 chunk
    const newContent = content.slice(lastContentRef.current.length);
    if (newContent.length === 0) {
      console.log('[StreamingText] No new content');
      return;
    }

    // 添加到缓冲区
    const renderedChunk = buffer.add(newContent);
    lastContentRef.current = content;

    // 更新显示内容
    if (renderedChunk) {
      setDisplayContent(prev => prev + renderedChunk);
    }

    // 使用 requestAnimationFrame 优化渲染
    if (rafIdRef.current) {
      cancelAnimationFrame(rafIdRef.current);
    }

    rafIdRef.current = requestAnimationFrame(() => {
      const updatedContent = buffer.getAll();
      if (updatedContent !== displayContent) {
        setDisplayContent(updatedContent);
      }
    });

    // 流式完成时刷新所有内容
    if (!isStreaming && content.length > 0) {
      const remaining = buffer.flush();
      if (remaining) {
        setDisplayContent(prev => prev + remaining);
      }
      onComplete?.();
    }

    return () => {
      if (rafIdRef.current) {
        cancelAnimationFrame(rafIdRef.current);
      }
    };
  }, [content, isStreaming, enableBuffer, onComplete]);

  // 光标闪烁效果
  useEffect(() => {
    if (!isStreaming) {
      setShowCursor(false);
      return;
    }

    const interval = setInterval(() => {
      setShowCursor(prev => !prev);
    }, 500);

    return () => clearInterval(interval);
  }, [isStreaming]);

  // 检查内容特性
  const hasCodeBlock = useMemo(() => {
    return /```[\s\S]*```/.test(displayContent) || /^```[\s\S]*$/.test(displayContent);
  }, [displayContent]);

  const hasMarkdown = useMemo(() => {
    return /(^|[^\\])[#*_`\-\[\]()]/.test(displayContent);
  }, [displayContent]);

  // 检测当前是否在不完整代码块中
  const isIncompleteCodeBlock = useMemo(() => {
    const codeBlockCount = (displayContent.match(/```/g) || []).length;
    return codeBlockCount % 2 === 1;
  }, [displayContent]);

  // 检测不完整代码块的语言 - MUST be called before early return
  const incompleteBlockLanguage = useMemo(() => {
    if (!isIncompleteCodeBlock) return null;
    const match = displayContent.match(/```(\w*)$/);
    return match ? match[1] : null;
  }, [displayContent, isIncompleteCodeBlock]);

  // 流式时，如果当前内容几乎为空（例如仅有一个 "(" 之类的占位符），交给上层的「生成中」状态展示即可
  if (isStreaming && displayContent.trim().length <= 1) {
    return null;
  }

  // 如果没有 Markdown 且没有代码块，直接渲染
  if (!hasMarkdown && !hasCodeBlock) {
    return (
      <p className="whitespace-pre-wrap break-words text-gray-800">
        {displayContent}
        {isStreaming && showCursor && (
          <span className="typing-cursor">|</span>
        )}
      </p>
    );
  }

  // 使用 Markdown 渲染
  return (
    <div className="markdown prose prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={{
          // 自定义代码块渲染
          code({ node, inline, className, children, ...props }) {
            const match = /language-(\w+)/.exec(className || '');
            const language = match ? match[1] : '';

            return !inline ? (
              <div className="relative group">
                <div className="absolute right-2 top-2 opacity-0 group-hover:opacity-100 transition-opacity">
                  <button
                    onClick={() => navigator.clipboard.writeText(String(children))}
                    className="px-2 py-1 text-xs bg-gray-700 text-white rounded hover:bg-gray-600"
                  >
                    复制
                  </button>
                </div>
                <code className={className} {...props}>
                  {children}
                </code>
              </div>
            ) : (
              <code className="px-1.5 py-0.5 bg-gray-100 text-gray-900 rounded text-sm font-mono" {...props}>
                {children}
              </code>
            );
          },
          // 自定义链接渲染
          a({ children, href }) {
            return (
              <a
                href={href}
                target="_blank"
                rel="noopener noreferrer"
                className="text-black underline hover:text-gray-700"
              >
                {children}
              </a>
            );
          },
          // 自定义表格渲染
          table({ children }) {
            return (
              <div className="overflow-x-auto my-4">
                <table className="min-w-full divide-y divide-gray-200 border border-gray-300">
                  {children}
                </table>
              </div>
            );
          },
          // 自定义表头渲染
          thead({ children }) {
            return <thead className="bg-gray-50">{children}</thead>;
          },
          // 自定义表格单元格渲染
          td({ children }) {
            return <td className="px-4 py-2 text-sm border-b border-gray-200">{children}</td>;
          },
          th({ children }) {
            return <th className="px-4 py-2 text-left text-xs font-medium text-gray-500 uppercase tracking-wider border-b-2 border-gray-200">
              {children}
            </th>;
          },
        }}
      >
        {displayContent}
      </ReactMarkdown>

      {/* 显示不完整代码块的预览 */}
      {isIncompleteCodeBlock && incompleteBlockLanguage && (
        <div className="mt-2 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
          <div className="flex items-center gap-2 text-xs text-yellow-700 mb-2">
            <div className="w-2 h-2 bg-yellow-500 rounded-full animate-pulse" />
            <span>正在生成{incompleteBlockLanguage}代码块...</span>
          </div>
        </div>
      )}

      {/* 光标 */}
      {isStreaming && showCursor && (
        <span className="typing-cursor" style={{ marginLeft: '2px' }}>|</span>
      )}
    </div>
  );
}


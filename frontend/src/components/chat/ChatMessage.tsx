/**
 * 聊天消息组件 - 增强版
 * 集成了增强的消息操作、思考链可视化和内容类型渲染
 */

import { useMemo, useState, useEffect } from 'react';
import { User, Bot, Layers } from 'lucide-react';
import { useChat } from '@/hooks/useChat';
import { useSettingsStore } from '@/store/settingsStore';
import { format } from 'date-fns';
import StreamingText from './StreamingText';
import { convertEventsToThoughtSteps } from './ThoughtChainView';
import ThoughtChainView from './ThoughtChainView';
import EnhancedMessageActions from './EnhancedMessageActions';
import SystemProgress from './SystemProgress';
import ContentTypeRenderer, { parseEventToContentBlock } from './ContentTypeRenderer';
import MindMapViewer from '@/components/mindmap/MindMapViewer';
import type { MindMapData } from '@/utils/mindMap';
import { parseMindMap } from '@/utils/mindMap';
import { parseContentType } from '@/utils/contentTypeConfig';
import type { Message, StreamContentType } from '@/types';

interface ChatMessageProps {
  message: Message;
  showThoughtChain?: boolean;
}

export default function ChatMessage({ message, showThoughtChain = false }: ChatMessageProps) {
  const { regenerateMessage, editMessage, createBranch, deleteMessage } = useChat();
  const { showTimestamp, fontSize } = useSettingsStore();
  const isUser = message.role === 'user';
  const isStreaming = message.status === 'streaming';

  // 🆕 是否显示内容类型视图
  const [showContentTypeView, setShowContentTypeView] = useState(
    message.metadata?.contentType === 'mind_map'
  );

  useEffect(() => {
    if (message.metadata?.contentType === 'mind_map') {
      setShowContentTypeView(true);
    }
  }, [message.metadata?.contentType]);

  // 提取系统事件
  const systemEvents = useMemo(() => {
    const events = message.metadata?.systemEvents || [];
    return events.map((e: any) => ({
      content: e.content,
      timestamp: e.timestamp
    }));
  }, [message.metadata]);

  // 尝试直接从消息内容中解析思维导图（兜底，防止元数据缺失时仍然只显示纯文本）
  const inlineMindMapData = useMemo<MindMapData | null>(() => {
    if (!message.content) return null;
    return parseMindMap(message.content);
  }, [message.content]);

  const displayContent = useMemo(() => {
    // 如果没有系统事件或内容为空，直接返回
    if (systemEvents.length === 0 || !message.content) {
      return message.content;
    }

    let cleaned = message.content;
    for (const event of systemEvents) {
      const step = event.content?.trim();
      if (!step) continue;
      cleaned = cleaned.replace(step, '');
    }

    return cleaned.replace(/^[\s.。…]+/, '');
  }, [message.content, systemEvents]);

  // 🆕 提取内容类型块（从增强的元数据中）
  const contentBlocks = useMemo(() => {
    const blocks: Array<{
      contentType: StreamContentType;
      content: string;
      agentSource?: string;
      timestamp?: string;
      metadata?: Record<string, any>;
    }> = [];

    // 从 metadata.contentTypes 中提取（新的增强格式）
    if (message.metadata?.contentBlocks) {
      for (const block of message.metadata.contentBlocks) {
        blocks.push({
          contentType: parseContentType(block.contentType),
          content: block.content || '',
          agentSource: block.agentSource,
          timestamp: block.timestamp,
          metadata: block.metadata,
        });
      }
    }

    // 从增强的事件数据中提取（兼容性）
    if (message.metadata?.enhancedEvents) {
      for (const event of message.metadata.enhancedEvents) {
        const parsed = parseEventToContentBlock(event);
        if (parsed && parsed.content) {
          blocks.push(parsed);
        }
      }
    }

    return blocks;
  }, [message.metadata]);

  // 转换元数据中的事件为思考步骤
  const thoughtSteps = useMemo(() => {
    const toolEvents = message.metadata?.toolEvents || [];
    const systemEvents = message.metadata?.systemEvents || [];
    const allEvents = [
      ...toolEvents.map((e: any) => ({ event: e.event, data: e.data, timestamp: e.timestamp })),
      ...systemEvents.map((e: any) => ({ event: 'system', data: { content: e.content }, timestamp: e.timestamp })),
    ];
    return convertEventsToThoughtSteps(allEvents);
  }, [message.metadata]);

  // 判断是否显示重试按钮
  const canRetry = message.metadata?.canRetry === true && message.status === 'error';

  // 🆕 判断是否可以使用内容类型视图
  const hasContentTypeBlocks = contentBlocks.length > 0;
  const canShowContentTypeView = hasContentTypeBlocks || message.metadata?.contentType;

  return (
    <div
      id={`message-${message.id}`}
      className={`flex gap-4 ${isUser ? 'justify-end' : 'justify-start'} message-slide-in group`}
    >
      {/* AI 消息: 头像 + 内容 */}
      {!isUser && (
        <>
          {/* 头像 */}
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-black flex items-center justify-center">
            <Bot className="w-5 h-5 text-white" />
          </div>

          {/* 消息内容 */}
          <div className="flex-1 max-w-[85%]">
            {/* Agent 名称 */}
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm font-medium text-gray-900">
                {message.agentName || 'AI 助手'}
              </span>
              {(message.metadata?.retryCount ?? 0) > 0 && (
                <span className="text-xs px-1.5 py-0.5 bg-yellow-100 text-yellow-700 rounded">
                  重试 {message.metadata?.retryCount ?? 0}
                </span>
              )}
              {message.metadata?.model && (
                <span className="text-xs text-gray-400">{message.metadata.model}</span>
              )}
              {showTimestamp && message.timestamp && (
                <span className="text-xs text-gray-400">
                  {format(new Date(message.timestamp), 'HH:mm')}
                </span>
              )}
              {/* 🆕 内容类型视图切换按钮 */}
              {canShowContentTypeView && (
                <button
                  onClick={() => setShowContentTypeView(!showContentTypeView)}
                  className="p-1 hover:bg-gray-100 rounded transition-colors"
                  title={showContentTypeView ? '切换到普通视图' : '切换到内容类型视图'}
                >
                  <Layers className="w-4 h-4 text-gray-500" />
                </button>
              )}
            </div>

            {/* 思考链 */}
            {showThoughtChain && thoughtSteps.length > 0 && (
              <ThoughtChainView
                steps={thoughtSteps}
                isStreaming={isStreaming}
              />
            )}

            {/* 🆕 内容类型视图 vs 普通视图 */}
            {showContentTypeView && canShowContentTypeView ? (
              /* 内容类型视图 */
              <div className="space-y-3">
                {/* 渲染内容类型块 */}
                {hasContentTypeBlocks && contentBlocks.map((block, index) => (
                  <ContentTypeRenderer
                    key={index}
                    contentType={block.contentType}
                    content={block.content}
                    isStreaming={isStreaming && index === contentBlocks.length - 1}
                    agentSource={block.agentSource}
                    timestamp={block.timestamp}
                    metadata={block.metadata}
                  />
                ))}

                {/* 如果没有内容块但有contentType，按内容类型渲染主内容 */}
                {!hasContentTypeBlocks && message.metadata?.contentType && (
                  <ContentTypeRenderer
                    contentType={parseContentType(message.metadata.contentType)}
                    content={message.content}
                    isStreaming={isStreaming}
                    agentSource={message.agentName}
                    timestamp={message.timestamp}
                    metadata={message.metadata}
                  />
                )}
              </div>
            ) : (
              /* 普通视图 */
              <>
                {/* 消息气泡 */}
                <div
                  className={`relative p-4 rounded-xl border-l-2 border-black bg-gray-50 hover:shadow-md transition-shadow ${
                    fontSize === 'sm' ? 'text-sm' : fontSize === 'lg' ? 'text-lg' : 'text-base'
                  }`}
                >
                  {/* 系统进度 - 实时显示执行过程 */}
                  {systemEvents.length > 0 && (
                    <SystemProgress events={systemEvents} isStreaming={isStreaming} />
                  )}

                  {/* 状态指示 */}
                  {message.status === 'streaming' && systemEvents.length === 0 && (
                    <div className="flex items-center gap-1.5 text-xs text-gray-400 mb-2">
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse" />
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse delay-100" />
                      <div className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-pulse delay-200" />
                      <span className="ml-1">生成中</span>
                    </div>
                  )}

                  {/* 消息内容 / 思维导图可视化 */}
                  {(
                    (message.metadata?.contentType === 'mind_map' &&
                      (message.metadata as any)?.mindMapData) ||
                    inlineMindMapData
                  ) ? (
                    <div className="space-y-3">
                      <div className="text-base font-semibold text-gray-900">
                        {((message.metadata as any)?.mindMapData as MindMapData | undefined)?.title ||
                          inlineMindMapData?.title}
                      </div>
                      <MindMapViewer
                        data={
                          (((message.metadata as any)?.mindMapData as MindMapData) ||
                            inlineMindMapData) as MindMapData
                        }
                        agentSource={message.agentName}
                      />
                    </div>
                  ) : (
                    <StreamingText content={displayContent} isStreaming={isStreaming} />
                  )}

                  {/* 错误信息 */}
                  {message.status === 'error' && message.metadata?.error && (
                    <div className="mt-3 p-3 bg-red-50 border border-red-200 rounded-lg">
                      <p className="text-sm text-red-700">{message.metadata.error}</p>
                      {canRetry && regenerateMessage && (
                        <button
                          onClick={() => regenerateMessage(message.id)}
                          className="mt-2 px-3 py-1.5 text-sm bg-red-600 text-white rounded hover:bg-red-700 transition-colors"
                        >
                          重试
                        </button>
                      )}
                    </div>
                  )}

                  {/* 计费信息 */}
                  {message.metadata?.billing && (
                    <div className="mt-2 text-xs text-gray-500">
                      {message.metadata.billing}
                    </div>
                  )}
                </div>
              </>
            )}

            {/* 操作按钮 */}
            <div className="mt-2">
              <EnhancedMessageActions
                message={message}
                onRegenerate={() => regenerateMessage(message.id)}
                onEdit={(id, content) => editMessage(id, content)}
                onDelete={deleteMessage}
                onBranch={createBranch}
                isStreaming={isStreaming}
                canRegenerate={true}
                canEdit={false}
              />
            </div>
          </div>
        </>
      )}

      {/* 用户消息: 内容 + 头像 */}
      {isUser && (
        <>
          {/* 消息内容 */}
          <div className="max-w-[70%]">
            <div
              className={`px-4 py-3 bg-black text-white rounded-xl hover:shadow-lg transition-all ${
                fontSize === 'sm' ? 'text-sm' : fontSize === 'lg' ? 'text-lg' : 'text-base'
              }`}
            >
              {message.content}
            </div>

            {/* 时间戳 */}
            {showTimestamp && message.timestamp && (
              <div className="mt-1 text-xs text-gray-400 text-right pr-2">
                {format(new Date(message.timestamp), 'HH:mm')}
              </div>
            )}

            {/* 操作按钮 */}
            <div className="mt-2">
              <EnhancedMessageActions
                message={message}
                onEdit={(id, content) => editMessage(id, content)}
                onDelete={deleteMessage}
                onBranch={createBranch}
                isStreaming={false}
                canRegenerate={false}
                canEdit={true}
              />
            </div>
          </div>

          {/* 头像 */}
          <div className="flex-shrink-0 w-10 h-10 rounded-full bg-gray-200 flex items-center justify-center">
            <User className="w-5 h-5 text-gray-600" />
          </div>
        </>
      )}
    </div>
  );
}

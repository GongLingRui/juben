/**
 * 聊天面板组件
 * 右侧 40% 区域 - 用户与 Agent 对话界面
 */

import { useChatStore } from '@/store/chatStore';
import { useAgentStore } from '@/store/agentStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { useSettingsStore } from '@/store/settingsStore';
import { useUIStore } from '@/store/uiStore';
import ChatMessage from '@/components/chat/ChatMessage';
import ChatInputArea from '@/components/workspace/ChatInputArea';
import { Loader2 } from 'lucide-react';
import { useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';

export default function ChatPanel() {
  const {
    messages,
    streamingMessage,
    isStreaming,
    sendMessage,
  } = useChatStore();

  const { agents, activeAgent } = useAgentStore();
  const { notes, setViewMode } = useWorkspaceStore();
  const { showThoughtChain } = useSettingsStore();
  const { thoughtChainExpanded } = useUIStore();
  const location = useLocation();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 自动滚动到底部
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingMessage]);

  useEffect(() => {
    if (!location.hash) return;
    const targetId = location.hash.replace('#', '');
    const element = document.getElementById(targetId);
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [location.hash, messages, streamingMessage]);

  // 获取当前 Agent 信息
  const currentAgent = agents.find((a) => a.id === activeAgent);
  const selectedNotesCount = notes.filter((n) => n.select_status === 1).length;
  const totalNotesCount = notes.length;

  const getAgentSuggestions = () => {
    const category = currentAgent?.category;
    const base = [
      currentAgent?.inputExample || '帮我生成一个短剧创意',
    ];

    const categorySuggestions: Record<string, string[]> = {
      planning: ['生成三幕结构大纲', '输出人物小传'],
      creation: ['写第一场戏', '生成关键对话'],
      evaluation: ['给出评分与问题清单', '输出优化建议'],
      analysis: ['提炼主题与核心冲突', '梳理人物关系'],
      workflow: ['按流程输出步骤', '拆解成可执行任务'],
      character: ['生成主要人物关系图', '补全人物背景'],
      story: ['输出故事梗概', '生成情节转折点'],
    };

    const extras = category ? categorySuggestions[category] || [] : [];
    const notesHint = selectedNotesCount > 0 ? ['基于已选 Notes 继续'] : [];
    return [...base, ...extras, ...notesHint].filter(Boolean);
  };

  const suggestions = getAgentSuggestions();

  const handleSendMessage = async (content: string) => {
    await sendMessage(content, activeAgent);
  };

  return (
    <div className="flex flex-col h-full bg-gray-50">
      {/* Agent 信息栏 */}
      <div className="flex-shrink-0 px-4 py-3 bg-white border-b border-gray-200">
        <div className="flex items-center gap-3">
          {/* Agent 图标 */}
          <div className="w-10 h-10 rounded-lg flex items-center justify-center bg-gray-100">
            <span className="text-2xl">
              {currentAgent?.icon || '🤖'}
            </span>
          </div>

          {/* Agent 名称和描述 */}
          <div className="flex-1 min-w-0">
            <h3 className="font-semibold text-gray-900 text-sm">
              {currentAgent?.displayName || '未知 Agent'}
            </h3>
            <p className="text-xs text-gray-500 truncate">
              {currentAgent?.description || '暂无描述'}
            </p>
          </div>

          {/* 状态指示器 */}
          {isStreaming && (
            <div className="flex items-center gap-2 text-xs text-blue-600">
              <Loader2 className="w-4 h-4 animate-spin" />
              <span>思考中...</span>
            </div>
          )}
        </div>

        {/* Notes 状态 */}
        {totalNotesCount > 0 && (
          <div className="mt-2 flex items-center gap-2 text-xs text-gray-500">
            <span>Notes: {selectedNotesCount}/{totalNotesCount} 已选</span>
            <button
              onClick={() => setViewMode('notes')}
              className="px-2 py-1 rounded-full border border-gray-200 hover:bg-gray-50"
            >
              查看 Notes
            </button>
          </div>
        )}
      </div>

      {/* 消息列表区 */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-4">
        {messages.length === 0 ? (
          // 空状态
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <div className="w-16 h-16 rounded-full bg-gray-200 flex items-center justify-center mb-4">
              <svg
                className="w-8 h-8"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z"
                />
              </svg>
            </div>
            <p className="text-sm font-medium">开始对话</p>
            <p className="text-xs mt-1">输入指令，让 AI 为你创作</p>
          </div>
        ) : (
          // 消息列表
          <>
            {messages.map((message) => (
              <ChatMessage
                key={message.id}
                message={message}
                showThoughtChain={showThoughtChain && thoughtChainExpanded}
              />
            ))}

            {/* 流式消息 */}
            {streamingMessage && (
              <ChatMessage
                message={{
                  id: 'streaming',
                  role: 'assistant',
                  content: streamingMessage,
                  timestamp: new Date().toISOString(),
                  status: 'streaming',
                }}
                showThoughtChain={showThoughtChain && thoughtChainExpanded}
              />
            )}

            {/* 滚动锚点 */}
            <div ref={messagesEndRef} />
          </>
        )}
      </div>

      {/* 输入区 */}
      <div className="flex-shrink-0 p-4 bg-white border-t border-gray-200">
        <ChatInputArea
          onSend={handleSendMessage}
          disabled={isStreaming}
          placeholder={
            currentAgent
              ? `与 ${currentAgent.displayName} 对话...`
              : '发送消息...'
          }
          suggestions={suggestions}
        />
      </div>
    </div>
  );
}

/**
 * 聊天状态管理 Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Message, MessageStatus, Thought } from '@/types';
import { sendMessageToAgent } from '@/services/chatService';
import { useWorkspaceStore } from '@/store/workspaceStore';

interface ChatState {
  messages: Message[];
  currentSession: string | null;
  streamingMessageId: string | null;
  streamingMessage: string | null;  // 新增：流式消息内容
  isStreaming: boolean;
  thoughtChain: Thought[];  // 新增：思维链

  // Actions
  addMessage: (message: Message) => void;
  updateMessage: (id: string, updates: Partial<Message>) => void;
  updateMessageMetadata: (id: string, metadataUpdater: (currentMetadata: any) => any) => void;
  deleteMessage: (id: string) => void;
  clearMessages: () => void;
  setMessages: (messages: Message[]) => void;

  setCurrentSession: (sessionId: string) => void;
  clearCurrentSession: () => void;

  setStreamingMessageId: (id: string | null) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingMessage: (content: string | null) => void;  // 新增
  setThoughtChain: (thoughts: Thought[]) => void;  // 新增
  appendThought: (thought: Thought) => void;  // 新增

  // Streaming helpers
  appendToMessage: (id: string, content: string) => void;
  setMessageStatus: (id: string, status: MessageStatus) => void;

  // 新增：发送消息
  sendMessage: (content: string, agentId: string) => Promise<void>;
}

export const useChatStore = create<ChatState>()(
  devtools(
    (set, get) => ({
      // Initial state
      messages: [],
      currentSession: null,
      streamingMessageId: null,
      streamingMessage: null,
      isStreaming: false,
      thoughtChain: [],

      // Message actions
      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
        })),

      updateMessage: (id, updates) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, ...updates } : msg
          ),
        })),

      // 函数式更新 metadata（用于追加系统事件等）
      updateMessageMetadata: (id, metadataUpdater) =>
        set((state) => {
          const updatedMessages = state.messages.map((msg) =>
            msg.id === id
              ? (() => {
                  const currentMetadata = msg.metadata || {};
                  const newMetadataPart = metadataUpdater(currentMetadata);

                  // 深度合并，特别处理数组类型字段
                  const mergedMetadata: any = { ...currentMetadata };

                  // 对 systemEvents 进行特殊处理 - 追加而不是覆盖
                  if (newMetadataPart.systemEvents) {
                    mergedMetadata.systemEvents = [
                      ...(currentMetadata.systemEvents || []),
                      ...newMetadataPart.systemEvents
                    ];
                  }

                  // 对 toolEvents 进行特殊处理 - 追加而不是覆盖
                  if (newMetadataPart.toolEvents) {
                    mergedMetadata.toolEvents = [
                      ...(currentMetadata.toolEvents || []),
                      ...newMetadataPart.toolEvents
                    ];
                  }

                  // 其他字段直接覆盖
                  Object.keys(newMetadataPart).forEach(key => {
                    if (key !== 'systemEvents' && key !== 'toolEvents') {
                      mergedMetadata[key] = newMetadataPart[key];
                    }
                  });

                  console.log('[chatStore] updateMessageMetadata:', id, 'systemEvents count:', mergedMetadata.systemEvents?.length || 0);
                  return { ...msg, metadata: mergedMetadata };
                })()
              : msg
          );
          return { messages: updatedMessages };
        }),

      deleteMessage: (id) =>
        set((state) => ({
          messages: state.messages.filter((msg) => msg.id !== id),
        })),

      clearMessages: () => set({ messages: [] }),

      setMessages: (messages) => set({ messages }),

      // Session actions
      setCurrentSession: (sessionId) => set({ currentSession: sessionId }),
      clearCurrentSession: () => set({ currentSession: null }),

      // Streaming actions
      setStreamingMessageId: (id) => set({ streamingMessageId: id }),
      setIsStreaming: (isStreaming) => set({ isStreaming }),

      // 新增：流式消息和思维链
      setStreamingMessage: (content) => set({ streamingMessage: content }),
      setThoughtChain: (thoughts) => set({ thoughtChain: thoughts }),
      appendThought: (thought) =>
        set((state) => ({
          thoughtChain: [...state.thoughtChain, thought],
        })),

      // Streaming helpers
      appendToMessage: (id, content) => {
        console.log('[chatStore] appendToMessage:', id, content.substring(0, 50));
        set((state) => {
          const updatedMessages = state.messages.map((msg) =>
            msg.id === id ? { ...msg, content: msg.content + content } : msg
          );
          const updatedMsg = updatedMessages.find(m => m.id === id);
          console.log('[chatStore] Updated message content:', updatedMsg?.content?.substring(0, 50) || 'empty');
          return { messages: updatedMessages };
        });
      },

      setMessageStatus: (id, status) =>
        set((state) => ({
          messages: state.messages.map((msg) =>
            msg.id === id ? { ...msg, status } : msg
          ),
        })),

      // 新增：发送消息
      sendMessage: async (content: string, agentId: string) => {
        const state = get();

        // 添加用户消息
        const userMessage: Message = {
          id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
          role: 'user',
          content,
          timestamp: new Date().toISOString(),
          status: 'streaming',
        };
        state.addMessage(userMessage);

        // 清空之前的思维链和流式消息
        state.setThoughtChain([]);
        state.setStreamingMessage('');
        state.setIsStreaming(true);

        try {
          // 调用流式 API
          await sendMessageToAgent(
            content,
            agentId,
            // onChunk callback
            (chunk: string, isThought: boolean) => {
              if (isThought) {
                return;
              } else {
                // 更新流式消息
                const current = get().streamingMessage || '';
                state.setStreamingMessage(current + chunk);
              }
            },
            // onThought callback
            (thought: Thought) => {
              state.appendThought(thought);
            }
          );

          // 流式完成，创建助手消息
          const assistantMessage: Message = {
            id: `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
            role: 'assistant',
            content: get().streamingMessage || '',
            timestamp: new Date().toISOString(),
            status: 'complete',
            metadata: {
              agentId,
              thoughtChain: get().thoughtChain,
            },
          };
          state.addMessage(assistantMessage);

          // 更新工作区内容
          const assistantContent = assistantMessage.content;
          if (assistantContent) {
            useWorkspaceStore.getState().setContent({
              id: assistantMessage.id,
              type: 'document',
              title: `${agentId} 生成结果`,
              content: assistantContent,
              metadata: {
                agentId,
                timestamp: assistantMessage.timestamp,
              },
            });
          }
        } catch (error) {
          console.error('[chatStore] Send message error:', error);
          // 添加错误消息
          state.addMessage({
            id: `msg_${Date.now()}_error`,
            role: 'assistant',
            content: `发送失败: ${error instanceof Error ? error.message : '未知错误'}`,
            timestamp: new Date().toISOString(),
            status: 'error',
          });
        } finally {
          state.setIsStreaming(false);
          state.setStreamingMessage(null);
        }
      },
    }),
    { name: 'ChatStore' }
  )
);

/**
 * 增强消息操作组件
 * 提供复制、编辑、删除、重新生成、分支等功能
 * 🆕 支持将选中的Agent输出片段保存为 Note
 */

import { Copy, Check, RefreshCw, Edit2, Trash2, GitBranch, Bookmark, FilePlus2 } from 'lucide-react';
import { useState } from 'react';
import type { Message } from '@/types';
import { createNote } from '@/services/noteService';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { useNotificationStore } from '@/store/notificationStore';

interface EnhancedMessageActionsProps {
  message: Message;
  onRegenerate?: () => void;
  onEdit?: (id: string, content: string) => void;
  onDelete?: (id: string) => void;
  onBranch?: (id: string) => void;
  isStreaming?: boolean;
  canRegenerate?: boolean;
  canEdit?: boolean;
}

export default function EnhancedMessageActions({
  message,
  onRegenerate,
  onEdit,
  onDelete,
  onBranch,
  isStreaming = false,
  canRegenerate = false,
  canEdit = false,
}: EnhancedMessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [bookmarked, setBookmarked] = useState(false);
  const [savingToNote, setSavingToNote] = useState(false);
  const { loadNotes } = useWorkspaceStore();
  const { success, error: showError } = useNotificationStore();

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('复制失败:', err);
    }
  };

  const handleEdit = () => {
    if (onEdit) {
      onEdit(message.id, message.content);
    }
  };

  const handleDelete = () => {
    if (onDelete) {
      onDelete(message.id);
    }
  };

  const handleRegenerate = () => {
    if (onRegenerate && !isStreaming) {
      onRegenerate();
    }
  };

  const handleBranch = () => {
    if (onBranch) {
      onBranch(message.id);
    }
  };

  const handleSaveSelectionToNote = async () => {
    // 防止重复点击
    if (savingToNote) return;
    
    // 如果消息有内容，即使流式响应还在进行中，也允许保存
    // 这样可以避免流式响应完成后状态未及时更新的问题
    if (isStreaming && !message.content?.trim()) {
      // 只有在流式响应中且消息内容为空时才禁用
      return;
    }

    try {
      // 仅针对 AI 消息保存到 Note
      if (message.role !== 'assistant') {
        showError('仅支持保存 AI 消息内容', '用户消息无法保存为 Note');
        return;
      }

      setSavingToNote(true);

      // 尝试获取选中的文本
      const selection = window.getSelection();
      let text = '';

      if (selection && !selection.isCollapsed) {
        // 检查选中内容是否在当前消息内
        const container = document.getElementById(`message-${message.id}`);
        if (container) {
          const { anchorNode, focusNode } = selection;
          const isInside =
            (anchorNode && (container.contains(anchorNode) || container === anchorNode.parentElement)) ||
            (focusNode && (container.contains(focusNode) || container === focusNode.parentElement));

          if (isInside) {
            text = selection.toString().trim();
          }
        }
      }

      // 如果没有有效选区，则使用整条消息内容
      if (!text) {
        // 优先使用原始 content，如果没有则尝试从 metadata 中提取
        text = message.content?.trim() || '';
        
        // 如果是思维导图类型，尝试提取结构化数据
        if (!text && message.metadata?.contentType === 'mind_map') {
          const mindMapData = message.metadata?.mindMapData;
          if (mindMapData) {
            text = JSON.stringify(mindMapData, null, 2);
          }
        }

        // 如果还是没有内容，尝试从 displayContent 或其他字段获取
        if (!text && (message as any).displayContent) {
          text = String((message as any).displayContent).trim();
        }
      }

      if (!text || text.length === 0) {
        showError('无法保存', '消息内容为空，无法保存为 Note');
        setSavingToNote(false);
        return;
      }

      const userId = localStorage.getItem('userId') || 'default_user';
      const sessionId = localStorage.getItem('sessionId') || 'default_session';
      const action = message.metadata?.agentId || message.agentName || 'agent_output';
      const name = `${action}_${Date.now()}`;
      const title = message.agentName 
        ? `${message.agentName} 输出片段` 
        : message.metadata?.contentType === 'mind_map'
        ? '思维导图'
        : 'AI 输出片段';

      console.log('[EnhancedMessageActions] 保存到 Note:', { userId, sessionId, action, name, textLength: text.length });

      const res = await createNote({
        user_id: userId,
        session_id: sessionId,
        action,
        name,
        context: text,
        title,
        content_type: message.metadata?.contentType || 'text',
        metadata: {
          ...(message.metadata || {}),
          source_message_id: message.id,
          saved_from: 'chat_selection',
          agent_name: message.agentName,
        },
      });

      if (res.success) {
        success('保存成功', `内容已保存到 Notes，可在左侧工作区查看`);
        
        // 刷新当前会话的 Notes 列表，确保左侧 Notes 面板能立即看到
        try {
          await loadNotes(userId, sessionId);
        } catch (loadErr) {
          console.warn('[EnhancedMessageActions] 刷新 Notes 列表失败:', loadErr);
          // 即使刷新失败也不影响保存成功的提示
        }
      } else {
        showError('保存失败', res.message || '无法保存到 Notes，请稍后重试');
        console.error('[EnhancedMessageActions] 保存到 Note 失败:', res);
      }
    } catch (err) {
      console.error('[EnhancedMessageActions] 保存选中内容到 Note 失败:', err);
      showError('保存失败', err instanceof Error ? err.message : '保存过程中发生错误，请稍后重试');
    } finally {
      setSavingToNote(false);
    }
  };

  return (
    <div className="flex items-center gap-1">
      {/* 复制按钮 */}
      <button
        onClick={handleCopy}
        className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors"
        title="复制"
      >
        {copied ? (
          <Check className="w-4 h-4 text-green-600" />
        ) : (
          <Copy className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {/* 编辑按钮 - 仅用户消息或可编辑的AI消息 */}
      {canEdit && onEdit && (
        <button
          onClick={handleEdit}
          disabled={isStreaming}
          className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="编辑"
        >
          <Edit2 className="w-4 h-4 text-gray-400" />
        </button>
      )}

      {/* 重新生成按钮 - 仅AI消息 */}
      {canRegenerate && onRegenerate && message.role === 'assistant' && (
        <button
          onClick={handleRegenerate}
          disabled={isStreaming}
          className={`p-1.5 rounded-lg transition-colors ${
            isStreaming
              ? 'opacity-50 cursor-not-allowed'
              : 'hover:bg-gray-200'
          }`}
          title="重新生成"
        >
          <RefreshCw className={`w-4 h-4 text-gray-400 ${isStreaming ? 'animate-spin' : ''}`} />
        </button>
      )}

      {/* 创建分支按钮 */}
      {onBranch && message.role === 'assistant' && (
        <button
          onClick={handleBranch}
          disabled={isStreaming}
          className="p-1.5 rounded-lg hover:bg-gray-200 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="创建分支"
        >
          <GitBranch className="w-4 h-4 text-gray-400" />
        </button>
      )}

      {/* 删除按钮 */}
      {onDelete && (
        <button
          onClick={handleDelete}
          disabled={isStreaming}
          className="p-1.5 rounded-lg hover:bg-red-100 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title="删除"
        >
          <Trash2 className="w-4 h-4 text-gray-400 hover:text-red-600" />
        </button>
      )}

      {/* 收藏按钮 */}
      <button
        onClick={() => setBookmarked(!bookmarked)}
        className={`p-1.5 rounded-lg transition-colors ${
          bookmarked ? 'bg-yellow-100' : 'hover:bg-gray-200'
        }`}
        title="收藏"
      >
        <Bookmark
          className={`w-4 h-4 ${
            bookmarked ? 'text-yellow-600 fill-yellow-600' : 'text-gray-400'
          }`}
        />
      </button>

      {/* 🆕 保存选中内容为 Note（仅AI消息） */}
      {message.role === 'assistant' && (
        <button
          onClick={handleSaveSelectionToNote}
          disabled={
            savingToNote || 
            // 只有在流式响应中且消息内容为空时才禁用
            // 如果消息有内容，即使流式响应还在进行中，也允许保存
            (isStreaming && !message.content?.trim()) ||
            // 错误状态的消息不允许保存
            message.status === 'error'
          }
          className={`p-1.5 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
            savingToNote 
              ? 'bg-blue-100 cursor-wait' 
              : message.status === 'error'
              ? 'opacity-30'
              : 'hover:bg-gray-200'
          }`}
          title={
            savingToNote 
              ? '正在保存...' 
              : message.status === 'error'
              ? '错误消息无法保存'
              : (isStreaming && !message.content?.trim())
              ? '等待内容输出...'
              : '将选中内容保存为 Note（未选中则保存整条消息）'
          }
        >
          <FilePlus2 className={`w-4 h-4 ${savingToNote ? 'text-blue-600 animate-pulse' : 'text-gray-400'}`} />
        </button>
      )}
    </div>
  );
}

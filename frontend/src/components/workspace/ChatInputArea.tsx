/**
 * 简单的输入区域组件
 * 用于 ChatPanel，接受外部回调函数
 */

import { useState, useRef, useEffect, KeyboardEvent, useMemo } from 'react';
import { Send, Layers, FileText, Mic } from 'lucide-react';
import { useWorkspaceStore, type Note } from '@/store/workspaceStore';
import { AGENTS_CONFIG } from '@/config/agents';
import { clsx } from 'clsx';

interface ChatInputAreaProps {
  onSend: (content: string) => void | Promise<void>;
  disabled?: boolean;
  placeholder?: string;
  suggestions?: string[];
}

export default function ChatInputArea({
  onSend,
  disabled = false,
  placeholder = '发送消息...',
  suggestions = [],
}: ChatInputAreaProps) {
  const [input, setInput] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const { notes, setViewMode } = useWorkspaceStore();

  const selectedNotes = useMemo(() => notes.filter((n) => n.select_status === 1), [notes]);

  // 🆕 创建 agent action 到 displayName 的映射
  const agentDisplayNameMap = useMemo(() => {
    const map = new Map<string, string>();
    AGENTS_CONFIG.forEach(agent => {
      map.set(agent.id, agent.displayName);
      map.set(agent.name, agent.displayName);
      map.set(agent.id.replace('_', '_'), agent.displayName);
      map.set(agent.name.toLowerCase(), agent.displayName);
    });
    return map;
  }, []);

  // 🆕 生成笔记引用名称（与 InputArea.tsx 保持一致）
  const generateNoteReference = (note: Note): string => {
    // 获取 agent 的显示名称
    const agentDisplayName = agentDisplayNameMap.get(note.action || '') || 
                            note.metadata?.agent_name || 
                            note.action?.replace(/_agent$/, '').replace(/_/g, ' ') ||
                            'note';
    
    // 将显示名称转换为适合引用的格式（去除空格，使用下划线）
    const agentNameForRef = agentDisplayName
      .replace(/\s+/g, '_')
      .replace(/[^\w\u4e00-\u9fa5_]/g, '') // 保留中文、英文、数字和下划线
      .toLowerCase();

    // 计算该 agent 下的笔记索引（按创建时间排序）
    const sameActionNotes = notes
      .filter(n => n.action === note.action)
      .sort((a, b) => {
        // 按创建时间排序
        const timeA = new Date(a.created_at || 0).getTime();
        const timeB = new Date(b.created_at || 0).getTime();
        return timeA - timeB;
      });
    
    const noteIndex = sameActionNotes.findIndex(n => n.id === note.id) + 1;

    return `${agentNameForRef}_${noteIndex}`;
  };

  // 🆕 解析笔记引用名称，找到对应的笔记
  const findNoteByReference = (refName: string): Note | null => {
    // 尝试匹配所有笔记的引用名称
    for (const note of notes) {
      const noteRef = generateNoteReference(note);
      if (noteRef === refName) {
        return note;
      }
    }
    return null;
  };

  // 🆕 解析输入内容中的 @笔记名称，替换为完整笔记内容
  const expandNoteReferences = (text: string): string => {
    // 匹配 @笔记名称 格式（支持 @笔记名 或 @笔记名_数字）
    const noteRefPattern = /@([a-z0-9_\u4e00-\u9fa5]+(?:_\d+)?)/g;
    let expandedText = text;
    const foundRefs = new Set<string>();

    // 收集所有笔记引用
    let match;
    while ((match = noteRefPattern.exec(text)) !== null) {
      const refName = match[1];
      if (!foundRefs.has(refName)) {
        foundRefs.add(refName);
        const note = findNoteByReference(refName);
        if (note) {
          // 替换为完整笔记内容
          const noteContent = [
            `【${note.title || note.name || '笔记'}】`,
            note.context || '',
            note.metadata?.agent_name ? `\n来源：${note.metadata.agent_name}` : ''
          ].filter(Boolean).join('\n');
          
          expandedText = expandedText.replace(
            new RegExp(`@${refName.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}`, 'g'),
            noteContent
          );
        }
      }
    }

    return expandedText;
  };

  // 自动调整高度
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  // 语音输入初始化
  useEffect(() => {
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SpeechRecognition) {
      setSpeechSupported(false);
      return;
    }
    setSpeechSupported(true);
    const recognition: SpeechRecognition = new SpeechRecognition();
    recognition.lang = 'zh-CN';
    recognition.continuous = true;
    recognition.interimResults = false;
    recognition.onresult = (event: SpeechRecognitionEvent) => {
      const lastResult = event.results[event.results.length - 1];
      if (lastResult && lastResult.isFinal) {
        const transcript = lastResult[0].transcript.trim();
        setInput((prev) => (prev ? `${prev} ${transcript}` : transcript));
      }
    };
    recognition.onend = () => {
      setIsRecording(false);
    };
    recognition.onerror = () => {
      setIsRecording(false);
    };
    recognitionRef.current = recognition;
  }, []);

  const handleSend = async () => {
    if (!input.trim() || disabled) return;
    
    // 🆕 解析笔记引用，将 @笔记名称 替换为完整内容
    const expandedContent = expandNoteReferences(input.trim());
    
    console.log('[ChatInputArea] 发送消息:', {
      original: input.trim(),
      expanded: expandedContent.substring(0, 200) + (expandedContent.length > 200 ? '...' : '')
    });
    
    await onSend(expandedContent);
    setInput('');
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleInsertNotes = () => {
    if (selectedNotes.length === 0) return;
    
    // 🆕 插入 @笔记名称 格式，而不是完整内容
    const noteRefs = selectedNotes.map(note => `@${generateNoteReference(note)}`).join(' ');
    const separator = input.trim() ? ' ' : '';
    setInput((prev) => prev ? `${prev}${separator}${noteRefs} ` : `${noteRefs} `);
    
    // 设置光标位置到末尾
    setTimeout(() => {
      if (textareaRef.current) {
        const newLength = textareaRef.current.value.length;
        textareaRef.current.setSelectionRange(newLength, newLength);
        textareaRef.current.focus();
      }
    }, 0);
  };

  const toggleRecording = () => {
    if (!speechSupported || !recognitionRef.current) return;
    if (isRecording) {
      recognitionRef.current.stop();
      setIsRecording(false);
    } else {
      recognitionRef.current.start();
      setIsRecording(true);
    }
  };

  return (
    <div className="relative">
      {/* 快捷建议 */}
      {suggestions.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-2">
          {suggestions.slice(0, 3).map((suggestion) => (
            <button
              key={suggestion}
              type="button"
              onClick={() => setInput(suggestion)}
              className="px-3 py-1.5 text-xs rounded-full border border-gray-200 bg-white text-gray-600 hover:border-blue-200 hover:text-blue-600 hover:bg-blue-50 transition-colors"
              disabled={disabled}
            >
              {suggestion}
            </button>
          ))}
        </div>
      )}

      <textarea
        ref={textareaRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        disabled={disabled}
        rows={1}
        className={clsx(
          'w-full px-4 py-3 pr-12 rounded-lg',
          'bg-gray-50 border border-gray-200',
          'focus:bg-white focus:border-blue-500 focus:ring-2 focus:ring-blue-500/20',
          'resize-none transition-all duration-200',
          'placeholder:text-gray-400',
          disabled && 'opacity-50 cursor-not-allowed'
        )}
      />

      {/* Notes 操作 */}
      {notes.length > 0 && (
        <div className="flex items-center gap-2 mt-2 text-xs text-gray-500">
          <button
            type="button"
            onClick={handleInsertNotes}
            disabled={selectedNotes.length === 0 || disabled}
            className={clsx(
              'inline-flex items-center gap-1 px-2.5 py-1 rounded-full border',
              selectedNotes.length > 0
                ? 'border-indigo-200 text-indigo-600 hover:bg-indigo-50'
                : 'border-gray-200 text-gray-400 cursor-not-allowed'
            )}
          >
            <Layers className="w-3.5 h-3.5" />
            插入已选 Notes
          </button>
          <button
            type="button"
            onClick={() => setViewMode('notes')}
            className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            <FileText className="w-3.5 h-3.5" />
            查看 Notes
          </button>
          <span className="ml-auto">Enter 发送 · Shift+Enter 换行</span>
        </div>
      )}

      <button
        onClick={handleSend}
        disabled={disabled || !input.trim()}
        className={clsx(
          'absolute right-2 bottom-2',
          'p-2 rounded-lg transition-colors',
          'bg-blue-600 text-white hover:bg-blue-700',
          'disabled:opacity-40 disabled:cursor-not-allowed'
        )}
        title="发送 (Enter)"
      >
        <Send className="w-4 h-4" />
      </button>

      {speechSupported && (
        <button
          type="button"
          onClick={toggleRecording}
          className={clsx(
            'absolute right-12 bottom-2 p-2 rounded-lg transition-colors',
            isRecording ? 'bg-red-50 text-red-600' : 'bg-gray-100 text-gray-500 hover:bg-gray-200'
          )}
          title={isRecording ? '停止语音输入' : '语音输入'}
        >
          <Mic className="w-4 h-4" />
        </button>
      )}
    </div>
  );
}

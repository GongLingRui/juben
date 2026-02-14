/**
 * 输入区域组件
 * 支持@引用Notes功能
 */

import { useState, useRef, useEffect, KeyboardEvent, useMemo } from 'react';
import { useChat } from '@/hooks/useChat';
import { Send, Paperclip, Mic, X, Square, Layers, AudioLines, Search } from 'lucide-react';
import { useSettingsStore } from '@/store/settingsStore';
import { useWorkspaceStore } from '@/store/workspaceStore';
import { useAgentStore } from '@/store/agentStore';
import { addProjectFile } from '@/services/projectService';
import { transcribeAudio } from '@/services/asrService';
import { clsx } from 'clsx';
import { AGENTS_CONFIG } from '@/config/agents';

export default function InputArea() {
  const { sendMessage, isStreaming, stopStreaming } = useChat();
  const { fontSize } = useSettingsStore();
  const { notes, loadNotes } = useWorkspaceStore();
  const { getActiveAgent } = useAgentStore();
  const [input, setInput] = useState('');
  const [files, setFiles] = useState<File[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const [asrSupported, setAsrSupported] = useState(false);
  const [asrRecording, setAsrRecording] = useState(false);
  const [asrTranscribing, setAsrTranscribing] = useState(false);
  const [asrError, setAsrError] = useState<string | null>(null);
  const recordedChunksRef = useRef<Blob[]>([]);

  // 🆕 @引用相关状态
  const [showAtMention, setShowAtMention] = useState(false);
  const [atSearchQuery, setAtSearchQuery] = useState('');
  const [atCursorIndex, setAtCursorIndex] = useState(-1);
  const [selectedNoteIndex, setSelectedNoteIndex] = useState(0);
  const dropdownRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    const supported = typeof MediaRecorder !== 'undefined' && !!navigator.mediaDevices?.getUserMedia;
    setAsrSupported(supported);
  }, []);

  // 🆕 创建 agent action 到 displayName 的映射
  const agentDisplayNameMap = useMemo(() => {
    const map = new Map<string, string>();
    AGENTS_CONFIG.forEach(agent => {
      // 支持多种 action 格式匹配
      map.set(agent.id, agent.displayName);
      map.set(agent.name, agent.displayName);
      map.set(agent.id.replace('_', '_'), agent.displayName);
      map.set(agent.name.toLowerCase(), agent.displayName);
    });
    return map;
  }, []);

  // 🆕 使用 ref 存储状态，避免闭包问题
  const atCursorIndexRef = useRef(-1);
  const showAtMentionRef = useRef(false);

  useEffect(() => {
    atCursorIndexRef.current = atCursorIndex;
  }, [atCursorIndex]);

  useEffect(() => {
    showAtMentionRef.current = showAtMention;
  }, [showAtMention]);

  // 🆕 监听@符号输入
  useEffect(() => {
    const handleInputChange = (e: Event) => {
      const target = e.target as HTMLTextAreaElement;
      const value = target.value;
      const cursorPosition = target.selectionStart;
      const currentAtCursorIndex = atCursorIndexRef.current;
      const currentShowAtMention = showAtMentionRef.current;

      // 检查是否刚刚输入了@
      if (value[cursorPosition - 1] === '@') {
        const newAtCursorIndex = cursorPosition - 1;
        atCursorIndexRef.current = newAtCursorIndex;
        setAtCursorIndex(newAtCursorIndex);
        setShowAtMention(true);
        showAtMentionRef.current = true;
        setAtSearchQuery('');
        setSelectedNoteIndex(0);
        
        // 🆕 自动加载笔记列表
        const userId = localStorage.getItem('userId') || 'default_user';
        const sessionId = localStorage.getItem('sessionId') || 'default_session';
        loadNotes(userId, sessionId).catch(err => {
          console.warn('[InputArea] 加载笔记失败:', err);
        });
      } else if (currentShowAtMention && currentAtCursorIndex >= 0) {
        // 在@引用模式下，更新搜索查询
        const textAfterAt = value.substring(currentAtCursorIndex + 1, cursorPosition);
        setAtSearchQuery(textAfterAt);

        // 检查是否按了空格、换行或退格，关闭引用菜单
        const lastChar = value[cursorPosition - 1];
        if (lastChar === ' ' || lastChar === '\n' || cursorPosition <= currentAtCursorIndex) {
          setShowAtMention(false);
          showAtMentionRef.current = false;
          setAtSearchQuery('');
        }
      }
    };

    const textarea = textareaRef.current;
    if (textarea) {
      textarea.addEventListener('input', handleInputChange);
      return () => textarea.removeEventListener('input', handleInputChange);
    }
  }, [loadNotes]);

  // 🆕 点击外部关闭下拉菜单
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      const target = e.target as Node;
      // 检查点击是否在输入框或下拉菜单外部
      if (
        dropdownRef.current && 
        !dropdownRef.current.contains(target) &&
        textareaRef.current &&
        !textareaRef.current.contains(target)
      ) {
        console.log('[InputArea] 点击外部，关闭笔记列表');
        setShowAtMention(false);
        showAtMentionRef.current = false;
        setAtSearchQuery('');
      }
    };

    if (showAtMention) {
      document.addEventListener('mousedown', handleClickOutside);
      return () => document.removeEventListener('mousedown', handleClickOutside);
    }
  }, [showAtMention]);

  // 🆕 过滤Notes（支持按 agent 名称和笔记内容搜索）
  const filteredNotes = useMemo(() => {
    if (!atSearchQuery.trim()) {
      return notes.slice(0, 10); // 无搜索时显示前10条
    }

    const searchLower = atSearchQuery.toLowerCase().trim();
    return notes.filter(note => {
      // 搜索笔记标题
      const title = (note.title || note.name || '').toLowerCase();
      if (title.includes(searchLower)) return true;

      // 搜索笔记内容（前200字符）
      const context = (note.context || '').toLowerCase().substring(0, 200);
      if (context.includes(searchLower)) return true;

      // 搜索 agent 显示名称
      const agentDisplayName = agentDisplayNameMap.get(note.action || '') || '';
      if (agentDisplayName.toLowerCase().includes(searchLower)) return true;

      // 搜索 action 字段
      const action = (note.action || '').toLowerCase();
      if (action.includes(searchLower)) return true;

      // 搜索 metadata 中的 agent_name
      const metadataAgentName = (note.metadata?.agent_name || '').toLowerCase();
      if (metadataAgentName.includes(searchLower)) return true;

      return false;
    }).slice(0, 10); // 限制显示10条
  }, [notes, atSearchQuery, agentDisplayNameMap]);

  // 🆕 调试：监听 showAtMention 状态变化
  useEffect(() => {
    if (showAtMention) {
      console.log('[InputArea] 笔记列表显示状态:', {
        showAtMention,
        notesCount: notes.length,
        filteredCount: filteredNotes.length,
        atCursorIndex,
        atSearchQuery
      });
    }
  }, [showAtMention, notes.length, filteredNotes.length, atCursorIndex, atSearchQuery]);

  const isLikelyTextFile = (file: File) => {
    if (file.type.startsWith('text/')) return true;
    if (file.type === 'application/json') return true;
    const lower = file.name.toLowerCase();
    return ['.txt', '.md', '.json', '.csv', '.srt'].some(ext => lower.endsWith(ext));
  };

  const handleSend = async () => {
    if (isStreaming || isUploading) return;
    if (!input.trim() && files.length === 0) return;

    setUploadError(null);

    let referencesText = '';
    if (files.length > 0) {
      const projectId = localStorage.getItem('projectId') || '';
      if (!projectId) {
        setUploadError('请先进入一个项目后再上传文件');
        return;
      }

      setIsUploading(true);
      const uploadedRefs: string[] = [];
      const errors: string[] = [];

      for (const file of files) {
        if (!isLikelyTextFile(file)) {
          errors.push(`${file.name} 暂不支持该格式`);
          continue;
        }
        try {
          const content = await file.text();
          if (!content.trim()) {
            errors.push(`${file.name} 内容为空`);
            continue;
          }
          const result = await addProjectFile(projectId, {
            filename: file.name,
            file_type: 'reference',
            content,
            agent_source: 'user_upload',
            tags: ['user_upload', 'chat_upload']
          });
          if (result.file?.id) {
            uploadedRefs.push(result.file.id);
          } else {
            errors.push(`${file.name} 上传失败`);
          }
        } catch (error) {
          console.error('上传文件失败:', error);
          errors.push(`${file.name} 上传失败`);
        }
      }

      setIsUploading(false);

      if (errors.length > 0) {
        setUploadError(errors.slice(0, 2).join('；'));
      }
      if (uploadedRefs.length > 0) {
        referencesText = `\n\n参考文件：${uploadedRefs.map((id) => `@file[${id}]`).join(' ')}`;
      } else if (!input.trim()) {
        setUploadError('文件上传失败，未发送消息');
        return;
      }
    }

    const activeAgent = getActiveAgent();
    let baseInput =
      input.trim() ||
      (activeAgent?.category === 'evaluation'
        ? '请基于上传的文件进行评估'
        : '请基于上传的文件进行分析');

    // 🆕 解析笔记引用，将 @笔记名称 替换为完整内容
    baseInput = expandNoteReferences(baseInput);
    
    console.log('[InputArea] 发送消息:', {
      original: input.trim(),
      expanded: baseInput.substring(0, 200) + (baseInput.length > 200 ? '...' : '')
    });

    sendMessage(`${baseInput}${referencesText}`);
    setInput('');
    setFiles([]);
  };

  // 🆕 生成Note引用名称：agent显示名_序号
  const generateNoteReference = (note: any): string => {
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
  const findNoteByReference = (refName: string): any => {
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

  // 🆕 选择Note引用
  const selectNoteReference = (note: any) => {
    const refName = generateNoteReference(note);
    const beforeAt = input.substring(0, atCursorIndex);
    // 计算 @ 符号后的文本长度（包括搜索查询）
    const afterAtStart = atCursorIndex + 1;
    const afterAt = input.substring(afterAtStart + atSearchQuery.length);
    const newInput = `${beforeAt}@${refName} ${afterAt}`;

    setInput(newInput);
    setShowAtMention(false);
    setAtSearchQuery('');

    // 设置光标位置到引用后
    setTimeout(() => {
      if (textareaRef.current) {
        const newCursorPos = atCursorIndex + refName.length + 2; // +2 for @ and space
        textareaRef.current.setSelectionRange(newCursorPos, newCursorPos);
        textareaRef.current.focus();
      }
    }, 0);
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    // 🆕 检测 @ 符号输入（通过键盘事件，更可靠）
    if (e.key === '@' || (e.key === '2' && e.shiftKey)) {
      // 延迟一帧，确保 @ 已经输入到 textarea
      setTimeout(() => {
        const textarea = textareaRef.current;
        if (textarea) {
          const cursorPosition = textarea.selectionStart;
          const value = textarea.value;
          
          // 检查光标前是否有 @
          if (value[cursorPosition - 1] === '@') {
            const atIndex = cursorPosition - 1;
            atCursorIndexRef.current = atIndex;
            setAtCursorIndex(atIndex);
            setShowAtMention(true);
            showAtMentionRef.current = true;
            setAtSearchQuery('');
            setSelectedNoteIndex(0);
            
            console.log('[InputArea] 通过键盘事件检测到 @ 符号', {
              atIndex,
              cursorPosition,
              value: value.substring(0, 20)
            });
            
            // 自动加载笔记列表
            const userId = localStorage.getItem('userId') || 'default_user';
            const sessionId = localStorage.getItem('sessionId') || 'default_session';
            loadNotes(userId, sessionId).catch(err => {
              console.warn('[InputArea] 加载笔记失败:', err);
            });
          }
        }
      }, 0);
    }

    // 🆕 处理@引用菜单的键盘导航
    if (showAtMention && filteredNotes.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setSelectedNoteIndex(prev =>
          prev < filteredNotes.length - 1 ? prev + 1 : 0
        );
        // 滚动到选中项
        setTimeout(() => {
          const selectedElement = document.getElementById(`note-option-${selectedNoteIndex}`);
          selectedElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }, 0);
      } else if (e.key === 'ArrowUp') {
        e.preventDefault();
        setSelectedNoteIndex(prev =>
          prev > 0 ? prev - 1 : filteredNotes.length - 1
        );
        // 滚动到选中项
        setTimeout(() => {
          const selectedElement = document.getElementById(`note-option-${selectedNoteIndex}`);
          selectedElement?.scrollIntoView({ block: 'nearest', behavior: 'smooth' });
        }, 0);
      } else if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        const selectedNote = filteredNotes[selectedNoteIndex];
        if (selectedNote) {
          selectNoteReference(selectedNote);
        }
      } else if (e.key === 'Escape') {
        e.preventDefault();
        setShowAtMention(false);
        showAtMentionRef.current = false;
        setAtSearchQuery('');
      }
      return;
    }

    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  };

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFiles = Array.from(e.target.files || []);
    setFiles((prev) => [...prev, ...selectedFiles]);
  };

  const removeFile = (index: number) => {
    setFiles((prev) => prev.filter((_, i) => i !== index));
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

  const startAsrRecording = async () => {
    if (!asrSupported || asrRecording) return;
    setAsrError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = stream;
      const recorder = new MediaRecorder(stream);
      recordedChunksRef.current = [];
      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          recordedChunksRef.current.push(event.data);
        }
      };
      recorder.onstop = async () => {
        const blob = new Blob(recordedChunksRef.current, { type: 'audio/webm' });
        setAsrTranscribing(true);
        const result = await transcribeAudio(blob, 'zh');
        setAsrTranscribing(false);
        if (result.success && result.text) {
          setAsrError(null);
          setInput((prev) => (prev ? `${prev} ${result.text}` : result.text || ''));
        } else {
          setAsrError(result.message || '语音转写失败');
        }
      };
      recorder.start();
      mediaRecorderRef.current = recorder;
      setAsrRecording(true);
    } catch (error) {
      setAsrError('麦克风权限被拒绝或不可用');
      setAsrRecording(false);
    }
  };

  const stopAsrRecording = () => {
    const recorder = mediaRecorderRef.current;
    if (!recorder) return;
    recorder.stop();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    mediaStreamRef.current = null;
    mediaRecorderRef.current = null;
    setAsrRecording(false);
  };

  return (
    <div className="border-t border-gray-200 bg-white p-4">
      {uploadError && (
        <div className="mb-2 text-xs text-red-600 bg-red-50 border border-red-200 px-2 py-1 rounded">
          {uploadError}
        </div>
      )}
      {asrError && (
        <div className="mb-2 text-xs text-red-600 bg-red-50 border border-red-200 px-2 py-1 rounded">
          {asrError}
        </div>
      )}
      {/* 文件列表 */}
      {files.length > 0 && (
        <div className="flex flex-wrap gap-2 mb-3 animate-slide-down">
          {files.map((file, index) => (
            <div
              key={index}
              className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 rounded-lg text-sm animate-fade-in hover:shadow-md transition-all"
              style={{ animationDelay: `${index * 50}ms` }}
            >
              <Paperclip className="w-4 h-4 text-gray-500" />
              <span className="text-gray-700 max-w-[200px] truncate">{file.name}</span>
              <button
                onClick={() => removeFile(index)}
                className="p-0.5 hover:bg-gray-200 rounded hover-scale active-scale"
              >
                <X className="w-3 h-3 text-gray-500" />
              </button>
            </div>
          ))}
        </div>
      )}

      {/* 输入框 */}
      <div className="flex items-end gap-3 max-w-4xl mx-auto">
        {/* 附件按钮 */}
        <label className="flex-shrink-0 p-2 rounded-lg hover:bg-gray-100 cursor-pointer transition-all hover-scale active-scale icon-bounce">
          <input
            type="file"
            multiple
            onChange={handleFileSelect}
            className="hidden"
          />
          <Paperclip className="w-5 h-5 text-gray-500" />
        </label>

        {/* 文本输入 */}
        <div className="flex-1 relative">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => {
              const newValue = e.target.value;
              const oldValue = input;
              const cursorPosition = e.target.selectionStart;
              
              setInput(newValue);
              
              // 🆕 检测 @ 符号输入 - 改进的检测逻辑
              // 方法1: 检查新输入的字符
              const newChar = newValue[cursorPosition - 1];
              const isAtSymbol = newChar === '@';
              
              // 方法2: 检查是否在光标前有 @ 符号（更可靠）
              const textBeforeCursor = newValue.substring(0, cursorPosition);
              const lastAtIndex = textBeforeCursor.lastIndexOf('@');
              const hasAtBeforeCursor = lastAtIndex >= 0;
              
              // 检查 @ 后是否有空格或换行（如果有，说明是新的 @）
              const textAfterLastAt = textBeforeCursor.substring(lastAtIndex + 1);
              const hasSpaceAfterAt = textAfterLastAt.includes(' ') || textAfterLastAt.includes('\n');
              
              if (isAtSymbol || (hasAtBeforeCursor && !hasSpaceAfterAt && !showAtMentionRef.current)) {
                // 刚刚输入了 @ 或光标在 @ 后且没有空格
                const atIndex = lastAtIndex >= 0 ? lastAtIndex : cursorPosition - 1;
                atCursorIndexRef.current = atIndex;
                setAtCursorIndex(atIndex);
                setShowAtMention(true);
                showAtMentionRef.current = true;
                setAtSearchQuery('');
                setSelectedNoteIndex(0);
                
                console.log('[InputArea] @ 符号检测成功，显示笔记列表', {
                  atIndex,
                  cursorPosition,
                  newValue: newValue.substring(0, 20)
                });
                
                // 自动加载笔记列表
                const userId = localStorage.getItem('userId') || 'default_user';
                const sessionId = localStorage.getItem('sessionId') || 'default_session';
                loadNotes(userId, sessionId).catch(err => {
                  console.warn('[InputArea] 加载笔记失败:', err);
                });
              } else if (showAtMentionRef.current && atCursorIndexRef.current >= 0) {
                // 在@引用模式下，更新搜索查询
                const currentAtIndex = atCursorIndexRef.current;
                const textAfterAt = newValue.substring(currentAtIndex + 1, cursorPosition);
                setAtSearchQuery(textAfterAt);

                // 检查是否按了空格、换行或退格，关闭引用菜单
                const lastChar = newValue[cursorPosition - 1];
                if (lastChar === ' ' || lastChar === '\n' || cursorPosition <= currentAtIndex) {
                  console.log('[InputArea] 关闭笔记列表', { lastChar, cursorPosition, currentAtIndex });
                  setShowAtMention(false);
                  showAtMentionRef.current = false;
                  setAtSearchQuery('');
                }
              }
            }}
            onKeyDown={handleKeyDown}
            placeholder="输入消息... 输入@可引用Notes"
            disabled={isStreaming}
            aria-label="消息输入框"
            aria-describedby="input-description"
            className={`w-full px-4 py-3 pr-12 border border-gray-200 rounded-xl resize-none focus:outline-none focus:border-black focus:ring-1 focus:ring-black transition-all input-focus-effect ${
              fontSize === 'sm' ? 'text-sm' : fontSize === 'lg' ? 'text-lg' : 'text-base'
            }`}
            rows={1}
            style={{ maxHeight: '200px' }}
          />

          {/* 字符计数 */}
          {input.length > 0 && (
            <span id="input-description" className="absolute bottom-2 right-14 text-xs text-gray-400" aria-live="polite">
              {input.length}
            </span>
          )}

          {/* 🆕 @引用下拉菜单 */}
          {showAtMention && (
            <div
              ref={dropdownRef}
              role="listbox"
              aria-label="引用笔记列表"
              aria-activedescendant={selectedNoteIndex >= 0 ? `note-option-${selectedNoteIndex}` : undefined}
              className="absolute bottom-full left-0 right-0 mb-2 bg-white border border-gray-200 rounded-xl shadow-lg max-h-80 overflow-hidden z-[100] animate-fade-in"
              style={{ 
                minWidth: '300px',
                maxWidth: '100%'
              }}
            >
              {/* 搜索框 */}
              {notes.length > 0 && (
                <div className="sticky top-0 bg-white border-b border-gray-200 p-2">
                  <div className="relative">
                    <Search className="absolute left-2 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                    <input
                      type="text"
                      value={atSearchQuery}
                      onChange={(e) => {
                        setAtSearchQuery(e.target.value);
                        setSelectedNoteIndex(0);
                      }}
                      placeholder="搜索笔记..."
                      className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                      autoFocus
                    />
                  </div>
                </div>
              )}

              {/* 笔记列表 */}
              <div className="max-h-64 overflow-y-auto">
                {filteredNotes.length > 0 ? (
                  filteredNotes.map((note, index) => {
                    const refName = generateNoteReference(note);
                    const isSelected = index === selectedNoteIndex;
                    const agentDisplayName = agentDisplayNameMap.get(note.action || '') || 
                                            note.metadata?.agent_name || 
                                            note.action?.replace(/_agent$/, '').replace(/_/g, ' ') ||
                                            '未知Agent';

                    return (
                      <div
                        key={note.id}
                        id={`note-option-${index}`}
                        role="option"
                        aria-selected={isSelected}
                        onClick={() => selectNoteReference(note)}
                        className={clsx(
                          'flex items-start gap-3 p-3 cursor-pointer transition-colors border-b border-gray-100 last:border-b-0',
                          isSelected ? 'bg-blue-50 border-blue-200' : 'hover:bg-gray-50'
                        )}
                      >
                        <Layers className={clsx(
                          'w-4 h-4 mt-0.5 flex-shrink-0',
                          isSelected ? 'text-blue-600' : 'text-gray-400'
                        )} aria-hidden="true" />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2 mb-1 flex-wrap">
                            <span className={clsx(
                              'text-sm font-medium font-mono',
                              isSelected ? 'text-blue-600' : 'text-gray-900'
                            )}>
                              @{refName}
                            </span>
                            <span className={clsx(
                              'text-xs px-2 py-0.5 rounded-full whitespace-nowrap',
                              isSelected ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-600'
                            )}>
                              {agentDisplayName}
                            </span>
                          </div>
                          <p className="text-xs text-gray-500 line-clamp-2">
                            {note.title || note.context?.substring(0, 100) || '无标题'}
                          </p>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="p-4 text-center text-gray-400 text-sm" role="status">
                    {notes.length === 0 ? (
                      <>
                        <Layers className="w-8 h-8 mx-auto mb-2 opacity-50" aria-hidden="true" />
                        <p>暂无Notes可用</p>
                        <p className="text-xs mt-1">与Agent对话后生成的内容将保存为Notes</p>
                      </>
                    ) : (
                      <>
                        <Search className="w-8 h-8 mx-auto mb-2 opacity-50" />
                        <p>未找到匹配的Notes</p>
                        <p className="text-xs mt-1">尝试使用不同的关键词搜索</p>
                      </>
                    )}
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* 发送/停止按钮 */}
        <button
          onClick={isStreaming ? stopStreaming : handleSend}
          disabled={(!input.trim() && files.length === 0 && !isStreaming) || isUploading}
          aria-label={isStreaming ? "停止生成" : "发送消息"}
          aria-pressed={isStreaming}
          className={`flex-shrink-0 p-3 rounded-xl transition-all hover-scale active-scale ${
            isStreaming
              ? 'bg-red-600 hover:bg-red-700 text-white hover:shadow-lg'
              : input.trim() || files.length > 0
              ? 'bg-black hover:bg-gray-800 text-white hover:shadow-lg button-ripple'
              : 'bg-gray-100 text-gray-400 cursor-not-allowed'
          }`}
        >
          {isStreaming ? (
            <Square className="w-5 h-5" />
          ) : (
            <Send className="w-5 h-5 send-icon-animate" />
          )}
        </button>

        {/* 浏览器语音输入按钮 */}
        {speechSupported && (
          <button
            onClick={toggleRecording}
            className={`flex-shrink-0 p-2 rounded-lg transition-all hover-scale active-scale icon-bounce ${
              isRecording ? 'bg-red-50' : 'hover:bg-gray-100'
            }`}
            title={isRecording ? '停止语音输入' : '语音输入'}
          >
            <Mic className={`w-5 h-5 ${isRecording ? 'text-red-600' : 'text-gray-500'}`} />
          </button>
        )}

        {/* ASR录音转写按钮 */}
        {asrSupported && (
          <button
            onClick={asrRecording ? stopAsrRecording : startAsrRecording}
            disabled={asrTranscribing}
            className={`flex-shrink-0 p-2 rounded-lg transition-all hover-scale active-scale icon-bounce ${
              asrRecording ? 'bg-blue-50' : 'hover:bg-gray-100'
            }`}
            title={asrRecording ? '停止录音并转写' : '录音转写'}
          >
            <AudioLines className={`w-5 h-5 ${asrRecording ? 'text-blue-600' : 'text-gray-500'}`} />
          </button>
        )}
      </div>

      {/* 提示文本 */}
      <div className="text-center mt-2">
        {isUploading && (
          <p className="text-xs text-gray-500 mb-1">正在上传文件...</p>
        )}
        <p className="text-xs text-gray-400">
          AI 生成的内容可能不准确，请核实重要信息
        </p>
        {asrTranscribing && (
          <p className="text-xs text-blue-500 mt-1">语音转写中...</p>
        )}
      </div>
    </div>
  );
}

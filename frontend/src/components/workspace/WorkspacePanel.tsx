/**
 * 工作区面板组件
显示 AI 生成的最终成果（剧本、大纲、思维导图、JSON 报告等）
 */

import { useWorkspaceStore, WorkspaceViewType, Note } from '@/store/workspaceStore';
import { useChatStore } from '@/store/chatStore';
import { useAgentStore } from '@/store/agentStore';
import {
  FileText,
  Network,
  Code,
  BookOpen,
  FileJson,
  Save,
  Copy,
  Download,
  Undo,
  Redo,
  Maximize2,
  Minimize2,
  CheckSquare,
  Square,
  Layers,
  ChevronDown
} from 'lucide-react';
import { useState, useEffect, useMemo } from 'react';
import { clsx } from 'clsx';

// 视图类型配置
const VIEW_TYPE_CONFIG: Record<
  WorkspaceViewType,
  { icon: any; label: string; color: string }
> = {
  document: { icon: FileText, label: '文档', color: 'blue' },
  mindmap: { icon: Network, label: '思维导图', color: 'green' },
  json: { icon: FileJson, label: 'JSON', color: 'purple' },
  outline: { icon: BookOpen, label: '大纲', color: 'orange' },
  script: { icon: FileText, label: '剧本', color: 'red' },
  evaluation: { icon: Code, label: '评估', color: 'cyan' },
  notes: { icon: Layers, label: 'Notes', color: 'indigo' },
};

export default function WorkspacePanel() {
  const {
    currentContent,
    viewMode,
    isDirty,
    canUndo,
    canRedo,
    notes,
    notesGroupedByAction,
    isLoadingNotes,
    toggleNoteSelection,
    exportNotes,
    exportSelectedNotes,
    createNoteFromContent,
    updateNotesSelectionBulk
  } = useWorkspaceStore();
  const { messages } = useChatStore();
  const { activeAgent, agents } = useAgentStore();

  const [isFullscreen, setIsFullscreen] = useState(false);
  const [selectedActionFilter, setSelectedActionFilter] = useState<string | null>(null);
  const [activeTocId, setActiveTocId] = useState<string | null>(null);
  const [tocCollapsed, setTocCollapsed] = useState(false);
  const [noteSaveHint, setNoteSaveHint] = useState<string | null>(null);

  // 加载Notes
  useEffect(() => {
    const userId = localStorage.getItem('userId') || 'default_user';
    const sessionId = localStorage.getItem('sessionId') || 'default_session';
    useWorkspaceStore.getState().loadNotes(userId, sessionId);
  }, []);

  // 获取最新的 AI 输出内容
  const activeAgentInfo = agents.find((agent) => agent.id === activeAgent);

  useEffect(() => {
    if (messages.length === 0) return;
    // 查找最新完成的 AI 消息作为工作区内容
    const latestAIMessage = [...messages]
      .reverse()
      .find((m) => m.role === 'assistant' && m.status === 'complete' && !!m.content);

    if (!latestAIMessage) return;

    const nextId = `msg_${latestAIMessage.id}`;
    if (currentContent?.id === nextId && currentContent.content === latestAIMessage.content) {
      return;
    }

    useWorkspaceStore.getState().setContent({
      id: nextId,
      type: 'document',
      title: `${activeAgentInfo?.displayName || activeAgent} 生成结果`,
      content: latestAIMessage.content,
      metadata: {
        agentId: activeAgent,
        agentName: activeAgentInfo?.displayName,
        timestamp: latestAIMessage.timestamp || new Date().toISOString(),
      },
    });
  }, [messages, currentContent, activeAgent, activeAgentInfo]);


  const handleSave = async () => {
    await useWorkspaceStore.getState().saveContent();
  };

  const handleCopy = async () => {
    await useWorkspaceStore.getState().copyContent();
  };

  const handleExport = async () => {
    await useWorkspaceStore.getState().exportContent('md');
  };

  const handleSaveAsNote = async () => {
    if (!currentContent) return;
    const noteId = await createNoteFromContent(currentContent);
    if (noteId) {
      const created = useWorkspaceStore.getState().notes.find((n) => n.id === noteId);
      if (created) {
        await useWorkspaceStore.getState().updateNoteSelection(created, true);
      }
      setNoteSaveHint('已保存为 Note');
      setTimeout(() => setNoteSaveHint(null), 2000);
    }
  };

  const handleUndo = () => {
    useWorkspaceStore.getState().undo();
  };

  const handleRedo = () => {
    useWorkspaceStore.getState().redo();
  };

  const handleViewChange = (newView: WorkspaceViewType) => {
    useWorkspaceStore.getState().setViewMode(newView);
  };

  const contentStats = currentContent
    ? {
        chars: currentContent.content.length,
        sections: Math.max(1, Math.ceil(currentContent.content.length / 500)),
      }
    : null;
  const contentToc = currentContent ? generateToc(currentContent.content) : [];

  useEffect(() => {
    if (!currentContent || contentToc.length === 0) return;
    const observer = new IntersectionObserver(
      (entries) => {
        const visible = entries
          .filter((entry) => entry.isIntersecting)
          .sort((a, b) => (a.boundingClientRect.top > b.boundingClientRect.top ? 1 : -1));
        if (visible.length > 0) {
          setActiveTocId(visible[0].target.id);
        }
      },
      { root: null, rootMargin: '0px 0px -70% 0px', threshold: 0.1 }
    );

    contentToc.forEach((item) => {
      const el = document.getElementById(item.id);
      if (el) observer.observe(el);
    });

    return () => observer.disconnect();
  }, [currentContent, contentToc]);

  return (
    <div
      className={clsx(
        'flex h-full min-w-0 flex-col bg-white',
        isFullscreen && 'fixed inset-0 z-50 w-full'
      )}
    >
      {/* 顶部工具栏 */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-200 bg-gray-50">
        <div className="flex items-center gap-3">
          {/* 视图类型切换 */}
          <div className="flex items-center gap-1 bg-white rounded-lg border border-gray-200 p-1">
            {(['document', 'notes'] as WorkspaceViewType[]).map((mode) => {
              const modeConfig = VIEW_TYPE_CONFIG[mode];
              const ModeIcon = modeConfig.icon;
              const isActive = viewMode === mode;
              return (
                <button
                  key={mode}
                  onClick={() => handleViewChange(mode)}
                  className={clsx(
                    'flex items-center gap-2 px-3 py-1.5 rounded-md text-sm transition-colors',
                    isActive
                      ? 'bg-gray-900 text-white'
                      : 'text-gray-600 hover:bg-gray-100'
                  )}
                >
                  <ModeIcon className="w-4 h-4" />
                  <span>{modeConfig.label}</span>
                </button>
              );
            })}
          </div>

          {/* 标题 */}
          {currentContent && (
            <h2 className="text-sm font-semibold text-gray-900 truncate max-w-md">
              {currentContent.title}
              {isDirty && <span className="text-red-500 ml-2">• 未保存</span>}
            </h2>
          )}
        </div>

        {/* 工具栏 */}
        <div className="flex items-center gap-2">
          {/* 撤销/重做 */}
          <div className="flex items-center gap-1 mr-2">
            <button
              onClick={handleUndo}
              disabled={!canUndo}
              className={clsx(
                'p-1.5 rounded-lg transition-colors',
                canUndo
                  ? 'hover:bg-gray-200 text-gray-700'
                  : 'text-gray-300 cursor-not-allowed'
              )}
              title="撤销"
            >
              <Undo className="w-4 h-4" />
            </button>
            <button
              onClick={handleRedo}
              disabled={!canRedo}
              className={clsx(
                'p-1.5 rounded-lg transition-colors',
                canRedo
                  ? 'hover:bg-gray-200 text-gray-700'
                  : 'text-gray-300 cursor-not-allowed'
              )}
              title="重做"
            >
              <Redo className="w-4 h-4" />
            </button>
          </div>

          {/* 保存 */}
          <button
            onClick={handleSave}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              isDirty
                ? 'bg-blue-600 text-white hover:bg-blue-700'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            )}
            title="保存"
          >
            <Save className="w-4 h-4" />
            <span className="hidden sm:inline">保存</span>
          </button>

          {/* 复制 */}
          <button
            onClick={handleCopy}
            className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-700 transition-colors"
            title="复制"
          >
            <Copy className="w-4 h-4" />
          </button>

          {/* 导出 */}
          <button
            onClick={handleExport}
            className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-700 transition-colors"
            title="导出"
          >
            <Download className="w-4 h-4" />
          </button>

          {/* 全屏切换 */}
          <button
            onClick={() => setIsFullscreen(!isFullscreen)}
            className="p-1.5 rounded-lg hover:bg-gray-200 text-gray-700 transition-colors"
            title={isFullscreen ? '退出全屏' : '全屏'}
          >
            {isFullscreen ? <Minimize2 className="w-4 h-4" /> : <Maximize2 className="w-4 h-4" />}
          </button>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="flex-1 overflow-auto scrollbar p-6">
        {viewMode === 'notes' ? (
          // Notes 视图
          <NotesView
            notes={notes}
            notesGroupedByAction={notesGroupedByAction}
            isLoadingNotes={isLoadingNotes}
            onToggleSelection={toggleNoteSelection}
            onExport={exportNotes}
            onExportSelected={exportSelectedNotes}
            onBulkSelect={updateNotesSelectionBulk}
            selectedActionFilter={selectedActionFilter}
            onActionFilterChange={setSelectedActionFilter}
          />
        ) : !currentContent ? (
          // 空状态
          <div className="h-full flex flex-col items-center justify-center text-gray-400">
            <FileText className="w-16 h-16 mb-4 opacity-50" />
            <p className="text-lg">暂无内容</p>
            <p className="text-sm mt-2">
              与右侧 Agent 对话后，生成的结果将显示在这里
            </p>
            {notes.length > 0 && (
              <button
                onClick={() => handleViewChange('notes')}
                className="mt-4 px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
              >
                查看 Notes
              </button>
            )}
          </div>
        ) : (
          // 文档视图
          <div className="prose prose-gray max-w-none">
            <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <div className="flex items-start justify-between gap-4">
                <div>
                  <div className="text-sm text-gray-500">生成结果</div>
                  <h2 className="text-base font-semibold text-gray-900 mt-1">
                    {currentContent.title}
                  </h2>
                  <div className="text-xs text-gray-500 mt-1">
                    {currentContent.metadata?.agentName || activeAgentInfo?.displayName || activeAgent}
                    {currentContent.metadata?.timestamp && (
                      <>
                        <span className="mx-2">•</span>
                        <span>
                          {new Date(currentContent.metadata.timestamp).toLocaleString('zh-CN')}
                        </span>
                      </>
                    )}
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleSaveAsNote}
                    className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    保存为 Note
                  </button>
                  <button
                    onClick={handleCopy}
                    className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
                  >
                    复制
                  </button>
                  <button
                    onClick={handleExport}
                    className="px-3 py-1.5 text-sm rounded-lg bg-gray-900 text-white hover:bg-gray-800"
                  >
                    导出 Markdown
                  </button>
                </div>
              </div>
              {contentStats && (
                <div className="mt-3 flex items-center gap-4 text-xs text-gray-500">
                  <span>{contentStats.chars} 字符</span>
                  <span>•</span>
                  <span>{contentStats.sections} 段</span>
                  {noteSaveHint && (
                    <>
                      <span>•</span>
                      <span className="text-green-600">{noteSaveHint}</span>
                    </>
                  )}
                </div>
              )}
            </div>
            {contentToc.length > 0 && (
              <div className="mb-4 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
                <div className="flex items-center justify-between mb-2">
                  <div className="text-sm font-medium text-gray-700">目录导航</div>
                  <button
                    onClick={() => setTocCollapsed((prev) => !prev)}
                    className="text-xs text-gray-500 hover:text-gray-700"
                  >
                    {tocCollapsed ? '展开' : '折叠'}
                  </button>
                </div>
                {!tocCollapsed && (
                  <div className="flex flex-wrap gap-2">
                    {contentToc.slice(0, 20).map((item) => (
                      <button
                        key={item.id}
                        onClick={() => {
                          const element = document.getElementById(item.id);
                          element?.scrollIntoView({ behavior: 'smooth', block: 'start' });
                        }}
                        className={clsx(
                          'px-3 py-1.5 text-xs rounded-full border transition-colors',
                          activeTocId === item.id
                            ? 'border-gray-900 text-gray-900 bg-gray-100'
                            : item.level === 1
                            ? 'border-gray-300 text-gray-700'
                            : item.level === 2
                            ? 'border-blue-200 text-blue-600'
                            : 'border-indigo-200 text-indigo-600'
                        )}
                      >
                        {item.text}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
            <div className="bg-white rounded-xl border border-gray-200 p-6 shadow-sm">
              {/* Markdown 渲染的内容 */}
              <div
                dangerouslySetInnerHTML={{
                  __html: renderMarkdown(currentContent.content),
                }}
              />
            </div>
          </div>
        )}
      </div>

      {/* 底部状态栏 */}
      {currentContent && (
        <div className="px-4 py-2 bg-gray-50 border-t border-gray-200 text-xs text-gray-500 flex items-center justify-between">
          <div className="flex items-center gap-4">
            <span>{currentContent.metadata?.agentName}</span>
            <span>•</span>
            <span>
              {currentContent.metadata?.timestamp
                ? new Date(
                    currentContent.metadata.timestamp
                  ).toLocaleString('zh-CN')
                : ''}
            </span>
          </div>
          <div className="flex items-center gap-4">
            <span>{currentContent.content.length} 字符</span>
            <span>•</span>
            <span>{Math.ceil(currentContent.content.length / 500)} 段</span>
          </div>
        </div>
      )}
    </div>
  );
}

// 简单的 Markdown 渲染函数
// 实际使用时建议安装 react-markdown 等库
function renderMarkdown(content: string): string {
  // 简单的 Markdown 转换
  let html = content
    // 转义 HTML
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    // 标题（带锚点）
    .replace(/^### (.*$)/gim, (_, text) => `<h3 id="${slugify(text)}">${text}</h3>`)
    .replace(/^## (.*$)/gim, (_, text) => `<h2 id="${slugify(text)}">${text}</h2>`)
    .replace(/^# (.*$)/gim, (_, text) => `<h1 id="${slugify(text)}">${text}</h1>`)
    // 粗体
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    // 斜体
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    // 代码块
    .replace(/```([\s\S]*?)```/g, '<pre><code>$1</code></pre>')
    .replace(/`(.*?)`/g, '<code class="bg-gray-100 px-1 rounded">$1</code>')
    // 链接
    .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline">$1</a>')
    // 无序列表
    .replace(/^\* (.*$)/gim, '<li>$1</li>')
    // 有序列表
    .replace(/^\d+\. (.*$)/gim, '<li>$1</li>')
    // 换行
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br />');

  return `<p>${html}</p>`;
}

function slugify(text: string): string {
  return text
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9\u4e00-\u9fa5\s-]/g, '')
    .replace(/\s+/g, '-')
    .replace(/-+/g, '-');
}

interface TocItem {
  id: string;
  text: string;
  level: 1 | 2 | 3;
}

function generateToc(content: string): TocItem[] {
  const items: TocItem[] = [];
  content.split('\n').forEach((line) => {
    const match = /^(#{1,3})\s+(.*)$/.exec(line.trim());
    if (!match) return;
    const level = match[1].length as 1 | 2 | 3;
    const text = match[2].trim();
    if (!text) return;
    items.push({ id: slugify(text), text, level });
  });
  return items;
}

// Notes视图组件
interface NotesViewProps {
  notes: Note[];
  notesGroupedByAction: Record<string, Note[]>;
  isLoadingNotes: boolean;
  onToggleSelection: (note: Note) => Promise<void>;
  onExport: (format: string) => Promise<void>;
  onExportSelected: () => Promise<void>;
  onBulkSelect: (notes: Note[], selected: boolean) => Promise<void>;
  selectedActionFilter: string | null;
  onActionFilterChange: (action: string | null) => void;
}

function NotesView({
  notes,
  notesGroupedByAction,
  isLoadingNotes,
  onToggleSelection,
  onExport,
  onExportSelected,
  onBulkSelect,
  selectedActionFilter,
  onActionFilterChange,
}: NotesViewProps) {
  const [expandedGroups, setExpandedGroups] = useState<Set<string>>(new Set());
  const [searchQuery, setSearchQuery] = useState('');
  const [showSelectedOnly, setShowSelectedOnly] = useState(false);
  const [sortOrder, setSortOrder] = useState<'newest' | 'oldest'>('newest');
  const [bulkComment, setBulkComment] = useState('');
  const [phaseFilter, setPhaseFilter] = useState('');
  const [categoryFilter, setCategoryFilter] = useState('');
  const [showRagOnly, setShowRagOnly] = useState(false);
  const [ragSourceFilter, setRagSourceFilter] = useState('');
  const [showRagGraph, setShowRagGraph] = useState(false);
  const [filterNameInput, setFilterNameInput] = useState('');
  const [savedFilters, setSavedFilters] = useState<
    { name: string; filters: { search: string; phase: string; category: string; selectedOnly: boolean; ragOnly: boolean; ragSource?: string } }[]
  >([]);

  const toggleGroup = (action: string) => {
    setExpandedGroups((prev) => {
      const next = new Set(prev);
      if (next.has(action)) {
        next.delete(action);
      } else {
        next.add(action);
      }
      return next;
    });
  };

  const displayedNotes = selectedActionFilter
    ? notes.filter((n) => n.action === selectedActionFilter)
    : notes;

  const getPhase = (note: Note): string => {
    const metaPhase = note.metadata?.phase;
    if (metaPhase) return metaPhase;
    const outputTag = note.metadata?.output_tag;
    const mapping: Record<string, string> = {
      drama_planning: 'planning',
      drama_creation: 'creation',
      drama_evaluation: 'evaluation',
      novel_screening: 'evaluation',
      story_analysis: 'analysis',
      character_development: 'character',
      plot_development: 'story',
      series_analysis: 'analysis',
    };
    if (outputTag && mapping[outputTag]) return mapping[outputTag];
    return '';
  };

  const getCategory = (note: Note): string => {
    return note.metadata?.category || '';
  };

  const baseNotes = displayedNotes
    .filter((note) => (showSelectedOnly ? note.select_status === 1 : true))
    .filter((note) => (phaseFilter ? getPhase(note) === phaseFilter : true))
    .filter((note) => (categoryFilter ? getCategory(note) === categoryFilter : true))
    .filter((note) => {
      if (!searchQuery) return true;
      const query = searchQuery.toLowerCase();
      return (
        note.title?.toLowerCase().includes(query) ||
        note.name?.toLowerCase().includes(query) ||
        note.context?.toLowerCase().includes(query) ||
        note.action?.toLowerCase().includes(query)
      );
    });

  const ragSourceCounts = baseNotes.reduce((acc, note) => {
    const ragTrace = note.metadata?.rag_trace;
    if (Array.isArray(ragTrace)) {
      ragTrace.forEach((item: any) => {
        const source = item?.source || 'unknown';
        acc[source] = (acc[source] || 0) + 1;
      });
    }
    return acc;
  }, {} as Record<string, number>);

  const ragGraphNodes = useMemo(() => {
    const entries = Object.entries(ragSourceCounts);
    if (entries.length === 0) return [];
    const max = Math.max(...entries.map(([, count]) => count));
    return entries.map(([source, count], idx) => ({
      id: source,
      count,
      radius: Math.max(10, Math.round((count / (max || 1)) * 24)),
      x: 60 + (idx % 5) * 80,
      y: 50 + Math.floor(idx / 5) * 80,
    }));
  }, [ragSourceCounts]);

  const filteredNotes = baseNotes
    .filter((note) => {
      if (!showRagOnly) return true;
      const ragTrace = note.metadata?.rag_trace;
      return Array.isArray(ragTrace) && ragTrace.length > 0;
    })
    .filter((note) => {
      if (!ragSourceFilter) return true;
      const ragTrace = note.metadata?.rag_trace;
      return Array.isArray(ragTrace) && ragTrace.some((item: any) => (item?.source || 'unknown') === ragSourceFilter);
    })
    .sort((a, b) => {
      const aTime = new Date(a.created_at).getTime();
      const bTime = new Date(b.created_at).getTime();
      return sortOrder === 'newest' ? bTime - aTime : aTime - bTime;
    });

  const groupedFilteredNotes = Object.entries(notesGroupedByAction).reduce(
    (acc, [action, groupNotes]) => {
      const groupFiltered = groupNotes
        .filter((note) => filteredNotes.some((n) => n.id === note.id));
      if (groupFiltered.length > 0) {
        acc[action] = groupFiltered;
      }
      return acc;
    },
    {} as Record<string, Note[]>
  );
  const selectedCount = filteredNotes.filter((note) => note.select_status === 1).length;
  const phaseOptions = Array.from(
    new Set(notes.map((note) => getPhase(note)).filter(Boolean))
  );
  const categoryOptions = Array.from(
    new Set(notes.map((note) => getCategory(note)).filter(Boolean))
  );

  useEffect(() => {
    try {
      const raw = localStorage.getItem('notes_saved_filters');
      if (raw) {
        setSavedFilters(JSON.parse(raw));
      }
    } catch {
      setSavedFilters([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('notes_saved_filters', JSON.stringify(savedFilters));
  }, [savedFilters]);

  const handleClearFilters = () => {
    setSearchQuery('');
    setPhaseFilter('');
    setCategoryFilter('');
    setShowSelectedOnly(false);
    setShowRagOnly(false);
    setRagSourceFilter('');
  };

  const handleSaveFilters = () => {
    const name = filterNameInput.trim();
    if (!name) return;
    const payload = {
      search: searchQuery,
      phase: phaseFilter,
      category: categoryFilter,
      selectedOnly: showSelectedOnly,
      ragOnly: showRagOnly,
      ragSource: ragSourceFilter,
    };
    setSavedFilters((prev) => [
      { name, filters: payload },
      ...prev.filter((item) => item.name !== name),
    ]);
    setFilterNameInput('');
  };

  const handleApplySaved = (name: string) => {
    const saved = savedFilters.find((item) => item.name === name);
    if (!saved) return;
    setSearchQuery(saved.filters.search);
    setPhaseFilter(saved.filters.phase);
    setCategoryFilter(saved.filters.category);
    setShowSelectedOnly(saved.filters.selectedOnly);
    setShowRagOnly(Boolean(saved.filters.ragOnly));
    setRagSourceFilter(saved.filters.ragSource || '');
  };

  const handleDeleteSaved = (name: string) => {
    setSavedFilters((prev) => prev.filter((item) => item.name !== name));
  };

  // 获取Agent显示名称
  const getActionDisplayName = (action: string): string => {
    const names: Record<string, string> = {
      'character_profile_generator': '人物小传',
      'character_relationship_analyzer': '人物关系',
      'plot_points_analyzer': '情节点分析',
      'story_summary_generator': '故事大纲',
      'major_plot_points_agent': '大情节点',
      'detailed_plot_points_agent': '详细情节点',
      'script_evaluation': '剧本评估',
      'ip_evaluation': 'IP评估',
      'story_evaluation': '故事评估',
    };
    return names[action] || action;
  };

  if (isLoadingNotes) {
    return (
      <div className="h-full flex items-center justify-center text-gray-400">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-indigo-600"></div>
        <p className="ml-3">加载Notes...</p>
      </div>
    );
  }

  if (notes.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400">
        <Layers className="w-16 h-16 mb-4 opacity-50" />
        <p className="text-lg">暂无Notes</p>
        <p className="text-sm mt-2">
          Agent生成的内容将保存为Notes，可以在这里查看和选择
        </p>
      </div>
    );
  }

  if (filteredNotes.length === 0) {
    return (
      <div className="h-full flex flex-col items-center justify-center text-gray-400">
        <Layers className="w-16 h-16 mb-4 opacity-50" />
        <p className="text-lg">没有匹配的 Notes</p>
        <p className="text-sm mt-2">请调整筛选或搜索条件</p>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* 过滤器和工具栏 */}
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex items-center gap-2">
            <input
              value={filterNameInput}
              onChange={(e) => setFilterNameInput(e.target.value)}
              placeholder="筛选名称"
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={handleSaveFilters}
              disabled={!filterNameInput.trim()}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              保存筛选
            </button>
            <select
              value=""
              onChange={(e) => {
                if (e.target.value) {
                  handleApplySaved(e.target.value);
                }
              }}
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            >
              <option value="">应用筛选</option>
              {savedFilters.map((item) => (
                <option key={item.name} value={item.name}>
                  {item.name}
                </option>
              ))}
            </select>
            {savedFilters.length > 0 && (
              <select
                value=""
                onChange={(e) => {
                  if (e.target.value) {
                    handleDeleteSaved(e.target.value);
                  }
                }}
                className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
              >
                <option value="">删除筛选</option>
                {savedFilters.map((item) => (
                  <option key={item.name} value={item.name}>
                    {item.name}
                  </option>
                ))}
              </select>
            )}
            <button
              onClick={handleClearFilters}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              清空
            </button>
          </div>
          <select
            value={selectedActionFilter || ''}
            onChange={(e) => onActionFilterChange(e.target.value || null)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">全部类型</option>
            {Object.keys(notesGroupedByAction).map((action) => (
              <option key={action} value={action}>
                {getActionDisplayName(action)} ({notesGroupedByAction[action].length})
              </option>
            ))}
          </select>
          <select
            value={phaseFilter}
            onChange={(e) => setPhaseFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">全部阶段</option>
            {phaseOptions.map((phase) => (
              <option key={phase} value={phase}>
                {phase}
              </option>
            ))}
          </select>
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="">全部分类</option>
            {categoryOptions.map((category) => (
              <option key={category} value={category}>
                {category}
              </option>
            ))}
          </select>
          <input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="搜索 Notes..."
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          />
          <button
            onClick={() => setShowSelectedOnly((prev) => !prev)}
            className={clsx(
              'px-3 py-1.5 text-sm rounded-lg border transition-colors',
              showSelectedOnly
                ? 'border-indigo-500 text-indigo-600 bg-indigo-50'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            仅看已选
          </button>
          <button
            onClick={() => setShowRagOnly((prev) => !prev)}
            className={clsx(
              'px-3 py-1.5 text-sm rounded-lg border transition-colors',
              showRagOnly
                ? 'border-blue-500 text-blue-600 bg-blue-50'
                : 'border-gray-200 text-gray-600 hover:bg-gray-50'
            )}
          >
            仅看含引用
          </button>
          <select
            value={sortOrder}
            onChange={(e) => setSortOrder(e.target.value as 'newest' | 'oldest')}
            className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
          >
            <option value="newest">最新优先</option>
            <option value="oldest">最早优先</option>
          </select>
          <button
            onClick={() => onBulkSelect(filteredNotes, true)}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            全选筛选结果
          </button>
          <button
            onClick={() => onBulkSelect(filteredNotes, false)}
            className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
          >
            取消全选
          </button>
          <div className="flex items-center gap-2">
            <input
              value={bulkComment}
              onChange={(e) => setBulkComment(e.target.value)}
              placeholder="批量评论..."
              className="px-3 py-1.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-indigo-500"
            />
            <button
              onClick={async () => {
                const selected = filteredNotes.filter((note) => note.select_status === 1);
                if (selected.length === 0 || !bulkComment.trim()) return;
                await Promise.all(
                  selected.map((note) =>
                    useWorkspaceStore.getState().updateNoteSelection(note, true, bulkComment.trim())
                  )
                );
                setBulkComment('');
              }}
              className="px-3 py-1.5 text-sm rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              添加评论
            </button>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={onExportSelected}
            className="px-3 py-1.5 text-sm bg-gray-900 text-white rounded-lg hover:bg-gray-800 transition-colors"
          >
            导出已选 ({selectedCount})
          </button>
          <button
            onClick={() => onExport('txt')}
            className="px-3 py-1.5 text-sm bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 transition-colors"
          >
            导出TXT
          </button>
          <button
            onClick={() => onExport('md')}
            className="px-3 py-1.5 text-sm bg-gray-600 text-white rounded-lg hover:bg-gray-700 transition-colors"
          >
            导出MD
          </button>
        </div>
      </div>

      {Object.keys(ragSourceCounts).length > 0 && (
        <div className="mt-4 rounded-lg border border-gray-200 bg-white p-4">
          <div className="flex items-center justify-between mb-2">
            <div className="text-sm font-medium text-gray-700">RAG 引用源</div>
            <button
              onClick={() => setShowRagGraph((prev) => !prev)}
              className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
            >
              {showRagGraph ? '隐藏图谱' : '显示图谱'}
            </button>
          </div>
          {showRagGraph && ragGraphNodes.length > 0 && (
            <div className="mb-3 overflow-auto">
              <svg width="480" height={Math.max(140, Math.ceil(ragGraphNodes.length / 5) * 80)}>
                {ragGraphNodes.map((node) => (
                  <g
                    key={node.id}
                    onClick={() => {
                      setShowRagOnly(true);
                      setRagSourceFilter(node.id);
                    }}
                    style={{ cursor: 'pointer' }}
                  >
                    <circle cx={node.x} cy={node.y} r={node.radius} fill="#3B82F6" opacity="0.2" />
                    <circle cx={node.x} cy={node.y} r={Math.max(8, node.radius - 5)} fill="#3B82F6" opacity="0.6" />
                    <text x={node.x} y={node.y + node.radius + 10} textAnchor="middle" fontSize="9" fill="#4B5563">
                      {node.id}
                    </text>
                  </g>
                ))}
              </svg>
            </div>
          )}
          <div className="space-y-2 mb-3">
            {Object.entries(ragSourceCounts).map(([source, count]) => {
              const total = Object.values(ragSourceCounts).reduce((sum, v) => sum + v, 0) || 1;
              const percent = Math.round((count / total) * 100);
              return (
                <div key={source}>
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>{source}</span>
                    <span>{percent}%</span>
                  </div>
                  <div className="h-1.5 bg-gray-100 rounded">
                    <div className="h-1.5 rounded bg-blue-500" style={{ width: `${percent}%` }} />
                  </div>
                </div>
              );
            })}
          </div>
          <div className="flex flex-wrap gap-2">
            {Object.entries(ragSourceCounts).map(([source, count]) => (
              <button
                key={source}
                onClick={() => {
                  setShowRagOnly(true);
                  setRagSourceFilter(source);
                }}
                className={clsx(
                  'px-3 py-1.5 text-xs rounded-full border transition-colors',
                  ragSourceFilter === source
                    ? 'border-blue-500 text-blue-700 bg-blue-50'
                    : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                )}
              >
                {source} ({count})
              </button>
            ))}
            {ragSourceFilter && (
              <button
                onClick={() => setRagSourceFilter('')}
                className="px-3 py-1.5 text-xs rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50"
              >
                清除引用源
              </button>
            )}
          </div>
        </div>
      )}

      {/* Notes列表 */}
      <div className="flex-1 overflow-y-auto space-y-4">
        {Object.entries(groupedFilteredNotes).map(([action, groupNotes]) => (
          <div key={action} className="border border-gray-200 rounded-lg overflow-hidden">
            {/* 分组标题 */}
            <button
              onClick={() => toggleGroup(action)}
              className="w-full flex items-center justify-between px-4 py-2 bg-gray-50 hover:bg-gray-100 transition-colors"
            >
              <div className="flex items-center gap-2">
                <ChevronDown
                  className={clsx(
                    'w-4 h-4 transition-transform',
                    expandedGroups.has(action) || 'transform -rotate-90'
                  )}
                />
                <span className="font-medium text-gray-700">
                  {getActionDisplayName(action)}
                </span>
                <span className="text-xs text-gray-500">({groupNotes.length})</span>
              </div>
            </button>

            {/* 分组内容 */}
            {expandedGroups.has(action) && (
              <div className="p-2 space-y-2">
                {groupNotes.map((note) => (
                  <NoteCard
                    key={note.id}
                    note={note}
                    onToggleSelection={onToggleSelection}
                  />
                ))}
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

// Note卡片组件
interface NoteCardProps {
  note: Note;
  onToggleSelection: (note: Note) => Promise<void>;
}

function NoteCard({ note, onToggleSelection }: NoteCardProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  const mindMap = note.metadata?.mind_map;
  const mindMapSvg = mindMap?.svg;

  return (
    <div
      className={clsx(
        'border rounded-lg p-3 transition-all',
        note.select_status === 1
          ? 'border-indigo-500 bg-indigo-50'
          : 'border-gray-200 bg-white hover:border-gray-300'
      )}
    >
      <div className="flex items-start gap-3">
        {/* 选择复选框 */}
        <button
          onClick={() => onToggleSelection(note)}
          className="mt-1 flex-shrink-0"
        >
          {note.select_status === 1 ? (
            <CheckSquare className="w-5 h-5 text-indigo-600" />
          ) : (
            <Square className="w-5 h-5 text-gray-400" />
          )}
        </button>

        {/* Note内容 */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className="text-sm font-medium text-gray-900">
              {note.title || note.name}
            </span>
            {note.select_status === 1 && (
              <span className="px-2 py-0.5 text-xs bg-indigo-100 text-indigo-700 rounded-full">
                已选择
              </span>
            )}
          </div>
          {(note.metadata?.phase || note.metadata?.category || note.metadata?.output_tag) && (
            <div className="flex flex-wrap gap-2 mb-2 text-[11px] text-gray-500">
              {note.metadata?.phase && (
                <span className="px-2 py-0.5 bg-gray-100 rounded">
                  phase:{note.metadata.phase}
                </span>
              )}
              {note.metadata?.category && (
                <span className="px-2 py-0.5 bg-gray-100 rounded">
                  category:{note.metadata.category}
                </span>
              )}
              {note.metadata?.output_tag && (
                <span className="px-2 py-0.5 bg-gray-100 rounded">
                  output:{note.metadata.output_tag}
                </span>
              )}
            </div>
          )}

          {!isExpanded ? (
            <p className="text-xs text-gray-500 line-clamp-2">
              {note.context}
            </p>
          ) : (
            <div className="text-sm text-gray-700 whitespace-pre-wrap">
              {note.context}
            </div>
          )}

          {mindMapSvg && (
            <div className="mt-2 rounded-lg border border-gray-200 bg-white p-2">
              {mindMap?.title && (
                <div className="text-xs font-medium text-gray-600 mb-1">{mindMap.title}</div>
              )}
              <div className="max-h-[180px] overflow-hidden">
                <div
                  className="origin-top-left scale-[0.85]"
                  dangerouslySetInnerHTML={{ __html: mindMapSvg }}
                />
              </div>
            </div>
          )}

          {note.user_comment && (
            <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded text-xs text-yellow-800">
              <strong>用户评论:</strong> {note.user_comment}
            </div>
          )}

          {note.metadata?.rag_trace && Array.isArray(note.metadata.rag_trace) && (
            <div className="mt-2 text-xs text-gray-500">
              RAG 引用: {note.metadata.rag_trace.length} 条
              {isExpanded && (
                <div className="mt-1 space-y-1">
                  {note.metadata.rag_trace.map((item: any, idx: number) => (
                    <div key={idx} className="px-2 py-1 bg-gray-50 rounded">
                      <div>来源: {item.source}</div>
                      <div>查询: {item.query}</div>
                      <div>结果: {item.result_count}</div>
                      {item.filename && (item.project_id || note.metadata?.project_id) && (
                        <div className="mt-1">
                          <a
                            href={`/files?project_id=${item.project_id || note.metadata?.project_id}&search=${encodeURIComponent(item.filename)}`}
                            className="text-blue-600 hover:underline"
                          >
                            打开关联文件
                          </a>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="flex items-center justify-between mt-2">
            <button
              onClick={() => setIsExpanded(!isExpanded)}
              className="text-xs text-indigo-600 hover:text-indigo-700"
            >
              {isExpanded ? '收起' : '展开'}
            </button>
            <span className="text-xs text-gray-400">
              {new Date(note.created_at).toLocaleString('zh-CN')}
            </span>
          </div>
        </div>
      </div>
    </div>
  );
}

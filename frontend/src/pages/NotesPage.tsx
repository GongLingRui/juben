/**
 * 笔记管理页面
 * 管理用户在创作过程中产生的所有笔记
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  FileText,
  Search,
  Filter,
  Download,
  Trash2,
  Edit,
  Check,
  X,
  Star,
  FolderOpen,
  Tag,
  Calendar,
  ChevronDown,
  Plus
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import * as noteService from '@/services/noteService';

type Note = {
  id: string;
  user_id: string;
  session_id: string;
  action: string;
  name: string;
  title?: string;
  context: string;
  select_status: number;
  user_comment?: string;
  content_type?: string;
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
};

type ContentFilter = 'all' | 'text' | 'markdown' | 'code' | 'image';
type ExportFormat = 'json' | 'md' | 'txt';

export default function NotesPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [notes, setNotes] = useState<Note[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState('');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedNotes, setSelectedNotes] = useState<Set<string>>(new Set());
  const [contentFilter, setContentFilter] = useState<ContentFilter>('all');
  const [actionFilter, setActionFilter] = useState<string>('all');
  const [showExportModal, setShowExportModal] = useState(false);
  const [exportFormat, setExportFormat] = useState<ExportFormat>('md');
  const [editingNote, setEditingNote] = useState<Note | null>(null);
  const [editContent, setEditContent] = useState('');
  const [viewMode, setViewMode] = useState<'grid' | 'list'>('grid');
  const [selectedOnly, setSelectedOnly] = useState(false);

  // 获取笔记列表
  const loadNotes = async () => {
    if (!user) return;

    setIsLoading(true);
    setError('');

    try {
      const response = await fetch(
        `/api/notes/list/${user.id}?session_id=&content_type=&action=&selected_only=${selectedOnly}&search=${encodeURIComponent(searchQuery)}&limit=100&offset=0`,
        {
          headers: {
            'Authorization': `Bearer ${localStorage.getItem('token')}`
          }
        }
      );

      if (response.ok) {
        const data = await response.json();
        setNotes(data.notes || []);
      } else {
        setError('获取笔记列表失败');
      }
    } catch (err) {
      console.error('加载笔记失败:', err);
      setError('加载笔记失败，请重试');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadNotes();
  }, [user, selectedOnly, searchQuery]);

  // 删除笔记
  const handleDeleteNote = async (noteId: string) => {
    if (!confirm('确定要删除这条笔记吗？')) return;

    try {
      const response = await fetch(`/api/notes/${noteId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        }
      });

      if (response.ok) {
        setNotes(notes.filter(n => n.id !== noteId));
      } else {
        alert('删除失败');
      }
    } catch (err) {
      console.error('删除笔记失败:', err);
      alert('删除失败');
    }
  };

  // 保存编辑
  const handleSaveEdit = async () => {
    if (!editingNote || !user) return;

    try {
      const result = await noteService.updateNoteContent(
        editingNote.id,
        user.id,
        editContent
      );

      if (result.success) {
        setNotes(notes.map(n =>
          n.id === editingNote.id
            ? { ...n, context: editContent }
            : n
        ));
        setEditingNote(null);
        setEditContent('');
      } else {
        alert(result.message || '保存失败');
      }
    } catch (err) {
      console.error('保存失败:', err);
      alert('保存失败');
    }
  };

  // 切换选择状态
  const toggleSelectNote = (noteId: string) => {
    const newSelected = new Set(selectedNotes);
    if (newSelected.has(noteId)) {
      newSelected.delete(noteId);
    } else {
      newSelected.add(noteId);
    }
    setSelectedNotes(newSelected);
  };

  // 导出笔记
  const handleExportNotes = async () => {
    if (!user) return;

    try {
      const response = await fetch('/api/notes/export', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          user_id: user.id,
          session_id: '',
          content_types: [],
          export_format: exportFormat,
          include_user_comments: true
        })
      });

      if (response.ok) {
        const data = await response.json();
        if (data.exported_data) {
          const blob = new Blob([data.exported_data], {
            type: exportFormat === 'json' ? 'application/json' :
                 exportFormat === 'md' ? 'text/markdown' : 'text/plain'
          });
          const url = URL.createObjectURL(blob);
          const a = document.createElement('a');
          a.href = url;
          a.download = data.filename || `notes.${exportFormat}`;
          a.click();
          URL.revokeObjectURL(url);
          setShowExportModal(false);
        }
      } else {
        alert('导出失败');
      }
    } catch (err) {
      console.error('导出失败:', err);
      alert('导出失败');
    }
  };

  // 过滤笔记
  const filteredNotes = notes.filter(note => {
    // 内容类型过滤
    if (contentFilter !== 'all' && note.content_type !== contentFilter) {
      return false;
    }

    // 动作过滤
    if (actionFilter !== 'all' && note.action !== actionFilter) {
      return false;
    }

    return true;
  });

  // 按动作分组
  const groupedNotes = filteredNotes.reduce((acc, note) => {
    const action = note.action || 'unknown';
    if (!acc[action]) {
      acc[action] = [];
    }
    acc[action].push(note);
    return acc;
  }, {} as Record<string, Note[]>);

  // 获取所有动作类型
  const actionTypes = Array.from(new Set(notes.map(n => n.action))).sort();

  const getActionIcon = (action: string) => {
    const iconMap: Record<string, string> = {
      'story-analysis': '📖',
      'character-creation': '👤',
      'plot-design': '📝',
      'dialogue-generation': '💬',
      'scene-description': '🎬',
      'script-evaluation': '⭐',
      'mind-map': '🗺️',
      'workflow': '⚙️',
    };
    return iconMap[action] || '📄';
  };

  const getActionLabel = (action: string) => {
    const labelMap: Record<string, string> = {
      'story-analysis': '故事分析',
      'character-creation': '角色创建',
      'plot-design': '情节设计',
      'dialogue-generation': '对话生成',
      'scene-description': '场景描述',
      'script-evaluation': '剧本评估',
      'mind-map': '思维导图',
      'workflow': '工作流',
    };
    return labelMap[action] || action;
  };

  return (
    <div className="flex h-screen bg-white">
      <MobileMenu />
      <Sidebar />

      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          !sidebarOpen ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-80'
        }`}
      >
        <Header />
        <StatusBar />

        <div className="flex flex-col flex-1 overflow-hidden">
          {/* 页面头部 */}
          <div className="border-b border-gray-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                    <FileText className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">笔记管理</h1>
                    <p className="text-sm text-gray-500 mt-1">
                      管理您的创作笔记，共 {notes.length} 条
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={() => setShowExportModal(true)}
                    className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-all hover-scale"
                  >
                    <Download className="w-4 h-4" />
                    <span className="font-medium">导出</span>
                  </button>
                </div>
              </div>

              {/* 工具栏 */}
              <div className="flex items-center gap-4">
                {/* 搜索框 */}
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索笔记..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm"
                  />
                </div>

                {/* 动作过滤 */}
                <select
                  value={actionFilter}
                  onChange={(e) => setActionFilter(e.target.value)}
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                >
                  <option value="all">全部类型</option>
                  {actionTypes.map(action => (
                    <option key={action} value={action}>
                      {getActionLabel(action)}
                    </option>
                  ))}
                </select>

                {/* 视图切换 */}
                <div className="flex items-center gap-1 border border-gray-200 rounded-lg overflow-hidden">
                  <button
                    onClick={() => setViewMode('grid')}
                    className={`p-2 hover:bg-gray-100 transition-colors ${
                      viewMode === 'grid' ? 'bg-gray-100' : ''
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <rect x="3" y="3" width="7" height="7" />
                      <rect x="14" y="3" width="7" height="7" />
                      <rect x="14" y="14" width="7" height="7" />
                      <rect x="3" y="14" width="7" height="7" />
                    </svg>
                  </button>
                  <button
                    onClick={() => setViewMode('list')}
                    className={`p-2 hover:bg-gray-100 transition-colors ${
                      viewMode === 'list' ? 'bg-gray-100' : ''
                    }`}
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <line x1="8" y1="6" x2="21" y2="6" />
                      <line x1="8" y1="12" x2="21" y2="12" />
                      <line x1="8" y1="18" x2="21" y2="18" />
                      <line x1="3" y1="6" x2="3.01" y2="6" />
                      <line x1="3" y1="12" x2="3.01" y2="12" />
                      <line x1="3" y1="18" x2="3.01" y2="18" />
                    </svg>
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 笔记列表 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              {error && (
                <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                  <button onClick={() => setError('')} className="ml-2 underline hover:text-red-900">
                    关闭
                  </button>
                </div>
              )}

              {isLoading ? (
                <div className="flex items-center justify-center py-12">
                  <div className="text-center">
                    <div className="w-12 h-12 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-500">加载中...</p>
                  </div>
                </div>
              ) : filteredNotes.length === 0 ? (
                <div className="text-center py-16">
                  <div className="w-20 h-20 bg-gray-100 rounded-full flex items-center justify-center mx-auto mb-4">
                    <FileText className="w-10 h-10 text-gray-400" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-900 mb-2">
                    {searchQuery ? '没有找到匹配的笔记' : '还没有笔记'}
                  </h3>
                  <p className="text-gray-500">
                    {searchQuery
                      ? '尝试调整搜索条件'
                      : '开始创作后，您的笔记将显示在这里'}
                  </p>
                </div>
              ) : viewMode === 'list' ? (
                <div className="space-y-3">
                  {filteredNotes.map((note) => (
                    <NoteListItem
                      key={note.id}
                      note={note}
                      isSelected={selectedNotes.has(note.id)}
                      isEditing={editingNote?.id === note.id}
                      editContent={editContent}
                      onToggleSelect={() => toggleSelectNote(note.id)}
                      onEdit={() => {
                        setEditingNote(note);
                        setEditContent(note.context);
                      }}
                      onSave={handleSaveEdit}
                      onCancel={() => {
                        setEditingNote(null);
                        setEditContent('');
                      }}
                      onDelete={() => handleDeleteNote(note.id)}
                      onEditContentChange={setEditContent}
                      getActionIcon={getActionIcon}
                      getActionLabel={getActionLabel}
                    />
                  ))}
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {filteredNotes.map((note) => (
                    <NoteCard
                      key={note.id}
                      note={note}
                      isSelected={selectedNotes.has(note.id)}
                      onToggleSelect={() => toggleSelectNote(note.id)}
                      onEdit={() => {
                        setEditingNote(note);
                        setEditContent(note.context);
                      }}
                      onDelete={() => handleDeleteNote(note.id)}
                      getActionIcon={getActionIcon}
                      getActionLabel={getActionLabel}
                    />
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />

      {/* 编辑笔记模态框 */}
      {editingNote && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-3xl w-full max-h-[80vh] flex flex-col">
            <div className="p-6 border-b border-gray-200">
              <h2 className="text-xl font-bold text-gray-900">编辑笔记</h2>
              <p className="text-sm text-gray-500 mt-1">{editingNote.title || editingNote.name}</p>
            </div>

            <div className="flex-1 overflow-y-auto p-6">
              <textarea
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                className="w-full h-full min-h-[400px] p-4 border border-gray-200 rounded-lg focus:outline-none focus:border-black font-mono text-sm resize-none"
                placeholder="笔记内容..."
              />
            </div>

            <div className="p-6 border-t border-gray-200 flex gap-3">
              <button
                onClick={() => {
                  setEditingNote(null);
                  setEditContent('');
                }}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
              >
                取消
              </button>
              <button
                onClick={handleSaveEdit}
                className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
              >
                保存
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 导出模态框 */}
      {showExportModal && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-4">导出笔记</h2>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">导出格式</label>
                <div className="space-y-2">
                  {(['json', 'md', 'txt'] as ExportFormat[]).map((format) => (
                    <label key={format} className="flex items-center gap-2 cursor-pointer">
                      <input
                        type="radio"
                        name="exportFormat"
                        value={format}
                        checked={exportFormat === format}
                        onChange={(e) => setExportFormat(e.target.value as ExportFormat)}
                        className="text-black focus:ring-black"
                      />
                      <span className="text-sm">
                        {format === 'json' && 'JSON 格式'}
                        {format === 'md' && 'Markdown 格式'}
                        {format === 'txt' && '纯文本格式'}
                      </span>
                    </label>
                  ))}
                </div>
              </div>

              <div className="flex gap-3 pt-4 border-t border-gray-200">
                <button
                  onClick={() => setShowExportModal(false)}
                  className="flex-1 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
                >
                  取消
                </button>
                <button
                  onClick={handleExportNotes}
                  className="flex-1 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors"
                >
                  导出
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * 笔记卡片组件
 */
function NoteCard({
  note,
  isSelected,
  onToggleSelect,
  onEdit,
  onDelete,
  getActionIcon,
  getActionLabel
}: {
  note: Note;
  isSelected: boolean;
  onToggleSelect: () => void;
  onEdit: () => void;
  onDelete: () => void;
  getActionIcon: (action: string) => string;
  getActionLabel: (action: string) => string;
}) {
  return (
    <div className={`group bg-white border rounded-xl p-4 transition-all hover:shadow-lg ${
      isSelected ? 'border-black bg-gray-50' : 'border-gray-200 hover:border-gray-300'
    }`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          <span className="text-2xl">{getActionIcon(note.action)}</span>
          <div>
            <h3 className="font-semibold text-gray-900 text-sm">
              {note.title || note.name}
            </h3>
            <p className="text-xs text-gray-500">
              {getActionLabel(note.action)}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-1">
          <button
            onClick={onToggleSelect}
            className={`p-1.5 rounded-lg transition-colors ${
              isSelected ? 'bg-black text-white' : 'hover:bg-gray-100'
            }`}
          >
            {isSelected ? <Check className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-gray-300 rounded" />}
          </button>
        </div>
      </div>

      <p className="text-sm text-gray-600 mb-4 line-clamp-3 min-h-[60px]">
        {note.context}
      </p>

      {note.user_comment && (
        <div className="mb-3 p-2 bg-gray-50 rounded-lg">
          <p className="text-xs text-gray-500">{note.user_comment}</p>
        </div>
      )}

      <div className="flex items-center justify-between pt-3 border-t border-gray-100">
        <div className="flex items-center gap-1 text-xs text-gray-500">
          <Calendar className="w-3 h-3" />
          {formatDistanceToNow(new Date(note.created_at), { addSuffix: true, locale: zhCN })}
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={onEdit}
            className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
            title="编辑"
          >
            <Edit className="w-4 h-4 text-gray-500" />
          </button>
          <button
            onClick={onDelete}
            className="p-1.5 hover:bg-red-100 rounded-lg transition-colors"
            title="删除"
          >
            <Trash2 className="w-4 h-4 text-red-500" />
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * 笔记列表项组件
 */
function NoteListItem({
  note,
  isSelected,
  isEditing,
  editContent,
  onToggleSelect,
  onEdit,
  onSave,
  onCancel,
  onDelete,
  onEditContentChange,
  getActionIcon,
  getActionLabel
}: {
  note: Note;
  isSelected: boolean;
  isEditing: boolean;
  editContent: string;
  onToggleSelect: () => void;
  onEdit: () => void;
  onSave: () => void;
  onCancel: () => void;
  onDelete: () => void;
  onEditContentChange: (content: string) => void;
  getActionIcon: (action: string) => string;
  getActionLabel: (action: string) => string;
}) {
  return (
    <div className={`bg-white border rounded-lg p-4 transition-all ${
      isSelected ? 'border-black bg-gray-50' : 'border-gray-200'
    }`}>
      <div className="flex items-start gap-4">
        <button
          onClick={onToggleSelect}
          className={`mt-1 p-1.5 rounded-lg transition-colors ${
            isSelected ? 'bg-black text-white' : 'hover:bg-gray-100'
          }`}
        >
          {isSelected ? <Check className="w-4 h-4" /> : <div className="w-4 h-4 border-2 border-gray-300 rounded" />}
        </button>

        <span className="text-2xl">{getActionIcon(note.action)}</span>

        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-2">
            <div>
              <h3 className="font-semibold text-gray-900">{note.title || note.name}</h3>
              <p className="text-xs text-gray-500">
                {getActionLabel(note.action)} · {formatDistanceToNow(new Date(note.created_at), { addSuffix: true, locale: zhCN })}
              </p>
            </div>

            <div className="flex items-center gap-1">
              <button
                onClick={onEdit}
                className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors"
                title="编辑"
              >
                <Edit className="w-4 h-4 text-gray-500" />
              </button>
              <button
                onClick={onDelete}
                className="p-1.5 hover:bg-red-100 rounded-lg transition-colors"
                title="删除"
              >
                <Trash2 className="w-4 h-4 text-red-500" />
              </button>
            </div>
          </div>

          {isEditing ? (
            <div className="space-y-2">
              <textarea
                value={editContent}
                onChange={(e) => onEditContentChange(e.target.value)}
                className="w-full p-3 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm resize-none"
                rows={6}
              />
              <div className="flex gap-2">
                <button
                  onClick={onSave}
                  className="px-3 py-1.5 bg-black text-white rounded-lg text-sm hover:bg-gray-800"
                >
                  保存
                </button>
                <button
                  onClick={onCancel}
                  className="px-3 py-1.5 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
                >
                  取消
                </button>
              </div>
            </div>
          ) : (
            <p className="text-sm text-gray-600">{note.context}</p>
          )}

          {note.user_comment && !isEditing && (
            <div className="mt-2 p-2 bg-gray-50 rounded-lg">
              <p className="text-xs text-gray-500">{note.user_comment}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

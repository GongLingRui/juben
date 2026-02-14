/**
 * 知识库管理页面
 * 用于管理文档、知识条目和搜索功能
 */

import React, { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Database,
  Upload,
  Search,
  FileText,
  Trash2,
  Edit,
  Eye,
  Download,
  Tag,
  Calendar,
  TrendingUp,
  Plus,
  FolderOpen,
  BookOpen,
  Filter,
  RefreshCw,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { getKnowledgeCollections, searchKnowledge } from '@/services/extendedApi';

interface KnowledgeDocument {
  id: string;
  title: string;
  content: string;
  category?: string;
  tags?: string[];
  createdAt?: string;
  updatedAt?: string;
  size?: number;
  source?: string;
  relevance?: number;
}

interface KnowledgeCategory {
  name: string;
  description?: string;
  count?: number;
}

export const KnowledgeBasePage: React.FC = () => {
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<'documents' | 'upload' | 'search' | 'stats'>('documents');
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState<string>('all');
  const [selectedDocument, setSelectedDocument] = useState<KnowledgeDocument | null>(null);
  const [searchResults, setSearchResults] = useState<KnowledgeDocument[]>([]);
  const [categories, setCategories] = useState<KnowledgeCategory[]>([]);
  const [documents, setDocuments] = useState<KnowledgeDocument[]>([]);
  const [localDocuments, setLocalDocuments] = useState<KnowledgeDocument[]>([]);
  const [editingDocumentId, setEditingDocumentId] = useState<string | null>(null);
  const [searchHistory, setSearchHistory] = useState<
    { query: string; timestamp: string; count: number }[]
  >([]);
  const [uploadForm, setUploadForm] = useState({ title: '', content: '', tags: '' });
  const [uploadFile, setUploadFile] = useState<File | null>(null);
  const [uploadMessage, setUploadMessage] = useState('');
  const [stats, setStats] = useState({
    totalDocuments: 0,
    totalCategories: 0,
  });

  useEffect(() => {
    try {
      const raw = localStorage.getItem('knowledge_documents');
      const rawHistory = localStorage.getItem('knowledge_search_history');
      if (raw) {
        const parsed = JSON.parse(raw);
        setLocalDocuments(parsed);
        setDocuments(parsed);
      }
      if (rawHistory) {
        setSearchHistory(JSON.parse(rawHistory));
      }
    } catch {
      setLocalDocuments([]);
    }

    const loadCollections = async () => {
      try {
        const response = await getKnowledgeCollections();
        const collectionList = response.collections || [];
        const mapped = collectionList.map((item) => ({
          name: item.name,
          description: item.info?.description || '',
          count: item.info?.count || item.info?.size || 0,
        }));
        setCategories(mapped);
        setStats({
          totalDocuments: mapped.reduce((acc, item) => acc + (item.count || 0), 0) + localDocuments.length,
          totalCategories: mapped.length,
        });
      } catch (err: any) {
        error('加载失败', err?.message || '无法加载知识库集合');
      }
    };
    loadCollections();
  }, [localDocuments.length]);

  const handleSearch = async () => {
    if (!searchQuery.trim()) {
      error('搜索失败', '请输入搜索关键词');
      return;
    }
    try {
      const response = await searchKnowledge(searchQuery.trim(), selectedCategory === 'all' ? undefined : selectedCategory);
      const results = response.search_result?.results || response.search_result?.items || response.search_result || [];
      const mapped: KnowledgeDocument[] = (Array.isArray(results) ? results : []).map((item: any, index: number) => ({
        id: item.id || item.doc_id || `${index}`,
        title: item.title || item.source || `结果 ${index + 1}`,
        content: item.content || item.text || item.snippet || JSON.stringify(item),
        category: item.collection || selectedCategory,
        source: item.source || item.url,
        size: item.size || item.bytes || item.file_size,
        updatedAt: item.updated_at || item.updatedAt,
        tags: item.tags || [],
        relevance: item.score ?? item.relevance ?? item.similarity,
      }));
      setSearchResults(mapped);
      setActiveTab('search');
      const now = new Date().toISOString();
      const updatedHistory = (() => {
        const existing = searchHistory.find((entry) => entry.query === searchQuery.trim());
        if (existing) {
          return searchHistory.map((entry) =>
            entry.query === searchQuery.trim()
              ? { ...entry, count: entry.count + 1, timestamp: now }
              : entry
          );
        }
        return [{ query: searchQuery.trim(), timestamp: now, count: 1 }, ...searchHistory].slice(0, 20);
      })();
      setSearchHistory(updatedHistory);
      localStorage.setItem('knowledge_search_history', JSON.stringify(updatedHistory));
      success('搜索完成', `找到 ${mapped.length} 条结果`);
    } catch (err: any) {
      error('搜索失败', err?.message || '无法完成搜索');
    }
  };

  const handleDeleteDocument = async (docId: string) => {
    if (!window.confirm('确定要删除这个文档吗？')) return;
    const updated = localDocuments.filter((doc) => doc.id !== docId);
    setLocalDocuments(updated);
    setDocuments(updated);
    localStorage.setItem('knowledge_documents', JSON.stringify(updated));
    success('删除成功', '文档已删除');
  };

  const handleViewDocument = (doc: KnowledgeDocument) => {
    setSelectedDocument(doc);
  };

  const handleCreateLocalDoc = () => {
    if (!uploadForm.title.trim() || !uploadForm.content.trim()) {
      error('创建失败', '标题和内容不能为空');
      return;
    }
    const now = new Date().toISOString();
    const doc: KnowledgeDocument = {
      id: editingDocumentId || `local_${Date.now()}`,
      title: uploadForm.title.trim(),
      content: uploadForm.content.trim(),
      category: '本地文档',
      tags: uploadForm.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      createdAt: editingDocumentId
        ? localDocuments.find((doc) => doc.id === editingDocumentId)?.createdAt
        : now,
      updatedAt: now,
    };
    const updated = editingDocumentId
      ? localDocuments.map((item) => (item.id === editingDocumentId ? doc : item))
      : [doc, ...localDocuments];
    setLocalDocuments(updated);
    setDocuments(updated);
    localStorage.setItem('knowledge_documents', JSON.stringify(updated));
    setUploadForm({ title: '', content: '', tags: '' });
    setUploadFile(null);
    setUploadMessage('');
    setEditingDocumentId(null);
    success(editingDocumentId ? '更新成功' : '创建成功', '本地知识文档已保存');
    setActiveTab('documents');
  };

  const handleUploadFile = (file: File) => {
    const allowed = ['text/plain', 'text/markdown', 'application/json'];
    if (!allowed.includes(file.type) && !file.name.match(/\.(txt|md|markdown|json)$/i)) {
      setUploadMessage('仅支持 txt / md / json 文件');
      return;
    }
    setUploadFile(file);
    setUploadMessage('');
    const reader = new FileReader();
    reader.onload = () => {
      const text = String(reader.result || '');
      setUploadForm((prev) => ({
        ...prev,
        title: prev.title || file.name.replace(/\.[^/.]+$/, ''),
        content: text,
      }));
      setUploadMessage(`已加载 ${file.name}，可继续编辑后保存`);
    };
    reader.onerror = () => {
      setUploadMessage('文件读取失败，请重试');
    };
    reader.readAsText(file);
  };

  const formatFileSize = (bytes: number) => {
    if (bytes === undefined || bytes === null) return '-';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatRelevance = (value?: number) => {
    if (value === undefined || value === null) return null;
    if (value <= 1) return `${Math.round(value * 100)}%`;
    if (value <= 100) return `${Math.round(value)}%`;
    return `${Math.round(value)}`;
  };

  const renderDocumentsTab = () => (
    <div className="space-y-6">
      {/* 统计卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">总文档数</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalDocuments}</p>
            </div>
            <FileText className="w-8 h-8 text-blue-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">分类数</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalCategories}</p>
            </div>
            <FolderOpen className="w-8 h-8 text-purple-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">本地文档</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{localDocuments.length}</p>
            </div>
            <Database className="w-8 h-8 text-green-500" />
          </div>
        </div>

        <div className="bg-white rounded-lg shadow p-5">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500">集合数量</p>
              <p className="text-2xl font-bold text-gray-900 mt-1">{categories.length}</p>
            </div>
            <Search className="w-8 h-8 text-orange-500" />
          </div>
        </div>
      </div>

      {/* 文档列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden">
        <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
          <h2 className="text-lg font-semibold text-gray-900">文档列表</h2>
          <div className="flex items-center gap-3">
            <select
              value={selectedCategory}
              onChange={(e) => setSelectedCategory(e.target.value)}
              className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-blue-500"
            >
              <option value="all">所有分类</option>
              {localDocuments.length > 0 && (
                <option value="本地文档">本地文档 ({localDocuments.length})</option>
              )}
              {categories.map((cat) => (
                <option key={cat.name} value={cat.name}>
                  {cat.name} ({cat.count || 0})
                </option>
              ))}
            </select>
            <button
              onClick={() => setActiveTab('upload')}
              className="flex items-center gap-2 px-4 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm font-medium"
            >
              <Plus className="w-4 h-4" />
              上传文档
            </button>
          </div>
        </div>

        <div className="overflow-x-auto">
          <table className="min-w-full divide-y divide-gray-200">
            <thead className="bg-gray-50">
              <tr>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标题</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">分类</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">标签</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">大小</th>
                <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">更新时间</th>
                <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 uppercase">操作</th>
              </tr>
            </thead>
            <tbody className="bg-white divide-y divide-gray-200">
              {documents
                .filter((doc) => selectedCategory === 'all' || doc.category === selectedCategory)
                .map((doc) => (
                <tr key={doc.id} className="hover:bg-gray-50">
                  <td className="px-6 py-4">
                    <div className="flex items-center gap-3">
                      <FileText className="w-5 h-5 text-gray-400" />
                      <div>
                        <div className="text-sm font-medium text-gray-900">{doc.title}</div>
                        {doc.source && (
                          <div className="text-xs text-gray-500">来源: {doc.source}</div>
                        )}
                      </div>
                    </div>
                  </td>
                  <td className="px-6 py-4">
                    <span className="inline-flex px-2 py-1 text-xs font-medium bg-blue-100 text-blue-700 rounded">
                      {doc.category || '未知'}
                    </span>
                  </td>
                  <td className="px-6 py-4">
                    <div className="flex flex-wrap gap-1">
                      {(doc.tags || []).slice(0, 2).map((tag) => (
                        <span
                          key={tag}
                          className="inline-flex px-2 py-0.5 text-xs bg-gray-100 text-gray-600 rounded"
                        >
                          {tag}
                        </span>
                      ))}
                      {(doc.tags || []).length > 2 && (
                        <span className="text-xs text-gray-500">+{(doc.tags || []).length - 2}</span>
                      )}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {doc.size ? formatFileSize(doc.size) : '-'}
                  </td>
                  <td className="px-6 py-4 text-sm text-gray-600">
                    {doc.updatedAt ? new Date(doc.updatedAt).toLocaleDateString() : '-'}
                  </td>
                  <td className="px-6 py-4 text-right">
                    <div className="flex items-center justify-end gap-1">
                      <button
                        onClick={() => handleViewDocument(doc)}
                        className="p-1.5 hover:bg-gray-100 rounded"
                        title="查看"
                      >
                        <Eye className="w-4 h-4 text-gray-600" />
                      </button>
                      {doc.id.startsWith('local_') && (
                        <button
                          onClick={() => handleDeleteDocument(doc.id)}
                          className="p-1.5 hover:bg-red-100 rounded"
                          title="删除"
                        >
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {/* 分类统计 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">分类统计</h3>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          {[...(localDocuments.length > 0
            ? [{ name: '本地文档', description: '本地保存内容', count: localDocuments.length }]
            : []),
            ...categories,
          ].map((cat) => (
            <div key={cat.name} className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-900">{cat.name}</h4>
                <span className="text-sm text-gray-500">{cat.count || 0} 篇</span>
              </div>
              <p className="text-sm text-gray-600">{cat.description}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );

  const renderUploadTab = () => (
    <div className="max-w-2xl mx-auto">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-6">
          {editingDocumentId ? '编辑本地文档' : '上传文档到知识库'}
        </h2>

        <div className="space-y-6">
          {/* 本地文档保存 */}
          <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center">
            <Upload className="w-10 h-10 mx-auto mb-4 text-gray-400" />
            <p className="text-gray-600 mb-2">支持拖拽或选择文件上传</p>
            <p className="text-sm text-gray-500">支持 txt / md / json 文件</p>
            <div className="mt-4">
              <input
                type="file"
                accept=".txt,.md,.markdown,.json,text/plain,text/markdown,application/json"
                onChange={(e) => e.target.files?.[0] && handleUploadFile(e.target.files[0])}
                className="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
              />
            </div>
            {uploadFile && <p className="mt-2 text-xs text-gray-500">已选择: {uploadFile.name}</p>}
            {uploadMessage && <p className="mt-3 text-xs text-blue-600">{uploadMessage}</p>}
          </div>

          {/* 文档信息 */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              文档标题 *
            </label>
            <input
              type="text"
              placeholder="输入文档标题"
              value={uploadForm.title}
              onChange={(e) => setUploadForm({ ...uploadForm, title: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              文档内容 *
            </label>
            <textarea
              placeholder="输入或粘贴文档内容..."
              rows={8}
              value={uploadForm.content}
              onChange={(e) => setUploadForm({ ...uploadForm, content: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 resize-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              标签
            </label>
            <input
              type="text"
              placeholder="输入标签，用逗号分隔"
              value={uploadForm.tags}
              onChange={(e) => setUploadForm({ ...uploadForm, tags: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
            />
          </div>

          <div className="bg-blue-50 rounded-lg p-4">
            <div className="flex items-start gap-3">
              <BookOpen className="w-5 h-5 text-blue-600 mt-0.5" />
              <div className="text-sm text-blue-800">
                <p className="font-medium mb-1">知识向量嵌入</p>
                <p>上传的文档将自动生成向量嵌入，支持语义搜索和智能检索</p>
              </div>
            </div>
          </div>

          <div className="flex gap-3 pt-4 border-t border-gray-200">
            <button
              onClick={() => {
                setEditingDocumentId(null);
                setActiveTab('documents');
              }}
              className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
            >
              取消
            </button>
            <button
              onClick={handleCreateLocalDoc}
              className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
            >
              {editingDocumentId ? '保存修改' : '保存文档'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );

  const renderSearchTab = () => (
    <div className="space-y-6">
      <div className="bg-white rounded-lg shadow p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">知识库搜索</h2>

        <div className="flex gap-3 mb-6">
          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            onKeyPress={(e) => e.key === 'Enter' && handleSearch()}
            placeholder="输入搜索关键词..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500"
          />
          <button
            onClick={handleSearch}
            className="px-6 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium flex items-center gap-2"
          >
            <Search className="w-4 h-4" />
            搜索
          </button>
        </div>

        <div className="flex items-center gap-4 text-sm text-gray-600">
          <label className="flex items-center gap-2">
            <input type="checkbox" defaultChecked className="rounded" />
            语义搜索
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" className="rounded" />
            全文搜索
          </label>
          <label className="flex items-center gap-2">
            <input type="checkbox" defaultChecked className="rounded" />
            包摘要
          </label>
        </div>
      </div>

      {/* 搜索结果 */}
      {searchResults.length > 0 && (
        <div className="bg-white rounded-lg shadow p-6">
          <div className="flex items-center justify-between mb-4">
            <h3 className="font-semibold text-gray-900">
              搜索结果 ({searchResults.length})
            </h3>
            {(() => {
              const scores = searchResults
                .map((doc) => doc.relevance)
                .filter((value): value is number => value !== undefined && value !== null);
              if (scores.length === 0) return null;
              const avg = scores.reduce((acc, v) => acc + v, 0) / scores.length;
              return (
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <TrendingUp className="w-4 h-4" />
                  平均相关度: {formatRelevance(avg)}
                </div>
              );
            })()}
          </div>

          <div className="space-y-4">
            {searchResults.map((doc, index) => (
              <div
                key={doc.id}
                className="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow cursor-pointer"
                onClick={() => handleViewDocument(doc)}
              >
                <div className="flex items-start gap-4">
                  <div className="flex-shrink-0 w-8 h-8 bg-blue-100 rounded-full flex items-center justify-center">
                    <span className="text-sm font-medium text-blue-600">{index + 1}</span>
                  </div>
                  <div className="flex-1">
                    <h4 className="font-medium text-gray-900 mb-1">{doc.title}</h4>
                    <p className="text-sm text-gray-600 mb-2 line-clamp-2">
                      {doc.content}
                    </p>
                    <div className="flex items-center gap-3 text-xs text-gray-500">
                      <span className="px-2 py-0.5 bg-gray-100 rounded">{doc.category}</span>
                      {doc.size !== undefined && <span>{formatFileSize(doc.size)}</span>}
                      {formatRelevance(doc.relevance) && (
                        <span>相关度: {formatRelevance(doc.relevance)}</span>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );

  const renderStatsTab = () => (
    <div className="space-y-6">
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {/* 热门分类 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">热门分类</h3>
          <div className="space-y-3">
            {[...(localDocuments.length > 0
              ? [{ name: '本地文档', count: localDocuments.length }]
              : []),
              ...categories.map((cat) => ({ name: cat.name, count: cat.count || 0 })),
            ]
              .sort((a, b) => (b.count || 0) - (a.count || 0))
              .slice(0, 6)
              .map((cat, index) => (
                <div key={cat.name} className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <span className="flex-shrink-0 w-6 h-6 bg-blue-100 rounded-full flex items-center justify-center text-sm font-medium text-blue-600">
                      {index + 1}
                    </span>
                    <span className="text-gray-900">{cat.name}</span>
                  </div>
                  <span className="text-sm text-gray-600">{cat.count || 0} 篇</span>
                </div>
              ))}
            {categories.length === 0 && localDocuments.length === 0 && (
              <div className="text-sm text-gray-500">暂无分类数据</div>
            )}
          </div>
        </div>

        {/* 概况 */}
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-lg font-semibold text-gray-900 mb-4">知识库概况</h3>
          <div className="space-y-4 text-sm text-gray-600">
            <div className="flex items-center justify-between">
              <span>文档总数</span>
              <span className="font-medium">{stats.totalDocuments}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>集合数量</span>
              <span className="font-medium">{categories.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>本地文档</span>
              <span className="font-medium">{localDocuments.length}</span>
            </div>
            <div className="flex items-center justify-between">
              <span>最近搜索</span>
              <span className="font-medium">{searchHistory.length}</span>
            </div>
          </div>
        </div>
      </div>

      {/* 搜索记录 */}
      <div className="bg-white rounded-lg shadow p-6">
        <h3 className="text-lg font-semibold text-gray-900 mb-4">最近搜索</h3>
        {searchHistory.length === 0 ? (
          <div className="text-sm text-gray-500">暂无搜索记录</div>
        ) : (
          <div className="divide-y divide-gray-100">
            {searchHistory.slice(0, 10).map((item) => (
              <div key={item.query} className="py-2 flex items-center justify-between text-sm">
                <div>
                  <div className="font-medium text-gray-900">{item.query}</div>
                  <div className="text-xs text-gray-500">
                    {new Date(item.timestamp).toLocaleString()}
                  </div>
                </div>
                <span className="text-xs text-gray-500">次数 {item.count}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  return (
    <div className="flex h-screen bg-gray-50">
      <MobileMenu />
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <StatusBar />

        <div className="flex-1 overflow-y-auto">
          {/* 页面头部 */}
          <div className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center">
                    <Database className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">知识库管理</h1>
                    <p className="text-sm text-gray-500 mt-1">
                      管理文档、知识条目和向量嵌入
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button className="p-2 hover:bg-gray-100 rounded-lg" title="刷新">
                    <RefreshCw className="w-5 h-5 text-gray-600" />
                  </button>
                  <button
                    onClick={() => setActiveTab('upload')}
                    className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
                  >
                    <Upload className="w-4 h-4" />
                    上传文档
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* 标签页导航 */}
          <div className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-6">
              <div className="flex items-center gap-1">
                <button
                  onClick={() => {
                    setEditingDocumentId(null);
                    setActiveTab('documents');
                  }}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'documents'
                      ? 'border-black text-black'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  文档管理
                </button>
                <button
                  onClick={() => setActiveTab('upload')}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'upload'
                      ? 'border-black text-black'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  上传文档
                </button>
                <button
                  onClick={() => {
                    setEditingDocumentId(null);
                    setActiveTab('search');
                  }}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'search'
                      ? 'border-black text-black'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  搜索知识
                </button>
                <button
                  onClick={() => {
                    setEditingDocumentId(null);
                    setActiveTab('stats');
                  }}
                  className={`px-4 py-3 font-medium text-sm border-b-2 transition-colors ${
                    activeTab === 'stats'
                      ? 'border-black text-black'
                      : 'border-transparent text-gray-600 hover:text-gray-900'
                  }`}
                >
                  统计分析
                </button>
              </div>
            </div>
          </div>

          {/* 内容区 */}
          <div className="max-w-7xl mx-auto px-6 py-8">
            {activeTab === 'documents' && renderDocumentsTab()}
            {activeTab === 'upload' && renderUploadTab()}
            {activeTab === 'search' && renderSearchTab()}
            {activeTab === 'stats' && renderStatsTab()}
          </div>
        </div>
      </div>

      <SettingsModal />

      {/* 文档详情弹窗 */}
      {selectedDocument && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden mx-4">
            <div className="p-6 border-b border-gray-200 flex items-center justify-between">
              <h3 className="text-lg font-semibold text-gray-900">
                {selectedDocument.title}
              </h3>
              <button
                onClick={() => setSelectedDocument(null)}
                className="p-2 hover:bg-gray-100 rounded-lg"
              >
                ✕
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[60vh]">
              <div className="flex items-center gap-4 text-sm text-gray-600 mb-4">
                <span className="px-2 py-1 bg-blue-100 text-blue-700 rounded">
                  {selectedDocument.category}
                </span>
                <span>{formatFileSize(selectedDocument.size)}</span>
                <span>
                  {selectedDocument.updatedAt
                    ? new Date(selectedDocument.updatedAt).toLocaleDateString()
                    : '-'}
                </span>
              </div>
              <div className="flex flex-wrap gap-2 mb-4">
                {(selectedDocument.tags || []).map((tag) => (
                  <span
                    key={tag}
                    className="px-2 py-1 bg-gray-100 text-gray-700 text-xs rounded"
                  >
                    {tag}
                  </span>
                ))}
                {(selectedDocument.tags || []).length === 0 && (
                  <span className="text-xs text-gray-400">暂无标签</span>
                )}
              </div>
              <div className="prose prose-sm max-w-none">
                <p className="text-gray-700 whitespace-pre-wrap">{selectedDocument.content}</p>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 flex justify-end gap-3">
              <button
                onClick={() => setSelectedDocument(null)}
                className="px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 font-medium"
              >
                关闭
              </button>
              {selectedDocument.id.startsWith('local_') && (
                <button
                  onClick={() => {
                    setActiveTab('upload');
                    setUploadForm({
                      title: selectedDocument.title,
                      content: selectedDocument.content,
                      tags: (selectedDocument.tags || []).join(', '),
                    });
                    setEditingDocumentId(selectedDocument.id);
                    setSelectedDocument(null);
                  }}
                  className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 font-medium"
                >
                  继续编辑
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default KnowledgeBasePage;

/**
 * 文件系统浏览页面
 * 展示所有 Agent 输出的 artifacts 和文件
 */

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useLocation, Link } from 'react-router-dom';
import {
  FolderOpen,
  FileText,
  Download,
  Trash2,
  Eye,
  Filter,
  Search,
  RefreshCw,
  Calendar,
  User,
  HardDrive,
  Tag,
  ChevronRight,
  ChevronDown,
  X,
  Archive,
  Restore,
  Package,
  Recycle,
  FileSearch,
  CheckCircle2,
  Upload,
} from 'lucide-react';
import { clsx } from 'clsx';
import { API_BASE_URL, getAuthHeaderValue } from '@/services/api';

// ==================== 类型定义 ====================

interface ArtifactMetadata {
  artifact_id: string;
  filename: string;
  file_path: string;
  file_type: string;
  agent_source: string;
  user_id: string;
  session_id: string;
  project_id: string;
  file_size: number;
  content_hash: string;
  created_at: string;
  updated_at: string;
  tags: string[];
  description: string;
  parent_id?: string;
  children_ids?: string[];
  preview?: string;
  metadata?: Record<string, any>;
}

interface ArtifactListResponse {
  success: boolean;
  total: number;
  data: ArtifactMetadata[];
}

interface StatisticsResponse {
  success: boolean;
  data: {
    total_artifacts: number;
    type_counts: Record<string, number>;
    agent_counts: Record<string, number>;
    total_size_bytes: number;
    total_size_mb: number;
    avg_size_bytes: number;
    oldest_artifact: string;
    newest_artifact: string;
  };
}

// 文件类型显示名称和颜色
const FILE_TYPE_CONFIG: Record<string, { name: string; color: string; icon: string }> = {
  script: { name: '剧本', color: 'blue', icon: '📜' },
  outline: { name: '大纲', color: 'purple', icon: '📋' },
  character: { name: '人物', color: 'pink', icon: '👤' },
  plot_points: { name: '情节点', color: 'indigo', icon: '📍' },
  mind_map: { name: '思维导图', color: 'green', icon: '🧠' },
  ocr_result: { name: 'OCR结果', color: 'orange', icon: '📷' },
  evaluation: { name: '评测报告', color: 'red', icon: '📊' },
  analysis: { name: '分析报告', color: 'cyan', icon: '🔍' },
  markdown: { name: 'Markdown', color: 'gray', icon: '📝' },
  json: { name: 'JSON', color: 'yellow', icon: '🗂️' },
  image: { name: '图片', color: 'emerald', icon: '🖼️' },
  other: { name: '其他', color: 'slate', icon: '📄' },
};

// ==================== 组件 ====================

export default function FileSystemPage() {
  const location = useLocation();
  const [artifacts, setArtifacts] = useState<ArtifactMetadata[]>([]);
  const [statistics, setStatistics] = useState<StatisticsResponse['data'] | null>(null);
  const [loading, setLoading] = useState(true);
  const [selectedArtifact, setSelectedArtifact] = useState<ArtifactMetadata | null>(null);
  const [previewContent, setPreviewContent] = useState<string>('');
  const [showPreview, setShowPreview] = useState(false);
  const [filterNameInput, setFilterNameInput] = useState('');
  const [taskIdInput, setTaskIdInput] = useState('');
  const [reindexProgress, setReindexProgress] = useState<{
    task_id: string;
    status: string;
    total_files: number;
    processed_files: number;
    progress: number;
    error?: string | null;
  } | null>(null);
  const [showRagGraph, setShowRagGraph] = useState(false);
  const [showRecycleBin, setShowRecycleBin] = useState(false);
  const [recycleItems, setRecycleItems] = useState<ArtifactMetadata[]>([]);
  const [selectedFiles, setSelectedFiles] = useState<Set<string>>(new Set());
  const [isBatchMode, setIsBatchMode] = useState(false);

  // 过滤状态
  const [filters, setFilters] = useState({
    search: '',
    fileType: '',
    agentSource: '',
    userId: '',
    projectId: '',
    phase: '',
    category: '',
    ragOnly: false,
    ragSource: '',
  });
  const [savedFilters, setSavedFilters] = useState<
    { name: string; filters: typeof filters }[]
  >([]);

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    setFilters((prev) => ({
      ...prev,
      search: params.get('search') || prev.search,
      fileType: params.get('file_type') || prev.fileType,
      agentSource: params.get('agent_source') || prev.agentSource,
      userId: params.get('user_id') || prev.userId,
      projectId: params.get('project_id') || prev.projectId,
    }));
  }, [location.search]);

  useEffect(() => {
    try {
      const raw = localStorage.getItem('files_saved_filters');
      if (raw) {
        setSavedFilters(JSON.parse(raw));
      }
    } catch {
      setSavedFilters([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('files_saved_filters', JSON.stringify(savedFilters));
  }, [savedFilters]);

  // 加载数据
  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      // 加载 artifacts
      const params = new URLSearchParams();
      if (filters.fileType) params.append('file_type', filters.fileType);
      if (filters.agentSource) params.append('agent_source', filters.agentSource);
      if (filters.userId) params.append('user_id', filters.userId);
      if (filters.projectId) params.append('project_id', filters.projectId);

      const artifactsRes = await fetch(`${API_BASE_URL}/juben/files/artifacts?${params}`, {
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (artifactsRes.ok) {
        const artifactsData: ArtifactListResponse = await artifactsRes.json();
        setArtifacts(artifactsData.data || []);
      } else {
        setArtifacts([]);
      }

      // 加载统计
      const statsRes = await fetch(`${API_BASE_URL}/juben/files/statistics`, {
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (statsRes.ok) {
        const statsData: StatisticsResponse = await statsRes.json();
        setStatistics(statsData.data);
      }
    } catch (error) {
      console.error('加载数据失败:', error);
      setArtifacts([]);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // 预览文件
  const handlePreview = async (artifact: ArtifactMetadata) => {
    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/preview/${artifact.artifact_id}`, {
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      const data = await res.json();
      if (data.success) {
        setPreviewContent(data.content);
        setSelectedArtifact(artifact);
        setShowPreview(true);
      }
    } catch (error) {
      console.error('预览失败:', error);
    }
  };

  // 下载文件
  const handleDownload = async (artifact: ArtifactMetadata) => {
    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/download/${artifact.artifact_id}`, {
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = artifact.filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      }
    } catch (error) {
      console.error('下载失败:', error);
    }
  };

  // 删除文件
  const handleDelete = async (artifactId: string) => {
    if (!confirm('确定要删除这个文件吗？')) return;

    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/artifact/${artifactId}`, {
        method: 'DELETE',
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (res.ok) {
        await loadData();
      }
    } catch (error) {
      console.error('删除失败:', error);
    }
  };

  // 移到回收站
  const moveToRecycleBin = async (artifactId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/artifact/${artifactId}/move`, {
        method: 'POST',
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ target_folder: 'recycle_bin' }),
      });
      if (res.ok) {
        await loadData();
      }
    } catch (error) {
      console.error('移到回收站失败:', error);
    }
  };

  // 从回收站恢复
  const restoreFromRecycleBin = async (artifactId: string) => {
    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/recycle/${artifactId}/restore`, {
        method: 'POST',
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (res.ok) {
        await loadRecycleBinData();
      }
    } catch (error) {
      console.error('恢复失败:', error);
    }
  };

  // 永久删除
  const permanentDelete = async (artifactId: string) => {
    if (!confirm('确定要永久删除这个文件吗？此操作无法撤销！')) return;

    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/artifact/${artifactId}`, {
        method: 'DELETE',
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (res.ok) {
        await loadRecycleBinData();
      }
    } catch (error) {
      console.error('删除失败:', error);
    }
  };

  // 加载回收站数据
  const loadRecycleBinData = async () => {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/recycle`, {
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (res.ok) {
        const data = await res.json();
        setRecycleItems(data.data || []);
      } else {
        setRecycleItems([]);
      }
    } catch (error) {
      console.error('加载回收站失败:', error);
      setRecycleItems([]);
    } finally {
      setLoading(false);
    }
  };

  // 清空回收站
  const emptyRecycleBin = async () => {
    if (!confirm('确定要清空回收站吗？所有文件将被永久删除！')) return;

    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/recycle/cleanup`, {
        method: 'POST',
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
      });
      if (res.ok) {
        await loadRecycleBinData();
      }
    } catch (error) {
      console.error('清空回收站失败:', error);
    }
  };

  // 批量下载ZIP
  const handleBatchDownload = async () => {
    if (selectedFiles.size === 0) {
      alert('请先选择要下载的文件');
      return;
    }

    try {
      const res = await fetch(`${API_BASE_URL}/juben/files/download-zip`, {
        method: 'POST',
        headers: {
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ artifact_ids: Array.from(selectedFiles) }),
      });
      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `batch_download_${Date.now()}.zip`;
        a.click();
        URL.revokeObjectURL(url);
        setSelectedFiles(new Set());
        setIsBatchMode(false);
      } else {
        alert('批量下载失败');
      }
    } catch (error) {
      console.error('批量下载失败:', error);
      alert('批量下载失败');
    }
  };

  // 批量移到回收站
  const handleBatchMoveToRecycleBin = async () => {
    if (selectedFiles.size === 0) {
      alert('请先选择要移到回收站的文件');
      return;
    }

    if (!confirm(`确定要移到回收站 ${selectedFiles.size} 个文件吗？`)) return;

    try {
      const promises = Array.from(selectedFiles).map(id =>
        fetch(`${API_BASE_URL}/juben/files/artifact/${id}/move`, {
          method: 'POST',
          headers: {
            ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ target_folder: 'recycle_bin' }),
        })
      );
      await Promise.all(promises);
      await loadData();
      setSelectedFiles(new Set());
      setIsBatchMode(false);
    } catch (error) {
      console.error('批量移到回收站失败:', error);
      alert('批量移到回收站失败');
    }
  };

  // 切换文件选择
  const toggleFileSelection = (artifactId: string) => {
    const newSelected = new Set(selectedFiles);
    if (newSelected.has(artifactId)) {
      newSelected.delete(artifactId);
    } else {
      newSelected.add(artifactId);
    }
    setSelectedFiles(newSelected);
  };

  // 全选
  const selectAllFiles = () => {
    const allIds = new Set(filteredArtifacts.map(a => a.artifact_id));
    setSelectedFiles(allIds);
  };

  // 取消全选
  const clearSelection = () => {
    setSelectedFiles(new Set());
  };

  // 格式化文件大小
  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  };

  // 格式化时间
  const formatDate = (isoString: string): string => {
    const date = new Date(isoString);
    return date.toLocaleString('zh-CN');
  };

  const baseArtifacts = (artifacts || []).filter((artifact) => {
    if (filters.search) {
      const searchLower = filters.search.toLowerCase();
      if (!artifact.filename.toLowerCase().includes(searchLower) &&
          !artifact.description?.toLowerCase().includes(searchLower)) {
        return false;
      }
    }
    if (filters.phase) {
      const phaseTag = (artifact.tags || []).find((tag) => tag.startsWith('phase:'));
      if (!phaseTag || phaseTag !== `phase:${filters.phase}`) {
        return false;
      }
    }
    if (filters.category) {
      const categoryTag = (artifact.tags || []).find((tag) => tag.startsWith('category:'));
      if (!categoryTag || categoryTag !== `category:${filters.category}`) {
        return false;
      }
    }
    return true;
  });

  const ragSourceCounts = baseArtifacts.reduce((acc, artifact) => {
    const ragTrace = artifact.metadata?.rag_trace;
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
      radius: Math.max(12, Math.round((count / (max || 1)) * 28)),
      x: 60 + (idx % 5) * 90,
      y: 50 + Math.floor(idx / 5) * 90,
    }));
  }, [ragSourceCounts]);

  // 过滤后的 artifacts
  const filteredArtifacts = baseArtifacts.filter((artifact) => {
    if (filters.ragOnly) {
      const ragTrace = artifact.metadata?.rag_trace;
      if (!Array.isArray(ragTrace) || ragTrace.length === 0) {
        return false;
      }
    }
    if (filters.ragSource) {
      const ragTrace = artifact.metadata?.rag_trace;
      if (!Array.isArray(ragTrace) || !ragTrace.some((item: any) => (item?.source || 'unknown') === filters.ragSource)) {
        return false;
      }
    }
    return true;
  });

  const getMindMapPreview = (artifact: ArtifactMetadata) => {
    if (artifact.file_type !== 'mind_map' && !(artifact.tags || []).includes('mind_map')) {
      return null;
    }
    const mindMap = artifact.metadata?.mind_map;
    const svg = mindMap?.svg || artifact.metadata?.svg;
    const title = mindMap?.title;
    if (!svg) return null;
    return (
      <div className="mt-2 rounded-lg border border-gray-200 bg-white p-2">
        {title && (
          <div className="text-xs font-medium text-gray-600 mb-1">{title}</div>
        )}
        <div className="max-h-[140px] overflow-hidden">
          <div
            className="origin-top-left scale-[0.8]"
            dangerouslySetInnerHTML={{ __html: svg }}
          />
        </div>
      </div>
    );
  };

  const phaseOptions = Array.from(
    new Set(
      artifacts.flatMap((artifact) =>
        (artifact.tags || [])
          .filter((tag) => tag.startsWith('phase:'))
          .map((tag) => tag.replace('phase:', ''))
      )
    )
  );

  const categoryOptions = Array.from(
    new Set(
      artifacts.flatMap((artifact) =>
        (artifact.tags || [])
          .filter((tag) => tag.startsWith('category:'))
          .map((tag) => tag.replace('category:', ''))
      )
    )
  );

  const handleClearFilters = () => {
    setFilters({
      search: '',
      fileType: '',
      agentSource: '',
      userId: '',
      projectId: '',
      phase: '',
      category: '',
      ragOnly: false,
      ragSource: '',
    });
  };

  const handleSaveFilters = () => {
    const name = filterNameInput.trim();
    if (!name) return;
    setSavedFilters((prev) => [
      { name, filters: { ...filters } },
      ...prev.filter((item) => item.name !== name),
    ]);
    setFilterNameInput('');
  };

  const handleApplySaved = (name: string) => {
    const saved = savedFilters.find((item) => item.name === name);
    if (saved) {
      setFilters({ ...saved.filters, ragOnly: Boolean(saved.filters.ragOnly), ragSource: saved.filters.ragSource || '' });
    }
  };

  const handleDeleteSaved = (name: string) => {
    setSavedFilters((prev) => prev.filter((item) => item.name !== name));
  };

  useEffect(() => {
    if (!taskIdInput.trim()) return;
    const wsUrl = API_BASE_URL.replace('https://', 'wss://').replace('http://', 'ws://');
    const ws = new WebSocket(`${wsUrl}/juben/projects/reindex/stream/${taskIdInput.trim()}`);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        setReindexProgress(data);
      } catch {
        // ignore
      }
    };
    ws.onerror = () => {
      // ignore
    };
    return () => {
      ws.close();
    };
  }, [taskIdInput]);

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 头部 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="max-w-7xl mx-auto px-4 py-6">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-3">
              <div className="p-3 bg-blue-600 rounded-xl">
                <FolderOpen className="w-8 h-8 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                  文件系统
                </h1>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  所有 Agent 输出文件和 Artifacts
                </p>
              </div>
            </div>

            {/* 回收站和批量操作按钮 */}
            <div className="flex items-center gap-2">
              {showRecycleBin ? (
                <>
                  <button
                    onClick={() => setShowRecycleBin(false)}
                    className="flex items-center gap-2 px-3 py-1.5 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm font-medium transition-colors"
                  >
                    <HardDrive className="w-4 h-4" />
                    返回文件列表
                  </button>
                  <button
                    onClick={() => emptyRecycleBin()}
                    className="flex items-center gap-2 px-3 py-1.5 bg-red-100 hover:bg-red-200 text-red-700 rounded-lg text-sm font-medium transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                    清空回收站
                  </button>
                </>
              ) : (
                <>
                  <button
                    onClick={() => setShowRecycleBin(true)}
                    className="flex items-center gap-2 px-3 py-1.5 hover:bg-gray-100 rounded-lg text-sm font-medium transition-colors"
                  >
                    <Recycle className="w-4 h-4 text-gray-600" />
                    回收站
                  </button>
                  <div className="h-6 w-px bg-gray-300"></div>
                  <button
                    onClick={() => setIsBatchMode(!isBatchMode)}
                    className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors ${
                      isBatchMode
                        ? 'bg-blue-600 text-white'
                        : 'hover:bg-gray-100'
                    }`}
                  >
                    <Package className="w-4 h-4" />
                    {isBatchMode ? '退出批量模式' : '批量操作'}
                  </button>
                  {isBatchMode && selectedFiles.size > 0 && (
                    <>
                      <button
                        onClick={() => handleBatchMoveToRecycleBin()}
                        className="flex items-center gap-2 px-3 py-1.5 bg-orange-100 hover:bg-orange-200 text-orange-700 rounded-lg text-sm font-medium transition-colors"
                      >
                        <Recycle className="w-4 h-4" />
                        移到回收站
                      </button>
                      <button
                        onClick={handleBatchDownload}
                        className="flex items-center gap-2 px-3 py-1.5 bg-blue-100 hover:bg-blue-200 text-blue-700 rounded-lg text-sm font-medium transition-colors"
                      >
                        <Download className="w-4 h-4" />
                        批量下载
                      </button>
                    </>
                  )}
                </>
              )}
            </div>

            <button
              onClick={loadData}
              className="flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg transition-colors"
            >
              <RefreshCw className={clsx('w-4 h-4', loading && 'animate-spin')} />
              刷新
            </button>
          </div>

          {/* 索引任务进度 */}
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-6">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              索引任务进度
            </div>
            <div className="flex flex-wrap items-center gap-2">
              <input
                value={taskIdInput}
                onChange={(e) => setTaskIdInput(e.target.value)}
                placeholder="输入 task_id..."
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm min-w-[240px]"
              />
              {reindexProgress && (
                <div className="flex-1 min-w-[220px]">
                  <div className="flex items-center justify-between text-xs text-gray-500 mb-1">
                    <span>{reindexProgress.status}</span>
                    <span>{reindexProgress.progress?.toFixed(1) || 0}%</span>
                  </div>
                  <div className="h-2 bg-gray-100 rounded">
                    <div
                      className="h-2 rounded bg-blue-500"
                      style={{ width: `${reindexProgress.progress || 0}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">
                    {reindexProgress.processed_files}/{reindexProgress.total_files} 文件
                  </div>
                  {reindexProgress.error && (
                    <div className="text-xs text-red-600 mt-1">{reindexProgress.error}</div>
                  )}
                </div>
              )}
            </div>
          </div>

          {/* 统计卡片 */}
          {statistics && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <div className="bg-blue-50 dark:bg-blue-900/20 rounded-lg p-4">
                <div className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                  {statistics.total_artifacts ?? 0}
                </div>
                <div className="text-sm text-blue-700 dark:text-blue-300">
                  总文件数
                </div>
              </div>
              <div className="bg-green-50 dark:bg-green-900/20 rounded-lg p-4">
                <div className="text-2xl font-bold text-green-600 dark:text-green-400">
                  {statistics.total_size_mb ?? 0} MB
                </div>
                <div className="text-sm text-green-700 dark:text-green-300">
                  总大小
                </div>
              </div>
              <div className="bg-purple-50 dark:bg-purple-900/20 rounded-lg p-4">
                <div className="text-2xl font-bold text-purple-600 dark:text-purple-400">
                  {Object.keys(statistics.type_counts || {}).length}
                </div>
                <div className="text-sm text-purple-700 dark:text-purple-300">
                  文件类型
                </div>
              </div>
              <div className="bg-orange-50 dark:bg-orange-900/20 rounded-lg p-4">
                <div className="text-2xl font-bold text-orange-600 dark:text-orange-400">
                  {Object.keys(statistics.agent_counts || {}).length}
                </div>
                <div className="text-sm text-orange-700 dark:text-orange-300">
                  Agent 数量
                </div>
              </div>
            </div>
          )}
        </div>
      </header>

      {/* 主内容 */}
      <main className="max-w-7xl mx-auto px-4 py-6">
        {/* 过滤器 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-6">
          <div className="flex flex-wrap gap-4">
            <div className="flex items-center gap-2">
              <input
                value={filterNameInput}
                onChange={(e) => setFilterNameInput(e.target.value)}
                placeholder="筛选名称"
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
              />
              <button
                onClick={handleSaveFilters}
                disabled={!filterNameInput.trim()}
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
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
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
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
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
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
                className="px-3 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50"
              >
                清空
              </button>
            </div>

            {/* 搜索框 */}
            <div className="flex-1 min-w-[200px]">
              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="搜索文件名或描述..."
                  value={filters.search}
                  onChange={(e) => setFilters({ ...filters, search: e.target.value })}
                  className="w-full pl-10 pr-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                />
              </div>
            </div>

            {/* 文件类型过滤 */}
            <select
              value={filters.fileType}
              onChange={(e) => setFilters({ ...filters, fileType: e.target.value })}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="">所有类型</option>
              {Object.entries(FILE_TYPE_CONFIG).map(([key, { name }]) => (
                <option key={key} value={key}>{name}</option>
              ))}
            </select>

            {/* Agent 过滤 */}
            <select
              value={filters.agentSource}
              onChange={(e) => setFilters({ ...filters, agentSource: e.target.value })}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="">所有 Agent</option>
              <option value="short_drama_creator">短剧创作</option>
              <option value="short_drama_evaluation">短剧评测</option>
              <option value="ocr_agent">OCR 识别</option>
              <option value="workflow_orchestrator">工作流</option>
              <option value="mind_map">思维导图</option>
            </select>

            {/* 阶段过滤 */}
            <select
              value={filters.phase}
              onChange={(e) => setFilters({ ...filters, phase: e.target.value })}
              className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
            >
              <option value="">所有阶段</option>
              {phaseOptions.map((phase) => (
                <option key={phase} value={phase}>{phase}</option>
              ))}
            </select>

            {/* 分类过滤 */}
          <select
            value={filters.category}
            onChange={(e) => setFilters({ ...filters, category: e.target.value })}
            className="px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-white dark:bg-gray-700 text-gray-900 dark:text-white focus:ring-2 focus:ring-blue-500"
          >
            <option value="">所有分类</option>
            {categoryOptions.map((category) => (
              <option key={category} value={category}>{category}</option>
            ))}
          </select>
          <button
            onClick={() => setFilters({ ...filters, ragOnly: !filters.ragOnly })}
            className={clsx(
              'px-4 py-2 text-sm rounded-lg border transition-colors',
              filters.ragOnly
                ? 'border-blue-500 text-blue-600 bg-blue-50'
                : 'border-gray-300 text-gray-600 hover:bg-gray-50'
            )}
          >
            仅看含引用
          </button>
        </div>
        </div>

        {Object.keys(ragSourceCounts).length > 0 && (
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow p-4 mb-6">
            <div className="text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              RAG 引用源
            </div>
            <div className="flex items-center gap-2 mb-3">
              <button
                onClick={() => setShowRagGraph((prev) => !prev)}
                className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50"
              >
                {showRagGraph ? '隐藏图谱' : '显示图谱'}
              </button>
            </div>
            {showRagGraph && ragGraphNodes.length > 0 && (
              <div className="mb-4 overflow-auto">
                <svg width="520" height={Math.max(160, Math.ceil(ragGraphNodes.length / 5) * 90)}>
                  {ragGraphNodes.map((node) => (
                    <g
                      key={node.id}
                      onClick={() => setFilters({ ...filters, ragOnly: true, ragSource: node.id })}
                      style={{ cursor: 'pointer' }}
                    >
                      <circle cx={node.x} cy={node.y} r={node.radius} fill="#3B82F6" opacity="0.2" />
                      <circle cx={node.x} cy={node.y} r={Math.max(8, node.radius - 6)} fill="#3B82F6" opacity="0.6" />
                      <text x={node.x} y={node.y + node.radius + 12} textAnchor="middle" fontSize="10" fill="#4B5563">
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
                  onClick={() =>
                    setFilters({ ...filters, ragOnly: true, ragSource: source })
                  }
                  className={clsx(
                    'px-3 py-1.5 text-xs rounded-full border transition-colors',
                    filters.ragSource === source
                      ? 'border-blue-500 text-blue-700 bg-blue-50'
                      : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                  )}
                >
                  {source} ({count})
                </button>
              ))}
              {filters.ragSource && (
                <button
                  onClick={() => setFilters({ ...filters, ragSource: '' })}
                  className="px-3 py-1.5 text-xs rounded-full border border-gray-200 text-gray-500 hover:bg-gray-50"
                >
                  清除引用源
                </button>
              )}
            </div>
          </div>
        )}

        {/* 文件列表 */}
        <div className="bg-white dark:bg-gray-800 rounded-xl shadow overflow-hidden">
          {loading ? (
            <div className="p-12 text-center text-gray-500">
              加载中...
            </div>
          ) : filteredArtifacts.length === 0 ? (
            <div className="p-12 text-center text-gray-500">
              <FileText className="w-16 h-16 mx-auto mb-4 opacity-50" />
              <p>没有找到文件</p>
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-gray-50 dark:bg-gray-900">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      文件名
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      类型
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      来源
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      大小
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      创建时间
                    </th>
                    <th className="px-6 py-3 text-right text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
                  {filteredArtifacts.map((artifact) => {
                    const typeConfig = FILE_TYPE_CONFIG[artifact.file_type] || FILE_TYPE_CONFIG.other;
                    return (
                      <tr key={artifact.artifact_id} className="hover:bg-gray-50 dark:hover:bg-gray-750">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <span className="text-2xl">{typeConfig.icon}</span>
                            <div>
                              <div className="font-medium text-gray-900 dark:text-white">
                                {artifact.filename}
                              </div>
                              {artifact.description && (
                                <div className="text-xs text-gray-500 dark:text-gray-400 truncate max-w-xs">
                                  {artifact.description}
                                </div>
                              )}
                              {getMindMapPreview(artifact)}
                              {artifact.tags.length > 0 && (
                                <div className="flex gap-1 mt-1">
                                  {artifact.tags.map((tag) => (
                                    <span
                                      key={tag}
                                      className="px-2 py-0.5 bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 text-xs rounded"
                                    >
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              )}
                              {Array.isArray(artifact.metadata?.rag_trace) && artifact.metadata?.rag_trace?.length > 0 && (
                                <div className="mt-1 text-xs text-blue-600">
                                  引用链: {artifact.metadata.rag_trace.length} 条
                                </div>
                              )}
                            </div>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <span className={clsx(
                            'px-2 py-1 text-xs font-medium rounded',
                            `bg-${typeConfig.color}-100 text-${typeConfig.color}-700 dark:bg-${typeConfig.color}-900/30 dark:text-${typeConfig.color}-300`
                          )}>
                            {typeConfig.name}
                          </span>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          {artifact.agent_source}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          {formatFileSize(artifact.file_size)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600 dark:text-gray-400">
                          {formatDate(artifact.created_at)}
                        </td>
                        <td className="px-6 py-4">
                          <div className="flex items-center justify-end gap-2">
                            <button
                              onClick={() => handlePreview(artifact)}
                              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                              title="预览"
                            >
                              <Eye className="w-4 h-4 text-gray-500" />
                            </button>
                            <button
                              onClick={() => handleDownload(artifact)}
                              className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
                              title="下载"
                            >
                              <Download className="w-4 h-4 text-gray-500" />
                            </button>
                            <button
                              onClick={() => handleDelete(artifact.artifact_id)}
                              className="p-2 hover:bg-red-100 dark:hover:bg-red-900/30 rounded-lg transition-colors"
                              title="删除"
                            >
                              <Trash2 className="w-4 h-4 text-red-500" />
                            </button>
                          </div>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* 分页信息 */}
        {!loading && filteredArtifacts.length > 0 && (
          <div className="mt-4 text-center text-sm text-gray-500 dark:text-gray-400">
            显示 {filteredArtifacts.length} 个文件，共 {artifacts.length} 个
          </div>
        )}
      </main>

      {/* 预览弹窗 */}
      {showPreview && selectedArtifact && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-4xl w-full max-h-[80vh] overflow-hidden flex flex-col mx-4">
            {/* 头部 */}
            <div className="p-4 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  {selectedArtifact.filename}
                </h3>
                <p className="text-sm text-gray-500 dark:text-gray-400">
                  {selectedArtifact.file_path}
                </p>
              </div>
              <button
                onClick={() => setShowPreview(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                <X className="w-5 h-5 text-gray-500" />
              </button>
            </div>

            {/* 内容 */}
            <div className="flex-1 overflow-auto p-4">
              {Array.isArray(selectedArtifact.metadata?.rag_trace) && selectedArtifact.metadata?.rag_trace?.length > 0 && (
                <div className="mb-4 rounded-lg border border-blue-100 bg-blue-50 px-3 py-2 text-xs text-blue-800">
                  <div className="font-medium mb-1">RAG 引用链</div>
                  <div className="space-y-1">
                    {selectedArtifact.metadata.rag_trace.map((item: any, idx: number) => (
                      <div key={idx} className="bg-white/70 rounded px-2 py-1">
                        <div>来源: {item.source || 'unknown'}</div>
                        {item.query && <div>查询: {item.query}</div>}
                        {item.result_count !== undefined && <div>结果: {item.result_count}</div>}
                        {item.file_id && <div>文件: {item.file_id}</div>}
                        {item.filename && selectedArtifact.project_id && (
                          <div className="mt-1">
                            <Link
                              to={`/files?project_id=${selectedArtifact.project_id}&search=${encodeURIComponent(item.filename)}`}
                              className="text-blue-600 hover:underline"
                            >
                              打开关联文件
                            </Link>
                          </div>
                        )}
                      </div>
                    ))}
                  </div>
                </div>
              )}
              <pre className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap font-mono">
                {previewContent}
              </pre>
            </div>

            {/* 底部 */}
            <div className="p-4 border-t border-gray-200 dark:border-gray-700 flex justify-end gap-3">
              <button
                onClick={() => setShowPreview(false)}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg font-medium transition-colors"
              >
                关闭
              </button>
              <button
                onClick={() => {
                  handleDownload(selectedArtifact);
                  setShowPreview(false);
                }}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                下载
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

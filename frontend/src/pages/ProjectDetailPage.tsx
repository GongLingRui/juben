/**
 * 项目详情页面
 * 展示项目信息、文件、入口与编辑能力
 */

import { useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import { useProjectStore } from '@/store/projectStore';
import { useUIStore } from '@/store/uiStore';
import {
  ArrowLeft,
  FolderOpen,
  FileText,
  Calendar,
  Tag,
  Edit3,
  Save,
  Trash2,
  ExternalLink,
  Users,
  Layers,
  Package,
  Activity,
  Play,
  Database,
} from 'lucide-react';
import { formatDistanceToNow } from 'date-fns';
import { zhCN } from 'date-fns/locale';
import type { ProjectStatus } from '@/types';
import {
  listAssets,
  createAsset,
  deleteAsset,
  listAssetCollections
} from '@/services/assetsService';
import {
  listPipelineTemplates,
  runPipeline,
  listPipelineRuns
} from '@/services/pipelineService';
import {
  listReleaseTemplates,
  calculateRoi,
  generateChecklist
} from '@/services/releaseService';
import {
  listProjectMembers,
  addProjectMember,
  removeProjectMember
} from '@/services/projectService';
import {
  getMemorySettings,
  updateMemorySettings,
  getMemoryMetrics,
  getMemoryQuality,
  listMemorySnapshots,
  createMemorySnapshot,
  restoreMemorySnapshot
} from '@/services/memoryService';
import { useChatStore } from '@/store/chatStore';

export default function ProjectDetailPage() {
  const { projectId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const { sidebarOpen, sidebarCollapsed } = useUIStore();

  const {
    currentProject,
    projectFiles,
    isLoading,
    error,
    loadProject,
    updateProject,
    deleteProject,
    clearError,
  } = useProjectStore();

  const [isEditing, setIsEditing] = useState(false);
  const [editForm, setEditForm] = useState({
    name: '',
    description: '',
    tags: '',
    status: 'active' as ProjectStatus,
  });
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [activeTab, setActiveTab] = useState<'overview' | 'assets' | 'pipeline' | 'release' | 'team' | 'memory'>('overview');
  const [assets, setAssets] = useState<any[]>([]);
  const [assetCollections, setAssetCollections] = useState<Record<string, any[]>>({});
  const [assetForm, setAssetForm] = useState({ name: '', asset_type: 'generic', tags: '', collection: 'default' });
  const [pipelineTemplates, setPipelineTemplates] = useState<any[]>([]);
  const [pipelineRuns, setPipelineRuns] = useState<any[]>([]);
  const [pipelineInput, setPipelineInput] = useState('');
  const [selectedTemplateId, setSelectedTemplateId] = useState('');
  const [releaseTemplates, setReleaseTemplates] = useState<Record<string, any>>({});
  const [roiForm, setRoiForm] = useState({ views: 10000, ctr: 0.02, cvr: 0.03, arpu: 3, cost: 2000 });
  const [roiResult, setRoiResult] = useState<any | null>(null);
  const [checklist, setChecklist] = useState<string[]>([]);
  const [releasePlatform, setReleasePlatform] = useState('douyin');
  const [teamMembers, setTeamMembers] = useState<any[]>([]);
  const [memberForm, setMemberForm] = useState({ user_id: '', role: 'member', display_name: '' });
  const [selectedRunId, setSelectedRunId] = useState<string>('');
  const [ragSourceFilter, setRagSourceFilter] = useState<string>('all');
  const [memorySettings, setMemorySettings] = useState<any | null>(null);
  const [memoryMetrics, setMemoryMetrics] = useState<any | null>(null);
  const [memoryQuality, setMemoryQuality] = useState<any | null>(null);
  const [memorySnapshots, setMemorySnapshots] = useState<any[]>([]);
  const [snapshotLabel, setSnapshotLabel] = useState('');
  const [memoryQuery, setMemoryQuery] = useState('');

  const currentSession = useChatStore((state) => state.currentSession);
  const sessionId = currentSession || localStorage.getItem('sessionId') || 'default_session';
  const userId = localStorage.getItem('userId') || 'default-user';

  useEffect(() => {
    if (!projectId) return;
    loadProject(projectId);
  }, [projectId, loadProject]);

  useEffect(() => {
    if (!projectId) return;
    listAssets(projectId).then((res) => setAssets(res.data || [])).catch(() => setAssets([]));
    listAssetCollections(projectId).then((res) => setAssetCollections(res.data || {})).catch(() => setAssetCollections({}));
    listPipelineTemplates().then((res) => {
      setPipelineTemplates(res.data || []);
      if (!selectedTemplateId && res.data?.length) setSelectedTemplateId(res.data[0].id);
    }).catch(() => setPipelineTemplates([]));
    listPipelineRuns(projectId).then((res) => setPipelineRuns(res.data || [])).catch(() => setPipelineRuns([]));
    listReleaseTemplates().then((res) => setReleaseTemplates(res.data || {})).catch(() => setReleaseTemplates({}));
    listProjectMembers(projectId).then((res) => setTeamMembers(res.data || [])).catch(() => setTeamMembers([]));
  }, [projectId]);

  useEffect(() => {
    if (pipelineRuns.length && !selectedRunId) {
      setSelectedRunId(pipelineRuns[0].id);
    }
  }, [pipelineRuns, selectedRunId]);

  useEffect(() => {
    if (!projectId || !sessionId) return;
    getMemorySettings({ user_id: userId, project_id: projectId })
      .then((res) => setMemorySettings(res.data || null))
      .catch(() => setMemorySettings(null));
    getMemoryMetrics({ user_id: userId, session_id: sessionId, query: memoryQuery || currentProject?.name || '' })
      .then((res) => setMemoryMetrics(res.data || null))
      .catch(() => setMemoryMetrics(null));
    getMemoryQuality({ user_id: userId, session_id: sessionId, query: memoryQuery || currentProject?.name || '' })
      .then((res) => setMemoryQuality(res.data || null))
      .catch(() => setMemoryQuality(null));
    listMemorySnapshots({ user_id: userId, session_id: sessionId, project_id: projectId })
      .then((res) => setMemorySnapshots(res.data || []))
      .catch(() => setMemorySnapshots([]));
  }, [projectId, sessionId, memoryQuery, currentProject?.name]);

  useEffect(() => {
    if (!currentProject) return;
    setEditForm({
      name: currentProject.name,
      description: currentProject.description || '',
      tags: (currentProject.tags || []).join(', '),
      status: currentProject.status,
    });
  }, [currentProject]);

  useEffect(() => {
    const shouldEdit = searchParams.get('edit');
    if (shouldEdit === '1') {
      setIsEditing(true);
    }
  }, [searchParams]);

  const handleSave = async () => {
    if (!currentProject || !editForm.name.trim()) return;
    await updateProject(currentProject.id, {
      name: editForm.name.trim(),
      description: editForm.description.trim(),
      tags: editForm.tags
        .split(',')
        .map((tag) => tag.trim())
        .filter(Boolean),
      status: editForm.status,
    });
    setIsEditing(false);
  };

  const handleDelete = async () => {
    if (!currentProject) return;
    await deleteProject(currentProject.id);
    navigate('/projects');
  };

  const handleCreateAsset = async () => {
    if (!projectId || !assetForm.name.trim()) return;
    const res = await createAsset({
      project_id: projectId,
      name: assetForm.name.trim(),
      asset_type: assetForm.asset_type,
      tags: assetForm.tags.split(',').map((t) => t.trim()).filter(Boolean),
      collection: assetForm.collection || 'default'
    });
    if (res.success) {
      setAssets([res.data, ...assets]);
      setAssetForm({ name: '', asset_type: 'generic', tags: '', collection: 'default' });
      listAssetCollections(projectId).then((r) => setAssetCollections(r.data || {}));
    }
  };

  const handleDeleteAsset = async (assetId: string) => {
    if (!projectId) return;
    await deleteAsset(projectId, assetId);
    const updated = assets.filter((item) => item.id !== assetId);
    setAssets(updated);
    listAssetCollections(projectId).then((r) => setAssetCollections(r.data || {}));
  };

  const handleRunPipeline = async () => {
    if (!projectId || !pipelineInput.trim() || !selectedTemplateId) return;
    const userId = localStorage.getItem('userId') || 'default_user';
    const sessionId = localStorage.getItem('sessionId') || `pipeline_${Date.now()}`;
    const res = await runPipeline({
      template_id: selectedTemplateId,
      user_input: pipelineInput,
      user_id: userId,
      session_id: sessionId,
      project_id: projectId
    });
    if (res.success) {
      setPipelineRuns([res.data, ...pipelineRuns]);
    }
  };

  const handleCalculateRoi = async () => {
    const res = await calculateRoi(roiForm);
    if (res.success) setRoiResult(res.data);
  };

  const handleChecklist = async () => {
    const res = await generateChecklist({
      platform: releasePlatform,
      title: currentProject?.name || '未命名项目',
      episodes: Number((currentProject?.metadata as any)?.episodes || 30)
    });
    if (res.success) setChecklist(res.data?.checklist || []);
  };

  const handleAddMember = async () => {
    if (!projectId || !memberForm.user_id.trim()) return;
    const res = await addProjectMember(projectId, {
      user_id: memberForm.user_id.trim(),
      role: memberForm.role,
      display_name: memberForm.display_name.trim() || undefined
    });
    if (res.success) {
      setTeamMembers(res.data || []);
      setMemberForm({ user_id: '', role: 'member', display_name: '' });
    }
  };

  const handleRemoveMember = async (userId: string) => {
    if (!projectId) return;
    const res = await removeProjectMember(projectId, userId);
    if (res.success) setTeamMembers(res.data || []);
  };

  const handleToggleUserMemory = async (enabled: boolean) => {
    if (!projectId) return;
    const res = await updateMemorySettings({ user_id: userId, project_id: projectId, user_enabled: enabled });
    if (res.success) setMemorySettings(res.data || null);
  };

  const handleToggleProjectMemory = async (enabled: boolean) => {
    if (!projectId) return;
    const res = await updateMemorySettings({ user_id: userId, project_id: projectId, project_enabled: enabled });
    if (res.success) setMemorySettings(res.data || null);
  };

  const handleCreateSnapshot = async () => {
    if (!projectId || !sessionId) return;
    const res = await createMemorySnapshot({
      user_id: userId,
      session_id: sessionId,
      project_id: projectId,
      label: snapshotLabel || undefined
    });
    if (res.success) {
      setSnapshotLabel('');
      setMemorySnapshots([res.data, ...memorySnapshots]);
    }
  };

  const handleRestoreSnapshot = async (snapshotId: string) => {
    if (!sessionId) return;
    const res = await restoreMemorySnapshot(snapshotId, { user_id: userId, session_id: sessionId });
    if (res.success) {
      listMemorySnapshots({ user_id: userId, session_id: sessionId, project_id: projectId || undefined })
        .then((r) => setMemorySnapshots(r.data || []))
        .catch(() => setMemorySnapshots([]));
    }
  };

  const statusLabel = useMemo(() => {
    if (!currentProject) return '';
    switch (currentProject.status) {
      case 'active':
        return '进行中';
      case 'completed':
        return '已完成';
      case 'archived':
        return '已归档';
      case 'deleted':
        return '已删除';
      default:
        return currentProject.status;
    }
  }, [currentProject]);

  const tabs = useMemo(() => ([
    { id: 'overview', label: '概览', icon: Layers },
    { id: 'assets', label: '资产', icon: Package },
    { id: 'pipeline', label: '管线', icon: Activity },
    { id: 'release', label: '流通', icon: Play },
    { id: 'team', label: '协作', icon: Users },
    { id: 'memory', label: '记忆', icon: Database }
  ]), []);

  const selectedRun = useMemo(() => {
    if (!pipelineRuns.length) return null;
    if (!selectedRunId) return pipelineRuns[0];
    return pipelineRuns.find((run) => run.id === selectedRunId) || pipelineRuns[0];
  }, [pipelineRuns, selectedRunId]);

  const ragSourceStats = useMemo(() => {
    const stats: Record<string, { label: string; count: number }> = {};
    if (!selectedRun?.steps) return stats;
    selectedRun.steps.forEach((step: any) => {
      (step.rag_trace || []).forEach((item: any) => {
        const source = item.source || 'unknown';
        const collection = item.collection ? `/${item.collection}` : '';
        const key = `${source}${collection}`;
        if (!stats[key]) {
          stats[key] = { label: key, count: 0 };
        }
        stats[key].count += 1;
      });
    });
    return stats;
  }, [selectedRun]);

  const filteredRagTrace = useMemo(() => {
    if (!selectedRun?.steps) return [];
    const trace: any[] = [];
    selectedRun.steps.forEach((step: any) => {
      (step.rag_trace || []).forEach((item: any) => {
        const source = item.source || 'unknown';
        const collection = item.collection ? `/${item.collection}` : '';
        const key = `${source}${collection}`;
        if (ragSourceFilter === 'all' || ragSourceFilter === key) {
          trace.push({ ...item, step_name: step.name, step_id: step.id });
        }
      });
    });
    return trace;
  }, [selectedRun, ragSourceFilter]);

  const statusClass = useMemo(() => {
    if (!currentProject) return 'bg-gray-100 text-gray-700';
    switch (currentProject.status) {
      case 'active':
        return 'bg-green-100 text-green-700';
      case 'completed':
        return 'bg-blue-100 text-blue-700';
      case 'archived':
        return 'bg-gray-100 text-gray-700';
      case 'deleted':
        return 'bg-red-100 text-red-700';
      default:
        return 'bg-gray-100 text-gray-700';
    }
  }, [currentProject]);

  const phaseStats = useMemo(() => {
    const phases = [
      { key: 'planning', label: '策划', color: 'bg-blue-500' },
      { key: 'creation', label: '创作', color: 'bg-emerald-500' },
      { key: 'evaluation', label: '评估', color: 'bg-orange-500' },
      { key: 'analysis', label: '分析', color: 'bg-purple-500' },
      { key: 'workflow', label: '工作流', color: 'bg-slate-500' },
      { key: 'character', label: '人物', color: 'bg-pink-500' },
      { key: 'story', label: '情节', color: 'bg-indigo-500' },
      { key: 'utility', label: '工具', color: 'bg-gray-500' },
    ];

    const counts: Record<string, number> = {};
    phases.forEach((phase) => (counts[phase.key] = 0));

    if (projectFiles.length > 0) {
      projectFiles.forEach((file) => {
        const phaseTag = (file.tags || []).find((tag) => tag.startsWith('phase:'));
        if (phaseTag) {
          const key = phaseTag.replace('phase:', '');
          if (counts[key] !== undefined) counts[key] += 1;
        }
      });
    } else if (currentProject?.tags?.length) {
      currentProject.tags
        .filter((tag) => tag.startsWith('phase:'))
        .forEach((tag) => {
          const key = tag.replace('phase:', '');
          if (counts[key] !== undefined) counts[key] += 1;
        });
    }

    const total = Object.values(counts).reduce((acc, val) => acc + val, 0);
    return { phases, counts, total };
  }, [projectFiles, currentProject]);

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
          <div className="border-b border-gray-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-4">
                  <button
                    onClick={() => navigate('/projects')}
                    className="p-2 rounded-lg hover:bg-gray-100"
                  >
                    <ArrowLeft className="w-5 h-5 text-gray-600" />
                  </button>
                  <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                    <FolderOpen className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">项目详情</h1>
                    <p className="text-sm text-gray-500 mt-1">管理当前项目的所有信息</p>
                  </div>
                </div>
                {currentProject && (
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => {
                        setIsEditing((prev) => !prev);
                        if (!isEditing && currentProject) {
                          setEditForm({
                            name: currentProject.name,
                            description: currentProject.description || '',
                            tags: (currentProject.tags || []).join(', '),
                            status: currentProject.status,
                          });
                        }
                      }}
                      className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
                    >
                      <Edit3 className="w-4 h-4" />
                      {isEditing ? '取消编辑' : '编辑项目'}
                    </button>
                    {isEditing && (
                      <button
                        onClick={handleSave}
                        className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
                      >
                        <Save className="w-4 h-4" />
                        保存
                      </button>
                    )}
                    <button
                      onClick={() => setShowDeleteModal(true)}
                      className="flex items-center gap-2 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
                    >
                      <Trash2 className="w-4 h-4" />
                      删除
                    </button>
                  </div>
                )}
              </div>
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto space-y-6">
              <div className="flex flex-wrap gap-2">
                {tabs.map((tab) => {
                  const TabIcon = tab.icon;
                  const isActive = activeTab === tab.id;
                  return (
                    <button
                      key={tab.id}
                      onClick={() => setActiveTab(tab.id as typeof activeTab)}
                      className={`flex items-center gap-2 px-4 py-2 rounded-full border text-sm transition ${
                        isActive
                          ? 'bg-black text-white border-black'
                          : 'bg-white text-gray-600 border-gray-200 hover:bg-gray-50'
                      }`}
                    >
                      <TabIcon className="w-4 h-4" />
                      {tab.label}
                    </button>
                  );
                })}
              </div>

              {error && (
                <div className="p-4 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">
                  {error}
                  <button onClick={clearError} className="ml-2 underline hover:text-red-900">
                    关闭
                  </button>
                </div>
              )}

              {isLoading && !currentProject ? (
                <div className="flex items-center justify-center py-20">
                  <div className="text-center">
                    <div className="w-12 h-12 border-4 border-black border-t-transparent rounded-full animate-spin mx-auto mb-4"></div>
                    <p className="text-gray-500">加载中...</p>
                  </div>
                </div>
              ) : !currentProject ? (
                <div className="text-center py-20 text-gray-500">项目不存在或已删除</div>
              ) : activeTab === 'overview' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <div className="border border-gray-200 rounded-xl p-6">
                      {!isEditing ? (
                        <>
                          <div className="flex items-start justify-between gap-4">
                            <div>
                              <h2 className="text-xl font-semibold text-gray-900">{currentProject.name}</h2>
                              <p className="text-sm text-gray-600 mt-2">
                                {currentProject.description || '暂无描述'}
                              </p>
                            </div>
                            <span className={`px-2 py-1 rounded-full text-xs font-medium ${statusClass}`}>
                              {statusLabel}
                            </span>
                          </div>
                          <div className="flex flex-wrap gap-2 mt-4">
                            {(currentProject.tags || []).map((tag) => (
                              <span key={tag} className="inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-700 rounded text-xs">
                                <Tag className="w-3 h-3" />
                                {tag}
                              </span>
                            ))}
                            {(currentProject.tags || []).length === 0 && (
                              <span className="text-xs text-gray-400">暂无标签</span>
                            )}
                          </div>
                          <div className="flex items-center gap-4 text-xs text-gray-500 mt-4">
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              创建于 {formatDistanceToNow(new Date(currentProject.created_at), { addSuffix: true, locale: zhCN })}
                            </div>
                            <div className="flex items-center gap-1">
                              <Calendar className="w-3 h-3" />
                              更新于 {formatDistanceToNow(new Date(currentProject.updated_at), { addSuffix: true, locale: zhCN })}
                            </div>
                            <span>{currentProject.file_count} 个文件</span>
                          </div>
                        </>
                      ) : (
                        <div className="space-y-4">
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">项目名称</label>
                            <input
                              type="text"
                              value={editForm.name}
                              onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                              className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                            />
                          </div>
                          <div>
                            <label className="block text-sm font-medium text-gray-700 mb-2">项目描述</label>
                            <textarea
                              value={editForm.description}
                              onChange={(e) => setEditForm({ ...editForm, description: e.target.value })}
                              rows={4}
                              className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                            />
                          </div>
                          <div className="grid grid-cols-2 gap-3">
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">状态</label>
                              <select
                                value={editForm.status}
                                onChange={(e) => setEditForm({ ...editForm, status: e.target.value as ProjectStatus })}
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                              >
                                <option value="active">进行中</option>
                                <option value="completed">已完成</option>
                                <option value="archived">已归档</option>
                                <option value="deleted">已删除</option>
                              </select>
                            </div>
                            <div>
                              <label className="block text-sm font-medium text-gray-700 mb-2">标签</label>
                              <input
                                type="text"
                                value={editForm.tags}
                                onChange={(e) => setEditForm({ ...editForm, tags: e.target.value })}
                                className="w-full px-3 py-2 border border-gray-200 rounded-lg"
                                placeholder="用逗号分隔"
                              />
                            </div>
                          </div>
                        </div>
                      )}
                    </div>

                    {phaseStats.total > 0 && (
                      <div className="border border-gray-200 rounded-xl p-6">
                        <div className="flex items-center justify-between mb-4">
                          <h3 className="font-semibold text-gray-900">阶段分布</h3>
                          <span className="text-xs text-gray-500">基于项目文件标签</span>
                        </div>
                        <div className="w-full h-3 rounded-full bg-gray-100 overflow-hidden mb-4">
                          <div className="flex h-full">
                            {phaseStats.phases.map((phase) => {
                              const count = phaseStats.counts[phase.key] || 0;
                              if (count === 0) return null;
                              const width = Math.max(2, Math.round((count / phaseStats.total) * 100));
                              return (
                                <div
                                  key={phase.key}
                                  className={phase.color}
                                  style={{ width: `${width}%` }}
                                />
                              );
                            })}
                          </div>
                        </div>
                        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs text-gray-600">
                          {phaseStats.phases.map((phase) => (
                            <div key={phase.key} className="flex items-center gap-2">
                              <span className={`w-2.5 h-2.5 rounded-full ${phase.color}`} />
                              <span>{phase.label}</span>
                              <span className="text-gray-500">{phaseStats.counts[phase.key] || 0}</span>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="border border-gray-200 rounded-xl p-6">
                      <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-2">
                          <FileText className="w-5 h-5 text-gray-600" />
                          <h3 className="font-semibold text-gray-900">项目文件</h3>
                        </div>
                        <button
                          onClick={() => navigate(`/files?project_id=${currentProject.id}`)}
                          className="text-sm text-blue-600 hover:text-blue-700 flex items-center gap-1"
                        >
                          查看全部
                          <ExternalLink className="w-3 h-3" />
                        </button>
                      </div>
                      {projectFiles.length === 0 ? (
                        <div className="text-sm text-gray-500">暂无文件</div>
                      ) : (
                        <div className="divide-y divide-gray-100">
                          {projectFiles.slice(0, 8).map((file) => (
                            <div key={file.id} className="py-3 flex items-center justify-between text-sm">
                              <div>
                                <div className="font-medium text-gray-900">{file.filename}</div>
                                <div className="text-xs text-gray-500">
                                  {file.file_type} · {file.file_size ? `${Math.round(file.file_size / 1024)} KB` : '-'}
                                </div>
                              </div>
                              <div className="text-xs text-gray-500">
                                {formatDistanceToNow(new Date(file.updated_at), { addSuffix: true, locale: zhCN })}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="border border-gray-200 rounded-xl p-4 space-y-3">
                      <h4 className="font-semibold text-gray-900">快捷入口</h4>
                      <button
                        onClick={() => {
                          localStorage.setItem('projectId', currentProject.id);
                          navigate(`/workspace?project_id=${currentProject.id}`);
                        }}
                        className="w-full px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
                      >
                        进入工作区
                      </button>
                      <button
                        onClick={() => navigate(`/files?project_id=${currentProject.id}`)}
                        className="w-full px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
                      >
                        管理项目文件
                      </button>
                    </div>
                  </div>
                </div>
              ) : activeTab === 'assets' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900">资产库</h3>
                        <span className="text-xs text-gray-500">项目内素材集中管理</span>
                      </div>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                        <input
                          type="text"
                          value={assetForm.name}
                          onChange={(e) => setAssetForm({ ...assetForm, name: e.target.value })}
                          placeholder="资产名称"
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        />
                        <input
                          type="text"
                          value={assetForm.collection}
                          onChange={(e) => setAssetForm({ ...assetForm, collection: e.target.value })}
                          placeholder="集合名称"
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        />
                        <input
                          type="text"
                          value={assetForm.tags}
                          onChange={(e) => setAssetForm({ ...assetForm, tags: e.target.value })}
                          placeholder="标签(逗号分隔)"
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        />
                        <select
                          value={assetForm.asset_type}
                          onChange={(e) => setAssetForm({ ...assetForm, asset_type: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        >
                          <option value="generic">通用资产</option>
                          <option value="character">人物设定</option>
                          <option value="scene">场景设定</option>
                          <option value="prop">道具/素材</option>
                          <option value="note">Notes导入</option>
                        </select>
                      </div>
                      <button
                        onClick={handleCreateAsset}
                        className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm"
                      >
                        添加资产
                      </button>
                    </div>

                    <div className="border border-gray-200 rounded-xl p-6">
                      <h3 className="font-semibold text-gray-900 mb-4">资产列表</h3>
                      {assets.length === 0 ? (
                        <div className="text-sm text-gray-500">暂无资产</div>
                      ) : (
                        <div className="divide-y divide-gray-100">
                          {assets.map((asset) => (
                            <div key={asset.id} className="py-3 flex items-start justify-between gap-4">
                              <div>
                                <div className="text-sm font-medium text-gray-900">{asset.name}</div>
                                <div className="text-xs text-gray-500">
                                  {asset.asset_type} · {asset.collection || 'default'}
                                </div>
                                <div className="flex flex-wrap gap-2 mt-2">
                                  {(asset.tags || []).map((tag: string) => (
                                    <span key={tag} className="text-xs text-gray-600 bg-gray-100 px-2 py-1 rounded">
                                      {tag}
                                    </span>
                                  ))}
                                </div>
                              </div>
                              <button
                                onClick={() => handleDeleteAsset(asset.id)}
                                className="text-xs text-red-600 hover:text-red-700"
                              >
                                删除
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="border border-gray-200 rounded-xl p-4">
                      <h4 className="font-semibold text-gray-900 mb-3">资产集合</h4>
                      {Object.keys(assetCollections).length === 0 ? (
                        <div className="text-sm text-gray-500">暂无集合</div>
                      ) : (
                        <div className="space-y-3">
                          {Object.entries(assetCollections).map(([collection, items]: [string, any]) => (
                            <div key={collection} className="text-sm">
                              <div className="font-medium text-gray-900">{collection}</div>
                              <div className="text-xs text-gray-500">{items.length} 条资产</div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : activeTab === 'pipeline' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900">创作管线</h3>
                        <span className="text-xs text-gray-500">一键串联策划-创作-评估</span>
                      </div>
                      <select
                        value={selectedTemplateId}
                        onChange={(e) => setSelectedTemplateId(e.target.value)}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      >
                        {pipelineTemplates.map((tpl) => (
                          <option key={tpl.id} value={tpl.id}>
                            {tpl.name}
                          </option>
                        ))}
                      </select>
                      <textarea
                        value={pipelineInput}
                        onChange={(e) => setPipelineInput(e.target.value)}
                        rows={4}
                        placeholder="输入用户需求或创作目标"
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      />
                      <button
                        onClick={handleRunPipeline}
                        className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm"
                      >
                        启动管线
                      </button>
                    </div>

                    <div className="border border-gray-200 rounded-xl p-6">
                      <div className="flex items-center justify-between mb-4">
                        <h3 className="font-semibold text-gray-900">运行记录</h3>
                        <select
                          value={selectedRun?.id || ''}
                          onChange={(e) => setSelectedRunId(e.target.value)}
                          className="px-3 py-2 border border-gray-200 rounded-lg text-xs"
                        >
                          {pipelineRuns.map((run) => (
                            <option key={run.id} value={run.id}>
                              {run.name || run.id}
                            </option>
                          ))}
                        </select>
                      </div>
                      {!selectedRun ? (
                        <div className="text-sm text-gray-500">暂无运行记录</div>
                      ) : (
                        <div className="space-y-4">
                          {selectedRun.steps?.map((step: any) => (
                            <div key={step.id} className="border border-gray-100 rounded-lg p-4">
                              <div className="flex items-center justify-between">
                                <div className="text-sm font-medium text-gray-900">{step.name}</div>
                                <span className="text-xs text-gray-500">{step.status}</span>
                              </div>
                              <div className="text-xs text-gray-500 mt-2">Agent: {step.agent_id}</div>
                              <div className="text-xs text-gray-600 mt-2 whitespace-pre-wrap">
                                {step.output || '暂无输出'}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="border border-gray-200 rounded-xl p-4">
                      <h4 className="font-semibold text-gray-900 mb-3">RAG 引用链</h4>
                      <div className="flex flex-wrap gap-2 mb-3">
                        <button
                          onClick={() => setRagSourceFilter('all')}
                          className={`px-2 py-1 rounded-full text-xs border ${
                            ragSourceFilter === 'all'
                              ? 'bg-black text-white border-black'
                              : 'bg-white text-gray-600 border-gray-200'
                          }`}
                        >
                          全部
                        </button>
                        {Object.values(ragSourceStats).map((item) => (
                          <button
                            key={item.label}
                            onClick={() => setRagSourceFilter(item.label)}
                            className={`px-2 py-1 rounded-full text-xs border ${
                              ragSourceFilter === item.label
                                ? 'bg-black text-white border-black'
                                : 'bg-white text-gray-600 border-gray-200'
                            }`}
                          >
                            {item.label} · {item.count}
                          </button>
                        ))}
                      </div>
                      {filteredRagTrace.length === 0 ? (
                        <div className="text-sm text-gray-500">暂无引用</div>
                      ) : (
                        <div className="space-y-2 max-h-96 overflow-y-auto">
                          {filteredRagTrace.map((item, idx) => (
                            <div key={`${item.timestamp}-${idx}`} className="border border-gray-100 rounded-lg p-3 text-xs">
                              <div className="font-medium text-gray-900">{item.step_name || '步骤'}</div>
                              <div className="text-gray-500 mt-1">来源: {item.source}</div>
                              {item.collection && (
                                <div className="text-gray-500">集合: {item.collection}</div>
                              )}
                              <div className="text-gray-600 mt-1">查询: {item.query}</div>
                              <div className="text-gray-500 mt-1">命中: {item.result_count}</div>
                              {item.error && <div className="text-red-500 mt-1">{item.error}</div>}
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : activeTab === 'release' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <div className="flex items-center justify-between">
                        <h3 className="font-semibold text-gray-900">平台规范</h3>
                        <select
                          value={releasePlatform}
                          onChange={(e) => setReleasePlatform(e.target.value)}
                          className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        >
                          {Object.entries(releaseTemplates).map(([key, value]) => (
                            <option key={key} value={key}>
                              {(value as any).name || key}
                            </option>
                          ))}
                        </select>
                      </div>
                      {releaseTemplates[releasePlatform] && (
                        <div className="text-sm text-gray-600 space-y-1">
                          <div>集数建议: {releaseTemplates[releasePlatform].episodes}</div>
                          <div>单集时长: {releaseTemplates[releasePlatform].episode_length_sec}s</div>
                          <div>强钩子窗口: {releaseTemplates[releasePlatform].hook_window_sec}s</div>
                          <div>标签: {(releaseTemplates[releasePlatform].tags || []).join(' / ')}</div>
                          <div className="text-gray-500">{releaseTemplates[releasePlatform].description}</div>
                        </div>
                      )}
                      <button
                        onClick={handleChecklist}
                        className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm"
                      >
                        生成投放检查清单
                      </button>
                      {checklist.length > 0 && (
                        <ul className="text-sm text-gray-700 space-y-2">
                          {checklist.map((item, idx) => (
                            <li key={idx} className="border border-gray-100 rounded-lg p-2">
                              {item}
                            </li>
                          ))}
                        </ul>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="border border-gray-200 rounded-xl p-4 space-y-3">
                      <h4 className="font-semibold text-gray-900">ROI 预估</h4>
                      <input
                        type="number"
                        value={roiForm.views}
                        onChange={(e) => setRoiForm({ ...roiForm, views: Number(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        placeholder="曝光量"
                      />
                      <input
                        type="number"
                        step="0.01"
                        value={roiForm.ctr}
                        onChange={(e) => setRoiForm({ ...roiForm, ctr: Number(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        placeholder="点击率"
                      />
                      <input
                        type="number"
                        step="0.01"
                        value={roiForm.cvr}
                        onChange={(e) => setRoiForm({ ...roiForm, cvr: Number(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        placeholder="转化率"
                      />
                      <input
                        type="number"
                        step="0.1"
                        value={roiForm.arpu}
                        onChange={(e) => setRoiForm({ ...roiForm, arpu: Number(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        placeholder="ARPU"
                      />
                      <input
                        type="number"
                        step="0.1"
                        value={roiForm.cost}
                        onChange={(e) => setRoiForm({ ...roiForm, cost: Number(e.target.value) })}
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        placeholder="投放成本"
                      />
                      <button
                        onClick={handleCalculateRoi}
                        className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm"
                      >
                        计算 ROI
                      </button>
                      {roiResult && (
                        <div className="text-sm text-gray-700 space-y-1">
                          <div>点击: {roiResult.clicks}</div>
                          <div>转化: {roiResult.conversions}</div>
                          <div>收入: {roiResult.revenue}</div>
                          <div>ROI: {roiResult.roi}</div>
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              ) : activeTab === 'team' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <h3 className="font-semibold text-gray-900">团队成员</h3>
                      <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                        <input
                          type="text"
                          value={memberForm.user_id}
                          onChange={(e) => setMemberForm({ ...memberForm, user_id: e.target.value })}
                          placeholder="用户ID"
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        />
                        <input
                          type="text"
                          value={memberForm.display_name}
                          onChange={(e) => setMemberForm({ ...memberForm, display_name: e.target.value })}
                          placeholder="显示名"
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        />
                        <select
                          value={memberForm.role}
                          onChange={(e) => setMemberForm({ ...memberForm, role: e.target.value })}
                          className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        >
                          <option value="owner">Owner</option>
                          <option value="editor">Editor</option>
                          <option value="member">Member</option>
                          <option value="viewer">Viewer</option>
                        </select>
                      </div>
                      <button
                        onClick={handleAddMember}
                        className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm"
                      >
                        添加成员
                      </button>
                    </div>

                    <div className="border border-gray-200 rounded-xl p-6">
                      {teamMembers.length === 0 ? (
                        <div className="text-sm text-gray-500">暂无成员</div>
                      ) : (
                        <div className="divide-y divide-gray-100">
                          {teamMembers.map((member) => (
                            <div key={member.user_id} className="py-3 flex items-center justify-between text-sm">
                              <div>
                                <div className="font-medium text-gray-900">
                                  {member.display_name || member.user_id}
                                </div>
                                <div className="text-xs text-gray-500">{member.role}</div>
                              </div>
                              <button
                                onClick={() => handleRemoveMember(member.user_id)}
                                className="text-xs text-red-600 hover:text-red-700"
                              >
                                移除
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="border border-gray-200 rounded-xl p-4">
                      <h4 className="font-semibold text-gray-900 mb-2">协作说明</h4>
                      <p className="text-xs text-gray-600">
                        使用成员角色控制协作权限，Owner/Editor 负责内容生产，Viewer 只读查看。
                      </p>
                    </div>
                  </div>
                </div>
              ) : activeTab === 'memory' ? (
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                  <div className="lg:col-span-2 space-y-6">
                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <h3 className="font-semibold text-gray-900">记忆开关</h3>
                      <div className="flex items-center justify-between text-sm">
                        <span>用户维度记忆</span>
                        <button
                          onClick={() => handleToggleUserMemory(!memorySettings?.user_enabled)}
                          className={`px-3 py-1 rounded-full text-xs border ${
                            memorySettings?.user_enabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                          }`}
                        >
                          {memorySettings?.user_enabled ? '已开启' : '已关闭'}
                        </button>
                      </div>
                      <div className="flex items-center justify-between text-sm">
                        <span>项目维度记忆</span>
                        <button
                          onClick={() => handleToggleProjectMemory(!memorySettings?.project_enabled)}
                          className={`px-3 py-1 rounded-full text-xs border ${
                            memorySettings?.project_enabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                          }`}
                        >
                          {memorySettings?.project_enabled ? '已开启' : '已关闭'}
                        </button>
                      </div>
                      <div className="text-xs text-gray-500">
                        当前生效: {memorySettings?.effective_enabled ? '开启' : '关闭'}
                      </div>
                    </div>

                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <h3 className="font-semibold text-gray-900">记忆质量</h3>
                      <input
                        type="text"
                        value={memoryQuery}
                        onChange={(e) => setMemoryQuery(e.target.value)}
                        placeholder="用于评估的查询关键词（可选）"
                        className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                      />
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="border border-gray-100 rounded-lg p-3">
                          <div className="text-xs text-gray-500">命中率</div>
                          <div className="text-lg font-semibold text-gray-900">{memoryQuality?.hit_rate ?? 0}</div>
                        </div>
                        <div className="border border-gray-100 rounded-lg p-3">
                          <div className="text-xs text-gray-500">冲突率</div>
                          <div className="text-lg font-semibold text-gray-900">{memoryQuality?.conflict_rate ?? 0}</div>
                        </div>
                        <div className="border border-gray-100 rounded-lg p-3">
                          <div className="text-xs text-gray-500">记忆条数</div>
                          <div className="text-lg font-semibold text-gray-900">{memoryQuality?.memory_count ?? 0}</div>
                        </div>
                        <div className="border border-gray-100 rounded-lg p-3">
                          <div className="text-xs text-gray-500">冲突键</div>
                          <div className="text-sm text-gray-700">
                            {(memoryQuality?.conflict_keys || []).length ? (memoryQuality?.conflict_keys || []).join(',') : '无'}
                          </div>
                        </div>
                      </div>
                      <div className="grid grid-cols-2 gap-4 text-sm">
                        <div className="border border-gray-100 rounded-lg p-3">
                          <div className="text-xs text-gray-500">短期记忆</div>
                          <div className="text-lg font-semibold text-gray-900">{memoryMetrics?.short_term?.message_count ?? 0}</div>
                        </div>
                        <div className="border border-gray-100 rounded-lg p-3">
                          <div className="text-xs text-gray-500">中期记忆</div>
                          <div className="text-lg font-semibold text-gray-900">{memoryMetrics?.middle_term?.memory_count ?? 0}</div>
                        </div>
                      </div>
                    </div>

                    <div className="border border-gray-200 rounded-xl p-6 space-y-4">
                      <h3 className="font-semibold text-gray-900">记忆快照</h3>
                      <div className="flex gap-2">
                        <input
                          type="text"
                          value={snapshotLabel}
                          onChange={(e) => setSnapshotLabel(e.target.value)}
                          placeholder="快照标签（可选）"
                          className="flex-1 px-3 py-2 border border-gray-200 rounded-lg text-sm"
                        />
                        <button
                          onClick={handleCreateSnapshot}
                          className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 text-sm"
                        >
                          创建快照
                        </button>
                      </div>
                      {memorySnapshots.length === 0 ? (
                        <div className="text-sm text-gray-500">暂无快照</div>
                      ) : (
                        <div className="divide-y divide-gray-100">
                          {memorySnapshots.map((snapshot) => (
                            <div key={snapshot.id} className="py-3 flex items-start justify-between gap-4 text-sm">
                              <div>
                                <div className="font-medium text-gray-900">{snapshot.label || snapshot.id}</div>
                                <div className="text-xs text-gray-500">{snapshot.created_at}</div>
                              </div>
                              <button
                                onClick={() => handleRestoreSnapshot(snapshot.id)}
                                className="text-xs text-blue-600 hover:text-blue-700"
                              >
                                回滚
                              </button>
                            </div>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-4">
                    <div className="border border-gray-200 rounded-xl p-4">
                      <h4 className="font-semibold text-gray-900 mb-2">记忆说明</h4>
                      <p className="text-xs text-gray-600">
                        快照用于保存当前会话的中期记忆状态，回滚只影响记忆，不会删除聊天记录。
                      </p>
                    </div>
                  </div>
                </div>
              ) : null}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />

      {showDeleteModal && currentProject && (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4">
          <div className="bg-white rounded-2xl shadow-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold text-gray-900 mb-2">删除项目</h2>
            <p className="text-gray-600 mb-6">
              确定要删除项目 "{currentProject.name}" 吗？此操作无法撤销。
            </p>
            <div className="flex gap-3">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="flex-1 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                取消
              </button>
              <button
                onClick={handleDelete}
                className="flex-1 px-4 py-2 bg-red-600 text-white rounded-lg hover:bg-red-700"
              >
                删除
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

/**
 * 图谱审核中心页面
 */

import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import { useGraphStore } from '@/store/graphStore';
import { useUIStore } from '@/store/uiStore';
import { ClipboardCheck, ChevronLeft, ChevronRight, AlertTriangle, CheckCircle2, Sparkles } from 'lucide-react';
import { graphService } from '@/services/graphService';

const PAGE_SIZE = 20;

type ReviewStatus = 'pending' | 'approved' | 'rejected' | 'all';

type ReviewSelection = {
  nodes: number[];
  plot_nodes: number[];
  relationships: number[];
};

export default function GraphReviewCenterPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const navigate = useNavigate();
  const {
    currentStoryId,
    setCurrentStoryId,
    loadStories,
    stories,
    listReviewQueueEntries,
    getReviewQueueEntry,
    submitGraphReview,
    updateReviewQueueStatus,
  } = useGraphStore();

  const [statusFilter, setStatusFilter] = useState<ReviewStatus>('pending');
  const [queueItems, setQueueItems] = useState<any[]>([]);
  const [queueTotal, setQueueTotal] = useState(0);
  const [queueOffset, setQueueOffset] = useState(0);
  const [queueLoading, setQueueLoading] = useState(false);
  const [refreshTick, setRefreshTick] = useState(0);
  const [selectedReview, setSelectedReview] = useState<any | null>(null);
  const [selection, setSelection] = useState<ReviewSelection>({
    nodes: [],
    plot_nodes: [],
    relationships: [],
  });
  const [dependencyNotice, setDependencyNotice] = useState('');
  const [graphValidateResult, setGraphValidateResult] = useState<any | null>(null);
  const [characterConsistencyResult, setCharacterConsistencyResult] = useState<any | null>(null);
  const [projectId, setProjectId] = useState(localStorage.getItem('projectId') || '');
  const [enableLlmCheck, setEnableLlmCheck] = useState(true);
  const [validationLoading, setValidationLoading] = useState(false);

  useEffect(() => {
    loadStories();
  }, []);

  useEffect(() => {
    if (!currentStoryId && stories.length > 0) {
      setCurrentStoryId(stories[0].story_id);
    }
  }, [stories]);

  useEffect(() => {
    const loadQueue = async () => {
      if (!currentStoryId) return;
      setQueueLoading(true);
      try {
        const response = await listReviewQueueEntries({
          story_id: currentStoryId,
          status: statusFilter === 'all' ? undefined : statusFilter,
          limit: PAGE_SIZE,
          offset: queueOffset,
        });
        setQueueItems(response?.items || []);
        setQueueTotal(response?.total || 0);
      } finally {
        setQueueLoading(false);
      }
    };
    loadQueue();
  }, [currentStoryId, statusFilter, queueOffset, refreshTick]);

  const toggleSelection = (key: keyof ReviewSelection, index: number) => {
    setSelection((prev) => {
      const set = new Set(prev[key]);
      if (set.has(index)) {
        set.delete(index);
      } else {
        set.add(index);
      }
      return { ...prev, [key]: Array.from(set) };
    });
  };

  const normalizeRelationshipPayload = (rel: any) => ({
    ...rel,
    source: rel.source_name || rel.source,
    target: rel.target_name || rel.target,
    source_id: rel.source_id || (rel.source_name ? rel.source : undefined),
    target_id: rel.target_id || (rel.target_name ? rel.target : undefined),
  });

  const ensureRelationshipDependencies = (selectedNodes: any[], relsPayload: any[], allNodes: any[]) => {
    const nodeByName = new Map<string, any>();
    allNodes.forEach((node) => {
      const key = (node.name || '').trim().toLowerCase();
      if (key) nodeByName.set(key, node);
    });
    const selectedNames = new Set(
      selectedNodes.map((node) => (node.name || '').trim().toLowerCase()).filter(Boolean)
    );
    const added: any[] = [];
    relsPayload.forEach((rel) => {
      if (rel.source_id && rel.target_id) return;
      const srcName = (rel.source_name || rel.source || '').trim().toLowerCase();
      const tgtName = (rel.target_name || rel.target || '').trim().toLowerCase();
      if (srcName && !selectedNames.has(srcName) && nodeByName.has(srcName)) {
        const node = nodeByName.get(srcName);
        added.push(node);
        selectedNames.add(srcName);
      }
      if (tgtName && !selectedNames.has(tgtName) && nodeByName.has(tgtName)) {
        const node = nodeByName.get(tgtName);
        added.push(node);
        selectedNames.add(tgtName);
      }
    });
    return added;
  };

  const openReview = async (item: any) => {
    let detail = item;
    if (!item?.payload) {
      detail = await getReviewQueueEntry(item.review_id);
    }
    setSelectedReview(detail);
    const payload = detail?.payload || {};
    setSelection({
      nodes: (payload.nodes || []).map((_: any, idx: number) => idx),
      plot_nodes: (payload.plot_nodes || []).map((_: any, idx: number) => idx),
      relationships: (payload.relationships || []).map((_: any, idx: number) => idx),
    });
    setDependencyNotice('');
  };

  const handleApprove = async () => {
    if (!currentStoryId || !selectedReview?.payload) return;
    const payload = selectedReview.payload || {};
    const selectedNodes = selection.nodes.map((idx) => payload.nodes?.[idx]).filter(Boolean) || [];
    const selectedPlots = selection.plot_nodes.map((idx) => payload.plot_nodes?.[idx]).filter(Boolean) || [];
    const selectedRels = selection.relationships
      .map((idx) => payload.relationships?.[idx])
      .filter(Boolean)
      .map(normalizeRelationshipPayload);

    const allCandidateNodes = payload.nodes || [];
    const missingDeps = ensureRelationshipDependencies(selectedNodes, selectedRels, allCandidateNodes);
    if (missingDeps.length > 0) {
      setDependencyNotice(`已自动补齐 ${missingDeps.length} 个关系依赖节点`);
      missingDeps.forEach((node) => selectedNodes.push(node));
    }

    await submitGraphReview({
      story_id: currentStoryId,
      nodes: selectedNodes,
      plot_nodes: selectedPlots,
      relationships: selectedRels,
      review_id: selectedReview.review_id,
    });
    setSelectedReview(null);
    setQueueOffset(0);
    setRefreshTick((prev) => prev + 1);
  };

  const handleReject = async () => {
    if (!selectedReview?.review_id) return;
    await updateReviewQueueStatus({ review_id: selectedReview.review_id, status: 'rejected' });
    setSelectedReview(null);
    setQueueOffset(0);
    setRefreshTick((prev) => prev + 1);
  };

  const totalPages = Math.max(1, Math.ceil(queueTotal / PAGE_SIZE));
  const currentPage = Math.floor(queueOffset / PAGE_SIZE) + 1;

  const handleGraphValidate = async () => {
    if (!currentStoryId) return;
    setValidationLoading(true);
    try {
      const res = await graphService.validateGraph(currentStoryId);
      setGraphValidateResult(res.data || null);
    } finally {
      setValidationLoading(false);
    }
  };

  const handleCharacterConsistency = async () => {
    if (!projectId) return;
    setValidationLoading(true);
    try {
      const res = await graphService.checkCharacterConsistency({
        project_id: projectId,
        llm_check: enableLlmCheck,
      } as any);
      setCharacterConsistencyResult(res.data || null);
    } finally {
      setValidationLoading(false);
    }
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
          <div className="border-b border-gray-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-emerald-500 to-teal-600 rounded-xl flex items-center justify-center">
                    <ClipboardCheck className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">审核中心</h1>
                    <p className="text-sm text-gray-500 mt-1">统一处理抽取队列中的低置信度条目</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleGraphValidate}
                    disabled={!currentStoryId || validationLoading}
                    className="px-4 py-2 border border-gray-200 rounded-lg text-sm hover:bg-gray-50 disabled:opacity-50"
                  >
                    图谱自动校验
                  </button>
                  <button
                    onClick={handleCharacterConsistency}
                    disabled={!projectId || validationLoading}
                    className="px-4 py-2 bg-black text-white rounded-lg text-sm hover:bg-gray-800 disabled:opacity-50"
                  >
                    人物一致性检测
                  </button>
                </div>
              </div>

              <div className="flex flex-wrap items-center gap-3">
                <select
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  value={currentStoryId || ''}
                  onChange={(e) => {
                    setCurrentStoryId(e.target.value);
                    setQueueOffset(0);
                    setSelectedReview(null);
                  }}
                >
                  <option value="" disabled>
                    选择故事
                  </option>
                  {stories.map((story: any) => (
                    <option key={story.story_id} value={story.story_id}>
                      {story.name}
                    </option>
                  ))}
                </select>

                <div className="flex items-center gap-2">
                  {(['pending', 'approved', 'rejected', 'all'] as ReviewStatus[]).map((status) => (
                    <button
                      key={status}
                      className={`px-3 py-1.5 text-xs rounded-full border ${
                        statusFilter === status
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-white text-gray-500 border-gray-200'
                      }`}
                      onClick={() => {
                        setStatusFilter(status);
                        setQueueOffset(0);
                        setSelectedReview(null);
                      }}
                    >
                      {status === 'pending'
                        ? '待审'
                        : status === 'approved'
                        ? '已审'
                        : status === 'rejected'
                        ? '已拒绝'
                        : '全部'}
                    </button>
                  ))}
                </div>

                <div className="ml-auto flex items-center gap-2 text-xs text-gray-500">
                  <span>
                    共 {queueTotal} 条 · 第 {currentPage} / {totalPages} 页
                  </span>
                  <button
                    className="p-1 border border-gray-200 rounded"
                    onClick={() => setQueueOffset(Math.max(0, queueOffset - PAGE_SIZE))}
                    disabled={queueOffset === 0}
                  >
                    <ChevronLeft className="w-4 h-4" />
                  </button>
                  <button
                    className="p-1 border border-gray-200 rounded"
                    onClick={() => setQueueOffset(Math.min(queueOffset + PAGE_SIZE, (totalPages - 1) * PAGE_SIZE))}
                    disabled={queueOffset + PAGE_SIZE >= queueTotal}
                  >
                    <ChevronRight className="w-4 h-4" />
                  </button>
                </div>
              </div>

              <div className="mt-4 grid grid-cols-1 md:grid-cols-3 gap-3">
                <input
                  type="text"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  placeholder="项目ID（人物一致性检测）"
                  className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
                <label className="flex items-center gap-2 text-sm text-gray-600">
                  <input
                    type="checkbox"
                    checked={enableLlmCheck}
                    onChange={(e) => setEnableLlmCheck(e.target.checked)}
                  />
                  启用动机一致性（LLM）
                </label>
                <div className="text-xs text-gray-500 flex items-center">
                  {validationLoading ? '检测中...' : '准备就绪'}
                </div>
              </div>
            </div>
          </div>

          <div className="flex flex-1 overflow-hidden">
            <div className="w-1/3 border-r border-gray-200 overflow-y-auto">
              {queueLoading && (
                <div className="p-4 text-sm text-gray-500">加载中...</div>
              )}
              {!queueLoading && !currentStoryId && (
                <div className="p-4 text-sm text-gray-500">请先选择故事</div>
              )}
              {!queueLoading && queueItems.length === 0 && (
                <div className="p-4 text-sm text-gray-500">暂无审核条目</div>
              )}
              <div className="divide-y divide-gray-200">
                {queueItems.map((item) => (
                  <button
                    key={item.review_id}
                    onClick={() => openReview(item)}
                    className={`w-full text-left px-4 py-3 hover:bg-gray-50 ${
                      selectedReview?.review_id === item.review_id ? 'bg-emerald-50' : ''
                    }`}
                  >
                    <div className="flex items-center justify-between text-sm">
                      <span className="font-medium text-gray-900">
                        {item.review_id?.slice(0, 8)}
                      </span>
                      <span className="text-xs text-gray-500">{item.status}</span>
                    </div>
                    <div className="text-xs text-gray-500 mt-1">
                      节点 {item.nodes_count || 0} · 情节 {item.plot_nodes_count || 0} · 关系 {item.relationships_count || 0}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            <div className="flex-1 overflow-y-auto">
              <div className="p-6 border-b border-gray-200 bg-gray-50">
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="border border-gray-200 rounded-xl p-4 bg-white">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-orange-500" />
                      <span className="text-sm font-semibold text-gray-900">图谱冲突详情</span>
                    </div>
                    {!graphValidateResult ? (
                      <div className="text-xs text-gray-500">暂无校验结果</div>
                    ) : (graphValidateResult.issues || []).length === 0 ? (
                      <div className="text-xs text-emerald-600 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" /> 未发现冲突
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {graphValidateResult.issues.map((issue: any, idx: number) => (
                          <button
                            key={`${issue.message || issue}-${idx}`}
                            className="text-left text-xs text-gray-700 border border-gray-100 rounded-lg p-2 hover:bg-gray-50"
                            onClick={() => {
                              const focus = issue.source_id || issue.target_id || (issue.nodes && issue.nodes[0]);
                              if (currentStoryId) {
                                navigate(`/graph?story_id=${currentStoryId}${focus ? `&focus_node=${focus}` : ''}`);
                              }
                            }}
                          >
                            {issue.message || issue}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>

                  <div className="border border-gray-200 rounded-xl p-4 bg-white">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-4 h-4 text-indigo-500" />
                      <span className="text-sm font-semibold text-gray-900">人物一致性详情</span>
                    </div>
                    {!characterConsistencyResult ? (
                      <div className="text-xs text-gray-500">暂无检测结果</div>
                    ) : (characterConsistencyResult.issues || []).length === 0 ? (
                      <div className="text-xs text-emerald-600 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" /> 未发现明显问题
                      </div>
                    ) : (
                      <div className="space-y-2">
                        {characterConsistencyResult.issues.map((issue: string, idx: number) => (
                          <button
                            key={`${issue}-${idx}`}
                            className="text-left text-xs text-gray-700 border border-gray-100 rounded-lg p-2 hover:bg-gray-50"
                            onClick={() => {
                              if (currentStoryId) {
                                navigate(`/graph?story_id=${currentStoryId}`);
                              }
                            }}
                          >
                            {issue}
                          </button>
                        ))}
                      </div>
                    )}
                    {characterConsistencyResult?.llm_motivation && (
                      <div className="mt-3 border-t border-gray-100 pt-2">
                        <div className="text-xs text-gray-500">动机一致性（LLM）</div>
                        <div className="text-xs text-gray-700 mt-1">
                          {characterConsistencyResult.llm_motivation.summary || '无摘要'}
                        </div>
                        <div className="text-xs text-gray-500 mt-1">
                          评分: {characterConsistencyResult.llm_motivation.score ?? '-'}
                        </div>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {!selectedReview && (
                <div className="p-6 text-sm text-gray-500">请选择左侧审核条目查看详情</div>
              )}
              {selectedReview && (
                <div className="p-6 space-y-4">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="text-lg font-semibold text-gray-900">审核详情</h3>
                      <p className="text-xs text-gray-500 mt-1">审核ID：{selectedReview.review_id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <button
                        className="px-3 py-2 text-sm rounded-lg border border-gray-200 text-gray-600"
                        onClick={handleReject}
                      >
                        拒绝
                      </button>
                      <button
                        className="px-3 py-2 text-sm rounded-lg bg-emerald-600 text-white"
                        onClick={handleApprove}
                      >
                        确认入库
                      </button>
                    </div>
                  </div>

                  {dependencyNotice && (
                    <div className="text-xs text-amber-600">{dependencyNotice}</div>
                  )}

                  <div className="grid grid-cols-3 gap-4">
                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-2">节点</div>
                      <div className="space-y-2">
                        {(selectedReview.payload?.nodes || []).map((item: any, idx: number) => (
                          <label key={`node-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={selection.nodes.includes(idx)}
                              onChange={() => toggleSelection('nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.name}</span> ({item.type})
                              {item.confidence !== undefined ? ` · 置信度 ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {(selectedReview.payload?.nodes || []).length === 0 && (
                          <div className="text-xs text-gray-500">无节点</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-2">情节节点</div>
                      <div className="space-y-2">
                        {(selectedReview.payload?.plot_nodes || []).map((item: any, idx: number) => (
                          <label key={`plot-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={selection.plot_nodes.includes(idx)}
                              onChange={() => toggleSelection('plot_nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.title}</span>
                              {item.confidence !== undefined ? ` · 置信度 ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {(selectedReview.payload?.plot_nodes || []).length === 0 && (
                          <div className="text-xs text-gray-500">无情节节点</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-2">关系</div>
                      <div className="space-y-2">
                        {(selectedReview.payload?.relationships || []).map((item: any, idx: number) => (
                          <label key={`rel-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={selection.relationships.includes(idx)}
                              onChange={() => toggleSelection('relationships', idx)}
                            />
                            <span>
                              <span className="font-medium">
                                {item.source} → {item.target}
                              </span>{' '}
                              ({item.type})
                              {item.confidence !== undefined ? ` · 置信度 ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {(selectedReview.payload?.relationships || []).length === 0 && (
                          <div className="text-xs text-gray-500">无关系</div>
                        )}
                      </div>
                    </div>
                  </div>

                  {(selectedReview.payload?.validation_issues || []).length > 0 && (
                    <div className="text-xs text-amber-600">
                      校验提示：{selectedReview.payload.validation_issues.join('；')}
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
}

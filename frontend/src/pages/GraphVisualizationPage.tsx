/**
 * 图数据库可视化页面
 * Graph Database Visualization Page
 *
 * 提供交互式剧本图谱可视化功能，包括：
 * - 角色、情节、世界观规则的关系网络
 * - 角色网络分析
 * - 图谱统计信息
 * - 节点和关系的搜索与过滤
 */

import { useState, useEffect } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useGraphStore } from '@/store/graphStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import { GraphVisualization } from '@/components/graph';
import { Network, BookOpen, Plus, Search, ChevronDown, Link2, ClipboardCheck, AlertTriangle, CheckCircle2, Sparkles } from 'lucide-react';
import { graphService } from '@/services/graphService';

export default function GraphVisualizationPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const {
    currentStoryId,
    setCurrentStoryId,
    loadStoryElements,
    loadStatistics,
    setFilter,
    createCharacter,
    createPlotNode,
    createWorldRule,
    createStory,
    createGenericNode,
    createRelationship,
    extractGraphFromText,
    extractGraphFromFile,
    submitGraphReview,
    createReviewQueueEntry,
    loadStories,
    loadRelationTypes,
    stories,
    nodes,
    relationTypeOptions,
    setSelectedNodeId,
  } = useGraphStore();

  const [showStorySelector, setShowStorySelector] = useState(true);
  const [selectedStoryName, setSelectedStoryName] = useState('');
  const [quickAddOpen, setQuickAddOpen] = useState(false);
  const [quickAddType, setQuickAddType] = useState<
    'Character' | 'PlotNode' | 'WorldRule' | 'Location' | 'Item' | 'Conflict' | 'Theme' | 'Motivation'
  >('Character');
  const [quickAddForm, setQuickAddForm] = useState({
    name: '',
    description: '',
    ruleType: 'general',
    status: 'alive',
    location: '',
    sequenceNumber: 1,
    tensionScore: 50,
    importance: 50,
    constraints: '',
    examples: '',
    category: '',
  });
  const [storyModalOpen, setStoryModalOpen] = useState(false);
  const [storyForm, setStoryForm] = useState({
    name: '',
    description: '',
    genre: '',
    tags: '',
    status: 'active',
  });
  const [relationshipModalOpen, setRelationshipModalOpen] = useState(false);
  const [relationshipForm, setRelationshipForm] = useState({
    sourceId: '',
    targetId: '',
    relationType: 'INFLUENCES',
    description: '',
  });
  const [extractModalOpen, setExtractModalOpen] = useState(false);
  const [extractForm, setExtractForm] = useState({
    content: '',
    chunkSize: 4000,
    overlap: 200,
  });
  const [extractFile, setExtractFile] = useState<File | null>(null);
  const [fileInputKey, setFileInputKey] = useState(0);
  const [previewModalOpen, setPreviewModalOpen] = useState(false);
  const [previewPayload, setPreviewPayload] = useState({
    high: {
      nodes: [] as any[],
      plot_nodes: [] as any[],
      relationships: [] as any[],
    },
    low: {
      nodes: [] as any[],
      plot_nodes: [] as any[],
      relationships: [] as any[],
    },
    validation_issues: [] as any[],
  });
  const [previewSelection, setPreviewSelection] = useState({
    high: {
      nodes: [] as number[],
      plot_nodes: [] as number[],
      relationships: [] as number[],
    },
    low: {
      nodes: [] as number[],
      plot_nodes: [] as number[],
      relationships: [] as number[],
    },
  });
  const [dependencyNotice, setDependencyNotice] = useState('');
  const [validationLoading, setValidationLoading] = useState(false);
  const [graphValidateResult, setGraphValidateResult] = useState<any | null>(null);
  const [characterConsistencyResult, setCharacterConsistencyResult] = useState<any | null>(null);
  const [projectId, setProjectId] = useState(localStorage.getItem('projectId') || '');
  const [enableLlmCheck, setEnableLlmCheck] = useState(true);

  // 初始化：选择第一个故事
  useEffect(() => {
    loadStories();
    loadRelationTypes();
  }, []);

  useEffect(() => {
    if (!currentStoryId && stories.length > 0) {
      const firstStory = stories[0] as any;
      setCurrentStoryId(firstStory.story_id);
      setSelectedStoryName(firstStory.name);
      loadStoryElements(firstStory.story_id);
      loadStatistics(firstStory.story_id);
    }
  }, [stories]);

  useEffect(() => {
    const storyId = searchParams.get('story_id');
    const focusNode = searchParams.get('focus_node');
    if (storyId) {
      const story = stories.find((s: any) => s.story_id === storyId);
      if (story) {
        setCurrentStoryId(story.story_id);
        setSelectedStoryName(story.name);
        loadStoryElements(story.story_id);
        loadStatistics(story.story_id);
      }
    }
    if (focusNode) {
      setSelectedNodeId(focusNode);
    }
  }, [searchParams, stories]);

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

  const handleStoryChange = (storyId: string, storyName: string) => {
    setCurrentStoryId(storyId);
    setSelectedStoryName(storyName);
    loadStoryElements(storyId);
    loadStatistics(storyId);
    setShowStorySelector(false);
  };

  const resetQuickAddForm = () => {
    setQuickAddForm({
      name: '',
      description: '',
      ruleType: 'general',
      status: 'alive',
      location: '',
      sequenceNumber: 1,
      tensionScore: 50,
      importance: 50,
      constraints: '',
      examples: '',
      category: '',
    });
  };

  const handleQuickAddSubmit = async () => {
    if (!currentStoryId || !quickAddForm.name.trim()) return;

    if (quickAddType === 'Character') {
      await createCharacter({
        story_id: currentStoryId,
        name: quickAddForm.name.trim(),
        status: quickAddForm.status as any,
        location: quickAddForm.location || null,
        persona: [],
        arc: 0,
        backstory: null,
        motivations: [],
        flaws: [],
        strengths: [],
      });
    } else if (quickAddType === 'PlotNode') {
      await createPlotNode({
        story_id: currentStoryId,
        title: quickAddForm.name.trim(),
        description: quickAddForm.description.trim(),
        sequence_number: Number(quickAddForm.sequenceNumber) || 1,
        tension_score: Number(quickAddForm.tensionScore) || 50,
        chapter: null,
        characters_involved: [],
        locations: [],
        conflicts: [],
        themes: [],
        importance: Number(quickAddForm.importance) || 50,
        timestamp: null,
      });
    } else if (quickAddType === 'WorldRule') {
      await createWorldRule({
        story_id: currentStoryId,
        name: quickAddForm.name.trim(),
        description: quickAddForm.description.trim(),
        rule_type: quickAddForm.ruleType.trim() || 'general',
        constraints: quickAddForm.constraints
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
        examples: quickAddForm.examples
          .split(',')
          .map((item) => item.trim())
          .filter(Boolean),
      });
    } else {
      await createGenericNode(quickAddType, {
        name: quickAddForm.name.trim(),
        description: quickAddForm.description.trim(),
        category: quickAddForm.category.trim(),
      });
    }

    await loadStoryElements(currentStoryId);
    await loadStatistics(currentStoryId);
    resetQuickAddForm();
    setQuickAddOpen(false);
  };

  const resetStoryForm = () => {
    setStoryForm({
      name: '',
      description: '',
      genre: '',
      tags: '',
      status: 'active',
    });
  };

  const handleCreateStory = async () => {
    if (!storyForm.name.trim()) return;
    const created = await createStory({
      name: storyForm.name.trim(),
      description: storyForm.description.trim(),
      genre: storyForm.genre.trim() || null,
      tags: storyForm.tags
        .split(',')
        .map((item) => item.trim())
        .filter(Boolean),
      status: storyForm.status,
    });
    await loadStories();
    if (created?.story_id) {
      setCurrentStoryId(created.story_id);
      setSelectedStoryName(created.name || storyForm.name.trim());
      await loadStoryElements(created.story_id);
      await loadStatistics(created.story_id);
    }
    resetStoryForm();
    setStoryModalOpen(false);
  };

  const resetRelationshipForm = () => {
    setRelationshipForm({
      sourceId: '',
      targetId: '',
      relationType: 'INFLUENCES',
      description: '',
    });
  };

  const handleCreateRelationship = async () => {
    if (!currentStoryId || !relationshipForm.sourceId || !relationshipForm.targetId) return;
    if (relationshipForm.sourceId === relationshipForm.targetId) return;
    await createRelationship({
      source_id: relationshipForm.sourceId,
      target_id: relationshipForm.targetId,
      relation_type: relationshipForm.relationType as any,
      properties: relationshipForm.description
        ? { description: relationshipForm.description.trim() }
        : {},
    });
    resetRelationshipForm();
    setRelationshipModalOpen(false);
  };

  const resetExtractForm = () => {
    setExtractForm({
      content: '',
      chunkSize: 4000,
      overlap: 200,
    });
    setExtractFile(null);
    setFileInputKey((prev) => prev + 1);
  };

  const handleExtractPreview = async () => {
    if (!currentStoryId) return;
    if (!extractFile && !extractForm.content.trim()) return;
    let result: any = null;
    if (extractFile) {
      result = await extractGraphFromFile({
        story_id: currentStoryId,
        file: extractFile,
        chunk_size: extractForm.chunkSize,
        overlap: extractForm.overlap,
        dry_run: true,
      });
    } else {
      result = await extractGraphFromText({
        story_id: currentStoryId,
        content: extractForm.content.trim(),
        chunk_size: extractForm.chunkSize,
        overlap: extractForm.overlap,
        dry_run: true,
      });
    }
    const pending = result?.pending_review || {};
    const created = {
      nodes: result?.nodes || [],
      plot_nodes: result?.plot_nodes || [],
      relationships: result?.relationships || [],
    };
    const low = {
      nodes: pending.nodes || [],
      plot_nodes: pending.plot_nodes || [],
      relationships: pending.relationships || [],
    };
    setPreviewPayload({
      high: created,
      low,
      validation_issues: result?.validation_issues || [],
    });
    setPreviewSelection({
      high: {
        nodes: created.nodes.map((_: any, idx: number) => idx),
        plot_nodes: created.plot_nodes.map((_: any, idx: number) => idx),
        relationships: created.relationships.map((_: any, idx: number) => idx),
      },
      low: {
        nodes: low.nodes.map((_: any, idx: number) => idx),
        plot_nodes: low.plot_nodes.map((_: any, idx: number) => idx),
        relationships: low.relationships.map((_: any, idx: number) => idx),
      },
    });
    setDependencyNotice('');
    setPreviewModalOpen(true);
    resetExtractForm();
    setExtractModalOpen(false);
  };

  const togglePreviewSelection = (
    bucket: 'high' | 'low',
    key: 'nodes' | 'plot_nodes' | 'relationships',
    index: number
  ) => {
    setPreviewSelection((prev) => {
      const set = new Set(prev[bucket][key]);
      if (set.has(index)) {
        set.delete(index);
      } else {
        set.add(index);
      }
      return { ...prev, [bucket]: { ...prev[bucket], [key]: Array.from(set) } };
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

  const handleSubmitPreview = async () => {
    if (!currentStoryId) return;
    const selectedHighNodes = previewSelection.high.nodes
      .map((idx) => previewPayload.high.nodes[idx])
      .filter(Boolean);
    const selectedHighPlots = previewSelection.high.plot_nodes
      .map((idx) => previewPayload.high.plot_nodes[idx])
      .filter(Boolean);
    const selectedHighRels = previewSelection.high.relationships
      .map((idx) => previewPayload.high.relationships[idx])
      .filter(Boolean)
      .map(normalizeRelationshipPayload);

    const selectedLowNodes = previewSelection.low.nodes
      .map((idx) => previewPayload.low.nodes[idx])
      .filter(Boolean);
    const selectedLowPlots = previewSelection.low.plot_nodes
      .map((idx) => previewPayload.low.plot_nodes[idx])
      .filter(Boolean);
    const selectedLowRels = previewSelection.low.relationships
      .map((idx) => previewPayload.low.relationships[idx])
      .filter(Boolean)
      .map(normalizeRelationshipPayload);

    const selectedNodes = [...selectedHighNodes, ...selectedLowNodes];
    const selectedPlots = [...selectedHighPlots, ...selectedLowPlots];
    const selectedRels = [...selectedHighRels, ...selectedLowRels];

    const allCandidateNodes = [...previewPayload.high.nodes, ...previewPayload.low.nodes];
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
    });
    setPreviewModalOpen(false);
  };

  const handleSaveToReviewQueue = async () => {
    if (!currentStoryId) return;
    const selectedLowNodes = previewSelection.low.nodes
      .map((idx) => previewPayload.low.nodes[idx])
      .filter(Boolean);
    const selectedLowPlots = previewSelection.low.plot_nodes
      .map((idx) => previewPayload.low.plot_nodes[idx])
      .filter(Boolean);
    const selectedLowRels = previewSelection.low.relationships
      .map((idx) => previewPayload.low.relationships[idx])
      .filter(Boolean);
    if (
      selectedLowNodes.length === 0 &&
      selectedLowPlots.length === 0 &&
      selectedLowRels.length === 0
    ) {
      return;
    }

    await createReviewQueueEntry({
      story_id: currentStoryId,
      payload: {
        nodes: selectedLowNodes,
        plot_nodes: selectedLowPlots,
        relationships: selectedLowRels,
        validation_issues: previewPayload.validation_issues || [],
      },
      source: 'extract:preview',
    });
    setPreviewModalOpen(false);
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
                  <div className="w-12 h-12 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-xl flex items-center justify-center">
                    <Network className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">图谱可视化</h1>
                    <p className="text-sm text-gray-500 mt-1">
                      探索剧本中的人物关系、情节发展和世界观规则
                    </p>
                  </div>
                </div>

                <div className="flex items-center gap-2">
                  {/* 快速添加按钮 */}
                  <button
                    onClick={() => setQuickAddOpen(true)}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    title="快速添加节点"
                  >
                    <Plus className="w-4 h-4 mr-2" />
                    添加
                  </button>
                  <button
                    onClick={() => setRelationshipModalOpen(true)}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    title="创建关系"
                  >
                    <Link2 className="w-4 h-4 mr-2" />
                    关系
                  </button>
                  <button
                    onClick={() => setExtractModalOpen(true)}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    title="自动抽取图谱"
                  >
                    自动抽取
                  </button>
                  <button
                    onClick={() => navigate('/graph/review')}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 transition-colors"
                    title="审核中心"
                  >
                    <ClipboardCheck className="w-4 h-4 mr-2" />
                    审核中心
                  </button>
                  <button
                    onClick={handleGraphValidate}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-lg hover:bg-gray-50 transition-colors"
                    title="图谱自动校验"
                    disabled={!currentStoryId || validationLoading}
                  >
                    图谱校验
                  </button>
                  <button
                    onClick={handleCharacterConsistency}
                    className="inline-flex items-center px-3 py-2 text-sm font-medium text-white bg-black rounded-lg hover:bg-gray-800 transition-colors"
                    title="人物一致性检测"
                    disabled={!projectId || validationLoading}
                  >
                    人物一致性
                  </button>
                </div>
              </div>

              {/* 工具栏 */}
              <div className="flex items-center gap-4">
                {/* 故事选择器 */}
                <div className="relative">
                  <button
                    onClick={() => setShowStorySelector(!showStorySelector)}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <BookOpen className="w-4 h-4 text-gray-600" />
                    <span className="text-sm font-medium text-gray-900">
                      {selectedStoryName || '选择故事'}
                    </span>
                    <ChevronDown
                      className={`w-4 h-4 text-gray-500 transition-transform ${
                        showStorySelector ? 'rotate-180' : ''
                      }`}
                    />
                  </button>

                  {showStorySelector && (
                    <div className="absolute top-full left-0 mt-2 w-64 bg-white border border-gray-200 rounded-lg shadow-lg z-10">
                      <div className="p-2">
                        {stories.length === 0 && (
                          <div className="px-3 py-2 text-sm text-gray-500">暂无故事，请先创建</div>
                        )}
                        {stories.map((story: any) => (
                          <button
                            key={story.story_id}
                            onClick={() => handleStoryChange(story.story_id, story.name)}
                            className={`w-full text-left px-3 py-2 rounded-lg transition-colors ${
                              currentStoryId === story.story_id
                                ? 'bg-indigo-50 text-indigo-700'
                                : 'hover:bg-gray-50 text-gray-700'
                            }`}
                          >
                            <div className="font-medium text-sm">{story.name}</div>
                            <div className="text-xs text-gray-500">{story.description}</div>
                          </button>
                        ))}
                        <button
                          onClick={() => {
                            setShowStorySelector(false);
                            setStoryModalOpen(true);
                          }}
                          className="w-full text-left px-3 py-2 rounded-lg transition-colors hover:bg-gray-50 text-gray-700"
                        >
                          <div className="font-medium text-sm">+ 新建故事</div>
                          <div className="text-xs text-gray-500">创建新的剧本项目</div>
                        </button>
                      </div>
                    </div>
                  )}
                </div>

                {/* 搜索框 */}
                <div className="relative flex-1 max-w-md">
                  <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                  <input
                    type="text"
                    placeholder="搜索节点..."
                    className="w-full pl-10 pr-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-indigo-500 text-sm"
                    onChange={(e) => setFilter({ searchQuery: e.target.value })}
                  />
                </div>
                <input
                  type="text"
                  value={projectId}
                  onChange={(e) => setProjectId(e.target.value)}
                  placeholder="项目ID（人物一致性）"
                  className="px-3 py-2 border border-gray-200 rounded-lg text-sm"
                />
                <label className="flex items-center gap-2 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={enableLlmCheck}
                    onChange={(e) => setEnableLlmCheck(e.target.checked)}
                  />
                  动机一致性（LLM）
                </label>
              </div>

              {(graphValidateResult || characterConsistencyResult) && (
                <div className="mt-4 grid grid-cols-1 lg:grid-cols-2 gap-4">
                  <div className="border border-gray-200 rounded-xl p-3 bg-white">
                    <div className="flex items-center gap-2 mb-2">
                      <AlertTriangle className="w-4 h-4 text-orange-500" />
                      <span className="text-sm font-semibold text-gray-900">图谱冲突</span>
                    </div>
                    {!graphValidateResult ? (
                      <div className="text-xs text-gray-500">暂无校验结果</div>
                    ) : (graphValidateResult.issues || []).length === 0 ? (
                      <div className="text-xs text-emerald-600 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" /> 未发现冲突
                      </div>
                    ) : (
                      <div className="space-y-1">
                        {graphValidateResult.issues.map((issue: any, idx: number) => (
                          <button
                            key={`${issue.message || issue}-${idx}`}
                            className="text-left text-xs text-gray-700 border border-gray-100 rounded-lg p-2 hover:bg-gray-50"
                            onClick={() => {
                              const focus = issue.source_id || issue.target_id || (issue.nodes && issue.nodes[0]);
                              if (focus) {
                                setSelectedNodeId(focus);
                              }
                            }}
                          >
                            {issue.message || issue}
                          </button>
                        ))}
                      </div>
                    )}
                  </div>
                  <div className="border border-gray-200 rounded-xl p-3 bg-white">
                    <div className="flex items-center gap-2 mb-2">
                      <Sparkles className="w-4 h-4 text-indigo-500" />
                      <span className="text-sm font-semibold text-gray-900">人物一致性</span>
                    </div>
                    {!characterConsistencyResult ? (
                      <div className="text-xs text-gray-500">暂无检测结果</div>
                    ) : (characterConsistencyResult.issues || []).length === 0 ? (
                      <div className="text-xs text-emerald-600 flex items-center gap-2">
                        <CheckCircle2 className="w-4 h-4" /> 未发现明显问题
                      </div>
                    ) : (
                      <div className="space-y-1">
                        {characterConsistencyResult.issues.map((issue: string, idx: number) => (
                          <div key={`${issue}-${idx}`} className="text-xs text-gray-700 border border-gray-100 rounded-lg p-2">
                            {issue}
                          </div>
                        ))}
                      </div>
                    )}
                    {characterConsistencyResult?.llm_motivation && (
                      <div className="mt-2 text-xs text-gray-600">
                        动机评分: {characterConsistencyResult.llm_motivation.score ?? '-'}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </div>
          </div>

          {/* 图谱可视化区域 */}
          <div className="flex-1 relative bg-gray-50">
            <GraphVisualization className="w-full h-full" height="100%" />
            {!currentStoryId && (
              <div className="absolute inset-0 flex items-center justify-center text-sm text-gray-500">
                请先选择或创建故事以查看图谱
              </div>
            )}
          </div>
        </div>
      </div>

      <SettingsModal />

      {/* 快速添加菜单（当用户点击"添加"按钮时显示） */}
      {quickAddOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">快速添加节点</h3>
              <button
                onClick={() => setQuickAddOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                关闭
              </button>
            </div>

            <div className="flex gap-2 mb-4">
              {(
                [
                  'Character',
                  'PlotNode',
                  'WorldRule',
                  'Location',
                  'Item',
                  'Conflict',
                  'Theme',
                  'Motivation',
                ] as const
              ).map((type) => (
                <button
                  key={type}
                  onClick={() => setQuickAddType(type)}
                  className={`px-3 py-2 text-sm rounded-lg border ${
                    quickAddType === type
                      ? 'bg-indigo-50 text-indigo-700 border-indigo-200'
                      : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {type === 'Character'
                    ? '角色'
                    : type === 'PlotNode'
                    ? '情节'
                    : type === 'WorldRule'
                    ? '规则'
                    : type === 'Location'
                    ? '地点'
                    : type === 'Item'
                    ? '物品'
                    : type === 'Conflict'
                    ? '冲突'
                    : type === 'Theme'
                    ? '主题'
                    : '动机'}
                </button>
              ))}
            </div>

            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder={quickAddType === 'PlotNode' ? '情节标题' : '名称'}
                value={quickAddForm.name}
                onChange={(e) => setQuickAddForm({ ...quickAddForm, name: e.target.value })}
              />

              {quickAddType !== 'Character' && quickAddType !== 'Location' && quickAddType !== 'Item' && quickAddType !== 'Conflict' && quickAddType !== 'Theme' && quickAddType !== 'Motivation' && (
                <textarea
                  className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="描述"
                  rows={3}
                  value={quickAddForm.description}
                  onChange={(e) => setQuickAddForm({ ...quickAddForm, description: e.target.value })}
                />
              )}

              {['Location', 'Item', 'Conflict', 'Theme', 'Motivation'].includes(quickAddType) && (
                <>
                  <textarea
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="描述"
                    rows={3}
                    value={quickAddForm.description}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, description: e.target.value })
                    }
                  />
                  <input
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="分类（可选）"
                    value={quickAddForm.category}
                    onChange={(e) => setQuickAddForm({ ...quickAddForm, category: e.target.value })}
                  />
                </>
              )}

              {quickAddType === 'Character' && (
                <>
                  <div className="flex gap-2">
                    <select
                      className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                      value={quickAddForm.status}
                      onChange={(e) => setQuickAddForm({ ...quickAddForm, status: e.target.value })}
                    >
                      <option value="alive">存活</option>
                      <option value="deceased">死亡</option>
                      <option value="unknown">未知</option>
                    </select>
                    <input
                      className="flex-1 rounded-lg border border-gray-200 px-3 py-2 text-sm"
                      placeholder="当前位置（可选）"
                      value={quickAddForm.location}
                      onChange={(e) => setQuickAddForm({ ...quickAddForm, location: e.target.value })}
                    />
                  </div>
                </>
              )}

              {quickAddType === 'PlotNode' && (
                <div className="grid grid-cols-3 gap-2">
                  <input
                    type="number"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="序号"
                    value={quickAddForm.sequenceNumber}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, sequenceNumber: Number(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="张力"
                    value={quickAddForm.tensionScore}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, tensionScore: Number(e.target.value) })
                    }
                  />
                  <input
                    type="number"
                    className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="重要性"
                    value={quickAddForm.importance}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, importance: Number(e.target.value) })
                    }
                  />
                </div>
              )}

              {quickAddType === 'WorldRule' && (
                <>
                  <input
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="规则类型（如 magic/physics）"
                    value={quickAddForm.ruleType}
                    onChange={(e) => setQuickAddForm({ ...quickAddForm, ruleType: e.target.value })}
                  />
                  <input
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="约束条件（逗号分隔）"
                    value={quickAddForm.constraints}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, constraints: e.target.value })
                    }
                  />
                  <input
                    className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                    placeholder="示例（逗号分隔）"
                    value={quickAddForm.examples}
                    onChange={(e) =>
                      setQuickAddForm({ ...quickAddForm, examples: e.target.value })
                    }
                  />
                </>
              )}
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600"
                onClick={() => setQuickAddOpen(false)}
              >
                取消
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white"
                onClick={handleQuickAddSubmit}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {storyModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">新建故事</h3>
              <button
                onClick={() => setStoryModalOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                关闭
              </button>
            </div>

            <div className="space-y-3">
              <input
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="故事名称"
                value={storyForm.name}
                onChange={(e) => setStoryForm({ ...storyForm, name: e.target.value })}
              />
              <textarea
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="故事简介"
                rows={3}
                value={storyForm.description}
                onChange={(e) => setStoryForm({ ...storyForm, description: e.target.value })}
              />
              <div className="grid grid-cols-2 gap-2">
                <input
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="题材（可选）"
                  value={storyForm.genre}
                  onChange={(e) => setStoryForm({ ...storyForm, genre: e.target.value })}
                />
                <select
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  value={storyForm.status}
                  onChange={(e) => setStoryForm({ ...storyForm, status: e.target.value })}
                >
                  <option value="active">进行中</option>
                  <option value="paused">暂停</option>
                  <option value="archived">已归档</option>
                </select>
              </div>
              <input
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="标签（逗号分隔）"
                value={storyForm.tags}
                onChange={(e) => setStoryForm({ ...storyForm, tags: e.target.value })}
              />
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600"
                onClick={() => setStoryModalOpen(false)}
              >
                取消
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white"
                onClick={handleCreateStory}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {relationshipModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-lg rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">创建关系</h3>
              <button
                onClick={() => setRelationshipModalOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                关闭
              </button>
            </div>

            <div className="space-y-3">
              <select
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                value={relationshipForm.sourceId}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, sourceId: e.target.value })}
              >
                <option value="">选择源节点</option>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.properties?.name || node.properties?.title || node.id} ({node.type})
                  </option>
                ))}
              </select>

              <select
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                value={relationshipForm.targetId}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, targetId: e.target.value })}
              >
                <option value="">选择目标节点</option>
                {nodes.map((node) => (
                  <option key={node.id} value={node.id}>
                    {node.properties?.name || node.properties?.title || node.id} ({node.type})
                  </option>
                ))}
              </select>

              <select
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                value={relationshipForm.relationType}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, relationType: e.target.value })}
              >
                {(relationTypeOptions.length > 0 ? relationTypeOptions : [
                  { value: 'SOCIAL_BOND', label: 'SOCIAL_BOND' },
                  { value: 'INFLUENCES', label: 'INFLUENCES' },
                ] as any).map((item: any) => (
                  <option key={item.value} value={item.value}>
                    {item.label || item.value}
                  </option>
                ))}
              </select>

              <textarea
                className="w-full rounded-lg border border-gray-200 px-3 py-2 text-sm"
                placeholder="关系描述（可选）"
                rows={2}
                value={relationshipForm.description}
                onChange={(e) => setRelationshipForm({ ...relationshipForm, description: e.target.value })}
              />
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600"
                onClick={() => setRelationshipModalOpen(false)}
              >
                取消
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white"
                onClick={handleCreateRelationship}
              >
                创建
              </button>
            </div>
          </div>
        </div>
      )}

      {extractModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-2xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-lg font-semibold text-gray-900">自动抽取图谱</h3>
              <button
                onClick={() => setExtractModalOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                关闭
              </button>
            </div>

            <div className="space-y-3">
              <textarea
                className={`w-full rounded-lg border border-gray-200 px-3 py-2 text-sm ${
                  extractFile ? 'bg-gray-50 text-gray-400' : ''
                }`}
                placeholder="粘贴剧本文本（人物/地点/冲突/动机会自动抽取）"
                rows={10}
                value={extractForm.content}
                disabled={!!extractFile}
                onChange={(e) => setExtractForm({ ...extractForm, content: e.target.value })}
              />
              {extractFile && (
                <div className="text-xs text-amber-600">
                  已选择文件，将以文件内容为准并忽略文本输入
                </div>
              )}
              <div className="flex items-center gap-3">
                <input
                  key={fileInputKey}
                  type="file"
                  accept=".txt,.md,.json"
                  onChange={(e) => {
                    const file = e.target.files ? e.target.files[0] : null;
                    setExtractFile(file);
                    if (file) {
                      setExtractForm({ ...extractForm, content: '' });
                    }
                  }}
                  className="text-sm"
                />
                {extractFile && (
                  <div className="flex items-center gap-2 text-xs text-gray-500">
                    <span>已选择文件：{extractFile.name}</span>
                    <button
                      className="text-xs text-gray-600 underline"
                      onClick={() => {
                        setExtractFile(null);
                        setFileInputKey((prev) => prev + 1);
                      }}
                    >
                      清除文件
                    </button>
                  </div>
                )}
              </div>
              <div className="grid grid-cols-2 gap-2">
                <input
                  type="number"
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="分块大小"
                  value={extractForm.chunkSize}
                  onChange={(e) =>
                    setExtractForm({ ...extractForm, chunkSize: Number(e.target.value) || 4000 })
                  }
                />
                <input
                  type="number"
                  className="rounded-lg border border-gray-200 px-3 py-2 text-sm"
                  placeholder="重叠长度"
                  value={extractForm.overlap}
                  onChange={(e) =>
                    setExtractForm({ ...extractForm, overlap: Number(e.target.value) || 200 })
                  }
                />
              </div>
            </div>

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600"
                onClick={() => setExtractModalOpen(false)}
              >
                取消
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white"
                onClick={handleExtractPreview}
              >
                预览抽取
              </button>
            </div>
          </div>
        </div>
      )}

      {previewModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/30">
          <div className="w-full max-w-4xl rounded-xl bg-white p-6 shadow-xl">
            <div className="flex items-center justify-between mb-4">
              <div>
                <h3 className="text-lg font-semibold text-gray-900">抽取预览</h3>
                <p className="text-xs text-gray-500 mt-1">
                  高置信度候选与低置信度待审可分别勾选，确认后统一入库
                </p>
              </div>
              <button
                onClick={() => setPreviewModalOpen(false)}
                className="text-gray-500 hover:text-gray-700"
              >
                关闭
              </button>
            </div>

            {dependencyNotice && (
              <div className="mb-3 text-xs text-amber-600">{dependencyNotice}</div>
            )}

            <div className="grid grid-cols-2 gap-4 max-h-[60vh] overflow-y-auto">
              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">高置信度候选</h4>
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-1">节点</div>
                      <div className="space-y-2">
                        {previewPayload.high.nodes.map((item, idx) => (
                          <label key={`high-node-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.high.nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('high', 'nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.name}</span> ({item.type})
                              {item.confidence !== undefined ? ` · 置信度 ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.high.nodes.length === 0 && (
                          <div className="text-xs text-gray-500">无候选节点</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-1">情节节点</div>
                      <div className="space-y-2">
                        {previewPayload.high.plot_nodes.map((item, idx) => (
                          <label key={`high-plot-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.high.plot_nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('high', 'plot_nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.title}</span>
                              {item.confidence !== undefined ? ` · 置信度 ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.high.plot_nodes.length === 0 && (
                          <div className="text-xs text-gray-500">无候选情节节点</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-1">关系</div>
                      <div className="space-y-2">
                        {previewPayload.high.relationships.map((item, idx) => (
                          <label key={`high-rel-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.high.relationships.includes(idx)}
                              onChange={() => togglePreviewSelection('high', 'relationships', idx)}
                            />
                            <span>
                              <span className="font-medium">
                                {item.source_name || item.source} → {item.target_name || item.target}
                              </span>{' '}
                              ({item.type})
                              {item.confidence !== undefined ? ` · 置信度 ${item.confidence}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.high.relationships.length === 0 && (
                          <div className="text-xs text-gray-500">无候选关系</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div className="space-y-4">
                <div>
                  <h4 className="text-sm font-medium text-gray-700 mb-2">低置信度待审</h4>
                  <div className="space-y-3">
                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-1">节点</div>
                      <div className="space-y-2">
                        {previewPayload.low.nodes.map((item, idx) => (
                          <label key={`low-node-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.low.nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('low', 'nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.name}</span> ({item.type}) - 置信度 {item.confidence}
                              {item.reason ? ` · ${item.reason}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.low.nodes.length === 0 && (
                          <div className="text-xs text-gray-500">无待审节点</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-1">情节节点</div>
                      <div className="space-y-2">
                        {previewPayload.low.plot_nodes.map((item, idx) => (
                          <label key={`low-plot-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.low.plot_nodes.includes(idx)}
                              onChange={() => togglePreviewSelection('low', 'plot_nodes', idx)}
                            />
                            <span>
                              <span className="font-medium">{item.title}</span> - 置信度 {item.confidence}
                              {item.reason ? ` · ${item.reason}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.low.plot_nodes.length === 0 && (
                          <div className="text-xs text-gray-500">无待审情节节点</div>
                        )}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs font-medium text-gray-500 mb-1">关系</div>
                      <div className="space-y-2">
                        {previewPayload.low.relationships.map((item, idx) => (
                          <label key={`low-rel-${idx}`} className="flex items-start gap-2 text-sm">
                            <input
                              type="checkbox"
                              checked={previewSelection.low.relationships.includes(idx)}
                              onChange={() => togglePreviewSelection('low', 'relationships', idx)}
                            />
                            <span>
                              <span className="font-medium">
                                {item.source} → {item.target}
                              </span>{' '}
                              ({item.type}) - 置信度 {item.confidence}
                              {item.reason ? ` · ${item.reason}` : ''}
                            </span>
                          </label>
                        ))}
                        {previewPayload.low.relationships.length === 0 && (
                          <div className="text-xs text-gray-500">无待审关系</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {previewPayload.validation_issues.length > 0 && (
              <div className="mt-4 text-xs text-amber-600">
                校验提示：{previewPayload.validation_issues.join('；')}
              </div>
            )}

            <div className="mt-6 flex justify-end gap-2">
              <button
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-600"
                onClick={() => setPreviewModalOpen(false)}
              >
                取消
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg border border-gray-200 text-gray-700"
                onClick={handleSaveToReviewQueue}
                disabled={previewPayload.low.nodes.length + previewPayload.low.plot_nodes.length + previewPayload.low.relationships.length === 0}
              >
                加入审核中心
              </button>
              <button
                className="px-4 py-2 text-sm rounded-lg bg-indigo-600 text-white"
                onClick={handleSubmitPreview}
              >
                确认入库
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

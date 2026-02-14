/**
 * 图数据库状态管理 Store
 * Graph Database Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type {
  GraphNode,
  GraphRelationship,
  CharacterData,
  PlotNodeData,
  WorldRuleData,
  CharacterNetwork,
  StoryElements,
  GraphStatistics,
  NodeType,
  RelationType,
} from '@/services/graphService';
import { graphService } from '@/services/graphService';

interface GraphState {
  // 当前故事 ID
  currentStoryId: string | null;
  stories: { story_id: string; name: string; description: string }[];

  // 图数据
  nodes: GraphNode[];
  relationships: GraphRelationship[];

  // 角色数据
  characters: CharacterData[];
  selectedCharacter: CharacterData | null;
  characterNetwork: CharacterNetwork | null;

  // 情节数据
  plotNodes: PlotNodeData[];
  selectedPlot: PlotNodeData | null;

  // 世界观规则
  worldRules: WorldRuleData[];

  // 统计信息
  statistics: GraphStatistics | null;

  // UI 状态
  loading: boolean;
  error: string | null;
  selectedNodeId: string | null;
  selectedRelationshipId: string | null;
  filter: {
    nodeTypes: NodeType[];
    relationTypes: RelationType[];
    searchQuery: string;
  };
  viewMode: 'force' | 'tree' | 'radial' | 'circle';
  relationTypeOptions: { value: RelationType; label: string; category?: string }[];

  // 操作
  setCurrentStoryId: (storyId: string | null) => void;
  setNodes: (nodes: GraphNode[]) => void;
  setRelationships: (relationships: GraphRelationship[]) => void;
  addNode: (node: GraphNode) => void;
  updateNode: (nodeId: string, updates: Partial<GraphNode>) => void;
  removeNode: (nodeId: string) => void;
  addRelationship: (relationship: GraphRelationship) => void;
  removeRelationship: (relationshipId: string) => void;

  setCharacters: (characters: CharacterData[]) => void;
  setSelectedCharacter: (character: CharacterData | null) => void;
  setCharacterNetwork: (network: CharacterNetwork | null) => void;

  setPlotNodes: (plots: PlotNodeData[]) => void;
  setSelectedPlot: (plot: PlotNodeData | null) => void;

  setWorldRules: (rules: WorldRuleData[]) => void;

  setStatistics: (statistics: GraphStatistics | null) => void;

  setLoading: (loading: boolean) => void;
  setError: (error: string | null) => void;
  setSelectedNodeId: (nodeId: string | null) => void;
  setSelectedRelationshipId: (relationshipId: string | null) => void;
  setFilter: (filter: Partial<GraphState['filter']>) => void;
  setViewMode: (mode: 'force' | 'tree' | 'radial' | 'circle') => void;
  setRelationTypeOptions: (
    types: { value: RelationType; label: string; category?: string }[]
  ) => void;

  // API 调用
  loadStories: () => Promise<void>;
  loadRelationTypes: () => Promise<void>;
  loadStoryElements: (storyId: string) => Promise<void>;
  loadCharacterNetwork: (characterId: string, depth?: number) => Promise<void>;
  loadStatistics: (storyId: string) => Promise<void>;
  createStory: (data: { name: string; description?: string; genre?: string | null; tags?: string[]; status?: string }) => Promise<any>;
  createCharacter: (data: Omit<CharacterData, 'character_id'>) => Promise<CharacterData>;
  createPlotNode: (data: Omit<PlotNodeData, 'plot_id'>) => Promise<PlotNodeData>;
  createWorldRule: (data: Omit<WorldRuleData, 'rule_id'>) => Promise<WorldRuleData>;
  createGenericNode: (nodeType: NodeType, data: { name: string; description?: string; category?: string | null }) => Promise<any>;
  createRelationship: (data: { source_id: string; target_id: string; relation_type: RelationType; properties?: Record<string, any> }) => Promise<any>;
  extractGraphFromText: (data: { story_id: string; content: string; chunk_size?: number; overlap?: number; provider?: string; model?: string; dry_run?: boolean }) => Promise<any>;
  extractGraphFromFile: (data: { story_id: string; file: File; chunk_size?: number; overlap?: number; provider?: string; model?: string; dry_run?: boolean }) => Promise<any>;
  submitGraphReview: (data: { story_id: string; nodes: any[]; plot_nodes: any[]; relationships: any[]; review_id?: string }) => Promise<any>;
  createReviewQueueEntry: (data: { story_id: string; payload: any; source?: string }) => Promise<any>;
  listReviewQueueEntries: (data: { story_id: string; status?: string; limit?: number; offset?: number }) => Promise<any>;
  getReviewQueueEntry: (reviewId: string) => Promise<any>;
  updateReviewQueueStatus: (data: { review_id: string; status: string; result?: any }) => Promise<any>;
  createSocialBond: (
    characterId1: string,
    characterId2: string,
    bondType: string,
    trustLevel: number,
    hiddenRelation?: boolean
  ) => Promise<void>;
  deleteNode: (nodeId: string, nodeType: NodeType) => Promise<void>;
  saveNodeUpdates: (nodeId: string, nodeType: NodeType, updates: Record<string, any>) => Promise<void>;
  searchNodes: (query: string, nodeTypes?: NodeType[]) => Promise<GraphNode[]>;

  // 重置
  reset: () => void;
}

const initialState = {
  currentStoryId: null,
  stories: [],
  nodes: [],
  relationships: [],
  characters: [],
  selectedCharacter: null,
  characterNetwork: null,
  plotNodes: [],
  selectedPlot: null,
  worldRules: [],
  statistics: null,
  loading: false,
  error: null,
  selectedNodeId: null,
  selectedRelationshipId: null,
  filter: {
    nodeTypes: [],
    relationTypes: [],
    searchQuery: '',
  },
  viewMode: 'force' as const,
  relationTypeOptions: [],
};

export const useGraphStore = create<GraphState>()(
  devtools(
    (set, get) => ({
      ...initialState,

      setCurrentStoryId: (storyId) => set({ currentStoryId: storyId }),
      loadStories: async () => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.listStories();
          if (response.success && response.data) {
            set({ stories: response.data as any, loading: false });
          } else {
            set({ error: response.error || '加载故事列表失败', loading: false });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载故事列表失败',
            loading: false,
          });
        }
      },

      setNodes: (nodes) => set({ nodes }),
      setRelationships: (relationships) => set({ relationships }),

      addNode: (node) =>
        set((state) => ({
          nodes: [...state.nodes, node],
        })),

      updateNode: (nodeId, updates) =>
        set((state) => ({
          nodes: state.nodes.map((node) =>
            node.id === nodeId ? { ...node, ...updates } : node
          ),
        })),

      removeNode: (nodeId) =>
        set((state) => ({
          nodes: state.nodes.filter((node) => node.id !== nodeId),
          relationships: state.relationships.filter(
            (rel) => rel.source !== nodeId && rel.target !== nodeId
          ),
        })),

      addRelationship: (relationship) =>
        set((state) => ({
          relationships: [...state.relationships, relationship],
        })),

      removeRelationship: (relationshipId) =>
        set((state) => ({
          relationships: state.relationships.filter(
            (rel) => rel.id !== relationshipId
          ),
        })),

      setCharacters: (characters) => set({ characters }),
      setSelectedCharacter: (character) => set({ selectedCharacter: character }),
      setCharacterNetwork: (network) => set({ characterNetwork: network }),

      setPlotNodes: (plots) => set({ plotNodes: plots }),
      setSelectedPlot: (plot) => set({ selectedPlot: plot }),

      setWorldRules: (rules) => set({ worldRules: rules }),

      setStatistics: (statistics) => set({ statistics }),

      setLoading: (loading) => set({ loading }),
      setError: (error) => set({ error }),
      setSelectedNodeId: (nodeId) => set({ selectedNodeId: nodeId }),
      setSelectedRelationshipId: (relationshipId) =>
        set({ selectedRelationshipId: relationshipId }),

      setFilter: (filter) =>
        set((state) => ({
          filter: { ...state.filter, ...filter },
        })),

      setViewMode: (mode) => set({ viewMode: mode }),
      setRelationTypeOptions: (types) => set({ relationTypeOptions: types }),

      // API 调用实现
      loadStoryElements: async (storyId) => {
        set({ loading: true, error: null, currentStoryId: storyId });
        try {
          const response = await graphService.getStoryElements({
            story_id: storyId,
          });

          if (response.success && response.data) {
            const elements = response.data;
            const inferredNodes = elements.nodes ?? [
              ...(elements.stories ?? []).map((story: any) => ({
                id: story.story_id,
                labels: ['Story'],
                properties: { ...story },
                type: 'Story' as const,
              })),
              ...elements.characters.map((char) => ({
                id: char.character_id,
                labels: ['Character'],
                properties: { ...char },
                type: 'Character' as const,
              })),
              ...elements.plot_nodes.map((plot) => ({
                id: plot.plot_id,
                labels: ['PlotNode'],
                properties: { ...plot },
                type: 'PlotNode' as const,
              })),
              ...elements.world_rules.map((rule) => ({
                id: rule.rule_id,
                labels: ['WorldRule'],
                properties: { ...rule },
                type: 'WorldRule' as const,
              })),
            ];
            set({
              characters: elements.characters,
              plotNodes: elements.plot_nodes,
              worldRules: elements.world_rules,
              relationships: elements.relationships ?? [],
              nodes: inferredNodes,
              loading: false,
            });
          } else {
            set({
              error: response.error || '加载故事元素失败',
              loading: false,
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载故事元素失败',
            loading: false,
          });
        }
      },

      loadRelationTypes: async () => {
        try {
          const response = await graphService.getRelationTypes();
          if (response.success && response.data) {
            set({ relationTypeOptions: response.data as any });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载关系类型失败',
          });
        }
      },

      loadCharacterNetwork: async (characterId, depth = 2) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          return;
        }

        set({ loading: true, error: null });
        try {
          const response = await graphService.getCharacterNetwork({
            character_id: characterId,
            story_id: currentStoryId,
            depth,
            include_hidden: true,
          });

          if (response.success && response.data) {
            set({
              characterNetwork: response.data,
              loading: false,
            });
          } else {
            set({
              error: response.error || '加载角色网络失败',
              loading: false,
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载角色网络失败',
            loading: false,
          });
        }
      },

      loadStatistics: async (storyId) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.getStoryStatistics(storyId);

          if (response.success && response.data) {
            set({
              statistics: response.data,
              loading: false,
            });
          } else {
            set({
              error: response.error || '加载统计信息失败',
              loading: false,
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载统计信息失败',
            loading: false,
          });
        }
      },

      createStory: async (data) => {
        set({ loading: true, error: null });
        try {
          const storyId = `story_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
          const response = await graphService.createStory({
            story_id: storyId,
            name: data.name,
            description: data.description || '',
            genre: data.genre ?? null,
            tags: data.tags || [],
            status: data.status || 'active',
          } as any);

          const created = (response.data as any)?.node ?? response.data;
          if (response.success && created) {
            set((state) => ({
              stories: [
                ...state.stories,
                {
                  story_id: created.story_id || storyId,
                  name: created.name || data.name,
                  description: created.description || data.description || '',
                },
              ],
              loading: false,
            }));
            return created;
          }

          set({
            error: response.error || '创建故事失败',
            loading: false,
          });
          throw new Error(response.error || '创建故事失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建故事失败',
            loading: false,
          });
          throw error;
        }
      },

      createCharacter: async (data) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          throw new Error('请先选择故事');
        }

        set({ loading: true, error: null });
        try {
          const characterId = `char_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          const response = await graphService.createCharacter({
            character_id: characterId,
            ...data,
            story_id: currentStoryId,
          });

          const created = (response.data as any)?.node ?? response.data;
          if (response.success && created) {
            set((state) => ({
              characters: [...state.characters, created],
              loading: false,
            }));
            return created;
          } else {
            set({
              error: response.error || '创建角色失败',
              loading: false,
            });
            throw new Error(response.error || '创建角色失败');
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建角色失败',
            loading: false,
          });
          throw error;
        }
      },

      createPlotNode: async (data) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          throw new Error('请先选择故事');
        }

        set({ loading: true, error: null });
        try {
          const plotId = `plot_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
          const response = await graphService.createPlotNode({
            plot_id: plotId,
            ...data,
            story_id: currentStoryId,
          });

          const created = (response.data as any)?.node ?? response.data;
          if (response.success && created) {
            set((state) => ({
              plotNodes: [...state.plotNodes, created],
              loading: false,
            }));
            return created;
          } else {
            set({
              error: response.error || '创建情节节点失败',
              loading: false,
            });
            throw new Error(response.error || '创建情节节点失败');
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建情节节点失败',
            loading: false,
          });
          throw error;
        }
      },

      createWorldRule: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.createWorldRule({
            rule_id: `rule_${Date.now()}`,
            story_id: data.story_id,
            name: data.name,
            description: data.description,
            rule_type: data.rule_type ?? 'general',
            constraints: data.constraints ?? [],
            examples: data.examples ?? [],
          });

          const created = (response.data as any)?.node ?? response.data;
          if (response.success && created) {
            const rule = created;
            set((state) => ({
              worldRules: [...state.worldRules, rule],
              loading: false,
            }));
            return rule;
          }

          set({
            error: response.error || '创建世界观规则失败',
            loading: false,
          });
          throw new Error(response.error || '创建世界观规则失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建世界观规则失败',
            loading: false,
          });
          throw error;
        }
      },

      createGenericNode: async (nodeType, data) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          throw new Error('请先选择故事');
        }

        set({ loading: true, error: null });
        try {
          const nodeId = `node_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
          const response = await graphService.createGenericNode(nodeType, {
            node_id: nodeId,
            story_id: currentStoryId,
            name: data.name,
            description: data.description || '',
            category: data.category || null,
          });

          const created = (response.data as any)?.node ?? response.data;
          if (response.success && created) {
            set((state) => ({
              nodes: [
                ...state.nodes,
                {
                  id: created.node_id || nodeId,
                  labels: [nodeType],
                  properties: created,
                  type: nodeType,
                },
              ],
              loading: false,
            }));
            return created;
          }

          set({
            error: response.error || '创建节点失败',
            loading: false,
          });
          throw new Error(response.error || '创建节点失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建节点失败',
            loading: false,
          });
          throw error;
        }
      },

      createRelationship: async (data) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          throw new Error('请先选择故事');
        }

        set({ loading: true, error: null });
        try {
          const response = await graphService.createRelationship({
            story_id: currentStoryId,
            source_id: data.source_id,
            target_id: data.target_id,
            relation_type: data.relation_type,
            properties: data.properties || {},
          });

          if (response.success) {
            await get().loadStoryElements(currentStoryId);
            set({ loading: false });
            return response.data;
          }

          set({
            error: response.error || '创建关系失败',
            loading: false,
          });
          throw new Error(response.error || '创建关系失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建关系失败',
            loading: false,
          });
          throw error;
        }
      },

      extractGraphFromText: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.extractGraph(data);
          if (response.success) {
            if (data.story_id && !data.dry_run) {
              await get().loadStoryElements(data.story_id);
              await get().loadStatistics(data.story_id);
            }
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '自动抽取失败',
            loading: false,
          });
          throw new Error(response.error || '自动抽取失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '自动抽取失败',
            loading: false,
          });
          throw error;
        }
      },

      extractGraphFromFile: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.extractGraphFile(data);
          if (response.success) {
            if (data.story_id && !data.dry_run) {
              await get().loadStoryElements(data.story_id);
              await get().loadStatistics(data.story_id);
            }
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '自动抽取失败',
            loading: false,
          });
          throw new Error(response.error || '自动抽取失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '自动抽取失败',
            loading: false,
          });
          throw error;
        }
      },

      submitGraphReview: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.submitGraphReview(data);
          if (response.success) {
            if (data.story_id) {
              await get().loadStoryElements(data.story_id);
              await get().loadStatistics(data.story_id);
            }
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '提交审核失败',
            loading: false,
          });
          throw new Error(response.error || '提交审核失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '提交审核失败',
            loading: false,
          });
          throw error;
        }
      },

      createReviewQueueEntry: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.createReviewQueueEntry(data);
          if (response.success) {
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '创建审核队列失败',
            loading: false,
          });
          throw new Error(response.error || '创建审核队列失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建审核队列失败',
            loading: false,
          });
          throw error;
        }
      },

      listReviewQueueEntries: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.listReviewQueueEntries(data);
          if (response.success) {
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '加载审核队列失败',
            loading: false,
          });
          throw new Error(response.error || '加载审核队列失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '加载审核队列失败',
            loading: false,
          });
          throw error;
        }
      },

      getReviewQueueEntry: async (reviewId) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.getReviewQueueEntry(reviewId);
          if (response.success) {
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '获取审核条目失败',
            loading: false,
          });
          throw new Error(response.error || '获取审核条目失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '获取审核条目失败',
            loading: false,
          });
          throw error;
        }
      },

      updateReviewQueueStatus: async (data) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.updateReviewQueueStatus(data);
          if (response.success) {
            set({ loading: false });
            return response.data;
          }
          set({
            error: response.error || '更新审核状态失败',
            loading: false,
          });
          throw new Error(response.error || '更新审核状态失败');
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '更新审核状态失败',
            loading: false,
          });
          throw error;
        }
      },

      createSocialBond: async (
        characterId1,
        characterId2,
        bondType,
        trustLevel,
        hiddenRelation = false
      ) => {
        set({ loading: true, error: null });
        try {
          const response = await graphService.createSocialBond({
            character_id_1: characterId1,
            character_id_2: characterId2,
            trust_level: trustLevel,
            bond_type: bondType,
            hidden_relation: hiddenRelation,
          });

          if (response.success) {
            set({ loading: false });
          } else {
            set({
              error: response.error || '创建社交关系失败',
              loading: false,
            });
            throw new Error(response.error || '创建社交关系失败');
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '创建社交关系失败',
            loading: false,
          });
          throw error;
        }
      },

      deleteNode: async (nodeId, nodeType) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          return;
        }

        set({ loading: true, error: null });
        try {
          if (nodeType === 'Story') {
            const response = await graphService.deleteStory(nodeId);
            if (response.success) {
              set((state) => ({
                stories: state.stories.filter((story) => story.story_id !== nodeId),
                nodes: state.nodes.filter((node) => node.id !== nodeId),
                relationships: state.relationships.filter(
                  (rel) => rel.source !== nodeId && rel.target !== nodeId
                ),
                characters: state.characters.filter((char) => char.story_id !== nodeId),
                plotNodes: state.plotNodes.filter((plot) => plot.story_id !== nodeId),
                worldRules: state.worldRules.filter((rule) => rule.story_id !== nodeId),
                currentStoryId: state.currentStoryId === nodeId ? null : state.currentStoryId,
                loading: false,
              }));
              return;
            }

            set({
              error: response.error || '删除故事失败',
              loading: false,
            });
            return;
          }

          const response = await graphService.deleteNode(nodeId, currentStoryId, nodeType);

          if (response.success) {
            set((state) => ({
              nodes: state.nodes.filter((node) => node.id !== nodeId),
              relationships: state.relationships.filter(
                (rel) => rel.source !== nodeId && rel.target !== nodeId
              ),
              characters: state.characters.filter((char) => char.character_id !== nodeId),
              plotNodes: state.plotNodes.filter((plot) => plot.plot_id !== nodeId),
              worldRules: state.worldRules.filter((rule) => rule.rule_id !== nodeId),
              loading: false,
            }));
          } else {
            set({
              error: response.error || '删除节点失败',
              loading: false,
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '删除节点失败',
            loading: false,
          });
        }
      },

      saveNodeUpdates: async (nodeId, nodeType, updates) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          return;
        }

        set({ loading: true, error: null });
        try {
          const response = await graphService.updateNode(nodeId, currentStoryId, nodeType, updates);

          if (response.success) {
            set((state) => ({
              nodes: state.nodes.map((node) =>
                node.id === nodeId
                  ? { ...node, properties: { ...node.properties, ...updates } }
                  : node
              ),
              stories:
                nodeType === 'Story'
                  ? state.stories.map((story) =>
                      story.story_id === nodeId ? { ...story, ...updates } : story
                    )
                  : state.stories,
              characters:
                nodeType === 'Character'
                  ? state.characters.map((char) =>
                      char.character_id === nodeId ? { ...char, ...updates } : char
                    )
                  : state.characters,
              plotNodes:
                nodeType === 'PlotNode'
                  ? state.plotNodes.map((plot) =>
                      plot.plot_id === nodeId ? { ...plot, ...updates } : plot
                    )
                  : state.plotNodes,
              worldRules:
                nodeType === 'WorldRule'
                  ? state.worldRules.map((rule) =>
                      rule.rule_id === nodeId ? { ...rule, ...updates } : rule
                    )
                  : state.worldRules,
              loading: false,
            }));
          } else {
            set({
              error: response.error || '更新节点失败',
              loading: false,
            });
          }
        } catch (error) {
          set({
            error: error instanceof Error ? error.message : '更新节点失败',
            loading: false,
          });
        }
      },

      searchNodes: async (query, nodeTypes) => {
        const { currentStoryId } = get();
        if (!currentStoryId) {
          set({ error: '请先选择故事' });
          return [];
        }

        try {
          const response = await graphService.searchNodes(currentStoryId, query, nodeTypes);

          if (response.success && response.data) {
            return response.data;
          } else {
            set({ error: response.error || '搜索节点失败' });
            return [];
          }
        } catch (error) {
          set({ error: error instanceof Error ? error.message : '搜索节点失败' });
          return [];
        }
      },

      reset: () => set(initialState),
    }),
    { name: 'GraphStore' }
  )
);

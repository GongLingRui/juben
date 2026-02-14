/**
 * 图数据库服务
 * Graph Database Service
 */

import { api } from './/api';

// ============ 类型定义 ============

export type NodeType =
  | 'Story'
  | 'Character'
  | 'PlotNode'
  | 'WorldRule'
  | 'Location'
  | 'Item'
  | 'Conflict'
  | 'Theme'
  | 'Motivation';

export type RelationType =
  | 'SOCIAL_BOND'
  | 'FAMILY_RELATION'
  | 'ROMANTIC_RELATION'
  | 'INFLUENCES'
  | 'LEADS_TO'
  | 'NEXT'
  | 'RESOLVES'
  | 'COMPLICATES'
  | 'INVOLVED_IN'
  | 'DRIVEN_BY'
  | 'CONTAINS'
  | 'VIOLATES'
  | 'ENFORCES'
  | 'LOCATED_IN'
  | 'LOCATED_AT'
  | 'OWNS'
  | 'PART_OF'
  | 'REPRESENTS'
  | 'OPPOSES'
  | 'SUPPORTS';

export type CharacterStatus = 'alive' | 'deceased' | 'unknown';

export interface GraphNode {
  id: string;
  labels: string[];
  properties: Record<string, any>;
  type: NodeType;
}

export interface GraphRelationship {
  id: string;
  type: RelationType;
  source: string;
  target: string;
  properties: Record<string, any>;
}

export interface CharacterData {
  character_id: string;
  name: string;
  story_id: string;
  status: CharacterStatus;
  location: string | null;
  persona: string[];
  arc: number;
  backstory: string | null;
  motivations: string[];
  flaws: string[];
  strengths: string[];
}

export interface PlotNodeData {
  plot_id: string;
  story_id: string;
  title: string;
  description: string;
  sequence_number: number;
  tension_score: number;
  timestamp: string | null;
  chapter: number | null;
  characters_involved: string[];
  locations: string[];
  conflicts: string[];
  themes: string[];
  importance: number;
}

export interface WorldRuleData {
  rule_id: string;
  story_id: string;
  name: string;
  description: string;
  rule_type: string;
  constraints: string[];
  examples: string[];
}

export interface SocialBondData {
  character_id_1: string;
  character_id_2: string;
  trust_level: number;
  bond_type: string;
  hidden_relation: boolean;
  description?: string;
}

export interface CharacterNetwork {
  center_character: CharacterData;
  connections: {
    character: CharacterData;
    relationship: SocialBondData;
    distance: number;
  }[];
  depth: number;
  total_nodes: number;
}

export interface GraphStatistics {
  total_characters: number;
  total_plot_nodes: number;
  total_world_rules: number;
  total_relationships: number;
  average_tension: number;
  most_connected_characters: Array<{
    character_id: string;
    name: string;
    connection_count: number;
  }>;
}

export interface StoryElements {
  stories?: any[];
  characters: CharacterData[];
  plot_nodes: PlotNodeData[];
  world_rules: WorldRuleData[];
  relationships: GraphRelationship[];
  locations: string[];
  conflicts: string[];
  themes: string[];
  nodes?: GraphNode[];
}

export interface StoryData {
  story_id: string;
  name: string;
  description: string;
  genre?: string | null;
  tags: string[];
  status: string;
}

export interface GraphReviewQueueEntry {
  review_id: string;
  story_id: string;
  status: 'pending' | 'approved' | 'rejected' | string;
  source?: string;
  nodes_count?: number;
  plot_nodes_count?: number;
  relationships_count?: number;
  created_at?: string;
  updated_at?: string;
  payload?: {
    nodes?: any[];
    plot_nodes?: any[];
    relationships?: any[];
    validation_issues?: any[];
  };
  result?: any;
}

export interface GraphReviewQueueList {
  items: GraphReviewQueueEntry[];
  total: number;
  limit: number;
  offset: number;
}

// ============ 请求/响应类型 ============

export interface CreateCharacterRequest {
  character_id: string;
  name: string;
  story_id: string;
  status?: CharacterStatus;
  location?: string | null;
  persona?: string[];
  arc?: number;
  backstory?: string | null;
  motivations?: string[];
  flaws?: string[];
  strengths?: string[];
}

export interface CreatePlotNodeRequest {
  plot_id: string;
  story_id: string;
  title: string;
  description: string;
  sequence_number: number;
  tension_score?: number;
  timestamp?: string | null;
  chapter?: number | null;
  characters_involved?: string[];
  locations?: string[];
  conflicts?: string[];
  themes?: string[];
  importance?: number;
}

export interface CreateWorldRuleRequest {
  rule_id: string;
  story_id: string;
  name: string;
  description: string;
  rule_type: string;
  constraints?: string[];
  examples?: string[];
}

export interface CreateSocialBondRequest {
  character_id_1: string;
  character_id_2: string;
  trust_level: number;
  bond_type: string;
  hidden_relation?: boolean;
  description?: string;
}

export interface GetCharacterNetworkRequest {
  character_id: string;
  story_id: string;
  depth?: number;
  include_hidden?: boolean;
}

export interface GetStoryElementsRequest {
  story_id: string;
  element_types?: NodeType[];
  limit?: number;
  offset?: number;
}

export interface GraphQueryRequest {
  cypher: string;
  parameters?: Record<string, any>;
}

export interface BaseResponse<T = any> {
  success: boolean;
  message: string;
  data?: T;
  error?: string;
}

// ============ API 方法 ============

export class GraphService {
  async listStories(): Promise<BaseResponse<StoryData[]>> {
    return api.get<BaseResponse<StoryData[]>>('/graph/stories');
  }

  async createStory(request: StoryData): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/graph/stories', request);
  }

  async deleteStory(storyId: string): Promise<BaseResponse<any>> {
    return api.delete<BaseResponse<any>>(`/graph/stories/${storyId}`);
  }
  /**
   * 创建或更新角色节点
   */
  async createCharacter(request: CreateCharacterRequest): Promise<BaseResponse<CharacterData>> {
    return api.post<BaseResponse<CharacterData>>('/graph/nodes/character', request);
  }

  /**
   * 获取角色详情
   */
  async getCharacter(characterId: string, storyId: string): Promise<BaseResponse<CharacterData>> {
    return api.get<BaseResponse<CharacterData>>(`/graph/nodes/character/${characterId}`, {
      story_id: storyId,
    });
  }

  /**
   * 创建或更新情节节点
   */
  async createPlotNode(request: CreatePlotNodeRequest): Promise<BaseResponse<PlotNodeData>> {
    return api.post<BaseResponse<PlotNodeData>>('/graph/nodes/plot', request);
  }

  /**
   * 获取情节详情
   */
  async getPlotNode(plotId: string, storyId: string): Promise<BaseResponse<PlotNodeData>> {
    return api.get<BaseResponse<PlotNodeData>>(`/graph/nodes/plot/${plotId}`, {
      story_id: storyId,
    });
  }

  /**
   * 创建或更新世界观规则
   */
  async createWorldRule(request: CreateWorldRuleRequest): Promise<BaseResponse<WorldRuleData>> {
    return api.post<BaseResponse<WorldRuleData>>('/graph/nodes/world-rule', request);
  }

  async createGenericNode(nodeType: NodeType, request: any): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>(`/graph/nodes/${nodeType}`, request);
  }

  async createRelationship(request: {
    story_id: string;
    source_id: string;
    target_id: string;
    relation_type: string;
    properties?: Record<string, any>;
  }): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/graph/relationships', request);
  }

  async getRelationTypes(): Promise<BaseResponse<Array<{ value: RelationType; label: string; category?: string }>>> {
    return api.get<BaseResponse<Array<{ value: RelationType; label: string; category?: string }>>>(
      '/graph/relationships/types'
    );
  }

  async extractGraph(request: {
    story_id: string;
    content: string;
    chunk_size?: number;
    overlap?: number;
    provider?: string;
    model?: string;
    dry_run?: boolean;
  }): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/graph/extract', request);
  }

  async extractGraphFile(params: {
    file: File;
    story_id: string;
    chunk_size?: number;
    overlap?: number;
    provider?: string;
    model?: string;
    dry_run?: boolean;
  }): Promise<BaseResponse<any>> {
    const form = new FormData();
    form.append('file', params.file);
    form.append('story_id', params.story_id);
    if (params.chunk_size) form.append('chunk_size', String(params.chunk_size));
    if (params.overlap) form.append('overlap', String(params.overlap));
    if (params.provider) form.append('provider', params.provider);
    if (params.model) form.append('model', params.model);
    if (params.dry_run !== undefined) form.append('dry_run', String(params.dry_run));

    const tokenRaw = localStorage.getItem('auth-storage');
    let authHeader: string | null = null;
    if (tokenRaw) {
      try {
        const parsed = JSON.parse(tokenRaw);
        const token = parsed?.state?.tokens?.accessToken;
        authHeader = token ? `Bearer ${token}` : null;
      } catch {
        authHeader = null;
      }
    }

    const response = await fetch(
      `${import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'}/graph/extract/file`,
      {
        method: 'POST',
        headers: {
          ...(authHeader ? { Authorization: authHeader } : {}),
        },
        body: form,
      }
    );

    if (!response.ok) {
      throw new Error(await response.text());
    }
    return response.json();
  }

  async submitGraphReview(request: {
    story_id: string;
    nodes: any[];
    plot_nodes: any[];
    relationships: any[];
    review_id?: string;
  }): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/graph/review/submit', request);
  }

  async createReviewQueueEntry(request: {
    story_id: string;
    payload: any;
    source?: string;
  }): Promise<BaseResponse<GraphReviewQueueEntry>> {
    return api.post<BaseResponse<GraphReviewQueueEntry>>('/graph/review/queue/create', request);
  }

  async listReviewQueueEntries(request: {
    story_id: string;
    status?: string;
    limit?: number;
    offset?: number;
  }): Promise<BaseResponse<GraphReviewQueueList>> {
    return api.post<BaseResponse<GraphReviewQueueList>>('/graph/review/queue/list', request);
  }

  async getReviewQueueEntry(reviewId: string): Promise<BaseResponse<GraphReviewQueueEntry>> {
    return api.get<BaseResponse<GraphReviewQueueEntry>>(`/graph/review/queue/${reviewId}`);
  }

  async updateReviewQueueStatus(request: {
    review_id: string;
    status: string;
    result?: any;
  }): Promise<BaseResponse<GraphReviewQueueEntry>> {
    return api.post<BaseResponse<GraphReviewQueueEntry>>('/graph/review/queue/update', request);
  }

  async findShortestPath(params: {
    story_id: string;
    source_id: string;
    target_id: string;
    max_depth?: number;
  }): Promise<BaseResponse<any>> {
    return api.get<BaseResponse<any>>('/graph/path', {
      story_id: params.story_id,
      source_id: params.source_id,
      target_id: params.target_id,
      max_depth: String(params.max_depth ?? 5),
    });
  }

  /**
   * 创建角色间的社交关系
   */
  async createSocialBond(request: CreateSocialBondRequest): Promise<BaseResponse<SocialBondData>> {
    return api.post<BaseResponse<SocialBondData>>('/graph/relationships/social', request);
  }

  /**
   * 获取角色网络分析
   */
  async getCharacterNetwork(
    request: GetCharacterNetworkRequest
  ): Promise<BaseResponse<CharacterNetwork>> {
    return api.post<BaseResponse<CharacterNetwork>>('/graph/network/character', request);
  }

  /**
   * 获取故事的所有元素
   */
  async getStoryElements(request: GetStoryElementsRequest): Promise<BaseResponse<StoryElements>> {
    return api.post<BaseResponse<StoryElements>>('/graph/story/elements', request);
  }

  /**
   * 获取故事统计信息
   */
  async getStoryStatistics(storyId: string): Promise<BaseResponse<GraphStatistics>> {
    return api.get<BaseResponse<GraphStatistics>>(`/graph/story/statistics/${storyId}`);
  }

  /**
   * 执行自定义 Cypher 查询
   */
  async executeQuery(request: GraphQueryRequest): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/graph/query', request);
  }

  /**
   * 删除节点
   */
  async deleteNode(nodeId: string, storyId: string, nodeType: NodeType): Promise<BaseResponse<void>> {
    return api.delete<BaseResponse<void>>(`/graph/nodes/${nodeType}/${nodeId}?story_id=${storyId}`);
  }

  /**
   * 删除关系
   */
  async deleteRelationship(relationshipId: string): Promise<BaseResponse<void>> {
    return api.delete<BaseResponse<void>>(`/graph/relationships/${relationshipId}`);
  }

  /**
   * 更新节点属性
   */
  async updateNode(
    nodeId: string,
    storyId: string,
    nodeType: NodeType,
    updates: Record<string, any>
  ): Promise<BaseResponse<void>> {
    return api.post<BaseResponse<void>>(`/graph/nodes/${nodeType}/${nodeId}`, {
      story_id: storyId,
      ...updates,
    });
  }

  /**
   * 搜索节点
   */
  async searchNodes(
    storyId: string,
    query: string,
    nodeTypes?: NodeType[]
  ): Promise<BaseResponse<GraphNode[]>> {
    return api.get<BaseResponse<GraphNode[]>>('/graph/search', {
      story_id: storyId,
      q: query,
      types: nodeTypes?.join(','),
    });
  }

  /**
   * 获取节点关系
   */
  async getNodeRelationships(
    nodeId: string,
    storyId: string,
    relationTypes?: RelationType[]
  ): Promise<BaseResponse<GraphRelationship[]>> {
    return api.get<BaseResponse<GraphRelationship[]>>(`/graph/nodes/${nodeId}/relationships`, {
      story_id: storyId,
      types: relationTypes?.join(','),
    });
  }

  /**
   * 批量创建节点
   */
  async batchCreateNodes(
    nodes: Array<{
      type: NodeType;
      data: CharacterData | PlotNodeData | WorldRuleData;
    }>
  ): Promise<BaseResponse<{ created: number; failed: number }>> {
    return api.post<BaseResponse<{ created: number; failed: number }>>('/graph/batch/nodes', {
      nodes,
    });
  }

  /**
   * 批量创建关系
   */
  async batchCreateRelationships(
    relationships: Array<{
      type: RelationType;
      source: string;
      target: string;
      properties?: Record<string, any>;
    }>
  ): Promise<BaseResponse<{ created: number; failed: number }>> {
    return api.post<BaseResponse<{ created: number; failed: number }>>(
      '/graph/batch/relationships',
      { relationships }
    );
  }

  /**
   * 图谱自动校验
   */
  async validateGraph(storyId: string): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/juben/quality/graph-validate', { story_id: storyId });
  }

  /**
   * 角色一致性检测
   */
  async checkCharacterConsistency(payload: { project_id: string; script_text?: string; llm_check?: boolean }): Promise<BaseResponse<any>> {
    return api.post<BaseResponse<any>>('/juben/quality/character-consistency', payload);
  }
}

// 导出单例
export const graphService = new GraphService();

export default graphService;

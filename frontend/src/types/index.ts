/**
 * 全局类型定义
 */

// ==================== 聊天相关类型 ====================

export type MessageRole = 'user' | 'assistant' | 'system';

export type MessageStatus = 'sending' | 'streaming' | 'complete' | 'error';

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  timestamp: string;
  agentName?: string;
  agentId?: string;
  status?: MessageStatus;
  metadata?: MessageMetadata;
}

export interface MessageMetadata {
  agent?: string;
  thoughtChain?: Thought[];
  references?: Reference[];
  tokensUsed?: number;
  responseTime?: number;
  model?: string;
  agentId?: string;

  // System and tool events
  systemEvents?: SystemEvent[];
  toolEvents?: ToolEvent[];
  contentType?: StreamContentType | string;
  contentBlocks?: Array<{
    contentType: StreamContentType | string;
    content: string;
    agentSource?: string;
    timestamp?: string;
    metadata?: Record<string, any>;
  }>;
  enhancedEvents?: Array<Record<string, any>>;

  // Error handling
  error?: string;
  canRetry?: boolean;
  retryCount?: number;

  // Billing information
  billing?: string;

  // Other metadata
  originalContent?: string;
}

export interface SystemEvent {
  content: string;
  timestamp?: string;
}

export interface ToolEvent {
  event: string;
  data: ToolEventData;
  timestamp?: string;
}

export interface ToolEventData {
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  status?: 'started' | 'running' | 'completed' | 'failed';
  error?: string;
}

export interface Thought {
  step: number;
  content: string;
  timestamp: string;
}

export interface Reference {
  id: string;
  title: string;
  url?: string;
  source: string;
  snippet?: string;
}

// ==================== Agent 相关类型 ====================

export type AgentStatus = 'active' | 'idle' | 'busy' | 'error';

export type AgentCategory =
  | 'planning'
  | 'creation'
  | 'evaluation'
  | 'analysis'
  | 'workflow'
  | 'utility'
  | 'character'
  | 'story';

export interface Agent {
  id: string;
  name: string;
  displayName: string;
  description: string;
  category: AgentCategory;
  icon: string;
  model: string;
  apiEndpoint: string;
  features: string[];
  capabilities: string[];
  inputExample: string;
  outputExample: string;
  status: 'active' | 'beta' | 'experimental';
}

// ==================== API 相关类型 ====================

export interface ChatRequest {
  input: string;
  user_id?: string;
  session_id?: string;
  project_id?: string;
  model_provider?: string;
  model?: string;
  enable_web_search?: boolean;
  enable_knowledge_base?: boolean;
  agent_id?: string;
}

export interface ChatResponse {
  success: boolean;
  message?: string;
  data?: any;
  error?: string;
}

export interface StreamEvent {
  event: string;
  data: {
    content: string;
    metadata?: Record<string, any>;
    timestamp: string;
  };
}

// ==================== 状态相关类型 ====================

export interface ChatState {
  messages: Message[];
  currentSession: string | null;
  streamingMessage: string | null;
  isStreaming: boolean;
}

export interface AgentState {
  agents: Agent[];
  activeAgent: string;
  searchQuery: string;
  selectedCategory: AgentCategory | 'all';
}

export interface SettingsState {
  theme: 'light' | 'dark';
  model: string;
  streamEnabled: boolean;
  showThoughtChain: boolean;
  fontSize: 'sm' | 'md' | 'lg';
}

export interface UIState {
  sidebarOpen: boolean;
  thoughtChainExpanded: boolean;
  agentListOpen: boolean;
}

// ==================== SSE 事件类型 ====================

export type SSEEventType =
  | 'message'          // 普通消息
  | 'llm_chunk'        // LLM内容块
  | 'system'           // 系统消息
  | 'billing'          // 计费信息
  | 'error'            // 错误
  | 'tool_call'        // 🆕 工具调用开始
  | 'tool_return'      // 🆕 工具调用返回
  | 'tool_processing'  // 工具处理中
  | 'tool_complete'    // 工具完成
  | 'done'             // 完成
  | 'complete'         // 完成（同done）
  | 'thought'          // 思考过程（前端自定义）
  | 'progress'         // 🆕 进度更新
  | 'metadata';        // 元数据

// 🆕 流式内容类型枚举（与后端保持一致）- juben剧本创作专用
export type StreamContentType =
  // 基础类型
  | 'text'
  | 'markdown'
  | 'json'
  // 思考和分析类
  | 'thought'
  | 'plan_step'
  | 'insight'
  // 人物相关
  | 'character_profile'
  | 'character_relationship'
  // 故事结构相关
  | 'story_summary'
  | 'story_outline'
  | 'story_type'
  | 'five_elements'
  | 'series_info'
  | 'series_analysis'
  // 情节相关
  | 'major_plot'
  | 'detailed_plot'
  | 'drama_analysis'
  | 'plot_analysis'
  // 创作相关
  | 'script'
  | 'drama_plan'
  | 'proposal'
  // 可视化
  | 'mind_map'
  // 评估相关
  | 'evaluation'
  | 'script_evaluation'
  | 'story_evaluation'
  | 'outline_evaluation'
  | 'ip_evaluation'
  | 'novel_screening'
  | 'score_analysis'
  // 工具相关
  | 'search_result'
  | 'knowledge_result'
  | 'reference_result'
  | 'document'
  | 'formatted_content'
  // 系统相关
  | 'system_progress'
  | 'tool_result'
  | 'workflow_progress'
  | 'result_integration'
  | 'text_operation'
  | 'batch_progress'
  // 其他
  | 'final_answer'
  | 'error_content';

// 🆕 增强版事件负载结构（与后端保持一致）
export interface EventPayload {
  id?: number;
  content_type?: StreamContentType;
  data: string | EventData;
  metadata?: EventMetadata;
}

export interface EventData {
  content?: string;
  agent?: string;
  thought?: string;
  references?: Reference[];
  tool_name?: string;
  tool_input?: Record<string, unknown>;
  tool_output?: string;
  plan_steps?: string[];
}

export interface EventMetadata {
  tokens_used?: number;
  model?: string;
  provider?: string;
  agent?: string;
  step?: number;
  total_steps?: number;
  processing_time?: number;
  error_code?: string;
}

// 🆕 增强版SSE事件（支持新格式）
export interface EnhancedSSEEvent {
  event_type?: SSEEventType;
  agent_source?: string;
  timestamp: string;
  payload?: EventPayload;

  // 兼容旧格式
  event?: SSEEventType;
  data?: {
    content?: string;
    agent?: string;
    thought?: string;
    references?: Reference[];
    metadata?: EventMetadata;
    error?: string;
    type?: string;
    tool_name?: string;
  };
}

// 保留旧接口以兼容现有代码
export interface SSEEvent {
  event: SSEEventType;
  data: {
    content?: string;
    agent?: string;
    thought?: string;
    references?: Reference[];
    metadata?: EventMetadata;
    error?: string;
    type?: string;
    tool_name?: string;
    content_type?: StreamContentType;
    agent_source?: string;
  };
  timestamp: string;
}

// ==================== 模型相关类型 ====================

export interface ModelInfo {
  name: string;
  display_name: string;
  description: string;
  max_tokens: number;
  thinking_enabled?: boolean;
}

export interface ModelListResponse {
  success: boolean;
  provider: string;
  models: ModelInfo[];
  default_model: string;
  purpose_models: Record<string, string>;
  total_count: number;
}

// ==================== 工具类型 ====================

export type Dict<T = any> = Record<string, T>;

export type Optional<T> = T | null | undefined;

export type PromiseOr<T> = T | Promise<T>;

// ==================== 项目管理相关类型 ====================

export type ProjectStatus = 'active' | 'archived' | 'deleted' | 'completed';

export type FileType =
  | 'conversation'
  | 'drama_planning'
  | 'character_profile'
  | 'script'
  | 'plot_points'
  | 'evaluation'
  | 'note'
  | 'reference'
  | 'export'
  | 'other';

export interface Project {
  id: string;
  name: string;
  description: string;
  user_id: string;
  created_at: string;
  updated_at: string;
  status: ProjectStatus;
  tags: string[];
  metadata: Record<string, any>;
  file_count: number;
}

export interface ProjectFile {
  id: string;
  project_id: string;
  filename: string;
  file_type: FileType;
  agent_source: string | null;
  content: any;
  tags: string[];
  created_at: string;
  updated_at: string;
  file_size: number;
  version: number;
}

export interface ProjectCreateRequest {
  name: string;
  description?: string;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface ProjectUpdateRequest {
  name?: string;
  description?: string;
  status?: ProjectStatus;
  tags?: string[];
  metadata?: Record<string, any>;
}

export interface ProjectSearchRequest {
  query?: string;
  tags?: string[];
  status?: ProjectStatus;
  date_from?: string;
  date_to?: string;
  page?: number;
  page_size?: number;
}

export interface ExportFormat {
  value: 'json' | 'txt' | 'md' | 'pdf';
  label: string;
  icon: string;
}

/**
 * 内容类型渲染组件
 * 根据 StreamContentType 渲染不同样式的内容块
 *
 * 功能:
 * - 根据 content_type 显示不同的图标和样式
 * - 支持折叠/展开
 * - 专业的视觉区分
 */

import { useMemo, useState } from 'react';
import {
  Brain,
  ClipboardList,
  Lightbulb,
  BarChart3,
  PenTool,
  CheckCircle2,
  User,
  Link2,
  BookOpen,
  Film,
  ScrollText,
  Star,
  Settings2,
  Wrench,
  ChevronDown,
  ChevronRight,
} from 'lucide-react';
import StreamingText from './StreamingText';
import { parseMindMap, type MindMapData } from '@/utils/mindMap';
import MindMapViewer from '@/components/mindmap/MindMapViewer';
// 内容类型枚举（与后端保持一致）- juben剧本创作专用
export type StreamContentTypeEnum =
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

interface ContentBlockProps {
  contentType: StreamContentTypeEnum;
  content: string;
  isStreaming?: boolean;
  agentSource?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
}

// 内容类型配置 - juben剧本创作专用
const CONTENT_TYPE_CONFIG: Record<StreamContentTypeEnum, {
  icon: React.ComponentType<{ className?: string }>;
  displayName: string;
  color: string;
  bgColor: string;
  textColor: string;
}> = {
  // 基础类型
  text: {
    icon: Settings2,
    displayName: '文本',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  markdown: {
    icon: BookOpen,
    displayName: 'Markdown',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  json: {
    icon: Settings2,
    displayName: 'JSON数据',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    textColor: 'text-slate-900',
  },

  // 思考和分析类
  thought: {
    icon: Brain,
    displayName: '思考过程',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-900',
  },
  plan_step: {
    icon: ClipboardList,
    displayName: '执行步骤',
    color: 'text-purple-600',
    bgColor: 'bg-purple-50',
    textColor: 'text-purple-900',
  },
  insight: {
    icon: Lightbulb,
    displayName: '洞察分析',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-900',
  },

  // 人物相关
  character_profile: {
    icon: User,
    displayName: '人物画像',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-900',
  },
  character_relationship: {
    icon: Link2,
    displayName: '人物关系',
    color: 'text-pink-600',
    bgColor: 'bg-pink-50',
    textColor: 'text-pink-900',
  },

  // 故事结构相关
  story_summary: {
    icon: BookOpen,
    displayName: '故事梗概',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-900',
  },
  story_outline: {
    icon: BookOpen,
    displayName: '故事大纲',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-900',
  },
  story_type: {
    icon: Settings2,
    displayName: '故事类型',
    color: 'text-stone-600',
    bgColor: 'bg-stone-50',
    textColor: 'text-stone-900',
  },
  five_elements: {
    icon: Settings2,
    displayName: '故事五元素',
    color: 'text-violet-600',
    bgColor: 'bg-violet-50',
    textColor: 'text-violet-900',
  },
  series_info: {
    icon: Settings2,
    displayName: '系列信息',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    textColor: 'text-cyan-900',
  },
  series_analysis: {
    icon: BarChart3,
    displayName: '系列分析',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
    textColor: 'text-teal-900',
  },

  // 情节相关
  major_plot: {
    icon: Film,
    displayName: '大情节点',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },
  detailed_plot: {
    icon: Film,
    displayName: '详细情节点',
    color: 'text-rose-600',
    bgColor: 'bg-rose-50',
    textColor: 'text-rose-900',
  },
  drama_analysis: {
    icon: ScrollText,
    displayName: '戏剧功能分析',
    color: 'text-red-700',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },
  plot_analysis: {
    icon: Film,
    displayName: '情节分析',
    color: 'text-red-800',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },

  // 创作相关
  script: {
    icon: ScrollText,
    displayName: '剧本',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-900',
  },
  drama_plan: {
    icon: PenTool,
    displayName: '剧本策划',
    color: 'text-green-600',
    bgColor: 'bg-green-50',
    textColor: 'text-green-900',
  },
  proposal: {
    icon: PenTool,
    displayName: '内容提案',
    color: 'text-lime-600',
    bgColor: 'bg-lime-50',
    textColor: 'text-lime-900',
  },

  // 可视化
  mind_map: {
    icon: Brain,
    displayName: '思维导图',
    color: 'text-sky-600',
    bgColor: 'bg-sky-50',
    textColor: 'text-sky-900',
  },

  // 评估相关
  evaluation: {
    icon: Star,
    displayName: '综合评估',
    color: 'text-orange-600',
    bgColor: 'bg-orange-50',
    textColor: 'text-orange-900',
  },
  script_evaluation: {
    icon: Star,
    displayName: '剧本评估',
    color: 'text-amber-600',
    bgColor: 'bg-amber-50',
    textColor: 'text-amber-900',
  },
  story_evaluation: {
    icon: Star,
    displayName: '故事评估',
    color: 'text-yellow-600',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-900',
  },
  outline_evaluation: {
    icon: Star,
    displayName: '大纲评估',
    color: 'text-yellow-700',
    bgColor: 'bg-yellow-50',
    textColor: 'text-yellow-900',
  },
  ip_evaluation: {
    icon: Star,
    displayName: 'IP评估',
    color: 'text-fuchsia-600',
    bgColor: 'bg-fuchsia-50',
    textColor: 'text-fuchsia-900',
  },
  novel_screening: {
    icon: Star,
    displayName: '小说筛选',
    color: 'text-violet-600',
    bgColor: 'bg-violet-50',
    textColor: 'text-violet-900',
  },
  score_analysis: {
    icon: BarChart3,
    displayName: '评分分析',
    color: 'text-indigo-600',
    bgColor: 'bg-indigo-50',
    textColor: 'text-indigo-900',
  },

  // 工具相关
  search_result: {
    icon: Wrench,
    displayName: '搜索结果',
    color: 'text-blue-600',
    bgColor: 'bg-blue-50',
    textColor: 'text-blue-900',
  },
  knowledge_result: {
    icon: BookOpen,
    displayName: '知识库结果',
    color: 'text-cyan-600',
    bgColor: 'bg-cyan-50',
    textColor: 'text-cyan-900',
  },
  reference_result: {
    icon: BookOpen,
    displayName: '参考文献',
    color: 'text-teal-600',
    bgColor: 'bg-teal-50',
    textColor: 'text-teal-900',
  },
  document: {
    icon: Settings2,
    displayName: '文档生成',
    color: 'text-stone-600',
    bgColor: 'bg-stone-50',
    textColor: 'text-stone-900',
  },
  formatted_content: {
    icon: Settings2,
    displayName: '格式化输出',
    color: 'text-zinc-600',
    bgColor: 'bg-zinc-50',
    textColor: 'text-zinc-900',
  },

  // 系统相关
  system_progress: {
    icon: Settings2,
    displayName: '系统进度',
    color: 'text-gray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  tool_result: {
    icon: Wrench,
    displayName: '工具结果',
    color: 'text-slate-600',
    bgColor: 'bg-slate-50',
    textColor: 'text-slate-900',
  },
  workflow_progress: {
    icon: Settings2,
    displayName: '工作流进度',
    color: 'text-coolGray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },
  result_integration: {
    icon: Settings2,
    displayName: '结果整合',
    color: 'text-neutral-600',
    bgColor: 'bg-neutral-50',
    textColor: 'text-neutral-900',
  },
  text_operation: {
    icon: Settings2,
    displayName: '文本操作',
    color: 'text-zinc-600',
    bgColor: 'bg-zinc-50',
    textColor: 'text-zinc-900',
  },
  batch_progress: {
    icon: Settings2,
    displayName: '批处理进度',
    color: 'text-warmGray-600',
    bgColor: 'bg-gray-50',
    textColor: 'text-gray-900',
  },

  // 其他
  final_answer: {
    icon: CheckCircle2,
    displayName: '最终答案',
    color: 'text-emerald-600',
    bgColor: 'bg-emerald-50',
    textColor: 'text-emerald-900',
  },
  error_content: {
    icon: Wrench,
    displayName: '错误',
    color: 'text-red-600',
    bgColor: 'bg-red-50',
    textColor: 'text-red-900',
  },
};

export default function ContentTypeRenderer({
  contentType,
  content,
  isStreaming = false,
  agentSource,
  timestamp,
  metadata = {},
}: ContentBlockProps) {
  const [expanded, setExpanded] = useState(true);
  const config = CONTENT_TYPE_CONFIG[contentType] || CONTENT_TYPE_CONFIG.text;
  const Icon = config.icon;
  const mindMapData = useMemo<MindMapData | null>(() => {
    if (contentType !== 'mind_map') return null;
    const fromMeta = metadata?.mindMapData;
    return parseMindMap(fromMeta || content);
  }, [contentType, metadata, content]);

  // 判断是否可折叠（长内容或特定类型）
  const isCollapsible = content.length > 200 || [
    // 思考和分析类通常较长
    'thought',
    'plan_step',
    'insight',
    // 故事结构分析
    'story_summary',
    'story_outline',
    'five_elements',
    'series_analysis',
    // 情节分析
    'major_plot',
    'detailed_plot',
    'drama_analysis',
    'plot_analysis',
    // 剧本和策划
    'script',
    'drama_plan',
    // 评估类通常包含详细内容
    'evaluation',
    'script_evaluation',
    'story_evaluation',
    'outline_evaluation',
    'ip_evaluation',
    'novel_screening',
    'score_analysis',
    // 工具结果
    'search_result',
    'knowledge_result',
    'reference_result',
    'document',
  ].includes(contentType);

  return (
    <div
      className={`mb-3 rounded-lg border transition-all duration-300 ${
        isStreaming ? 'shadow-sm animate-fade-in' : 'shadow-sm'
      } ${config.bgColor} ${config.color}`}
    >
      {/* 头部 */}
      <div
        className={`flex items-center justify-between px-4 py-2.5 border-b ${config.color} border-opacity-20`}
        onClick={() => isCollapsible && setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2.5">
          {/* 图标 */}
          <div className={`p-1.5 rounded-lg ${config.bgColor} ${config.color}`}>
            <Icon className="w-4 h-4" />
          </div>

          {/* 类型名称 */}
          <span className={`text-sm font-semibold ${config.textColor}`}>
            {config.displayName}
          </span>

          {/* Agent来源 */}
          {agentSource && (
            <span className="text-xs text-gray-500 bg-white px-2 py-0.5 rounded-full">
              {agentSource}
            </span>
          )}

          {/* 流式状态 */}
          {isStreaming && (
            <div className="flex items-center gap-1.5 text-xs text-gray-500">
              <div className="w-1.5 h-1.5 bg-current rounded-full animate-pulse" />
              <span>生成中</span>
            </div>
          )}
        </div>

        {/* 折叠按钮 */}
        {isCollapsible && (
          <button className="p-1 hover:bg-white hover:bg-opacity-50 rounded transition-colors">
            {expanded ? (
              <ChevronDown className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        )}
      </div>

      {/* 内容 */}
      {expanded && (
        <div className="p-4">
          {contentType === 'mind_map' && mindMapData ? (
            <div className="space-y-3">
              <div className="text-base font-semibold text-gray-900">{mindMapData.title}</div>
              <MindMapViewer data={mindMapData} agentSource={agentSource} />
            </div>
          ) : (
            <div className={`prose prose-sm max-w-none ${config.textColor}`}>
              <StreamingText
                content={content}
                isStreaming={isStreaming}
                enableBuffer={true}
              />
            </div>
          )}

          {/* 元数据 */}
          {Object.keys(metadata).length > 0 && (
            <div className="mt-3 pt-3 border-t border-gray-200 border-opacity-30">
              <details className="text-xs">
                <summary className="cursor-pointer text-gray-600 hover:text-gray-900">
                  查看元数据
                </summary>
                <pre className="mt-2 p-2 bg-white bg-opacity-50 rounded overflow-x-auto">
                  {JSON.stringify(metadata, null, 2)}
                </pre>
              </details>
            </div>
          )}

          {/* 时间戳 */}
          {timestamp && (
            <div className="mt-2 text-xs text-gray-500 text-right">
              {new Date(timestamp).toLocaleString('zh-CN')}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/**
 * 内容块列表组件
 * 用于渲染多个连续的内容块
 */
interface ContentBlockListProps {
  blocks: Array<{
    contentType: StreamContentTypeEnum;
    content: string;
    agentSource?: string;
    timestamp?: string;
    metadata?: Record<string, any>;
  }>;
  isStreaming?: boolean;
}

export function ContentBlockList({ blocks, isStreaming = false }: ContentBlockListProps) {
  if (!blocks || blocks.length === 0) {
    return null;
  }

  return (
    <div className="space-y-3">
      {blocks.map((block, index) => (
        <ContentTypeRenderer
          key={index}
          contentType={block.contentType}
          content={block.content}
          isStreaming={isStreaming && index === blocks.length - 1}
          agentSource={block.agentSource}
          timestamp={block.timestamp}
          metadata={block.metadata}
        />
      ))}
    </div>
  );
}

/**
 * 解析后端事件为内容块
 */
export function parseEventToContentBlock(event: any): {
  contentType: StreamContentTypeEnum;
  content: string;
  agentSource?: string;
  timestamp?: string;
  metadata?: Record<string, any>;
} | null {
  try {
    // 兼容多种事件格式
    const contentType = event.payload?.content_type || event.content_type || 'text';
    const content = event.payload?.data || event.content || '';
    const agentSource = event.agent_source || event.agentSource;
    const timestamp = event.timestamp;
    const metadata = event.payload?.metadata || event.metadata || {};

    return {
      contentType,
      content,
      agentSource,
      timestamp,
      metadata,
    };
  } catch (error) {
    console.error('Failed to parse event:', error);
    return null;
  }
}

/**
 * 工具执行显示组件
 * 显示 Agent 调用工具的过程和结果
 */

import { Wrench, CheckCircle, XCircle, Loader2, ExternalLink, Image as ImageIcon } from 'lucide-react';

export interface ToolCall {
  tool_name: string;
  parameters: Record<string, any>;
  result?: {
    log_id: string;
    msg: string;
    code: number;
    data: any;
  };
  error?: string;
  timestamp?: string;
}

interface ToolExecutionDisplayProps {
  toolCalls: ToolCall[];
  isExecuting?: boolean;
}

export default function ToolExecutionDisplay({ toolCalls, isExecuting }: ToolExecutionDisplayProps) {
  if (toolCalls.length === 0 && !isExecuting) {
    return null;
  }

  return (
    <div className="space-y-3">
      <div className="flex items-center gap-2 text-xs text-gray-500">
        <Wrench className="w-4 h-4" />
        <span>工具调用记录</span>
      </div>

      <div className="space-y-2">
        {toolCalls.map((call, index) => (
          <ToolCallCard key={index} call={call} />
        ))}

        {isExecuting && (
          <div className="flex items-center gap-3 px-4 py-3 bg-blue-50 border border-blue-200 rounded-lg">
            <Loader2 className="w-5 h-5 text-blue-600 animate-spin" />
            <div className="flex-1">
              <p className="text-sm font-medium text-blue-900">正在执行工具...</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * 单个工具调用卡片
 */
interface ToolCallCardProps {
  call: ToolCall;
}

function ToolCallCard({ call }: ToolCallCardProps) {
  const isSuccess = call.result?.code === 0;
  const isError = call.error || call.result?.code !== 0;

  // 获取工具图标
  const getToolIcon = (toolName: string) => {
    switch (toolName) {
      case 'search_url':
        return '🔍';
      case 'baike_search':
        return '📚';
      case 'knowledge_base':
        return '💾';
      default:
        return '🔧';
    }
  };

  // 获取工具名称显示
  const getToolDisplayName = (toolName: string) => {
    switch (toolName) {
      case 'search_url':
        return '网页搜索';
      case 'baike_search':
        return '百度百科';
      case 'knowledge_base':
        return '知识库查询';
      default:
        return toolName;
    }
  };

  return (
    <div className="border border-gray-200 rounded-lg overflow-hidden">
      {/* 工具调用头部 */}
      <div className={`flex items-center gap-3 px-4 py-3 ${
        isSuccess ? 'bg-green-50' : isError ? 'bg-red-50' : 'bg-gray-50'
      }`}>
        {/* 工具图标 */}
        <span className="text-xl">{getToolIcon(call.tool_name)}</span>

        {/* 工具名称和状态 */}
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium text-gray-900">
              {getToolDisplayName(call.tool_name)}
            </span>
            {isSuccess && (
              <CheckCircle className="w-4 h-4 text-green-600" />
            )}
            {isError && (
              <XCircle className="w-4 h-4 text-red-600" />
            )}
          </div>

          {/* 参数显示 */}
          {Object.keys(call.parameters).length > 0 && (
            <div className="text-xs text-gray-500 mt-1">
              {Object.entries(call.parameters).map(([key, value]) => (
                <span key={key} className="mr-3">
                  <span className="font-medium">{key}:</span> {JSON.stringify(value)}
                </span>
              ))}
            </div>
          )}
        </div>

        {/* 时间戳 */}
        {call.timestamp && (
          <span className="text-xs text-gray-400">
            {new Date(call.timestamp).toLocaleTimeString()}
          </span>
        )}
      </div>

      {/* 搜索结果 */}
      {isSuccess && call.result?.data && Array.isArray(call.result.data) && (
        <SearchResultsList results={call.result.data} />
      )}

      {/* 百科结果 */}
      {isSuccess && call.result?.data?.baike && (
        <BaikeResult data={call.result.data} />
      )}

      {/* 错误信息 */}
      {isError && (
        <div className="px-4 py-3 bg-red-50 text-sm text-red-700">
          {call.error || call.result?.msg || '执行失败'}
        </div>
      )}
    </div>
  );
}

/**
 * 搜索结果列表
 */
interface SearchResultsListProps {
  results: Array<{
    title: string;
    url: string;
    image_url: string;
    sitename: string;
    summary: string;
    has_image: boolean;
  }>;
}

function SearchResultsList({ results }: SearchResultsListProps) {
  if (results.length === 0) {
    return (
      <div className="px-4 py-3 text-sm text-gray-500">
        未找到搜索结果
      </div>
    );
  }

  return (
    <div className="px-4 py-3 space-y-3">
      <div className="text-xs text-gray-500">
        找到 {results.length} 条结果
      </div>
      <div className="space-y-3">
        {results.slice(0, 3).map((result, index) => (
          <div
            key={index}
            className="flex gap-3 p-3 bg-white rounded border border-gray-200 hover:shadow-sm transition-shadow"
          >
            {/* 图片 */}
            {result.has_image && result.image_url && (
              <img
                src={result.image_url}
                alt={result.title}
                className="w-20 h-14 object-cover rounded flex-shrink-0"
              />
            )}

            {/* 内容 */}
            <div className="flex-1 min-w-0">
              <a
                href={result.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm font-medium text-blue-600 hover:underline line-clamp-1 flex items-center gap-1"
              >
                {result.title}
                <ExternalLink className="w-3 h-3 flex-shrink-0" />
              </a>
              <p className="text-xs text-gray-500 mt-1 line-clamp-2">
                {result.summary}
              </p>
              <p className="text-xs text-gray-400 mt-1">{result.sitename}</p>
            </div>
          </div>
        ))}

        {results.length > 3 && (
          <div className="text-center text-xs text-gray-500">
            还有 {results.length - 3} 条结果...
          </div>
        )}
      </div>
    </div>
  );
}

/**
 * 百科结果
 */
interface BaikeResultProps {
  data: {
    baike: any;
    videos: any[];
  };
}

function BaikeResult({ data }: BaikeResultProps) {
  if (!data.baike && (!data.videos || data.videos.length === 0)) {
    return null;
  }

  return (
    <div className="px-4 py-3 space-y-3">
      {/* 百科内容 */}
      {data.baike && (
        <div>
          <div className="text-xs text-gray-500 mb-2">百科内容</div>
          <div className="p-3 bg-white rounded border border-gray-200">
            <h4 className="text-sm font-medium text-gray-900 mb-1">
              {data.baike.lemma_title}
            </h4>
            <p className="text-xs text-gray-600 line-clamp-2">
              {data.baike.lemma_desc}
            </p>
          </div>
        </div>
      )}

      {/* 视频内容 */}
      {data.videos && data.videos.length > 0 && (
        <div>
          <div className="text-xs text-gray-500 mb-2">相关视频</div>
          <div className="text-xs text-gray-600">
            找到 {data.videos.length} 个相关视频
          </div>
        </div>
      )}
    </div>
  );
}

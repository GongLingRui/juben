/**
 * 工具调用演示页面
 * 展示 Agent 如何调用外部工具
 */

import { useEffect, useState } from 'react';
import { Search, BookOpen, Loader2, Wrench, History } from 'lucide-react';
import { useUIStore } from '@/store/uiStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import { ToolExecutionDisplay } from '@/components/tools';
import toolService, { ToolExecuteResult } from '@/services/toolService';

type ToolType = 'search' | 'baike';

export default function ToolsDemoPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const [activeTool, setActiveTool] = useState<ToolType>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [results, setResults] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('tools_demo_history');
      const lastQuery = localStorage.getItem('tools_demo_query');
      if (raw) setHistory(JSON.parse(raw));
      if (lastQuery) setSearchQuery(lastQuery);
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('tools_demo_history', JSON.stringify(history.slice(0, 20)));
  }, [history]);

  useEffect(() => {
    if (searchQuery) localStorage.setItem('tools_demo_query', searchQuery);
  }, [searchQuery]);

  // 工具配置
  const tools = [
    {
      id: 'search' as ToolType,
      name: '网页搜索工具',
      icon: Search,
      description: '搜索互联网并返回相关网页结果',
      placeholder: '输入关键词搜索...',
      example: '去有风的地方'
    },
    {
      id: 'baike' as ToolType,
      name: '百度百科工具',
      icon: BookOpen,
      description: '搜索百度百科，获取词条详细解释',
      placeholder: '输入词条名称...',
      example: '刘德华'
    }
  ];

  // 执行工具
  const handleExecute = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setResults(null);
    setErrorMessage('');

    try {
      let result: ToolExecuteResult;

      if (activeTool === 'search') {
        result = await toolService.executeTool({
          tool_name: 'search_url',
          parameters: {
            query: searchQuery,
            max_results: 5
          }
        });
      } else {
        result = await toolService.executeTool({
          tool_name: 'baike_search',
          parameters: {
            query: searchQuery,
            include_videos: true
          }
        });
      }

      setResults(result);

      // 添加到历史
      setHistory(prev => [{
        tool_name: activeTool === 'search' ? 'search_url' : 'baike_search',
        parameters: { query: searchQuery },
        result: result,
        timestamp: new Date().toISOString(),
        success: result.success
      } as any, ...prev].slice(0, 10));

    } catch (error) {
      console.error('工具执行失败:', error);
      setErrorMessage('执行失败，请稍后重试');
      setResults({
        success: false,
        tool_name: activeTool === 'search' ? 'search_url' : 'baike_search',
        error: '执行失败，请稍后重试'
      });
    } finally {
      setLoading(false);
    }
  };

  // 加载示例
  const loadExample = (example: string) => {
    setSearchQuery(example);
  };

  // 快速搜索（便捷接口）
  const handleQuickSearch = async (query: string) => {
    setSearchQuery(query);
    setLoading(true);
    setErrorMessage('');

    try {
      const response = await toolService.quickSearch(query, 5);

      setResults({
        success: true,
        tool_name: 'search_url',
        result: {
          log_id: 'quick_' + Date.now(),
          msg: 'success',
          code: 0,
          data: response.results
        }
      });

      setHistory(prev => [{
        tool_name: 'search_url',
        parameters: { query },
        result: response,
        timestamp: new Date().toISOString()
      }, ...prev].slice(0, 10));

    } catch (error) {
      console.error('快速搜索失败:', error);
      setErrorMessage('快速搜索失败');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex h-screen bg-white">
      {/* 移动端菜单 */}
      <MobileMenu />

      {/* 侧边栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          !sidebarOpen ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-80'
        }`}
      >
        {/* 顶部导航 */}
        <Header />

        {/* 状态栏 */}
        <StatusBar />

        {/* 页面内容 */}
        <div className="flex flex-col flex-1 overflow-hidden">
        {/* 页面标题 */}
        <div className="border-b border-gray-200 bg-white">
          <div className="max-w-6xl mx-auto px-6 py-4">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 bg-black rounded-lg flex items-center justify-center">
                <Wrench className="w-5 h-5 text-white" />
              </div>
              <div>
                <h1 className="text-xl font-bold text-gray-900">工具调用演示</h1>
                <p className="text-xs text-gray-500 mt-1">
                  展示 Agent 如何调用外部工具获取信息
                </p>
              </div>
            </div>
          </div>

          {/* 工具切换 */}
          <div className="max-w-6xl mx-auto px-6 mt-4">
            <div className="flex gap-2">
              {tools.map((tool) => {
                const Icon = tool.icon;
                return (
                  <button
                    key={tool.id}
                    onClick={() => {
                      setActiveTool(tool.id);
                      setResults(null);
                      setSearchQuery('');
                    }}
                    className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all ${
                      activeTool === tool.id
                        ? 'bg-black text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {tool.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 主内容 */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto px-6 py-6">
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* 左侧：工具控制 */}
              <div className="lg:col-span-1 space-y-4">
                {/* 工具说明 */}
                <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                  <h3 className="text-sm font-medium text-gray-900 mb-2">
                    {tools.find(t => t.id === activeTool)?.name}
                  </h3>
                  <p className="text-xs text-gray-600 mb-3">
                    {tools.find(t => t.id === activeTool)?.description}
                  </p>

                  {/* 示例 */}
                  <div className="space-y-2">
                    <div className="text-xs text-gray-500">试试这些示例：</div>
                    {tools.map((tool) => (
                      <button
                        key={tool.id}
                        onClick={() => loadExample(tool.example)}
                        className={`w-full text-left px-3 py-2 text-xs bg-white rounded border border-gray-200 hover:border-black transition-colors ${
                          activeTool === tool.id ? 'block' : 'hidden'
                        }`}
                      >
                        "{tool.example}"
                      </button>
                    ))}
                  </div>
                </div>

                {/* 搜索框 */}
                <div className="space-y-3">
                  <input
                    type="text"
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleExecute()}
                    placeholder={tools.find(t => t.id === activeTool)?.placeholder}
                    className="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                    disabled={loading}
                  />
                  <button
                    onClick={handleExecute}
                    disabled={loading || !searchQuery.trim()}
                    className="w-full px-4 py-3 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center justify-center gap-2 text-sm font-medium"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="w-4 h-4 animate-spin" />
                        执行中...
                      </>
                    ) : (
                      <>
                        <Wrench className="w-4 h-4" />
                        执行工具
                      </>
                    )}
                  </button>
                </div>

                {/* 执行历史 */}
                {history.length > 0 && (
                  <div className="p-4 bg-gray-50 rounded-lg border border-gray-200">
                    <div className="flex items-center gap-2 text-xs text-gray-500 mb-3">
                      <History className="w-3 h-3" />
                      <span>执行历史</span>
                    </div>
                    <div className="space-y-2 max-h-48 overflow-y-auto">
                      {history.map((item, index) => (
                        <div
                          key={index}
                          onClick={() => {
                            setSearchQuery(item.parameters.query);
                            setResults(item.result);
                          }}
                          className="px-3 py-2 bg-white rounded border border-gray-200 hover:border-black cursor-pointer transition-colors"
                        >
                          <div className="text-xs text-gray-600 truncate">
                            {item.parameters.query}
                          </div>
                          <div className="text-xs text-gray-400 mt-1">
                            {new Date(item.timestamp).toLocaleTimeString()}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* 右侧：结果显示 */}
              <div className="lg:col-span-2">
                {errorMessage && (
                  <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded border border-red-100">
                    {errorMessage}
                  </div>
                )}
                {results && (
                  <ToolExecutionDisplay
                    toolCalls={[
                      {
                        tool_name: results.tool_name,
                        parameters: { query: searchQuery },
                        result: results.result,
                        error: results.error
                      }
                    ]}
                    isExecuting={false}
                  />
                )}

                {!results && !loading && (
                  <div className="flex flex-col items-center justify-center h-full text-center py-16">
                    <div className="w-16 h-16 bg-gray-100 rounded-full flex items-center justify-center mb-4">
                      <Wrench className="w-8 h-8 text-gray-400" />
                    </div>
                    <h3 className="text-lg font-medium text-gray-900 mb-2">工具调用演示</h3>
                    <p className="text-sm text-gray-500 max-w-md">
                      在左侧选择工具并输入关键词，查看 Agent 如何调用外部工具获取信息
                    </p>
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
        </div>
      </div>

      {/* 设置弹窗 */}
      <SettingsModal />
    </div>
  );
}

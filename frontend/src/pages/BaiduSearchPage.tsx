/**
 * 百度搜索页面
 * 集成百度搜索、百科词条、百度百科、秒懂百科四个服务
 */

import { useEffect, useState } from 'react';
import { Search, BookOpen, Video, Globe, Loader2 } from 'lucide-react';
import { useUIStore } from '@/store/uiStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import { BaiduSearchResult, BaiduBaikeContent, BaiduVideoList } from '@/components/baidu';
import baiduService, {
  WebSearchParams,
  LemmaContentParams,
  SecondKnowParams,
  ComprehensiveParams
} from '@/services/baiduService';

type TabType = 'search' | 'baike' | 'video' | 'comprehensive';

export default function BaiduSearchPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const [activeTab, setActiveTab] = useState<TabType>('search');
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(false);

  // 搜索结果状态
  const [searchResults, setSearchResults] = useState<any[]>([]);
  const [baikeContent, setBaikeContent] = useState<any>(null);
  const [videos, setVideos] = useState<any[]>([]);
  const [history, setHistory] = useState<any[]>([]);
  const [errorMessage, setErrorMessage] = useState('');

  useEffect(() => {
    try {
      const raw = localStorage.getItem('baidu_search_history');
      if (raw) setHistory(JSON.parse(raw));
    } catch {
      setHistory([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('baidu_search_history', JSON.stringify(history.slice(0, 20)));
  }, [history]);

  // 标签页配置
  const tabs = [
    { id: 'search' as TabType, name: '百度搜索', icon: Search },
    { id: 'baike' as TabType, name: '百度百科', icon: BookOpen },
    { id: 'video' as TabType, name: '秒懂百科', icon: Video },
    { id: 'comprehensive' as TabType, name: '组合查询', icon: Globe },
  ];

  // 执行搜索
  const handleSearch = async () => {
    if (!searchQuery.trim()) return;

    setLoading(true);
    setErrorMessage('');
    try {
      switch (activeTab) {
        case 'search':
          await handleWebSearch();
          break;
        case 'baike':
          await handleBaikeContent();
          break;
        case 'video':
          await handleVideoSearch();
          break;
        case 'comprehensive':
          await handleComprehensiveSearch();
          break;
      }
      setHistory((prev) => [
        { query: searchQuery.trim(), tab: activeTab, timestamp: new Date().toISOString() },
        ...prev,
      ].slice(0, 20));
    } catch (error) {
      console.error('搜索失败:', error);
      setErrorMessage('搜索失败，请稍后重试');
    } finally {
      setLoading(false);
    }
  };

  // 百度搜索
  const handleWebSearch = async () => {
    const params: WebSearchParams = {
      query: searchQuery,
      top_k: 10,
      search_recency_filter: 'month'
    };
    const response = await baiduService.webSearch(params);
    setSearchResults(response.data || []);
  };

  // 百度百科
  const handleBaikeContent = async () => {
    const params: LemmaContentParams = {
      search_key: searchQuery,
      search_type: 'lemmaTitle'
    };
    const response = await baiduService.getLemmaContent(params);
    setBaikeContent(response.data || null);
  };

  // 秒懂百科视频
  const handleVideoSearch = async () => {
    const params: SecondKnowParams = {
      search_key: searchQuery,
      search_type: 'lemmaTitle',
      limit: 6
    };
    const response = await baiduService.searchSecondKnow(params);
    setVideos(response.data || []);
  };

  // 组合查询
  const handleComprehensiveSearch = async () => {
    const params: ComprehensiveParams = {
      keyword: searchQuery,
      max_videos: 3
    };
    const response = await baiduService.comprehensiveSearch(params);

    if (response.data) {
      setBaikeContent(response.data.baike || null);
      setVideos(response.data.videos || []);
    }
  };

  // 按回车搜索
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
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
            <h1 className="text-xl font-bold text-gray-900">百度搜索</h1>
            <p className="text-xs text-gray-500 mt-1">
              集成百度搜索、百科词条、百度百科、秒懂百科四大服务
            </p>
          </div>

          {/* 标签页切换 */}
          <div className="max-w-6xl mx-auto px-6">
            <div className="flex gap-1 border-b border-gray-200">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => {
                      setActiveTab(tab.id);
                      setSearchQuery('');
                      setSearchResults([]);
                      setBaikeContent(null);
                      setVideos([]);
                    }}
                    className={`flex items-center gap-2 px-4 py-2.5 text-sm font-medium border-b-2 transition-colors ${
                      activeTab === tab.id
                        ? 'border-black text-black'
                        : 'border-transparent text-gray-500 hover:text-gray-700'
                    }`}
                  >
                    <Icon className="w-4 h-4" />
                    {tab.name}
                  </button>
                );
              })}
            </div>
          </div>
        </div>

        {/* 搜索框 */}
        <div className="border-b border-gray-100 bg-gray-50">
          <div className="max-w-3xl mx-auto px-6 py-4">
            <div className="flex gap-3">
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={
                  activeTab === 'search'
                    ? '搜索全网信息...'
                    : activeTab === 'baike'
                    ? '搜索百科词条...'
                    : activeTab === 'video'
                    ? '搜索百科视频...'
                    : '组合查询...'
                }
                className="flex-1 px-4 py-2.5 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-black focus:border-transparent text-sm"
                disabled={loading}
              />
              <button
                onClick={handleSearch}
                disabled={loading || !searchQuery.trim()}
                className="px-5 py-2.5 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors disabled:bg-gray-300 disabled:cursor-not-allowed flex items-center gap-2 text-sm font-medium"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    搜索中...
                  </>
                ) : (
                  <>
                    <Search className="w-4 h-4" />
                    搜索
                  </>
                )}
              </button>
            </div>

            {/* 搜索提示 */}
            {activeTab === 'search' && (
              <div className="mt-2 flex items-center gap-3 text-xs text-gray-500">
                <span>每日免费额度: 100 次</span>
                <span>•</span>
                <span>支持时间过滤: 最近7天/30天/180天/365天</span>
              </div>
            )}
          </div>
        </div>

        {history.length > 0 && (
          <div className="border-b border-gray-100 bg-white">
            <div className="max-w-3xl mx-auto px-6 py-3">
              <div className="text-xs text-gray-500 mb-2">最近搜索</div>
              <div className="flex flex-wrap gap-2">
                {history.slice(0, 6).map((item, idx) => (
                  <button
                    key={`${item.query}-${idx}`}
                    onClick={() => {
                      setSearchQuery(item.query);
                      setActiveTab(item.tab as TabType);
                    }}
                    className="px-2 py-1 text-xs bg-gray-100 rounded hover:bg-gray-200"
                  >
                    {item.query}
                  </button>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* 结果展示区 */}
        <div className="flex-1 overflow-y-auto">
          <div className="max-w-6xl mx-auto px-6 py-4">
            {errorMessage && (
              <div className="mb-4 p-3 bg-red-50 text-red-700 text-sm rounded border border-red-100">
                {errorMessage}
              </div>
            )}
            {loading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
              </div>
            ) : (
              <>
                {/* 百度搜索结果 */}
                {activeTab === 'search' && (
                  <>
                    {searchResults.length > 0 && (
                      <div className="mb-3 text-sm text-gray-500">
                        找到 {searchResults.length} 条结果
                      </div>
                    )}
                    <BaiduSearchResult results={searchResults} />
                  </>
                )}

                {/* 百科内容 */}
                {activeTab === 'baike' && (
                  <BaiduBaikeContent content={baikeContent} loading={loading} />
                )}

                {/* 视频列表 */}
                {activeTab === 'video' && (
                  <>
                    {videos.length > 0 && (
                      <div className="mb-3 text-sm text-gray-500">
                        找到 {videos.length} 个视频
                      </div>
                    )}
                    <BaiduVideoList videos={videos} loading={loading} />
                  </>
                )}

                {/* 组合查询 */}
                {activeTab === 'comprehensive' && (
                  <div className="space-y-6">
                    {/* 百科部分 */}
                    {baikeContent && (
                      <div>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">百科内容</h2>
                        <BaiduBaikeContent content={baikeContent} />
                      </div>
                    )}

                    {/* 视频部分 */}
                    {videos.length > 0 && (
                      <div>
                        <h2 className="text-base font-semibold text-gray-900 mb-3">相关视频</h2>
                        <BaiduVideoList videos={videos} />
                      </div>
                    )}

                    {!baikeContent && videos.length === 0 && (
                      <div className="text-center py-12 text-gray-500 text-sm">
                        请输入关键词进行组合查询
                      </div>
                    )}
                  </div>
                )}

                {/* 空状态 */}
                {!loading && searchResults.length === 0 && !baikeContent && videos.length === 0 && (
                  <div className="flex flex-col items-center justify-center py-16 text-center">
                    <div className="w-14 h-14 bg-gray-100 rounded-full flex items-center justify-center mb-3">
                      <Search className="w-7 h-7 text-gray-400" />
                    </div>
                    <h3 className="text-base font-medium text-gray-900 mb-2">开始搜索</h3>
                    <p className="text-sm text-gray-500 max-w-md">
                      输入关键词，探索百度搜索、百科、视频等丰富内容
                    </p>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
        </div>
      </div>

      {/* 设置弹窗 */}
      <SettingsModal />
    </div>
  );
}

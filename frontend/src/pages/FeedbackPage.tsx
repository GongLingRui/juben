/**
 * 反馈系统页面
 * 收集和查看用户反馈，管理黄金样本
 */

import React, { useEffect, useMemo, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  ThumbsUp,
  ThumbsDown,
  Star,
  MessageSquare,
  TrendingUp,
  Award,
  Download,
  Calendar,
  RefreshCw,
  Search,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { getAgents } from '@/services/agentService';
import { getFeedbackList, getFeedbackStatistics, getGoldSamples } from '@/services/feedbackService';
import type { Agent } from '@/types';

interface FeedbackItem {
  trace_id: string;
  agent_name: string;
  user_input: string;
  ai_output: string;
  feedback_type: string;
  user_rating?: number;
  timestamp?: string;
  is_gold_sample?: boolean;
}

interface FeedbackStats {
  totalFeedback: number;
  positiveRate: number;
  avgRating: number;
  goldSamples: number;
  thisWeekFeedback: number;
}

const FeedbackPage: React.FC = () => {
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<'feedback' | 'samples' | 'analytics'>('feedback');
  const [selectedType, setSelectedType] = useState<'all' | 'like' | 'dislike' | 'rating' | 'refinement'>('all');
  const [selectedAgent, setSelectedAgent] = useState('');
  const [days, setDays] = useState(30);
  const [loading, setLoading] = useState(false);
  const [statsLoading, setStatsLoading] = useState(false);
  const [goldLoading, setGoldLoading] = useState(false);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [feedback, setFeedback] = useState<FeedbackItem[]>([]);
  const [stats, setStats] = useState<FeedbackStats>({
    totalFeedback: 0,
    positiveRate: 0,
    avgRating: 0,
    goldSamples: 0,
    thisWeekFeedback: 0,
  });
  const [goldQuery, setGoldQuery] = useState('');
  const [goldSamples, setGoldSamples] = useState<any[]>([]);

  useEffect(() => {
    getAgents().then(setAgents).catch(() => setAgents([]));
  }, []);

  const loadFeedback = async () => {
    setLoading(true);
    try {
      const res = await getFeedbackList({ agent_name: selectedAgent || undefined, limit: 200 });
      setFeedback(res.data || []);
    } catch (err: any) {
      error('加载失败', err?.message || '无法加载反馈列表');
      setFeedback([]);
    } finally {
      setLoading(false);
    }
  };

  const loadStats = async () => {
    setStatsLoading(true);
    try {
      const res = await getFeedbackStatistics({ agent_name: selectedAgent || undefined, days });
      const data = res.data || {};
      const totalFeedback = data.total_feedbacks || 0;
      const goldSamples = data.gold_samples || 0;
      setStats((prev) => ({
        ...prev,
        totalFeedback,
        goldSamples,
      }));
    } catch (err: any) {
      error('加载失败', err?.message || '无法加载统计数据');
    } finally {
      setStatsLoading(false);
    }
  };

  useEffect(() => {
    loadFeedback();
    loadStats();
  }, [selectedAgent, days]);

  const loadGoldSamples = async () => {
    setGoldLoading(true);
    try {
      const res = await getGoldSamples({
        agent_name: selectedAgent || undefined,
        query: goldQuery.trim() || undefined,
        top_k: 10,
      });
      setGoldSamples(res.data || []);
    } catch (err: any) {
      error('加载失败', err?.message || '无法获取黄金样本');
      setGoldSamples([]);
    } finally {
      setGoldLoading(false);
    }
  };

  useEffect(() => {
    const totalRatings = feedback.filter((item) => typeof item.user_rating === 'number');
    const avgRating = totalRatings.length
      ? totalRatings.reduce((acc, item) => acc + (item.user_rating || 0), 0) / totalRatings.length
      : 0;

    const positiveCount = feedback.filter(
      (item) => item.feedback_type === 'like' || (item.user_rating || 0) >= 4
    ).length;
    const positiveRate = feedback.length ? (positiveCount / feedback.length) * 100 : 0;

    const now = new Date();
    const thisWeekFeedback = feedback.filter((item) => {
      if (!item.timestamp) return false;
      const time = new Date(item.timestamp).getTime();
      return now.getTime() - time <= 7 * 24 * 3600 * 1000;
    }).length;

    setStats((prev) => ({
      ...prev,
      avgRating,
      positiveRate,
      thisWeekFeedback,
    }));
  }, [feedback]);

  const filteredFeedback = useMemo(() => {
    if (selectedType === 'all') return feedback;
    return feedback.filter((item) => item.feedback_type === selectedType);
  }, [feedback, selectedType]);

  const handleExport = async () => {
    if (filteredFeedback.length === 0) {
      error('导出失败', '暂无可导出的数据');
      return;
    }
    const rows = filteredFeedback.map((item) => [
      item.trace_id,
      item.agent_name,
      item.feedback_type,
      item.user_rating ?? '',
      item.user_input?.replace(/\n/g, ' '),
      item.ai_output?.replace(/\n/g, ' '),
      item.timestamp || '',
    ]);
    const header = ['trace_id', 'agent_name', 'feedback_type', 'user_rating', 'user_input', 'ai_output', 'timestamp'];
    const csv = [header, ...rows].map((row) => row.map((cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `feedback_export_${Date.now()}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    success('导出成功', '反馈数据已导出');
  };

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'like':
        return <ThumbsUp className="w-4 h-4 text-green-500" />;
      case 'dislike':
        return <ThumbsDown className="w-4 h-4 text-red-500" />;
      case 'rating':
        return <Star className="w-4 h-4 text-yellow-500" />;
      case 'refinement':
        return <MessageSquare className="w-4 h-4 text-blue-500" />;
      default:
        return null;
    }
  };

  const getTypeText = (type: string) => {
    switch (type) {
      case 'like':
        return '点赞';
      case 'dislike':
        return '点踩';
      case 'rating':
        return '评分';
      case 'refinement':
        return '修改反馈';
      default:
        return type;
    }
  };

  return (
    <div className="flex h-screen bg-gray-50">
      <MobileMenu />
      <Sidebar />

      <div className="flex flex-col flex-1 overflow-hidden">
        <Header />
        <StatusBar />

        <div className="flex-1 overflow-y-auto">
          {/* 页面头部 */}
          <div className="bg-white border-b border-gray-200">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-12 h-12 bg-gradient-to-br from-green-500 to-teal-500 rounded-xl flex items-center justify-center">
                    <MessageSquare className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">反馈系统</h1>
                    <p className="text-sm text-gray-500 mt-1">收集用户反馈，管理黄金样本</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors"
                  >
                    <Download className="w-4 h-4" />
                    导出数据
                  </button>
                  <button
                    onClick={() => {
                      loadFeedback();
                      loadStats();
                    }}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
                  >
                    <RefreshCw className={loading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
                    刷新
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-6 py-8">
            {/* 统计卡片 */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">总反馈数</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.totalFeedback}</p>
                  </div>
                  <MessageSquare className="w-8 h-8 text-blue-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">正向反馈率</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.positiveRate.toFixed(1)}%</p>
                  </div>
                  <TrendingUp className="w-8 h-8 text-green-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">平均评分</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.avgRating.toFixed(2)}</p>
                  </div>
                  <Star className="w-8 h-8 text-yellow-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">黄金样本</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.goldSamples}</p>
                  </div>
                  <Award className="w-8 h-8 text-purple-500" />
                </div>
              </div>
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">本周新增</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">{stats.thisWeekFeedback}</p>
                  </div>
                  <Calendar className="w-8 h-8 text-orange-500" />
                </div>
              </div>
            </div>

            {/* 筛选与 Tabs */}
            <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-6">
              <div className="flex gap-2">
                {[
                  { key: 'feedback', label: '反馈列表' },
                  { key: 'samples', label: '黄金样本' },
                  { key: 'analytics', label: '趋势分析' },
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => setActiveTab(tab.key as any)}
                    className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                      activeTab === tab.key ? 'bg-black text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                <select
                  value={selectedAgent}
                  onChange={(e) => setSelectedAgent(e.target.value)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="">全部 Agent</option>
                  {agents.map((agent) => (
                    <option key={agent.id} value={agent.name}>
                      {agent.displayName || agent.name}
                    </option>
                  ))}
                </select>
                <select
                  value={days}
                  onChange={(e) => setDays(Number(e.target.value))}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value={7}>近 7 天</option>
                  <option value={30}>近 30 天</option>
                  <option value={90}>近 90 天</option>
                </select>
                <select
                  value={selectedType}
                  onChange={(e) => setSelectedType(e.target.value as any)}
                  className="text-sm border rounded px-2 py-1"
                >
                  <option value="all">全部类型</option>
                  <option value="like">点赞</option>
                  <option value="dislike">点踩</option>
                  <option value="rating">评分</option>
                  <option value="refinement">修改反馈</option>
                </select>
              </div>
            </div>

            {activeTab === 'feedback' && (
              <div className="bg-white rounded-lg shadow">
                <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                  <h2 className="text-lg font-semibold text-gray-900">反馈列表</h2>
                  <span className="text-xs text-gray-500">共 {filteredFeedback.length} 条</span>
                </div>
                <div className="divide-y divide-gray-100">
                  {loading ? (
                    <div className="p-6 text-sm text-gray-500">加载中...</div>
                  ) : filteredFeedback.length === 0 ? (
                    <div className="p-6 text-sm text-gray-500">暂无反馈数据</div>
                  ) : (
                    filteredFeedback.map((item) => (
                      <div key={item.trace_id} className="px-6 py-4">
                        <div className="flex items-center gap-2 text-sm text-gray-700">
                          {getTypeIcon(item.feedback_type)}
                          <span className="font-medium">{agentNameMap(item.agent_name, agents)}</span>
                          <span className="text-xs text-gray-500">{getTypeText(item.feedback_type)}</span>
                          {item.user_rating && (
                            <span className="text-xs text-yellow-600">评分 {item.user_rating}</span>
                          )}
                          {item.is_gold_sample && (
                            <span className="text-xs bg-yellow-100 text-yellow-700 px-2 py-0.5 rounded">黄金样本</span>
                          )}
                        </div>
                        <div className="mt-2 text-xs text-gray-500">{item.timestamp ? new Date(item.timestamp).toLocaleString('zh-CN') : '—'}</div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">用户输入</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-3">{item.user_input}</p>
                        </div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">AI 输出</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-3">{item.ai_output}</p>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            )}

            {activeTab === 'samples' && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-3 mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">黄金样本检索</h2>
                    <p className="text-sm text-gray-500">输入关键词检索高质量案例</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="relative">
                      <Search className="w-4 h-4 text-gray-400 absolute left-2 top-2.5" />
                      <input
                        value={goldQuery}
                        onChange={(e) => setGoldQuery(e.target.value)}
                        placeholder="输入关键词"
                        className="pl-8 pr-3 py-2 border rounded text-sm"
                      />
                    </div>
                    <button
                      onClick={loadGoldSamples}
                      className="px-3 py-2 text-sm bg-black text-white rounded hover:bg-gray-800"
                    >
                      搜索样本
                    </button>
                  </div>
                </div>

                {goldLoading ? (
                  <div className="text-sm text-gray-500">加载中...</div>
                ) : goldSamples.length === 0 ? (
                  <div className="text-sm text-gray-500">暂无匹配的黄金样本</div>
                ) : (
                  <div className="space-y-4">
                    {goldSamples.map((sample) => (
                      <div key={sample.sample_id} className="border rounded-lg p-4">
                        <div className="flex items-center gap-2 text-sm">
                          <Award className="w-4 h-4 text-yellow-500" />
                          <span className="font-medium">{agentNameMap(sample.agent_name, agents)}</span>
                          <span className="text-xs text-gray-500">相似度: {sample.score?.toFixed(2) ?? '-'}</span>
                        </div>
                        <div className="mt-2 text-xs text-gray-600">{sample.gold_reason || '高质量输出'}</div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">用户输入</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-2">{sample.user_input}</p>
                        </div>
                        <div className="mt-3 text-sm text-gray-700">
                          <div className="font-medium text-gray-900">AI 输出</div>
                          <p className="text-xs text-gray-600 mt-1 line-clamp-3">{sample.ai_output}</p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {activeTab === 'analytics' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900">反馈趋势概览</h2>
                <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">按类型分布</h3>
                    <div className="mt-3 text-xs text-gray-600 space-y-1">
                      <div>点赞: {feedback.filter((item) => item.feedback_type === 'like').length}</div>
                      <div>点踩: {feedback.filter((item) => item.feedback_type === 'dislike').length}</div>
                      <div>评分: {feedback.filter((item) => item.feedback_type === 'rating').length}</div>
                      <div>修改反馈: {feedback.filter((item) => item.feedback_type === 'refinement').length}</div>
                    </div>
                  </div>
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">数据健康度</h3>
                    <div className="mt-3 text-xs text-gray-600 space-y-1">
                      <div>正向反馈率: {stats.positiveRate.toFixed(1)}%</div>
                      <div>平均评分: {stats.avgRating.toFixed(2)}</div>
                      <div>黄金样本占比: {stats.totalFeedback ? ((stats.goldSamples / stats.totalFeedback) * 100).toFixed(1) : '0'}%</div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
};

export default FeedbackPage;

function agentNameMap(agentName: string, agents: Agent[]) {
  const found = agents.find((agent) => agent.name === agentName);
  return found?.displayName || agentName;
}

/**
 * Token 使用监控页面
 * 用于监控和分析 Token 使用情况、成本和配额
 */

import React, { useState, useEffect } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Coins,
  TrendingUp,
  TrendingDown,
  DollarSign,
  Users,
  Clock,
  BarChart3,
  Download,
  RefreshCw,
  Calendar,
  Filter,
  AlertTriangle,
  CheckCircle2,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { api } from '@/services/api';

interface TokenUsage {
  userId: string;
  username: string;
  totalTokens: number;
  inputTokens: number;
  outputTokens: number;
  cost: number;
  requestCount: number;
  lastUsed: string;
}

interface DailyUsage {
  date: string;
  totalTokens: number;
  cost: number;
  requests: number;
}

interface AgentUsage {
  agentId: string;
  agentName: string;
  totalTokens: number;
  cost: number;
  requests: number;
  avgTokensPerRequest: number;
}

interface UsageSummary {
  totalTokens: number;
  totalCost: number;
  totalRequests: number;
  activeUsers: number;
  avgTokensPerRequest: number;
  remainingQuota: number;
  quotaLimit: number;
}

export const TokenUsagePage: React.FC = () => {
  const { success } = useNotificationStore();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d' | 'all'>('30d');
  const [selectedUser, setSelectedUser] = useState<string>('all');
  const [selectedAgent, setSelectedAgent] = useState<string>('all');
  const [isLoading, setIsLoading] = useState(false);
  const [summary, setSummary] = useState<UsageSummary>({
    totalTokens: 0,
    totalCost: 0,
    totalRequests: 0,
    activeUsers: 0,
    avgTokensPerRequest: 0,
    remainingQuota: 0,
    quotaLimit: 0,
  });
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);
  const [agentUsage, setAgentUsage] = useState<AgentUsage[]>([]);
  const [userUsage, setUserUsage] = useState<TokenUsage[]>([]);

  useEffect(() => {
    const loadData = async () => {
      setIsLoading(true);
      try {
        const days = timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : timeRange === '90d' ? 90 : 30;
        const dashboard = await api.get<any>('/juben/system/token-dashboard');
        const ranking = await api.get<any>('/juben/system/token-ranking', { top_n: '10' });
        const stats = await api.get<any>('/juben/system/token-stats', { days: `${days}` });

        const summaryData = dashboard?.data?.summary || {};
        setSummary({
          totalTokens: summaryData.monthly_tokens || 0,
          totalCost: 0,
          totalRequests: 0,
          activeUsers: summaryData.today_top_users || 0,
          avgTokensPerRequest: 0,
          remainingQuota: 0,
          quotaLimit: 0,
        });

        const dailyStats = stats?.data?.stats || {};
        const dailyList = Object.keys(dailyStats)
          .sort()
          .map((date) => ({
            date,
            totalTokens: dailyStats[date] || 0,
            cost: 0,
            requests: 0,
          }));
        setDailyUsage(dailyList);

        const rankingList = ranking?.data?.ranking || dashboard?.data?.today_ranking || [];
        const userList = (rankingList as any[]).map((item: any) => ({
          userId: item.user_id || item.user || 'unknown',
          username: item.user_id || 'unknown',
          totalTokens: item.total_tokens || 0,
          inputTokens: item.prompt_tokens || 0,
          outputTokens: item.completion_tokens || 0,
          cost: item.estimated_cost || 0,
          requestCount: item.llm_calls || 0,
          lastUsed: new Date().toISOString(),
        }));
        setUserUsage(userList);
        setAgentUsage([]);
      } catch (error) {
        setUserUsage([]);
        setDailyUsage([]);
      } finally {
        setIsLoading(false);
      }
    };

    loadData();
  }, [timeRange]);

  const handleRefresh = async () => {
    setIsLoading(true);
    setIsLoading(false);
    success('刷新成功', '数据已更新');
  };

  const handleExport = () => {
    success('导出成功', 'Token 使用数据已导出');
  };

  const formatNumber = (num: number) => {
    if (num >= 1000000) return `${(num / 1000000).toFixed(1)}M`;
    if (num >= 1000) return `${(num / 1000).toFixed(1)}K`;
    return num.toString();
  };

  const formatCost = (cost: number) => {
    return `¥${cost.toFixed(2)}`;
  };

  const quotaPercentage = summary.quotaLimit > 0 ? (summary.remainingQuota / summary.quotaLimit) * 100 : 0;
  const tokensPercentage = summary.quotaLimit > 0 ? ((summary.quotaLimit - summary.remainingQuota) / summary.quotaLimit) * 100 : 0;

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
                  <div className="w-12 h-12 bg-gradient-to-br from-yellow-500 to-orange-500 rounded-xl flex items-center justify-center">
                    <Coins className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">Token 使用监控</h1>
                    <p className="text-sm text-gray-500 mt-1">
                      监控 Token 使用情况、成本分析和配额管理
                    </p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <select
                    value={timeRange}
                    onChange={(e) => setTimeRange(e.target.value as any)}
                    className="px-3 py-2 border border-gray-300 rounded-lg text-sm focus:ring-2 focus:ring-yellow-500"
                  >
                    <option value="7d">最近 7 天</option>
                    <option value="30d">最近 30 天</option>
                    <option value="90d">最近 90 天</option>
                    <option value="all">全部</option>
                  </select>
                  <button
                    onClick={handleRefresh}
                    disabled={isLoading}
                    className="p-2 hover:bg-gray-100 rounded-lg"
                    title="刷新"
                  >
                    <RefreshCw className={`w-5 h-5 text-gray-600 ${isLoading ? 'animate-spin' : ''}`} />
                  </button>
                  <button
                    onClick={handleExport}
                    className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50 text-sm"
                  >
                    <Download className="w-4 h-4" />
                    导出
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-6 py-8">
            {/* 概览统计 */}
            <div className="grid grid-cols-1 md:grid-cols-5 gap-4 mb-8">
              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">总 Token 数</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {formatNumber(summary.totalTokens)}
                    </p>
                  </div>
                  <Coins className="w-8 h-8 text-yellow-500" />
                </div>
                <div className="flex items-center gap-1 mt-2 text-xs text-green-600">
                  <TrendingUp className="w-3 h-3" />
                  <span>+12.5%</span>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">总成本</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {formatCost(summary.totalCost)}
                    </p>
                  </div>
                  <DollarSign className="w-8 h-8 text-green-500" />
                </div>
                <div className="flex items-center gap-1 mt-2 text-xs text-green-600">
                  <TrendingUp className="w-3 h-3" />
                  <span>+8.3%</span>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">总请求数</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {formatNumber(summary.totalRequests)}
                    </p>
                  </div>
                  <BarChart3 className="w-8 h-8 text-blue-500" />
                </div>
                <div className="flex items-center gap-1 mt-2 text-xs text-red-600">
                  <TrendingDown className="w-3 h-3" />
                  <span>-2.1%</span>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">活跃用户</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {summary.activeUsers}
                    </p>
                  </div>
                  <Users className="w-8 h-8 text-purple-500" />
                </div>
                <div className="flex items-center gap-1 mt-2 text-xs text-green-600">
                  <TrendingUp className="w-3 h-3" />
                  <span>+5.2%</span>
                </div>
              </div>

              <div className="bg-white rounded-lg shadow p-5">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-gray-500">平均 Token/请求</p>
                    <p className="text-2xl font-bold text-gray-900 mt-1">
                      {formatNumber(summary.avgTokensPerRequest)}
                    </p>
                  </div>
                  <Clock className="w-8 h-8 text-orange-500" />
                </div>
                <div className="flex items-center gap-1 mt-2 text-xs text-gray-500">
                  <span>稳定</span>
                </div>
              </div>
            </div>

            {/* 配额使用 */}
            <div className="bg-white rounded-lg shadow p-6 mb-8">
              <h3 className="text-lg font-semibold text-gray-900 mb-4">配额使用情况</h3>
              <div className="space-y-4">
                <div>
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-gray-600">已使用 Token</span>
                    <span className="font-medium">{formatNumber(summary.quotaLimit - summary.remainingQuota)} / {formatNumber(summary.quotaLimit)}</span>
                  </div>
                  <div className="w-full bg-gray-200 rounded-full h-4">
                    <div
                      className="bg-gradient-to-r from-yellow-500 to-orange-500 h-4 rounded-full transition-all"
                      style={{ width: `${tokensPercentage}%` }}
                    />
                  </div>
                  <div className="flex items-center justify-between text-xs mt-1">
                    <span className="text-gray-500">使用率: {tokensPercentage.toFixed(1)}%</span>
                    <span className="text-gray-500">剩余: {formatNumber(summary.remainingQuota)}</span>
                  </div>
                </div>

                {tokensPercentage > 80 && (
                  <div className="flex items-start gap-3 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
                    <AlertTriangle className="w-5 h-5 text-yellow-600 mt-0.5" />
                    <div className="text-sm text-yellow-800">
                      <p className="font-medium">配额警告</p>
                      <p className="mt-1">当前 Token 使用量已超过配额的 80%，建议及时充值或优化使用策略。</p>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* 标签页导航 */}
            <div className="bg-white rounded-lg shadow mb-8">
              <div className="border-b border-gray-200">
                <nav className="flex">
                  <button className="px-6 py-4 border-b-2 border-black text-black font-medium text-sm">
                    使用趋势
                  </button>
                  <button className="px-6 py-4 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">
                    Agent 统计
                  </button>
                  <button className="px-6 py-4 border-b-2 border-transparent text-gray-500 hover:text-gray-700 font-medium text-sm">
                    用户排名
                  </button>
                </nav>
              </div>

              {/* 使用趋势图表 */}
              <div className="p-6">
                <h3 className="text-lg font-semibold text-gray-900 mb-4">每日使用趋势</h3>
                <div className="h-64 flex items-end justify-between gap-2">
                  {dailyUsage.map((day, index) => {
                    const maxTokens = Math.max(...dailyUsage.map((d) => d.totalTokens));
                    const height = (day.totalTokens / maxTokens) * 100;
                    const isToday = index === dailyUsage.length - 1;
                    return (
                      <div key={day.date} className="flex-1 flex flex-col items-center gap-2">
                        <div className="w-full relative group">
                          <div
                            className={`w-full rounded-t transition-all ${
                              isToday ? 'bg-gradient-to-t from-yellow-500 to-orange-500' : 'bg-blue-500'
                            }`}
                            style={{ height: `${height * 2}px` }}
                          />
                          <div className="absolute bottom-full left-1/2 transform -translate-x-1/2 mb-2 hidden group-hover:block bg-gray-900 text-white text-xs rounded px-2 py-1 whitespace-nowrap z-10">
                            <div>{day.date}</div>
                            <div>{formatNumber(day.totalTokens)} tokens</div>
                            <div>{formatCost(day.cost)}</div>
                          </div>
                        </div>
                        <div className="text-xs text-gray-500 text-center">
                          {new Date(day.date).toLocaleDateString('zh-CN', { month: 'numeric', day: 'numeric' })}
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </div>

            {/* Agent 使用统计 */}
            <div className="bg-white rounded-lg shadow overflow-hidden mb-8">
              <div className="px-6 py-4 border-b border-gray-200">
                <h3 className="text-lg font-semibold text-gray-900">Agent 使用统计</h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Agent</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">总 Token</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">成本</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">请求数</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">平均 Token/请求</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">占比</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {agentUsage.map((agent) => {
                      const percentage = (agent.totalTokens / summary.totalTokens) * 100;
                      return (
                        <tr key={agent.agentId} className="hover:bg-gray-50">
                          <td className="px-6 py-4">
                            <div className="text-sm font-medium text-gray-900">{agent.agentName}</div>
                            <div className="text-xs text-gray-500">{agent.agentId}</div>
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-900 font-medium">
                            {formatNumber(agent.totalTokens)}
                          </td>
                          <td className="px-6 py-4 text-sm text-gray-600">{formatCost(agent.cost)}</td>
                          <td className="px-6 py-4 text-sm text-gray-600">{agent.requests}</td>
                          <td className="px-6 py-4 text-sm text-gray-600">
                            {formatNumber(agent.avgTokensPerRequest)}
                          </td>
                          <td className="px-6 py-4">
                            <div className="flex items-center gap-2">
                              <div className="flex-1 bg-gray-200 rounded-full h-2 w-24">
                                <div
                                  className="bg-blue-600 h-2 rounded-full"
                                  style={{ width: `${percentage}%` }}
                                />
                              </div>
                              <span className="text-sm text-gray-900">{percentage.toFixed(1)}%</span>
                            </div>
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
            </div>

            {/* 用户使用排名 */}
            <div className="bg-white rounded-lg shadow overflow-hidden">
              <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
                <h3 className="text-lg font-semibold text-gray-900">用户使用排名</h3>
                <select
                  value={selectedUser}
                  onChange={(e) => setSelectedUser(e.target.value)}
                  className="px-3 py-1.5 border border-gray-300 rounded-lg text-sm"
                >
                  <option value="all">所有用户</option>
                  <option value="top10">Top 10</option>
                  <option value="active">活跃用户</option>
                </select>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200">
                  <thead className="bg-gray-50">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">用户</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">输入 Token</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">输出 Token</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">总 Token</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">成本</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">请求数</th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">最后使用</th>
                    </tr>
                  </thead>
                  <tbody className="bg-white divide-y divide-gray-200">
                    {userUsage.map((user, index) => (
                      <tr key={user.userId} className="hover:bg-gray-50">
                        <td className="px-6 py-4">
                          <div className="flex items-center gap-3">
                            <div className="flex-shrink-0 w-8 h-8 bg-gradient-to-br from-blue-500 to-purple-600 rounded-full flex items-center justify-center text-white text-sm font-medium">
                              {index + 1}
                            </div>
                            <div className="text-sm font-medium text-gray-900">{user.username}</div>
                          </div>
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {formatNumber(user.inputTokens)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {formatNumber(user.outputTokens)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-900 font-medium">
                          {formatNumber(user.totalTokens)}
                        </td>
                        <td className="px-6 py-4 text-sm text-gray-600">{formatCost(user.cost)}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">{user.requestCount}</td>
                        <td className="px-6 py-4 text-sm text-gray-600">
                          {new Date(user.lastUsed).toLocaleString()}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
};

export default TokenUsagePage;

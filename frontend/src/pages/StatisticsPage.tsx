/**
 * 统计分析页面
 * 展示系统使用统计、性能分析等信息
 */

import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  TrendingUp,
  Users,
  MessageSquare,
  Activity,
  Clock,
  Zap,
  BarChart3,
  PieChart,
  Calendar,
  Download,
  Filter,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { statisticsService, SystemStats, DailyStats, SystemHealth, ResponseTimeDistribution, AgentUsageStats } from '@/services/statisticsService';

interface StatCard {
  title: string;
  value: string | number;
  change: string;
  changeType: 'increase' | 'decrease';
  icon: React.ElementType;
}

interface UsageData {
  date: string;
  users: number;
  messages: number;
  tokens: number;
  avgResponseTime?: number;
}

export const StatisticsPage: React.FC = () => {
  const { success, error } = useNotificationStore();
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('7d');
  const [isLoading, setIsLoading] = useState(false);
  const [statsData, setStatsData] = useState<SystemStats>({
    total_access: 0,
    today_access: 0,
    today_unique_users: 0,
    status: 'unknown',
  });
  const [systemHealth, setSystemHealth] = useState<SystemHealth | null>(null);
  const [responseTimeDist, setResponseTimeDist] = useState<ResponseTimeDistribution | null>(null);
  const [agentUsage, setAgentUsage] = useState<AgentUsageStats[]>([]);
  const [usageData, setUsageData] = useState<UsageData[]>([]);

  // 使用 ref 来追踪实时更新订阅
  const realTimeUnsubscribeRef = useRef<(() => void) | null>(null);

  // 加载统计数据
  const loadStats = useCallback(async () => {
    setIsLoading(true);
    try {
      // 并行加载所有统计数据
      const [systemStats, health, responseDist, agentStats, dailyStats] = await Promise.all([
        statisticsService.getSystemStats(),
        statisticsService.getSystemHealth(),
        statisticsService.getResponseTimeDistribution(),
        statisticsService.getAgentUsageStats(timeRange),
        statisticsService.getDailyStats(timeRange === '7d' ? 7 : timeRange === '30d' ? 30 : 90),
      ]);

      setStatsData(systemStats);
      setSystemHealth(health);
      setResponseTimeDist(responseDist);
      setAgentUsage(agentStats);

      // 转换每日数据
      const data: UsageData[] = dailyStats.map((stat) => ({
        date: new Date(stat.date).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }),
        users: stat.unique_users,
        messages: stat.access_count,
        tokens: 0, // 暂无token数据
        avgResponseTime: stat.avg_response_time,
      }));
      setUsageData(data);
    } catch (err: any) {
      error('加载失败', err?.message || '无法加载统计数据');
    } finally {
      setIsLoading(false);
    }
  }, [timeRange, error]);

  useEffect(() => {
    loadStats();

    // 订阅实时统计数据
    realTimeUnsubscribeRef.current = statisticsService.subscribeToRealTimeStats(
      (realTimeStats) => {
        // 实时更新部分数据
        if (realTimeStats.requests) {
          // 可以在这里更新实时数据
        }
      },
      (err) => {
        console.error('Real-time stats error:', err);
      }
    );

    return () => {
      // 清理订阅
      if (realTimeUnsubscribeRef.current) {
        realTimeUnsubscribeRef.current();
      }
    };
  }, [loadStats]);

  const statCards: StatCard[] = [
    {
      title: '总访问次数',
      value: statsData.total_access,
      change: '',
      changeType: 'increase',
      icon: Users,
    },
    {
      title: '今日访问',
      value: statsData.today_access,
      change: '',
      changeType: 'increase',
      icon: MessageSquare,
    },
    {
      title: '今日独立用户',
      value: statsData.today_unique_users,
      change: '',
      changeType: 'increase',
      icon: Activity,
    },
    {
      title: '系统状态',
      value: statsData.status === 'healthy' ? '正常' : statsData.status === 'degraded' ? '降级' : '异常',
      change: '',
      changeType: statsData.status === 'healthy' ? 'increase' : 'decrease',
      icon: Zap,
    },
  ];

  const handleExport = async () => {
    setIsLoading(true);
    try {
      const blob = await statisticsService.exportStatistics('json', timeRange);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `statistics_${new Date().toISOString().slice(0, 10)}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
      success('导出成功', '统计数据已导出');
    } catch (err) {
      error('导出失败', '请稍后重试');
    } finally {
      setIsLoading(false);
    }
  };

  // 计算Agent使用分布百分比
  const totalAgentUsage = agentUsage.reduce((sum, agent) => sum + agent.usage_count, 0);
  const agentUsageDistribution = agentUsage.map((agent) => ({
    name: agent.agent_name,
    usage: totalAgentUsage > 0 ? Math.round((agent.usage_count / totalAgentUsage) * 100) : 0,
    color: 'bg-blue-500',
  }));

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 头部 */}
      <div className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="py-6">
            <div className="flex items-center justify-between">
              <div>
                <h1 className="text-3xl font-bold text-gray-900 dark:text-white">
                  统计分析
                </h1>
                <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
                  查看系统使用情况和性能指标
                </p>
              </div>
              <div className="flex items-center gap-3">
                {/* 时间范围选择器 */}
                <div className="flex items-center bg-gray-100 dark:bg-gray-700 rounded-lg p-1">
                  {(['7d', '30d', '90d'] as const).map((range) => (
                    <button
                      key={range}
                      onClick={() => setTimeRange(range)}
                      className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                        timeRange === range
                          ? 'bg-white dark:bg-gray-600 text-gray-900 dark:text-white shadow'
                          : 'text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white'
                      }`}
                    >
                      {range === '7d' ? '7天' : range === '30d' ? '30天' : '90天'}
                    </button>
                  ))}
                </div>
                <button
                  onClick={handleExport}
                  disabled={isLoading}
                  className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors disabled:opacity-50"
                >
                  <Download className="w-4 h-4" />
                  {isLoading ? '导出中...' : '导出报告'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 统计卡片 */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          {statCards.map((card, index) => (
            <div
              key={index}
              className="bg-white dark:bg-gray-800 rounded-lg shadow p-6"
            >
              <div className="flex items-center justify-between">
                <div className="flex-1">
                  <p className="text-sm text-gray-500 dark:text-gray-400">
                    {card.title}
                  </p>
                  <p className="text-2xl font-bold text-gray-900 dark:text-white mt-2">
                    {card.value}
                  </p>
                  <div className="flex items-center mt-2">
                    <TrendingUp
                      className={`w-4 h-4 mr-1 ${
                        card.changeType === 'increase'
                          ? 'text-green-500'
                          : 'text-red-500'
                      }`}
                    />
                    <span
                      className={`text-sm font-medium ${
                        card.changeType === 'increase'
                          ? 'text-green-600 dark:text-green-400'
                          : 'text-red-600 dark:text-red-400'
                      }`}
                    >
                      {card.change}
                    </span>
                    <span className="text-sm text-gray-500 dark:text-gray-400 ml-1">
                      vs 上期
                    </span>
                  </div>
                </div>
                <div className="ml-4">
                  <card.icon className="w-8 h-8 text-blue-500" />
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* 图表区域 */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
          {/* 使用趋势图 */}
          <div className="lg:col-span-2 bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
                使用趋势
              </h2>
              <div className="flex items-center gap-4 text-sm">
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-blue-500" />
                  <span className="text-gray-600 dark:text-gray-400">消息数</span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="w-3 h-3 rounded-full bg-green-500" />
                  <span className="text-gray-600 dark:text-gray-400">用户数</span>
                </div>
              </div>
            </div>

            {/* 简化的图表展示 */}
            <div className="h-64 flex items-end gap-2">
              {usageData.map((item, index) => (
                <div
                  key={index}
                  className="flex-1 flex flex-col items-center gap-1"
                >
                  <div className="w-full flex gap-1 items-end h-full">
                    <div
                      className="flex-1 bg-blue-500 rounded-t transition-all hover:bg-blue-600"
                      style={{
                        height: `${(item.messages / 700) * 100}%`,
                        minHeight: '4px',
                      }}
                      title={`消息: ${item.messages}`}
                    />
                    <div
                      className="flex-1 bg-green-500 rounded-t transition-all hover:bg-green-600"
                      style={{
                        height: `${(item.users / 150) * 100}%`,
                        minHeight: '4px',
                      }}
                      title={`用户: ${item.users}`}
                    />
                  </div>
                  {index % Math.ceil(usageData.length / 7) === 0 && (
                    <span className="text-xs text-gray-500 dark:text-gray-400 transform -rotate-45 origin-top-left">
                      {item.date}
                    </span>
                  )}
                </div>
              ))}
            </div>
          </div>

          {/* Agent使用分布 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white mb-6">
              Agent使用分布
            </h2>
            <div className="space-y-4">
              {agentUsageDistribution.map((agent) => (
                <div key={agent.name}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-700 dark:text-gray-300">
                      {agent.name}
                    </span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {agent.usage}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`${agent.color} h-2 rounded-full transition-all`}
                      style={{ width: `${agent.usage}%` }}
                    />
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* 详细数据表格 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow overflow-hidden">
          <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-lg font-semibold text-gray-900 dark:text-white">
              详细数据
            </h2>
          </div>
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
              <thead className="bg-gray-50 dark:bg-gray-700">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    日期
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    活跃用户
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    消息数
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    Token使用
                  </th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                    平均响应时间
                  </th>
                </tr>
              </thead>
              <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                {usageData.slice(-7).map((item, index) => (
                  <tr key={index}>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {item.date}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {item.users}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {item.messages.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {item.tokens.toLocaleString()}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-900 dark:text-white">
                      {item.avgResponseTime ? `${item.avgResponseTime.toFixed(2)}s` : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* 性能指标 */}
        <div className="mt-8 grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-4">
              <Clock className="w-5 h-5 text-blue-500" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                响应时间分布
              </h3>
            </div>
            <div className="space-y-3">
              {responseTimeDist ? [
                { label: '快速 (<1s)', value: responseTimeDist.fast, color: 'bg-green-500' },
                { label: '正常 (1-2s)', value: responseTimeDist.normal, color: 'bg-blue-500' },
                { label: '较慢 (2-5s)', value: responseTimeDist.slow, color: 'bg-yellow-500' },
                { label: '超慢 (>5s)', value: responseTimeDist.very_slow, color: 'bg-red-500' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {item.label}
                    </span>
                    <span className="text-sm font-medium text-gray-900 dark:text-white">
                      {item.value}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
                    <div
                      className={`${item.color} h-2 rounded-full`}
                      style={{ width: `${item.value}%` }}
                    />
                  </div>
                </div>
              )) : (
                <div className="text-sm text-gray-500">加载中...</div>
              )}
            </div>
          </div>

          <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
            <div className="flex items-center gap-3 mb-4">
              <Activity className="w-5 h-5 text-purple-500" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                系统健康度
              </h3>
            </div>
            <div className="space-y-4">
              {systemHealth ? (
                <>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      API可用性
                    </span>
                    <span className="text-lg font-bold text-green-600">
                      {systemHealth.api_availability.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      错误率
                    </span>
                    <span className="text-lg font-bold text-green-600">
                      {systemHealth.error_rate.toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      CPU使用率
                    </span>
                    <span className="text-lg font-bold text-blue-600">
                      {systemHealth.cpu_usage.toFixed(0)}%
                    </span>
                  </div>
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      内存使用率
                    </span>
                    <span className="text-lg font-bold text-yellow-600">
                      {systemHealth.memory_usage.toFixed(0)}%
                    </span>
                  </div>
                </>
              ) : (
                <div className="text-sm text-gray-500">加载中...</div>
              )}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default StatisticsPage;

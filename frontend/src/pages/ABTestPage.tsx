/**
 * A/B 测试管理页面
 * 用于配置和管理 Agent 的 A/B 测试
 */

import React, { useEffect, useMemo, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  GitCompare,
  Plus,
  Clock,
  TrendingUp,
  Users,
  RefreshCw,
  Trophy,
} from 'lucide-react';
import { useNotificationStore } from '@/store/notificationStore';
import { getAgents } from '@/services/agentService';
import { getEvolutionStatus, getABTestStatus, promoteVersion } from '@/services/evolutionService';
import type { Agent } from '@/types';

interface ABTestSummary {
  agent_name: string;
  config?: any;
  traffic_stats?: any;
  performance_comparison?: any;
}

const ABTestPage: React.FC = () => {
  const { success, error } = useNotificationStore();
  const [activeTab, setActiveTab] = useState<'tests' | 'create' | 'results'>('tests');
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgent, setSelectedAgent] = useState('');
  const [tests, setTests] = useState<ABTestSummary[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isDetailLoading, setIsDetailLoading] = useState(false);
  const [detail, setDetail] = useState<ABTestSummary | null>(null);
  const [lastUpdated, setLastUpdated] = useState<string>('');

  useEffect(() => {
    const init = async () => {
      try {
        const list = await getAgents();
        setAgents(list);
        if (!selectedAgent && list.length > 0) {
          setSelectedAgent(list[0].name);
        }
      } catch {
        setAgents([]);
      }
    };
    init();
  }, []);

  const loadTests = async () => {
    setIsLoading(true);
    try {
      const response = await getEvolutionStatus();
      const abTests = (response.data?.active_ab_tests || []) as ABTestSummary[];
      setTests(abTests);
      setLastUpdated(new Date().toLocaleString('zh-CN'));
    } catch (err: any) {
      error('加载失败', err?.message || '无法加载 A/B 测试');
      setTests([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadTests();
  }, []);

  useEffect(() => {
    const loadDetail = async () => {
      if (!selectedAgent) return;
      setIsDetailLoading(true);
      try {
        const res = await getABTestStatus(selectedAgent);
        if (res.success) {
          setDetail(res.data as ABTestSummary);
        } else {
          setDetail(null);
        }
      } catch (err: any) {
        setDetail(null);
        error('加载失败', err?.message || '无法加载 A/B 测试详情');
      } finally {
        setIsDetailLoading(false);
      }
    };
    loadDetail();
  }, [selectedAgent]);

  const agentNameMap = useMemo(() => {
    const map = new Map<string, string>();
    agents.forEach((agent) => map.set(agent.name, agent.displayName || agent.name));
    return map;
  }, [agents]);

  const totalTests = tests.length;
  const totalTraffic = tests.reduce((acc, item) => acc + (item.traffic_stats?.total_requests || 0), 0);
  const avgLift = tests.length
    ? tests.reduce((acc, item) => acc + (item.performance_comparison?.comparison?.rating_diff || 0), 0) / tests.length
    : 0;

  const handlePromote = async (agentName: string, versionId?: string) => {
    if (!versionId) {
      error('晋升失败', '未找到可晋升的版本');
      return;
    }
    try {
      await promoteVersion(agentName, versionId);
      success('晋升成功', '已将新版本设为活跃版本');
      loadTests();
      if (selectedAgent === agentName) {
        const res = await getABTestStatus(agentName);
        setDetail(res.data as ABTestSummary);
      }
    } catch (err: any) {
      error('晋升失败', err?.message || '无法晋升版本');
    }
  };

  const renderStatusBadge = (comparison?: any) => {
    if (!comparison) return <span className="text-xs text-gray-500">暂无数据</span>;
    if (comparison?.significant_improvement) {
      return (
        <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-green-100 text-green-700">
          <Trophy className="w-3 h-3" />
          显著提升
        </span>
      );
    }
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs rounded bg-gray-100 text-gray-600">
        <Clock className="w-3 h-3" />
        等待更多数据
      </span>
    );
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
                  <div className="w-12 h-12 bg-gradient-to-br from-blue-500 to-cyan-500 rounded-xl flex items-center justify-center">
                    <GitCompare className="w-6 h-6 text-white" />
                  </div>
                  <div>
                    <h1 className="text-2xl font-bold text-gray-900">A/B 测试管理</h1>
                    <p className="text-sm text-gray-500 mt-1">配置和管理 Agent 的 A/B 测试</p>
                  </div>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={loadTests}
                    className="flex items-center gap-2 px-3 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-sm"
                  >
                    <RefreshCw className={isLoading ? 'w-4 h-4 animate-spin' : 'w-4 h-4'} />
                    刷新
                  </button>
                  <button
                    onClick={() => setActiveTab('create')}
                    className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-all"
                  >
                    <Plus className="w-4 h-4" />
                    配置指引
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div className="max-w-7xl mx-auto px-6 py-8">
            {/* Tabs */}
            <div className="flex gap-2 mb-6">
              {[
                { key: 'tests', label: '进行中的测试' },
                { key: 'results', label: '测试结果' },
                { key: 'create', label: '配置说明' },
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

            {activeTab === 'tests' && (
              <>
                {/* 统计卡片 */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">活跃测试</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{totalTests}</p>
                      </div>
                      <GitCompare className="w-8 h-8 text-blue-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">累计请求</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">{totalTraffic}</p>
                      </div>
                      <Users className="w-8 h-8 text-green-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">平均评分提升</p>
                        <p className="text-2xl font-bold text-gray-900 mt-1">
                          {avgLift >= 0 ? '+' : ''}{avgLift.toFixed(2)}
                        </p>
                      </div>
                      <TrendingUp className="w-8 h-8 text-purple-500" />
                    </div>
                  </div>
                  <div className="bg-white rounded-lg shadow p-5">
                    <div className="flex items-center justify-between">
                      <div>
                        <p className="text-sm text-gray-500">最近更新</p>
                        <p className="text-sm font-medium text-gray-900 mt-2">{lastUpdated || '—'}</p>
                      </div>
                      <Clock className="w-8 h-8 text-gray-400" />
                    </div>
                  </div>
                </div>

                {/* 测试列表 */}
                <div className="bg-white rounded-lg shadow">
                  <div className="px-6 py-4 border-b border-gray-200">
                    <h2 className="text-lg font-semibold text-gray-900">测试列表</h2>
                  </div>
                  <div className="divide-y divide-gray-100">
                    {tests.length === 0 ? (
                      <div className="p-8 text-center text-sm text-gray-500">
                        暂无进行中的 A/B 测试。请先在进化系统中产生候选版本。
                      </div>
                    ) : (
                      tests.map((test) => {
                        const comparison = test.performance_comparison || {};
                        const config = test.config || {};
                        const traffic = test.traffic_stats || {};
                        return (
                          <div key={test.agent_name} className="px-6 py-4 flex items-center justify-between">
                            <div>
                              <div className="flex items-center gap-3">
                                <h3 className="text-sm font-semibold text-gray-900">
                                  {agentNameMap.get(test.agent_name) || test.agent_name}
                                </h3>
                                {renderStatusBadge(comparison?.comparison)}
                              </div>
                              <div className="mt-2 text-xs text-gray-500 space-x-4">
                                <span>实验流量: {config.traffic_percentage ?? 0}%</span>
                                <span>请求数: {traffic.total_requests ?? 0}</span>
                                <span>评分提升: {(comparison?.comparison?.rating_diff ?? 0).toFixed(2)}</span>
                              </div>
                            </div>
                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => {
                                  setSelectedAgent(test.agent_name);
                                  setActiveTab('results');
                                }}
                                className="px-3 py-1.5 text-xs bg-gray-100 hover:bg-gray-200 rounded"
                              >
                                查看详情
                              </button>
                              {comparison?.comparison?.significant_improvement && config.treatment_version_id && (
                                <button
                                  onClick={() => handlePromote(test.agent_name, config.treatment_version_id)}
                                  className="px-3 py-1.5 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                                >
                                  晋升版本
                                </button>
                              )}
                            </div>
                          </div>
                        );
                      })
                    )}
                  </div>
                </div>
              </>
            )}

            {activeTab === 'results' && (
              <div className="bg-white rounded-lg shadow p-6">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <h2 className="text-lg font-semibold text-gray-900">测试结果详情</h2>
                    <p className="text-sm text-gray-500">选择 Agent 查看 A/B 对比数据</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <select
                      value={selectedAgent}
                      onChange={(e) => setSelectedAgent(e.target.value)}
                      className="text-sm border rounded px-2 py-1"
                    >
                      {agents.map((agent) => (
                        <option key={agent.id} value={agent.name}>
                          {agent.displayName || agent.name}
                        </option>
                      ))}
                    </select>
                    <button
                      onClick={() => selectedAgent && getABTestStatus(selectedAgent).then((res) => setDetail(res.data))}
                      className="px-3 py-1.5 text-xs bg-gray-100 rounded hover:bg-gray-200"
                    >
                      刷新详情
                    </button>
                  </div>
                </div>

                {isDetailLoading ? (
                  <div className="text-sm text-gray-500">加载中...</div>
                ) : !detail?.config ? (
                  <div className="text-sm text-gray-500">当前 Agent 暂无 A/B 测试配置。</div>
                ) : (
                  <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    <div className="lg:col-span-2">
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div className="border rounded-lg p-4">
                          <h3 className="text-sm font-semibold text-gray-900">对照组</h3>
                          <p className="text-xs text-gray-500 mt-1">版本: {detail?.performance_comparison?.control?.version || '—'}</p>
                          <div className="mt-3 text-xs text-gray-600 space-y-1">
                            <div>平均评分: {detail?.performance_comparison?.control?.avg_rating ?? 0}</div>
                            <div>反馈数: {detail?.performance_comparison?.control?.total_feedbacks ?? 0}</div>
                            <div>编辑率: {detail?.performance_comparison?.control?.edit_ratio_avg ?? 0}</div>
                          </div>
                        </div>
                        <div className="border rounded-lg p-4">
                          <h3 className="text-sm font-semibold text-gray-900">实验组</h3>
                          <p className="text-xs text-gray-500 mt-1">版本: {detail?.performance_comparison?.treatment?.version || '—'}</p>
                          <div className="mt-3 text-xs text-gray-600 space-y-1">
                            <div>平均评分: {detail?.performance_comparison?.treatment?.avg_rating ?? 0}</div>
                            <div>反馈数: {detail?.performance_comparison?.treatment?.total_feedbacks ?? 0}</div>
                            <div>编辑率: {detail?.performance_comparison?.treatment?.edit_ratio_avg ?? 0}</div>
                          </div>
                        </div>
                      </div>

                      <div className="mt-6 border rounded-lg p-4">
                        <h3 className="text-sm font-semibold text-gray-900">对比结论</h3>
                        <div className="mt-3 text-xs text-gray-600 space-y-1">
                          <div>评分差异: {detail?.performance_comparison?.comparison?.rating_diff ?? 0}</div>
                          <div>编辑率差异: {detail?.performance_comparison?.comparison?.edit_ratio_diff ?? 0}</div>
                          <div>
                            显著提升: {detail?.performance_comparison?.comparison?.significant_improvement ? '是' : '否'}
                          </div>
                        </div>
                      </div>
                    </div>

                    <div className="border rounded-lg p-4">
                      <h3 className="text-sm font-semibold text-gray-900">流量配置</h3>
                      <div className="mt-3 text-xs text-gray-600 space-y-2">
                        <div>实验流量: {detail?.config?.traffic_percentage ?? 0}%</div>
                        <div>对照版本: {detail?.config?.control_version_id || '—'}</div>
                        <div>实验版本: {detail?.config?.treatment_version_id || '—'}</div>
                        <div>请求总数: {detail?.traffic_stats?.total_requests ?? 0}</div>
                        <div>实验占比: {((detail?.traffic_stats?.treatment_ratio ?? 0) * 100).toFixed(1)}%</div>
                      </div>
                      {detail?.performance_comparison?.comparison?.significant_improvement && detail?.config?.treatment_version_id && (
                        <button
                          onClick={() => handlePromote(selectedAgent, detail?.config?.treatment_version_id)}
                          className="mt-4 w-full px-3 py-2 text-xs bg-green-600 text-white rounded hover:bg-green-700"
                        >
                          晋升实验版本
                        </button>
                      )}
                    </div>
                  </div>
                )}
              </div>
            )}

            {activeTab === 'create' && (
              <div className="bg-white rounded-lg shadow p-6">
                <h2 className="text-lg font-semibold text-gray-900">A/B 测试配置说明</h2>
                <p className="text-sm text-gray-500 mt-2">
                  当前 A/B 测试由进化系统自动配置。请先在进化系统中生成候选版本，再由系统写入测试配置。
                </p>
                <div className="mt-6 grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">启动流程</h3>
                    <ol className="mt-3 text-xs text-gray-600 space-y-1 list-decimal list-inside">
                      <li>在反馈系统中积累足够的样本与评分</li>
                      <li>进入进化系统，触发候选版本生成</li>
                      <li>系统自动配置 A/B 测试并开始分流</li>
                    </ol>
                  </div>
                  <div className="border rounded-lg p-4">
                    <h3 className="text-sm font-semibold text-gray-900">常见问题</h3>
                    <p className="mt-3 text-xs text-gray-600">
                      若未看到测试列表，请检查 Redis 配置是否开启，或是否已产生候选版本。
                    </p>
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

export default ABTestPage;
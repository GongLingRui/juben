/**
 * 质量控制页面
 * 提供稳定性测试、图验证、角色一致性检查等质量控制功能
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Shield,
  CheckCircle,
  AlertTriangle,
  XCircle,
  Activity,
  Users,
  Network,
  FileText,
  Play,
  Download,
  Loader2
} from 'lucide-react';
import api from '@/services/api';

type TestStatus = 'idle' | 'running' | 'completed' | 'error';
type IssueSeverity = 'critical' | 'warning' | 'info';

interface QualityIssue {
  id: string;
  type: string;
  severity: IssueSeverity;
  message: string;
  location?: string;
  suggestion?: string;
}

interface TestResult {
  status: 'pass' | 'fail' | 'warning';
  score: number;
  issues: QualityIssue[];
  summary: string;
}

export default function QualityControlPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'stability' | 'graph' | 'character' | 'all'>('all');
  const [testContent, setTestContent] = useState('');
  const [testResults, setTestResults] = useState<Record<string, TestResult>>({});
  const [testStatus, setTestStatus] = useState<Record<string, TestStatus>>({});

  // 运行稳定性测试
  const runStabilityTest = async () => {
    if (!testContent.trim()) {
      alert('请输入测试内容');
      return;
    }

    setTestStatus(prev => ({ ...prev, stability: 'running' }));

    try {
      const result = await api.post('/juben/quality/stability', {
        content: testContent,
        test_type: 'narrative_stability'
      });

      setTestResults(prev => ({
        ...prev,
        stability: {
          status: result.data?.score >= 80 ? 'pass' : result.data?.score >= 60 ? 'warning' : 'fail',
          score: result.data?.score || 0,
          issues: result.data?.issues || [],
          summary: result.data?.summary || '测试完成'
        }
      }));
      setTestStatus(prev => ({ ...prev, stability: 'completed' }));
    } catch (err) {
      console.error('稳定性测试失败:', err);
      setTestStatus(prev => ({ ...prev, stability: 'error' }));
    }
  };

  // 运行图验证
  const runGraphValidation = async () => {
    if (!testContent.trim()) {
      alert('请输入测试内容');
      return;
    }

    setTestStatus(prev => ({ ...prev, graph: 'running' }));

    try {
      const result = await api.post('/juben/quality/graph-validate', {
        graph_data: testContent
      });

      setTestResults(prev => ({
        ...prev,
        graph: {
          status: result.data?.valid ? 'pass' : 'fail',
          score: result.data?.validity_score || 0,
          issues: result.data?.issues || [],
          summary: result.data?.summary || '验证完成'
        }
      }));
      setTestStatus(prev => ({ ...prev, graph: 'completed' }));
    } catch (err) {
      console.error('图验证失败:', err);
      setTestStatus(prev => ({ ...prev, graph: 'error' }));
    }
  };

  // 运行角色一致性检查
  const runCharacterConsistency = async () => {
    if (!testContent.trim()) {
      alert('请输入测试内容');
      return;
    }

    setTestStatus(prev => ({ ...prev, character: 'running' }));

    try {
      const result = await api.post('/juben/quality/character-consistency', {
        story_content: testContent
      });

      setTestResults(prev => ({
        ...prev,
        character: {
          status: result.data?.consistency_score >= 80 ? 'pass' : result.data?.consistency_score >= 60 ? 'warning' : 'fail',
          score: result.data?.consistency_score || 0,
          issues: result.data?.inconsistencies || [],
          summary: result.data?.summary || '检查完成'
        }
      }));
      setTestStatus(prev => ({ ...prev, character: 'completed' }));
    } catch (err) {
      console.error('角色一致性检查失败:', err);
      setTestStatus(prev => ({ ...prev, character: 'error' }));
    }
  };

  // 运行所有测试
  const runAllTests = async () => {
    if (!testContent.trim()) {
      alert('请输入测试内容');
      return;
    }

    await Promise.all([
      runStabilityTest(),
      runGraphValidation(),
      runCharacterConsistency()
    ]);
  };

  const getStatusIcon = (status: TestStatus) => {
    switch (status) {
      case 'running':
        return <Loader2 className="w-5 h-5 animate-spin text-blue-500" />;
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'error':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <div className="w-5 h-5 border-2 border-gray-300 rounded-full" />;
    }
  };

  const getResultIcon = (result?: TestResult) => {
    if (!result) return null;

    switch (result.status) {
      case 'pass':
        return <CheckCircle className="w-8 h-8 text-green-500" />;
      case 'warning':
        return <AlertTriangle className="w-8 h-8 text-orange-500" />;
      case 'fail':
        return <XCircle className="w-8 h-8 text-red-500" />;
    }
  };

  const getSeverityColor = (severity: IssueSeverity) => {
    switch (severity) {
      case 'critical':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'warning':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'info':
        return 'bg-blue-100 text-blue-700 border-blue-200';
    }
  };

  const tests = [
    {
      id: 'stability',
      name: '稳定性测试',
      description: '检测剧情逻辑稳定性和连贯性',
      icon: <Activity className="w-6 h-6" />,
      run: runStabilityTest
    },
    {
      id: 'graph',
      name: '图验证',
      description: '验证角色关系图和情节结构的正确性',
      icon: <Network className="w-6 h-6" />,
      run: runGraphValidation
    },
    {
      id: 'character',
      name: '角色一致性',
      description: '检查角色行为和性格的一致性',
      icon: <Users className="w-6 h-6" />,
      run: runCharacterConsistency
    }
  ];

  return (
    <div className="flex h-screen bg-white">
      <MobileMenu />
      <Sidebar />

      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          !sidebarOpen ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-80'
        }`}
      >
        <Header />
        <StatusBar />

        <div className="flex flex-col flex-1 overflow-hidden">
          {/* 页面头部 */}
          <div className="border-b border-gray-200 bg-white">
            <div className="max-w-7xl mx-auto px-6 py-6">
              <div className="flex items-center gap-3 mb-2">
                <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                  <Shield className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">质量控制</h1>
                  <p className="text-sm text-gray-500 mt-1">
                    检测剧本质量问题和一致性问题
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              {/* 输入区域 */}
              <div className="bg-white border border-gray-200 rounded-xl p-6 mb-6">
                <h2 className="text-lg font-semibold text-gray-900 mb-4">测试内容</h2>
                <textarea
                  value={testContent}
                  onChange={(e) => setTestContent(e.target.value)}
                  placeholder="输入要测试的剧本内容、角色关系图数据或情节描述..."
                  className="w-full h-48 p-4 border border-gray-200 rounded-lg focus:outline-none focus:border-black resize-none font-mono text-sm"
                />

                <div className="flex items-center justify-between mt-4">
                  <p className="text-sm text-gray-500">
                    {testContent.length} 字符
                  </p>

                  <div className="flex items-center gap-3">
                    <button
                      onClick={() => setTestContent('')}
                      className="px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-sm"
                    >
                      清空
                    </button>
                    <button
                      onClick={runAllTests}
                      disabled={!testContent.trim()}
                      className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                    >
                      <Play className="w-4 h-4" />
                      <span>运行全部测试</span>
                    </button>
                  </div>
                </div>
              </div>

              {/* 测试卡片 */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mb-6">
                {tests.map((test) => (
                  <div
                    key={test.id}
                    className="bg-white border border-gray-200 rounded-xl p-5 hover:shadow-lg transition-all"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className="flex items-center gap-3">
                        <div className="p-2 bg-gray-100 rounded-lg">
                          {test.icon}
                        </div>
                        <div>
                          <h3 className="font-semibold text-gray-900">{test.name}</h3>
                          <p className="text-xs text-gray-500 mt-1">{test.description}</p>
                        </div>
                      </div>

                      {getStatusIcon(testStatus[test.id])}
                    </div>

                    <button
                      onClick={test.run}
                      disabled={!testContent.trim() || testStatus[test.id] === 'running'}
                      className="w-full px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors text-sm"
                    >
                      {testStatus[test.id] === 'running' ? '运行中...' : '运行测试'}
                    </button>

                    {testResults[test.id] && (
                      <div className="mt-4 pt-4 border-t border-gray-100">
                        <div className="flex items-center justify-between">
                          <div className="flex items-center gap-2">
                            {getResultIcon(testResults[test.id])}
                            <span className="text-2xl font-bold text-gray-900">
                              {testResults[test.id].score}%
                            </span>
                          </div>
                          <span className={`text-xs px-2 py-1 rounded-full ${
                            testResults[test.id].score >= 80 ? 'bg-green-100 text-green-700' :
                            testResults[test.id].score >= 60 ? 'bg-orange-100 text-orange-700' :
                            'bg-red-100 text-red-700'
                          }`}>
                            {testResults[test.id].score >= 80 ? '通过' :
                             testResults[test.id].score >= 60 ? '警告' : '未通过'}
                          </span>
                        </div>
                      </div>
                    )}
                  </div>
                ))}
              </div>

              {/* 测试结果详情 */}
              {Object.keys(testResults).length > 0 && (
                <div className="space-y-4">
                  <h2 className="text-lg font-semibold text-gray-900">测试结果详情</h2>

                  {Object.entries(testResults).map(([testId, result]) => (
                    <div key={testId} className="bg-white border border-gray-200 rounded-xl p-6">
                      <div className="flex items-start justify-between mb-4">
                        <div>
                          <h3 className="font-semibold text-gray-900 flex items-center gap-2">
                            {getResultIcon(result)}
                            {tests.find(t => t.id === testId)?.name}
                          </h3>
                          <p className="text-sm text-gray-600 mt-1">{result.summary}</p>
                        </div>

                        <span className="text-3xl font-bold text-gray-900">
                          {result.score}%
                        </span>
                      </div>

                      {result.issues.length > 0 ? (
                        <div className="space-y-3">
                          <h4 className="text-sm font-medium text-gray-700">
                            发现 {result.issues.length} 个问题
                          </h4>

                          {result.issues.map((issue, idx) => (
                            <div
                              key={idx}
                              className={`p-4 rounded-lg border ${getSeverityColor(issue.severity)}`}
                            >
                              <div className="flex items-start justify-between mb-2">
                                <h5 className="font-medium">{issue.message}</h5>
                                <span className="text-xs uppercase font-semibold">
                                  {issue.severity}
                                </span>
                              </div>

                              {issue.location && (
                                <p className="text-sm mb-2">
                                  <span className="font-medium">位置:</span> {issue.location}
                                </p>
                              )}

                              {issue.suggestion && (
                                <p className="text-sm">
                                  <span className="font-medium">建议:</span> {issue.suggestion}
                                </p>
                              )}
                            </div>
                          ))}
                        </div>
                      ) : (
                        <div className="p-4 bg-green-50 border border-green-200 rounded-lg">
                          <p className="text-sm text-green-700">
                            未发现问题，内容质量良好！
                          </p>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
}

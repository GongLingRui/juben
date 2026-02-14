/**
 * 小说筛选页面
 * 对小说进行筛选评估，判断是否适合改编为短剧
 */

import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  BookOpen,
  Star,
  TrendingUp,
  AlertCircle,
  CheckCircle2,
  XCircle,
  Play,
  FileText,
  Download,
  Loader2,
  Award,
  BarChart3
} from 'lucide-react';
import api from '@/services/api';

type EvaluationStatus = 'idle' | 'evaluating' | 'completed' | 'error';

interface EvaluationCriteria {
  id: string;
  name: string;
  description: string;
  weight: number;
  score?: number;
}

interface EvaluationResult {
  novel_id: string;
  novel_title: string;
  overall_score: number;
  recommendation: 'highly_recommended' | 'recommended' | 'conditional' | 'not_recommended';
  criteria_scores: Record<string, number>;
  strengths: string[];
  weaknesses: string[];
  suggestions: string[];
  market_analysis?: {
    target_audience: string;
    genre_fit: number;
    commercial_potential: number;
  };
  adaptation_challenges?: string[];
}

export default function NovelScreeningPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [novelTitle, setNovelTitle] = useState('');
  const [novelContent, setNovelContent] = useState('');
  const [novelSummary, setNovelSummary] = useState('');
  const [evaluationStatus, setEvaluationStatus] = useState<EvaluationStatus>('idle');
  const [evaluationResult, setEvaluationResult] = useState<EvaluationResult | null>(null);
  const [evaluationHistory, setEvaluationHistory] = useState<EvaluationResult[]>([]);

  // 评估标准
  const criteria: EvaluationCriteria[] = [
    {
      id: 'story_structure',
      name: '故事结构',
      description: '剧情完整性和结构清晰度',
      weight: 20
    },
    {
      id: 'character_depth',
      name: '角色深度',
      description: '角色塑造的立体感和成长性',
      weight: 20
    },
    {
      id: 'emotional_impact',
      name: '情感冲击',
      description: '情感张力和观众共鸣潜力',
      weight: 20
    },
    {
      id: 'visual_potential',
      name: '视觉化潜力',
      description: '场景描述的可视化程度',
      weight: 15
    },
    {
      id: 'dialogue_quality',
      name: '对话质量',
      description: '对话的自然度和戏剧性',
      weight: 15
    },
    {
      id: 'pace_rhythm',
      name: '节奏把握',
      description: '故事节奏和情节推进速度',
      weight: 10
    }
  ];

  // 运行评估
  const runEvaluation = async () => {
    if (!novelContent.trim() || !novelTitle.trim()) {
      alert('请填写小说标题和内容');
      return;
    }

    setEvaluationStatus('evaluating');
    setEvaluationResult(null);

    try {
      const response = await api.post('/api/novel-screening/evaluate', {
        novel_title: novelTitle,
        novel_content: novelContent,
        novel_summary: novelSummary || undefined,
        user_id: user?.id,
        evaluation_criteria: criteria.map(c => c.id)
      });

      const result = response.data || response;
      setEvaluationResult(result);
      setEvaluationHistory(prev => [result, ...prev].slice(0, 10));
      setEvaluationStatus('completed');
    } catch (err) {
      console.error('评估失败:', err);
      setEvaluationStatus('error');
    }
  };

  // 运行流式评估
  const runStreamEvaluation = async () => {
    if (!novelContent.trim() || !novelTitle.trim()) {
      alert('请填写小说标题和内容');
      return;
    }

    setEvaluationStatus('evaluating');

    try {
      const response = await fetch('/api/novel-screening/evaluate/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          novel_title: novelTitle,
          novel_content: novelContent,
          novel_summary: novelSummary || undefined,
          user_id: user?.id
        })
      });

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let result = null;

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              try {
                const data = JSON.parse(line.slice(6));
                if (data.event_type === 'result') {
                  result = data.data;
                } else if (data.event_type === 'done' || data.event_type === 'complete') {
                  setEvaluationResult(result);
                  setEvaluationHistory(prev => [result, ...prev].slice(0, 10));
                  setEvaluationStatus('completed');
                  return;
                }
              } catch (e) {
                console.error('解析SSE失败:', e);
              }
            }
          }
        }
      }
    } catch (err) {
      console.error('流式评估失败:', err);
      setEvaluationStatus('error');
    }
  };

  const getRecommendationInfo = (recommendation: string) => {
    switch (recommendation) {
      case 'highly_recommended':
        return {
          label: '强烈推荐',
          color: 'bg-green-100 text-green-700',
          icon: <Award className="w-5 h-5" />,
          description: '非常适合改编，具有很高的商业价值'
        };
      case 'recommended':
        return {
          label: '推荐',
          color: 'bg-blue-100 text-blue-700',
          icon: <CheckCircle2 className="w-5 h-5" />,
          description: '适合改编，具有良好的市场潜力'
        };
      case 'conditional':
        return {
          label: '有条件推荐',
          color: 'bg-orange-100 text-orange-700',
          icon: <AlertCircle className="w-5 h-5" />,
          description: '需要适当调整后才适合改编'
        };
      case 'not_recommended':
        return {
          label: '不推荐',
          color: 'bg-red-100 text-red-700',
          icon: <XCircle className="w-5 h-5" />,
          description: '不太适合改编为短剧'
        };
      default:
        return {
          label: '未知',
          color: 'bg-gray-100 text-gray-700',
          icon: null,
          description: ''
        };
    }
  };

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'text-green-600';
    if (score >= 60) return 'text-orange-600';
    return 'text-red-600';
  };

  const exportResult = () => {
    if (!evaluationResult) return;

    const data = JSON.stringify(evaluationResult, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `novel-screening-${evaluationResult.novel_id}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

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
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                  <BookOpen className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">小说筛选评估</h1>
                  <p className="text-sm text-gray-500 mt-1">
                    评估小说是否适合改编为短剧
                  </p>
                </div>
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                {/* 左侧：输入区 */}
                <div className="lg:col-span-1 space-y-6">
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">小说信息</h2>

                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          小说标题 *
                        </label>
                        <input
                          type="text"
                          value={novelTitle}
                          onChange={(e) => setNovelTitle(e.target.value)}
                          placeholder="输入小说标题"
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          小说简介（可选）
                        </label>
                        <textarea
                          value={novelSummary}
                          onChange={(e) => setNovelSummary(e.target.value)}
                          placeholder="简要介绍小说的主要内容和特色..."
                          rows={4}
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm resize-none"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">
                          小说内容/片段 *
                        </label>
                        <textarea
                          value={novelContent}
                          onChange={(e) => setNovelContent(e.target.value)}
                          placeholder="粘贴小说内容或关键章节片段进行评估..."
                          rows={12}
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm resize-none"
                        />
                      </div>

                      <div className="flex items-center justify-between text-sm text-gray-500">
                        <span>{novelContent.length} 字符</span>
                        <button
                          onClick={() => {
                            setNovelContent('');
                            setNovelSummary('');
                          }}
                          className="text-gray-600 hover:text-gray-900"
                        >
                          清空
                        </button>
                      </div>

                      <div className="flex gap-2">
                        <button
                          onClick={runEvaluation}
                          disabled={evaluationStatus === 'evaluating' || !novelContent.trim() || !novelTitle.trim()}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors text-sm"
                        >
                          {evaluationStatus === 'evaluating' ? (
                            <>
                              <Loader2 className="w-4 h-4 animate-spin" />
                              评估中...
                            </>
                          ) : (
                            <>
                              <Play className="w-4 h-4" />
                              开始评估
                            </>
                          )}
                        </button>

                        <button
                          onClick={runStreamEvaluation}
                          disabled={evaluationStatus === 'evaluating' || !novelContent.trim() || !novelTitle.trim()}
                          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 disabled:bg-gray-100 disabled:cursor-not-allowed transition-colors text-sm"
                        >
                          流式评估
                        </button>
                      </div>
                    </div>
                  </div>

                  {/* 评估历史 */}
                  {evaluationHistory.length > 0 && (
                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-4">评估历史</h2>

                      <div className="space-y-2">
                        {evaluationHistory.map((result, idx) => (
                          <button
                            key={idx}
                            onClick={() => setEvaluationResult(result)}
                            className="w-full p-3 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-left"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-medium text-gray-900 truncate">
                                {result.novel_title}
                              </span>
                              <span className={`text-sm font-bold ${getScoreColor(result.overall_score)}`}>
                                {result.overall_score}分
                              </span>
                            </div>
                          </button>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {/* 右侧：结果区 */}
                <div className="lg:col-span-2">
                  {evaluationStatus === 'idle' && (
                    <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
                      <BookOpen className="w-16 h-16 text-gray-400 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        等待评估
                      </h3>
                      <p className="text-gray-500">
                        在左侧填写小说信息后，点击"开始评估"按钮
                      </p>
                    </div>
                  )}

                  {evaluationStatus === 'evaluating' && (
                    <div className="bg-white border border-gray-200 rounded-xl p-12 text-center">
                      <Loader2 className="w-16 h-16 animate-spin text-black mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        正在评估...
                      </h3>
                      <p className="text-gray-500">
                        请稍候，这可能需要几秒钟
                      </p>
                    </div>
                  )}

                  {evaluationStatus === 'error' && (
                    <div className="bg-white border border-red-200 rounded-xl p-12 text-center">
                      <XCircle className="w-16 h-16 text-red-500 mx-auto mb-4" />
                      <h3 className="text-lg font-semibold text-gray-900 mb-2">
                        评估失败
                      </h3>
                      <p className="text-gray-500 mb-4">
                        请检查输入内容或稍后重试
                      </p>
                      <button
                        onClick={() => setEvaluationStatus('idle')}
                        className="px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800"
                      >
                        返回
                      </button>
                    </div>
                  )}

                  {evaluationStatus === 'completed' && evaluationResult && (
                    <div className="space-y-6">
                      {/* 顶部：总分和推荐 */}
                      <div className="bg-white border border-gray-200 rounded-xl p-6">
                        <div className="flex items-start justify-between mb-6">
                          <div>
                            <h2 className="text-xl font-bold text-gray-900 mb-2">
                              {evaluationResult.novel_title}
                            </h2>
                            <p className="text-sm text-gray-500">评估完成</p>
                          </div>

                          <button
                            onClick={exportResult}
                            className="flex items-center gap-2 px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors text-sm"
                          >
                            <Download className="w-4 h-4" />
                            导出结果
                          </button>
                        </div>

                        <div className="flex items-center justify-between p-6 bg-gray-50 rounded-xl mb-6">
                          <div>
                            <p className="text-sm text-gray-500 mb-1">综合评分</p>
                            <p className={`text-5xl font-bold ${getScoreColor(evaluationResult.overall_score)}`}>
                              {evaluationResult.overall_score}
                            </p>
                          </div>

                          <div className="flex-1 mx-8">
                            <div className="h-4 bg-gray-200 rounded-full overflow-hidden">
                              <div
                                className={`h-full transition-all ${
                                  evaluationResult.overall_score >= 80 ? 'bg-green-500' :
                                  evaluationResult.overall_score >= 60 ? 'bg-orange-500' : 'bg-red-500'
                                }`}
                                style={{ width: `${evaluationResult.overall_score}%` }}
                              />
                            </div>
                          </div>

                          <div className={`px-6 py-3 rounded-full ${getRecommendationInfo(evaluationResult.recommendation).color} flex items-center gap-2`}>
                            {getRecommendationInfo(evaluationResult.recommendation).icon}
                            <span className="font-semibold">
                              {getRecommendationInfo(evaluationResult.recommendation).label}
                            </span>
                          </div>
                        </div>

                        <p className="text-sm text-gray-600">
                          {getRecommendationInfo(evaluationResult.recommendation).description}
                        </p>
                      </div>

                      {/* 评估标准得分 */}
                      <div className="bg-white border border-gray-200 rounded-xl p-6">
                        <h3 className="text-lg font-semibold text-gray-900 mb-4">详细评估</h3>

                        <div className="space-y-4">
                          {criteria.map((criterion) => {
                            const score = evaluationResult.criteria_scores[criterion.id] || 0;
                            return (
                              <div key={criterion.id}>
                                <div className="flex items-center justify-between mb-2">
                                  <div>
                                    <h4 className="font-medium text-gray-900">{criterion.name}</h4>
                                    <p className="text-xs text-gray-500">{criterion.description}</p>
                                  </div>
                                  <span className={`text-lg font-bold ${getScoreColor(score)}`}>
                                    {score}分
                                  </span>
                                </div>

                                <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                                  <div
                                    className={`h-full transition-all ${
                                      score >= 80 ? 'bg-green-500' :
                                      score >= 60 ? 'bg-orange-500' : 'bg-red-500'
                                    }`}
                                    style={{ width: `${score}%` }}
                                  />
                                </div>
                              </div>
                            );
                          })}
                        </div>
                      </div>

                      {/* 优势和劣势 */}
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        {evaluationResult.strengths.length > 0 && (
                          <div className="bg-white border border-green-200 rounded-xl p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                              <CheckCircle2 className="w-5 h-5 text-green-500" />
                              优势
                            </h3>

                            <ul className="space-y-2">
                              {evaluationResult.strengths.map((strength, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                  <span className="text-green-500 mt-0.5">•</span>
                                  {strength}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}

                        {evaluationResult.weaknesses.length > 0 && (
                          <div className="bg-white border border-orange-200 rounded-xl p-6">
                            <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                              <AlertCircle className="w-5 h-5 text-orange-500" />
                              需要改进
                            </h3>

                            <ul className="space-y-2">
                              {evaluationResult.weaknesses.map((weakness, idx) => (
                                <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                  <span className="text-orange-500 mt-0.5">•</span>
                                  {weakness}
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>

                      {/* 建议 */}
                      {evaluationResult.suggestions.length > 0 && (
                        <div className="bg-white border border-blue-200 rounded-xl p-6">
                          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                            <TrendingUp className="w-5 h-5 text-blue-500" />
                            改编建议
                          </h3>

                          <ul className="space-y-2">
                            {evaluationResult.suggestions.map((suggestion, idx) => (
                              <li key={idx} className="flex items-start gap-2 text-sm text-gray-700">
                                <span className="text-blue-500 mt-0.5">{idx + 1}.</span>
                                {suggestion}
                              </li>
                            ))}
                          </ul>
                        </div>
                      )}

                      {/* 市场分析 */}
                      {evaluationResult.market_analysis && (
                        <div className="bg-white border border-gray-200 rounded-xl p-6">
                          <h3 className="text-lg font-semibold text-gray-900 mb-4 flex items-center gap-2">
                            <BarChart3 className="w-5 h-5" />
                            市场分析
                          </h3>

                          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                            <div className="p-4 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-500 mb-1">目标观众</p>
                              <p className="font-medium text-gray-900">
                                {evaluationResult.market_analysis.target_audience}
                              </p>
                            </div>

                            <div className="p-4 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-500 mb-1">类型适配度</p>
                              <p className={`text-2xl font-bold ${getScoreColor(evaluationResult.market_analysis.genre_fit)}`}>
                                {evaluationResult.market_analysis.genre_fit}%
                              </p>
                            </div>

                            <div className="p-4 bg-gray-50 rounded-lg">
                              <p className="text-xs text-gray-500 mb-1">商业潜力</p>
                              <p className={`text-2xl font-bold ${getScoreColor(evaluationResult.market_analysis.commercial_potential)}`}>
                                {evaluationResult.market_analysis.commercial_potential}%
                              </p>
                            </div>
                          </div>
                        </div>
                      )}
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
}

/**
 * 记忆管理页面（增强版）
 * 支持用户档案、风格分析、记忆设置等功能
 */

import { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUIStore } from '@/store/uiStore';
import { useAuthStore } from '@/store/authStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import {
  Database,
  User,
  Palette,
  Sparkles,
  Clock,
  Save,
  Trash2,
  Plus,
  Edit,
  BarChart3,
  FileText,
  Wand2
} from 'lucide-react';
import api from '@/services/api';

type UserProfile = {
  user_id: string;
  display_name?: string;
  preferences?: {
    theme?: string;
    language?: string;
    notification_enabled?: boolean;
  };
  writing_style?: {
    tone?: string;
    perspective?: string;
    pacing?: string;
  };
  demographics?: {
    age_range?: string;
    interests?: string[];
  };
  created_at?: string;
  updated_at?: string;
};

type StyleAnalysis = {
  style_profile: {
    tone: string;
    perspective: string;
    vocabulary_level: string;
    sentence_structure: string;
    dialogue_style?: string;
  };
  confidence: number;
  sample_count: number;
  last_updated: string;
};

type MemorySettings = {
  user_enabled: boolean;
  project_enabled: boolean;
  retention_days: number;
  max_context_items: number;
  effective_enabled: boolean;
  updated_at: string;
};

type StyleExample = {
  id: string;
  name: string;
  description: string;
  style_profile: any;
};

type MemorySnapshot = {
  snapshot_id: string;
  created_at: string;
  description: string;
  item_count: number;
};

export default function MemoryManagementPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [activeTab, setActiveTab] = useState<'profile' | 'style' | 'settings' | 'snapshots'>('profile');
  const [userProfile, setUserProfile] = useState<UserProfile | null>(null);
  const [styleAnalysis, setStyleAnalysis] = useState<StyleAnalysis | null>(null);
  const [memorySettings, setMemorySettings] = useState<MemorySettings | null>(null);
  const [styleExamples, setStyleExamples] = useState<StyleExample[]>([]);
  const [snapshots, setSnapshots] = useState<MemorySnapshot[]>([]);
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  // 加载用户档案
  const loadUserProfile = async () => {
    if (!user) return;

    try {
      const response = await api.get(`/juben/user/profile/${user.id}`);
      if (response.data) {
        setUserProfile(response.data);
      }
    } catch (err) {
      console.error('加载用户档案失败:', err);
    }
  };

  // 加载风格分析
  const loadStyleAnalysis = async () => {
    if (!user) return;

    try {
      const response = await api.get('/juben/user/style/examples');
      if (response.data?.examples) {
        setStyleExamples(response.data.examples);
      }
    } catch (err) {
      console.error('加载风格示例失败:', err);
    }
  };

  // 分析用户风格
  const analyzeStyle = async (content: string) => {
    if (!content.trim() || !user) {
      alert('请输入要分析的内容');
      return;
    }

    setIsAnalyzing(true);
    try {
      const response = await api.post('/juben/user/style/analyze', {
        user_id: user.id,
        content,
        analysis_type: 'comprehensive'
      });

      if (response.data) {
        setStyleAnalysis(response.data);
      }
    } catch (err) {
      console.error('风格分析失败:', err);
      alert('风格分析失败');
    } finally {
      setIsAnalyzing(false);
    }
  };

  // 保存用户档案
  const saveUserProfile = async () => {
    if (!user || !userProfile) return;

    try {
      const response = await api.post('/juben/user/profile', {
        user_id: user.id,
        ...userProfile
      });

      if (response.success) {
        alert('档案保存成功');
      } else {
        alert('档案保存失败');
      }
    } catch (err) {
      console.error('保存档案失败:', err);
      alert('保存档案失败');
    }
  };

  // 保存风格配置
  const saveStyleProfile = async (styleProfile: any) => {
    if (!user) return;

    try {
      const response = await api.post('/juben/user/style/save', {
        user_id: user.id,
        style_profile: styleProfile
      });

      if (response.success) {
        alert('风格配置保存成功');
      }
    } catch (err) {
      console.error('保存风格配置失败:', err);
      alert('保存风格配置失败');
    }
  };

  // 加载记忆快照
  const loadSnapshots = async () => {
    if (!user) return;

    try {
      const response = await api.get('/juben/user/memory/snapshots');
      if (response.data?.snapshots) {
        setSnapshots(response.data.snapshots);
      }
    } catch (err) {
      console.error('加载快照失败:', err);
    }
  };

  // 创建快照
  const createSnapshot = async (description: string) => {
    if (!user) return;

    try {
      const response = await api.post('/juben/user/memory/snapshots', {
        user_id: user.id,
        description
      });

      if (response.success) {
        alert('快照创建成功');
        loadSnapshots();
      }
    } catch (err) {
      console.error('创建快照失败:', err);
      alert('创建快照失败');
    }
  };

  // 恢复快照
  const restoreSnapshot = async (snapshotId: string) => {
    if (!confirm('确定要恢复到此快照吗？当前记忆状态将被覆盖。')) return;

    try {
      const response = await api.post(`/juben/user/memory/snapshots/${snapshotId}/restore`, {});
      if (response.success) {
        alert('快照恢复成功');
      }
    } catch (err) {
      console.error('恢复快照失败:', err);
      alert('恢复快照失败');
    }
  };

  useEffect(() => {
    if (user) {
      loadUserProfile();
      loadStyleAnalysis();
      loadSnapshots();
    }
  }, [user]);

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
                  <Database className="w-6 h-6 text-white" />
                </div>
                <div>
                  <h1 className="text-2xl font-bold text-gray-900">记忆管理</h1>
                  <p className="text-sm text-gray-500 mt-1">
                    管理用户档案、写作风格和记忆设置
                  </p>
                </div>
              </div>

              {/* 标签页 */}
              <div className="flex items-center gap-2 mt-6">
                <button
                  onClick={() => setActiveTab('profile')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'profile'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <User className="w-4 h-4 mr-2" />
                  用户档案
                </button>
                <button
                  onClick={() => setActiveTab('style')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'style'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Palette className="w-4 h-4 mr-2" />
                  风格分析
                </button>
                <button
                  onClick={() => setActiveTab('settings')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'settings'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Sparkles className="w-4 h-4 mr-2" />
                  记忆设置
                </button>
                <button
                  onClick={() => setActiveTab('snapshots')}
                  className={`px-4 py-2 rounded-lg text-sm font-medium transition-colors ${
                    activeTab === 'snapshots'
                      ? 'bg-black text-white'
                      : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                  }`}
                >
                  <Clock className="w-4 h-4 mr-2" />
                  记忆快照
                </button>
              </div>
            </div>
          </div>

          {/* 主内容区 */}
          <div className="flex-1 overflow-y-auto p-6">
            <div className="max-w-7xl mx-auto">
              {activeTab === 'profile' && userProfile && (
                <div className="space-y-6">
                  {/* 用户基本信息 */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-6">
                      <h2 className="text-lg font-semibold text-gray-900">用户档案</h2>
                      <button
                        onClick={saveUserProfile}
                        className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm"
                      >
                        <Save className="w-4 h-4" />
                        保存
                      </button>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">显示名称</label>
                        <input
                          type="text"
                          value={userProfile.display_name || ''}
                          onChange={(e) => setUserProfile({ ...userProfile, display_name: e.target.value })}
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm"
                          placeholder="输入显示名称"
                        />
                      </div>

                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">用户ID</label>
                        <input
                          type="text"
                          value={userProfile.user_id}
                          disabled
                          className="w-full px-4 py-2 border border-gray-200 rounded-lg bg-gray-50 text-gray-500 text-sm"
                        />
                      </div>
                    </div>

                    {/* 写作风格偏好 */}
                    <div className="mt-6">
                      <h3 className="text-sm font-medium text-gray-700 mb-3">写作风格偏好</h3>
                      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                        <div>
                          <label className="block text-xs text-gray-600 mb-1">基调</label>
                          <select
                            value={userProfile.writing_style?.tone || ''}
                            onChange={(e) => setUserProfile({
                              ...userProfile,
                              writing_style: { ...userProfile.writing_style, tone: e.target.value }
                            })}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                          >
                            <option value="">选择基调</option>
                            <option value="formal">正式</option>
                            <option value="casual">随意</option>
                            <option value="dramatic">戏剧化</option>
                            <option value="humorous">幽默</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs text-gray-600 mb-1">视角</label>
                          <select
                            value={userProfile.writing_style?.perspective || ''}
                            onChange={(e) => setUserProfile({
                              ...userProfile,
                              writing_style: { ...userProfile.writing_style, perspective: e.target.value }
                            })}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                          >
                            <option value="">选择视角</option>
                            <option value="first_person">第一人称</option>
                            <option value="third_person_limited">第三人称限制</option>
                            <option value="third_person_omniscient">第三人称全知</option>
                          </select>
                        </div>

                        <div>
                          <label className="block text-xs text-gray-600 mb-1">节奏</label>
                          <select
                            value={userProfile.writing_style?.pacing || ''}
                            onChange={(e) => setUserProfile({
                              ...userProfile,
                              writing_style: { ...userProfile.writing_style, pacing: e.target.value }
                            })}
                            className="w-full px-3 py-2 border border-gray-200 rounded-lg text-sm focus:outline-none focus:border-black"
                          >
                            <option value="">选择节奏</option>
                            <option value="fast">快节奏</option>
                            <option value="medium">中等节奏</option>
                            <option value="slow">慢节奏</option>
                            <option value="variable">多变节奏</option>
                          </select>
                        </div>
                      </div>
                    </div>

                    {/* 兴趣标签 */}
                    <div className="mt-6">
                      <h3 className="text-sm font-medium text-gray-700 mb-3">兴趣标签</h3>
                      <div className="flex flex-wrap gap-2">
                        {userProfile.demographics?.interests?.map((interest, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1.5 bg-gray-100 text-gray-700 rounded-full text-sm"
                          >
                            {interest}
                          </span>
                        )) || <span className="text-sm text-gray-400">无</span>}
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {activeTab === 'style' && (
                <div className="space-y-6">
                  {/* 风格分析工具 */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">风格分析</h2>

                    <div className="space-y-4">
                      <div>
                        <label className="block text-sm font-medium text-gray-700 mb-2">分析内容</label>
                        <textarea
                          value={''}
                          onChange={(e) => {
                            // 这里可以用state保存输入内容
                          }}
                          placeholder="输入要分析风格的内容..."
                          rows={6}
                          className="w-full px-4 py-3 border border-gray-200 rounded-lg focus:outline-none focus:border-black text-sm resize-none"
                        />
                      </div>

                      <button
                        onClick={() => analyzeStyle('示例内容')}
                        disabled={isAnalyzing}
                        className="w-full px-4 py-3 bg-black text-white rounded-lg hover:bg-gray-800 disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors"
                      >
                        {isAnalyzing ? (
                          <>
                            分析中...
                          </>
                        ) : (
                          <>
                            <Wand2 className="w-4 h-4 mr-2" />
                            分析风格
                          </>
                        )}
                      </button>
                    </div>

                    {/* 分析结果 */}
                    {styleAnalysis && (
                      <div className="mt-6 p-4 bg-blue-50 border border-blue-200 rounded-lg">
                        <h3 className="text-sm font-medium text-blue-900 mb-3">分析结果</h3>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                          <div>
                            <p className="text-xs text-blue-700 mb-1">基调</p>
                            <p className="text-sm font-medium text-blue-900">{styleAnalysis.style_profile.tone}</p>
                          </div>

                          <div>
                            <p className="text-xs text-blue-700 mb-1">视角</p>
                            <p className="text-sm font-medium text-blue-900">{styleAnalysis.style_profile.perspective}</p>
                          </div>

                          <div>
                            <p className="text-xs text-blue-700 mb-1">词汇水平</p>
                            <p className="text-sm font-medium text-blue-900">{styleAnalysis.style_profile.vocabulary_level}</p>
                          </div>

                          <div>
                            <p className="text-xs text-blue-700 mb-1">句子结构</p>
                            <p className="text-sm font-medium text-blue-900">{styleAnalysis.style_profile.sentence_structure}</p>
                          </div>
                        </div>

                        <div className="mt-4 pt-4 border-t border-blue-200">
                          <div className="flex items-center justify-between text-xs text-blue-700">
                            <span>置信度</span>
                            <span className="font-medium">{styleAnalysis.confidence?.toFixed(1)}%</span>
                          </div>
                          <div className="flex items-center justify-between text-xs text-blue-700 mt-1">
                            <span>样本数量</span>
                            <span className="font-medium">{styleAnalysis.sample_count}</span>
                          </div>
                          <div className="flex items-center justify-between text-xs text-blue-700 mt-1">
                            <span>最后更新</span>
                            <span className="font-medium">
                              {styleAnalysis.last_updated ? new Date(styleAnalysis.last_updated).toLocaleString('zh-CN') : '-'}
                            </span>
                          </div>
                        </div>

                        <div className="mt-4 pt-4 border-t border-blue-200 flex gap-2">
                          <button
                            onClick={() => saveStyleProfile(styleAnalysis.style_profile)}
                            className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                          >
                            保存为风格配置
                          </button>
                          <button
                            onClick={() => setStyleAnalysis(null)}
                            className="px-4 py-2 border border-gray-200 rounded-lg hover:bg-gray-50 text-sm"
                          >
                            清除结果
                          </button>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* 风格示例 */}
                  {styleExamples.length > 0 && (
                    <div className="bg-white border border-gray-200 rounded-xl p-6">
                      <h2 className="text-lg font-semibold text-gray-900 mb-4">风格示例</h2>

                      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                        {styleExamples.map((example) => (
                          <div
                            key={example.id}
                            className="p-4 border border-gray-200 rounded-lg hover:shadow-lg transition-all cursor-pointer"
                            onClick={() => {
                              if (confirm('确定要应用此风格配置吗？')) {
                                saveStyleProfile(example.style_profile);
                              }
                            }}
                          >
                            <h3 className="text-sm font-medium text-gray-900 mb-2">{example.name}</h3>
                            <p className="text-xs text-gray-600">{example.description}</p>
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>
              )}

              {activeTab === 'snapshots' && (
                <div className="space-y-6">
                  {/* 创建快照 */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <div className="flex items-center justify-between mb-4">
                      <h2 className="text-lg font-semibold text-gray-900">创建快照</h2>
                      <button
                        onClick={() => {
                          const description = prompt('请输入快照描述：', `快照 ${new Date().toLocaleString('zh-CN')}`);
                          if (description) {
                            createSnapshot(description);
                          }
                        }}
                        className="flex items-center gap-2 px-4 py-2 bg-black text-white rounded-lg hover:bg-gray-800 transition-colors text-sm"
                      >
                        <Plus className="w-4 h-4" />
                        创建快照
                      </button>
                    </div>

                    <p className="text-sm text-gray-500">
                      快照可以保存当前的记忆状态，方便后续恢复
                    </p>
                  </div>

                  {/* 快照列表 */}
                  <div className="bg-white border border-gray-200 rounded-xl p-6">
                    <h2 className="text-lg font-semibold text-gray-900 mb-4">快照列表</h2>

                    {snapshots.length === 0 ? (
                      <div className="text-center py-8 text-gray-500">
                        <FileText className="w-12 h-12 mx-auto mb-3 opacity-50" />
                        <p>暂无快照</p>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        {snapshots.map((snapshot) => (
                          <div
                            key={snapshot.snapshot_id}
                            className="flex items-center justify-between p-4 border border-gray-200 rounded-lg hover:shadow-md transition-all"
                          >
                            <div className="flex-1">
                              <h3 className="text-sm font-medium text-gray-900">{snapshot.description}</h3>
                              <p className="text-xs text-gray-500 mt-1">
                                {snapshot.item_count} 个记忆项 · {new Date(snapshot.created_at).toLocaleString('zh-CN')}
                              </p>
                            </div>

                            <div className="flex items-center gap-2">
                              <button
                                onClick={() => restoreSnapshot(snapshot.snapshot_id)}
                                className="px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 text-sm"
                              >
                                恢复
                              </button>
                              <button
                                onClick={() => {
                                  if (confirm('确定要删除此快照吗？')) {
                                    setSnapshots(prev => prev.filter(s => s.snapshot_id !== snapshot.snapshot_id));
                                  }
                                }}
                                className="p-1.5 hover:bg-red-100 rounded-lg transition-colors"
                              >
                                <Trash2 className="w-4 h-4 text-red-500" />
                              </button>
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </div>
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

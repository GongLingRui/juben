/**
 * 设置弹窗组件 - 增强版
 * 包含更多设置选项
 */

import { useUIStore } from '@/store/uiStore';
import { useSettingsStore } from '@/store/settingsStore';
import { useAgents } from '@/hooks/useAgents';
import { X, Monitor, Type, Zap, Eye, RotateCcw, Globe, Database, RefreshCw, Hash } from 'lucide-react';
import { useEffect, useState } from 'react';
import { getMemorySettings, updateMemorySettings } from '@/services/memoryService';

const MODELS = [
  { value: 'glm-4.7-flash', label: 'GLM-4.7 Flash', desc: '最新快速响应 (推荐)' },
  { value: 'glm-4-flash', label: 'GLM-4 Flash', desc: '快速响应' },
  { value: 'glm-4.1v-thinking-flash', label: 'GLM-4.1V Thinking', desc: '深度推理' },
  { value: 'glm-4-plus', label: 'GLM-4 Plus', desc: '强大性能' },
  { value: 'glm-4-air', label: 'GLM-4 Air', desc: '轻量级' },
  { value: 'qwen2.5:7b', label: 'Qwen2.5 7B', desc: '本地常用默认' },
];

const MODEL_PROVIDERS = [
  { value: 'zhipu', label: '智谱AI' },
  { value: 'openrouter', label: 'OpenRouter' },
  { value: 'openai', label: 'OpenAI' },
  { value: 'local', label: '本地模型' },
  { value: 'ollama', label: 'Ollama' },
];

export default function SettingsModal() {
  const { settingsModalOpen, setSettingsModalOpen } = useUIStore();
  const {
    theme,
    model,
    modelProvider,
    streamEnabled,
    showThoughtChain,
    fontSize,
    autoScroll,
    showTimestamp,
    enableWebSearch,
    enableKnowledgeBase,
    enableRetryOnError,
    maxRetries,
    memoryUserEnabled,
    memoryProjectEnabled,
    setTheme,
    setModel,
    setModelProvider,
    setStreamEnabled,
    setShowThoughtChain,
    setFontSize,
    setAutoScroll,
    setShowTimestamp,
    setEnableWebSearch,
    setEnableKnowledgeBase,
    setEnableRetryOnError,
    setMaxRetries,
    setMemoryUserEnabled,
    setMemoryProjectEnabled,
    resetSettings,
  } = useSettingsStore();

  const { activeAgentData } = useAgents();
  const [localModelInput, setLocalModelInput] = useState('');
  const [memoryEffectiveEnabled, setMemoryEffectiveEnabled] = useState(true);
  const userId = localStorage.getItem('userId') || 'default-user';
  const projectId = localStorage.getItem('projectId') || undefined;

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getMemorySettings({ user_id: userId, project_id: projectId });
        if (res?.data) {
          setMemoryUserEnabled(res.data.user_enabled);
          setMemoryProjectEnabled(res.data.project_enabled);
          setMemoryEffectiveEnabled(res.data.effective_enabled);
        }
      } catch {
        setMemoryEffectiveEnabled(memoryUserEnabled && memoryProjectEnabled);
      }
    };
    load();
  }, [userId, projectId]);

  const handleToggleUserMemory = async () => {
    const next = !memoryUserEnabled;
    setMemoryUserEnabled(next);
    try {
      const res = await updateMemorySettings({ user_id: userId, project_id: projectId, user_enabled: next });
      if (res?.data) {
        setMemoryProjectEnabled(res.data.project_enabled);
        setMemoryEffectiveEnabled(res.data.effective_enabled);
      } else {
        setMemoryEffectiveEnabled(next && memoryProjectEnabled);
      }
    } catch {
      setMemoryEffectiveEnabled(next && memoryProjectEnabled);
    }
  };

  const handleToggleProjectMemory = async () => {
    const next = !memoryProjectEnabled;
    setMemoryProjectEnabled(next);
    try {
      const res = await updateMemorySettings({ user_id: userId, project_id: projectId, project_enabled: next });
      if (res?.data) {
        setMemoryUserEnabled(res.data.user_enabled);
        setMemoryEffectiveEnabled(res.data.effective_enabled);
      } else {
        setMemoryEffectiveEnabled(memoryUserEnabled && next);
      }
    } catch {
      setMemoryEffectiveEnabled(memoryUserEnabled && next);
    }
  };

  useEffect(() => {
    if (modelProvider === 'local' || modelProvider === 'ollama') {
      setLocalModelInput(model);
    }
  }, [modelProvider, model]);

  if (!settingsModalOpen) return null;

  return (
    <>
      {/* 遮罩 */}
      <div
        className="fixed inset-0 bg-black/50 z-50 animate-fade-in"
        onClick={() => setSettingsModalOpen(false)}
      />

      {/* 弹窗 */}
      <div className="fixed inset-0 flex items-center justify-center z-50 p-4">
        <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg animate-scale-in max-h-[90vh] overflow-y-auto">
          {/* 头部 */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 sticky top-0 bg-white z-10">
            <h2 className="text-lg font-semibold">设置</h2>
            <button
              onClick={() => setSettingsModalOpen(false)}
              className="p-2 rounded-lg hover:bg-gray-100 hover-scale icon-rotate transition-all"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* 当前Agent信息 */}
          {activeAgentData && (
            <div className="mx-6 mt-4 p-4 bg-gray-50 rounded-lg">
              <div className="flex items-start gap-3">
                <span className="text-3xl">{activeAgentData.icon}</span>
                <div className="flex-1">
                  <h3 className="font-semibold text-gray-900">{activeAgentData.displayName}</h3>
                  <p className="text-sm text-gray-500 mt-1">{activeAgentData.description}</p>
                  <div className="flex items-center gap-2 mt-2">
                    <span className="text-xs px-2 py-0.5 bg-white text-gray-600 rounded">
                      {activeAgentData.category}
                    </span>
                    <span className="text-xs text-gray-400">模型: {activeAgentData.model}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* 内容 */}
          <div className="p-6 space-y-6">
            {/* 模型选择 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Zap className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">AI模型</label>
              </div>
              <select
                value={model}
                onChange={(e) => setModel(e.target.value)}
                className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black input-focus-effect transition-all"
              >
                {MODELS.map((m) => (
                  <option key={m.value} value={m.value}>
                    {m.label} - {m.desc}
                  </option>
                ))}
              </select>
              {(modelProvider === 'local' || modelProvider === 'ollama') && (
                <div className="mt-2">
                  <input
                    value={localModelInput}
                    onChange={(e) => {
                      setLocalModelInput(e.target.value);
                      setModel(e.target.value);
                    }}
                    placeholder="输入本地模型名称，如 qwen2.5:7b"
                    className="w-full px-4 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:border-black"
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    本地模型名称来自你的本地服务（Ollama/LM Studio/vLLM）
                  </p>
                </div>
              )}
            </div>

            {/* 模型提供商 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Hash className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">模型提供商</label>
              </div>
              <div className="grid grid-cols-3 gap-2">
                {MODEL_PROVIDERS.map((provider) => (
                  <button
                    key={provider.value}
                    onClick={() => setModelProvider(provider.value as any)}
                    className={`px-3 py-2 text-sm rounded-lg border-2 transition-all hover-scale ${
                      modelProvider === provider.value
                        ? 'border-gray-900 bg-gray-50'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {provider.label}
                  </button>
                ))}
              </div>
            </div>

            {/* 主题 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Monitor className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">主题</label>
              </div>
              <div className="flex gap-2">
                <button
                  onClick={() => setTheme('light')}
                  className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                    theme === 'light'
                      ? 'border-gray-900 bg-gray-50 shadow-sm'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  浅色
                </button>
                <button
                  onClick={() => setTheme('dark')}
                  className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                    theme === 'dark'
                      ? 'border-gray-900 bg-gray-50 shadow-sm'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  深色
                </button>
              </div>
            </div>

            {/* 字体大小 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Type className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">字体大小</label>
              </div>
              <div className="flex gap-2">
                {(['sm', 'md', 'lg'] as const).map((size) => (
                  <button
                    key={size}
                    onClick={() => setFontSize(size)}
                    className={`flex-1 px-4 py-2 rounded-lg border-2 transition-all hover-scale ${
                      fontSize === size
                        ? 'border-gray-900 bg-gray-50 shadow-sm'
                        : 'border-gray-200 hover:border-gray-300'
                    }`}
                  >
                    {size === 'sm' ? '小' : size === 'md' ? '中' : '大'}
                  </button>
                ))}
              </div>
            </div>

            {/* 开关选项 - 第一组 */}
            <div className="space-y-4">
              {/* 流式响应 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Zap className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">流式响应</div>
                    <div className="text-sm text-gray-500">实时显示生成内容</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={streamEnabled}
                    onChange={(e) => setStreamEnabled(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setStreamEnabled(!streamEnabled)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      streamEnabled ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        streamEnabled ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 网络搜索 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Globe className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">网络搜索</div>
                    <div className="text-sm text-gray-500">启用实时网络信息检索</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={enableWebSearch}
                    onChange={(e) => setEnableWebSearch(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setEnableWebSearch(!enableWebSearch)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      enableWebSearch ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        enableWebSearch ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 知识库 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Database className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">知识库查询</div>
                    <div className="text-sm text-gray-500">检索专业剧本资料</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={enableKnowledgeBase}
                    onChange={(e) => setEnableKnowledgeBase(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setEnableKnowledgeBase(!enableKnowledgeBase)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      enableKnowledgeBase ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        enableKnowledgeBase ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 错误重试 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <RefreshCw className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">自动重试</div>
                    <div className="text-sm text-gray-500">错误时自动重试 (最多{maxRetries}次)</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={enableRetryOnError}
                    onChange={(e) => setEnableRetryOnError(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setEnableRetryOnError(!enableRetryOnError)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      enableRetryOnError ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        enableRetryOnError ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 显示思考链 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <Eye className="w-5 h-5 text-gray-600" />
                  <div>
                    <div className="font-medium text-gray-900">思考过程</div>
                    <div className="text-sm text-gray-500">显示AI推理思考链</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showThoughtChain}
                    onChange={(e) => setShowThoughtChain(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setShowThoughtChain(!showThoughtChain)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      showThoughtChain ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        showThoughtChain ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 自动滚动 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-xs">↓</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">自动滚动</div>
                    <div className="text-sm text-gray-500">新消息时自动滚动到底部</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={autoScroll}
                    onChange={(e) => setAutoScroll(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setAutoScroll(!autoScroll)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      autoScroll ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        autoScroll ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>

              {/* 显示时间戳 */}
              <label className="flex items-center justify-between cursor-pointer">
                <div className="flex items-center gap-3">
                  <div className="w-5 h-5 bg-gray-200 rounded-full flex items-center justify-center">
                    <span className="text-xs">⏱</span>
                  </div>
                  <div>
                    <div className="font-medium text-gray-900">时间戳</div>
                    <div className="text-sm text-gray-500">显示消息时间</div>
                  </div>
                </div>
                <div className="relative">
                  <input
                    type="checkbox"
                    checked={showTimestamp}
                    onChange={(e) => setShowTimestamp(e.target.checked)}
                    className="sr-only"
                  />
                  <div
                    onClick={() => setShowTimestamp(!showTimestamp)}
                    className={`w-11 h-6 rounded-full transition-colors cursor-pointer ${
                      showTimestamp ? 'bg-gray-900' : 'bg-gray-200'
                    }`}
                  >
                    <div
                      className={`w-5 h-5 bg-white rounded-full shadow transition-transform ${
                        showTimestamp ? 'translate-x-5' : 'translate-x-0.5'
                      }`}
                    />
                  </div>
                </div>
              </label>
            </div>

            {/* 记忆开关 */}
            <div className="space-y-3">
              <div className="flex items-center gap-2">
                <Database className="w-5 h-5 text-gray-600" />
                <label className="font-medium text-gray-900">记忆开关</label>
                <span className="text-xs text-gray-400">生效: {memoryEffectiveEnabled ? '开启' : '关闭'}</span>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>用户维度记忆</span>
                <button
                  onClick={handleToggleUserMemory}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    memoryUserEnabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {memoryUserEnabled ? '已开启' : '已关闭'}
                </button>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>项目维度记忆</span>
                <button
                  onClick={handleToggleProjectMemory}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    memoryProjectEnabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {memoryProjectEnabled ? '已开启' : '已关闭'}
                </button>
              </div>
              {!projectId && (
                <div className="text-xs text-gray-400">未选择项目时，项目维度记忆不生效。</div>
              )}
            </div>

            {/* 重试次数 */}
            {enableRetryOnError && (
              <div className="space-y-3">
                <div className="flex items-center gap-2">
                  <RefreshCw className="w-5 h-5 text-gray-600" />
                  <label className="font-medium text-gray-900">最大重试次数</label>
                </div>
                <div className="flex gap-2">
                  {[1, 2, 3, 5].map((count) => (
                    <button
                      key={count}
                      onClick={() => setMaxRetries(count)}
                      className={`flex-1 px-4 py-2 text-sm rounded-lg border-2 transition-all hover-scale ${
                        maxRetries === count
                          ? 'border-gray-900 bg-gray-50 shadow-sm'
                          : 'border-gray-200 hover:border-gray-300'
                      }`}
                    >
                      {count}
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>

          {/* 底部 */}
          <div className="flex items-center justify-between px-6 py-4 border-t border-gray-200 sticky bottom-0 bg-white">
            <button
              onClick={resetSettings}
              className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900 transition-all hover-scale icon-rotate"
            >
              <RotateCcw className="w-4 h-4" />
              重置设置
            </button>
            <button
              onClick={() => setSettingsModalOpen(false)}
              className="px-6 py-2 text-sm text-white bg-gray-900 rounded-lg hover:bg-gray-800 transition-all hover-scale shadow-md hover:shadow-lg"
            >
              完成
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

/**
 * 工作流监控页面
 * 集成工作流可视化、模板管理和执行历史
 */

import React, { useState, useRef, useEffect } from 'react';
import { Play, Pause, RotateCcw, Download, FileText, Clock, Layers, History } from 'lucide-react';
import { WorkflowVisualizer, WorkflowEvent, NodeStatus, WorkflowTemplateManager, WorkflowHistory } from '@/components/workflow';
import { API_BASE_URL, getAuthHeaderValue } from '@/services/api';

interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  nodes: any[];
  variables: Record<string, any>;
  createdAt: string;
  updatedAt: string;
}

interface WorkflowExecution {
  id: string;
  workflowId: string;
  workflowName: string;
  status: 'success' | 'failed' | 'running' | 'paused';
  startTime: string;
  endTime?: string;
  duration?: number;
  input: any;
  output?: any;
  errorMessage?: string;
  nodesExecuted: number;
  nodesTotal: number;
}

type TabType = 'monitor' | 'templates' | 'history';

export default function WorkflowMonitorPage() {
  const [activeTab, setActiveTab] = useState<TabType>('monitor');
  const [workflowId, setWorkflowId] = useState<string>('');
  const [isRunning, setIsRunning] = useState(false);
  const [inputText, setInputText] = useState('');
  const [templateManagerOpen, setTemplateManagerOpen] = useState(false);
  const [historyOpen, setHistoryOpen] = useState(false);
  const [templates, setTemplates] = useState<WorkflowTemplate[]>([]);
  const [executions, setExecutions] = useState<WorkflowExecution[]>([]);
  const [workflowEvents, setWorkflowEvents] = useState<WorkflowEvent[]>([]);
  const [executionDetailOpen, setExecutionDetailOpen] = useState(false);
  const [selectedExecution, setSelectedExecution] = useState<WorkflowExecution | null>(null);
  const eventLogRef = useRef<HTMLDivElement>(null);
  const currentExecutionRef = useRef<WorkflowExecution | null>(null);

  useEffect(() => {
    try {
      const rawTemplates = localStorage.getItem('workflow_templates');
      const rawExecutions = localStorage.getItem('workflow_executions');
      if (rawTemplates) setTemplates(JSON.parse(rawTemplates));
      if (rawExecutions) setExecutions(JSON.parse(rawExecutions));
    } catch {
      setTemplates([]);
      setExecutions([]);
    }
  }, []);

  useEffect(() => {
    localStorage.setItem('workflow_templates', JSON.stringify(templates));
  }, [templates]);

  useEffect(() => {
    localStorage.setItem('workflow_executions', JSON.stringify(executions));
  }, [executions]);

  // 启动工作流
  const handleStartWorkflow = async () => {
    try {
      setIsRunning(true);
      setWorkflowEvents([]);
      if (eventLogRef.current) {
        eventLogRef.current.innerHTML = '';
      }
      const executionId = `exec_${Date.now()}`;
      const executionRecord: WorkflowExecution = {
        id: executionId,
        workflowId: workflowId || 'plot_points_workflow',
        workflowName: '情节点工作流',
        status: 'running',
        startTime: new Date().toISOString(),
        input: { text: inputText || '请生成一个现代都市言情短剧的故事大纲' },
        nodesExecuted: 0,
        nodesTotal: 8,
      };
      currentExecutionRef.current = executionRecord;
      setExecutions((prev) => [executionRecord, ...prev]);

      const response = await fetch(`${API_BASE_URL}/juben/plot-points-workflow/execute`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(getAuthHeaderValue() ? { Authorization: getAuthHeaderValue() as string } : {}),
        },
        body: JSON.stringify({
          input: inputText || '请生成一个现代都市言情短剧的故事大纲',
          user_id: 'demo_user',
          session_id: `session_${Date.now()}`,
        }),
      });

      if (!response.ok) {
        throw new Error('Failed to start workflow');
      }

      // 处理 SSE 响应
      const reader = response.body?.getReader();
      const decoder = new TextDecoder();

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
                handleWorkflowEvent(data);
              } catch (e) {
                console.error('Failed to parse event:', e);
              }
            }
          }
        }
      }

      setExecutions((prev) =>
        prev.map((execution) =>
          execution.id === executionId
            ? {
                ...execution,
                status: 'success',
                endTime: new Date().toISOString(),
                duration: Date.now() - new Date(execution.startTime).getTime(),
              }
            : execution
        )
      );
    } catch (error) {
      console.error('Workflow error:', error);
      if (currentExecutionRef.current) {
        setExecutions((prev) =>
          prev.map((execution) =>
            execution.id === currentExecutionRef.current!.id
              ? {
                  ...execution,
                  status: 'failed',
                  endTime: new Date().toISOString(),
                  duration: Date.now() - new Date(execution.startTime).getTime(),
                  errorMessage: error instanceof Error ? error.message : '工作流执行失败',
                }
              : execution
          )
        );
      }
    } finally {
      setIsRunning(false);
    }
  };

  // 处理工作流事件
  const handleWorkflowEvent = (event: WorkflowEvent | any) => {
    const eventType = event.event_type || event.event;
    const metadata = event.metadata || event.data?.metadata || {};
    // 更新 workflowId
    if (metadata?.workflow_id) {
      setWorkflowId(metadata.workflow_id);
    }

    // 记录事件日志
    if (eventLogRef.current) {
      const logEntry = document.createElement('div');
      logEntry.className = 'text-xs font-mono mb-1';
      logEntry.textContent = `[${new Date().toLocaleTimeString()}] ${JSON.stringify(event)}`;
      eventLogRef.current.appendChild(logEntry);
      eventLogRef.current.scrollTop = eventLogRef.current.scrollHeight;
    }
    setWorkflowEvents((prev) => [...prev, event]);

    if (eventType === 'workflow_node_event' && currentExecutionRef.current) {
      setExecutions((prev) =>
        prev.map((execution) =>
          execution.id === currentExecutionRef.current!.id
            ? {
                ...execution,
                nodesExecuted: Math.min(
                  execution.nodesExecuted + (metadata?.status === NodeStatus.SUCCESS ? 1 : 0),
                  execution.nodesTotal
                ),
              }
            : execution
        )
      );
    }
  };

  // 重置工作流
  const handleReset = () => {
    setWorkflowId('');
    setInputText('');
    setIsRunning(false);
    setWorkflowEvents([]);
    if (eventLogRef.current) {
      eventLogRef.current.innerHTML = '';
    }
  };

  const handleDownloadLog = () => {
    if (workflowEvents.length === 0) return;
    const content = workflowEvents.map((event) => JSON.stringify(event)).join('\n');
    const blob = new Blob([content], { type: 'application/json;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `workflow_events_${Date.now()}.jsonl`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  // 模板管理 handlers
  const handleLoadTemplate = (templateId: string) => {
    const template = templates.find((t) => t.id === templateId);
    if (template) {
      setWorkflowId(template.id);
      setInputText(template.description || '');
      setTemplateManagerOpen(false);
    }
  };

  const handleSaveTemplate = async (template: Omit<WorkflowTemplate, 'id' | 'createdAt' | 'updatedAt'>) => {
    const newTemplate: WorkflowTemplate = {
      ...template,
      id: `template_${Date.now()}`,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setTemplates([...templates, newTemplate]);
  };

  const handleDeleteTemplate = async (templateId: string) => {
    setTemplates(templates.filter((t) => t.id !== templateId));
  };

  // 历史记录 handlers
  const handleRerunExecution = async (executionId: string) => {
    const execution = executions.find((e) => e.id === executionId);
    if (execution) {
      setInputText(JSON.stringify(execution.input));
      setActiveTab('monitor');
      await handleStartWorkflow();
    }
  };

  const handleViewExecutionDetails = (executionId: string) => {
    const execution = executions.find((e) => e.id === executionId) || null;
    setSelectedExecution(execution);
    setExecutionDetailOpen(true);
  };

  const renderTabContent = () => {
    switch (activeTab) {
      case 'monitor':
        return (
          <div className="flex-1 flex overflow-hidden">
            {/* 工作流可视化 */}
            <div className="flex-1">
              <WorkflowVisualizer
                workflowId={workflowId}
                onEvent={handleWorkflowEvent}
                externalEvents={workflowEvents}
                className="h-full"
              />
            </div>

            {/* 事件日志侧边栏 */}
            <aside className="w-80 bg-white dark:bg-gray-800 border-l border-gray-200 dark:border-gray-700 flex flex-col">
              <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
                <h2 className="font-semibold text-gray-900 dark:text-white">事件日志</h2>
                <button
                  onClick={handleDownloadLog}
                  className="p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
                >
                  <Download className="w-4 h-4 text-gray-500" />
                </button>
              </div>
              <div
                ref={eventLogRef}
                className="flex-1 p-4 overflow-y-auto text-xs font-mono space-y-1"
              />
            </aside>
          </div>
        );

      case 'templates':
        return (
          <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              <Layers className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                工作流模板管理
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                管理和复用工作流模板
              </p>
              <button
                onClick={() => setTemplateManagerOpen(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                打开模板管理器
              </button>
            </div>
          </div>
        );

      case 'history':
        return (
          <div className="flex-1 flex items-center justify-center bg-gray-50 dark:bg-gray-900">
            <div className="text-center">
              <History className="w-16 h-16 mx-auto mb-4 text-gray-400" />
              <h3 className="text-lg font-semibold text-gray-900 dark:text-white mb-2">
                执行历史记录
              </h3>
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                查看过往工作流执行记录
              </p>
              <button
                onClick={() => setHistoryOpen(true)}
                className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg font-medium transition-colors"
              >
                查看执行历史
              </button>
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className="h-screen flex flex-col bg-gray-50 dark:bg-gray-900">
      {/* 头部控制栏 */}
      <header className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 px-6 py-4">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
              工作流监控器
            </h1>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
              监控、管理和分析工作流执行
            </p>
          </div>
          {activeTab === 'monitor' && (
            <div className="flex gap-3">
              <button
                onClick={handleStartWorkflow}
                disabled={isRunning}
                className="flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white rounded-lg font-medium transition-colors"
              >
                <Play className="w-4 h-4" />
                启动工作流
              </button>
              <button
                onClick={handleReset}
                className="flex items-center gap-2 px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-900 dark:text-white rounded-lg font-medium transition-colors"
              >
                <RotateCcw className="w-4 h-4" />
                重置
              </button>
            </div>
          )}
        </div>

        {/* 标签页导航 */}
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab('monitor')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'monitor'
                ? 'bg-black text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            <FileText className="w-4 h-4" />
            实时监控
          </button>
          <button
            onClick={() => setActiveTab('templates')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'templates'
                ? 'bg-black text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            <Layers className="w-4 h-4" />
            模板管理
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-colors ${
              activeTab === 'history'
                ? 'bg-black text-white'
                : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
            }`}
          >
            <Clock className="w-4 h-4" />
            执行历史
          </button>
        </div>

        {/* 输入区域 - 仅在监控标签显示 */}
        {activeTab === 'monitor' && (
          <div className="mt-4">
            <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
              输入文本
            </label>
            <textarea
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              placeholder="请输入要处理的文本..."
              rows={3}
              className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-700 text-gray-900 dark:text-white"
            />
          </div>
        )}
      </header>

      {/* 主内容区 */}
      {renderTabContent()}

      {/* 模板管理器弹窗 */}
      <WorkflowTemplateManager
        isOpen={templateManagerOpen}
        onClose={() => setTemplateManagerOpen(false)}
        templates={templates}
        onLoad={handleLoadTemplate}
        onSave={handleSaveTemplate}
        onDelete={handleDeleteTemplate}
      />

      {/* 执行历史弹窗 */}
      <WorkflowHistory
        isOpen={historyOpen}
        onClose={() => setHistoryOpen(false)}
        executions={executions}
        onRerun={handleRerunExecution}
        onViewDetails={handleViewExecutionDetails}
      />

      {executionDetailOpen && selectedExecution && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <div className="bg-white dark:bg-gray-800 rounded-xl shadow-xl max-w-3xl w-full max-h-[90vh] overflow-hidden">
            <div className="p-6 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div>
                <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                  执行详情
                </h3>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                  {selectedExecution.workflowName} · {selectedExecution.id}
                </p>
              </div>
              <button
                onClick={() => setExecutionDetailOpen(false)}
                className="p-2 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg"
              >
                ✕
              </button>
            </div>
            <div className="p-6 overflow-y-auto max-h-[70vh] space-y-4 text-sm">
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500">状态</div>
                  <div className="font-medium text-gray-900 dark:text-white">{selectedExecution.status}</div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">节点进度</div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {selectedExecution.nodesExecuted} / {selectedExecution.nodesTotal}
                  </div>
                </div>
                <div>
                  <div className="text-xs text-gray-500">开始时间</div>
                  <div className="font-medium text-gray-900 dark:text-white">
                    {new Date(selectedExecution.startTime).toLocaleString()}
                  </div>
                </div>
                {selectedExecution.endTime && (
                  <div>
                    <div className="text-xs text-gray-500">结束时间</div>
                    <div className="font-medium text-gray-900 dark:text-white">
                      {new Date(selectedExecution.endTime).toLocaleString()}
                    </div>
                  </div>
                )}
              </div>

              {selectedExecution.errorMessage && (
                <div className="p-3 bg-red-50 dark:bg-red-900/20 rounded-lg text-red-700 dark:text-red-300">
                  {selectedExecution.errorMessage}
                </div>
              )}

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                <div>
                  <div className="text-xs text-gray-500 mb-2">输入</div>
                  <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded-lg overflow-auto">
                    {JSON.stringify(selectedExecution.input, null, 2)}
                  </pre>
                </div>
                <div>
                  <div className="text-xs text-gray-500 mb-2">输出</div>
                  <pre className="text-xs bg-gray-50 dark:bg-gray-900 p-3 rounded-lg overflow-auto">
                    {selectedExecution.output ? JSON.stringify(selectedExecution.output, null, 2) : '暂无输出'}
                  </pre>
                </div>
              </div>
            </div>
            <div className="p-6 border-t border-gray-200 dark:border-gray-700 flex justify-end">
              <button
                onClick={() => setExecutionDetailOpen(false)}
                className="px-4 py-2 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 rounded-lg"
              >
                关闭
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

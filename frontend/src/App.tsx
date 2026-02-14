/**
 * App 根组件
 */

import { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { useAgentStore } from '@/store/agentStore';
import { useUIStore } from '@/store/uiStore';
import { getAgents } from '@/services/agentService';
import { NotificationContainer } from '@/components/notification';
import { GlobalSearch } from '@/components/search';
import { PrivateRoute, PublicRoute } from '@/components/auth';
import { ErrorBoundary } from '@/components/common/ErrorBoundary';
import LoginPage from '@/pages/LoginPage';
import RegisterPage from '@/pages/RegisterPage';
import UnauthorizedPage from '@/pages/UnauthorizedPage';
import MainPage from '@/pages/MainPage';
import SplitScreenPage from '@/pages/SplitScreenPage';
import BaiduSearchPage from '@/pages/BaiduSearchPage';
import ToolsDemoPage from '@/pages/ToolsDemoPage';
import ProjectsPage from '@/pages/ProjectsPage';
import ProjectDetailPage from '@/pages/ProjectDetailPage';
import OCRPage from '@/pages/OCRPage';
import FileSystemPage from '@/pages/FileSystemPage';
import GraphVisualizationPage from '@/pages/GraphVisualizationPage';
import GraphReviewCenterPage from '@/pages/GraphReviewCenterPage';
import WorkflowMonitorPage from '@/pages/WorkflowMonitorPage';
import AdminPage from '@/pages/AdminPage';
import StatisticsPage from '@/pages/StatisticsPage';
import EvolutionPage from '@/pages/EvolutionPage';
import FeedbackPage from '@/pages/FeedbackPage';
import ABTestPage from '@/pages/ABTestPage';
import KnowledgeBasePage from '@/pages/KnowledgeBasePage';
import TokenUsagePage from '@/pages/TokenUsagePage';
import MemorySettingsPage from '@/pages/MemorySettingsPage';

function App() {
  const { setAgents } = useAgentStore();
  const { searchOpen, setSearchOpen } = useUIStore();

  useEffect(() => {
    // 加载所有 Agents
    getAgents().then(setAgents).catch(console.error);
  }, [setAgents]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setSearchOpen(!searchOpen);
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [searchOpen, setSearchOpen]);

  const handleError = (error: Error, errorInfo: any) => {
    console.error('Application error:', error, errorInfo);
  };

  return (
    <ErrorBoundary onError={handleError}>
      <BrowserRouter>
        {/* 全局通知容器 */}
        <NotificationContainer />

        {/* 全局搜索 */}
        <GlobalSearch isOpen={searchOpen} onClose={() => setSearchOpen(false)} />

        <Routes>
          {/* 公共路由 */}
          <Route
            path="/login"
            element={
              <PublicRoute>
                <LoginPage />
              </PublicRoute>
            }
          />
          <Route
            path="/register"
            element={
              <PublicRoute>
                <RegisterPage />
              </PublicRoute>
            }
          />

          {/* 未授权页面 */}
          <Route path="/unauthorized" element={<UnauthorizedPage />} />

          {/* 受保护路由 - 默认重定向到工作区 */}
          <Route
            path="/"
            element={
              <PrivateRoute>
                <Navigate to="/workspace" replace />
              </PrivateRoute>
            }
          />

          {/* 分屏工作区页面 (新默认) */}
          <Route
            path="/workspace"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <SplitScreenPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 单栏聊天页面 (旧版保留) */}
          <Route
            path="/chat"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <MainPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 百度搜索页面 */}
          <Route
            path="/baidu"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <BaiduSearchPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 工具演示页面 */}
          <Route
            path="/tools"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ToolsDemoPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 项目管理页面 */}
          <Route
            path="/projects"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ProjectsPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/projects/:projectId"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ProjectDetailPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* OCR 识别页面 */}
          <Route
            path="/ocr"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <OCRPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 文件系统页面 */}
          <Route
            path="/files"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <FileSystemPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 图谱可视化页面 */}
          <Route
            path="/graph"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <GraphVisualizationPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/graph/review"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <GraphReviewCenterPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 知识库管理页面 */}
          <Route
            path="/knowledge"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <KnowledgeBasePage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 工作流监控页面 */}
          <Route
            path="/workflow"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <WorkflowMonitorPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 统计分析页面 */}
          <Route
            path="/statistics"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <StatisticsPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* Token 使用监控页面 */}
          <Route
            path="/tokens"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <TokenUsagePage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />
          <Route
            path="/memory-settings"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <MemorySettingsPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 进化/优化系统页面 */}
          <Route
            path="/evolution"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <EvolutionPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 反馈系统页面 */}
          <Route
            path="/feedback"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <FeedbackPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* A/B 测试管理页面 */}
          <Route
            path="/abtest"
            element={
              <PrivateRoute>
                <ErrorBoundary>
                  <ABTestPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 系统管理页面 - 需要管理员权限 */}
          <Route
            path="/admin"
            element={
              <PrivateRoute requireAdmin>
                <ErrorBoundary>
                  <AdminPage />
                </ErrorBoundary>
              </PrivateRoute>
            }
          />

          {/* 404 重定向到工作区 */}
          <Route path="*" element={<Navigate to="/workspace" replace />} />
        </Routes>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;

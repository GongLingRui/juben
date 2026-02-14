/**
 * 路由配置
 * 支持懒加载、代码分割和错误处理
 */
import { lazy } from 'react';
import { RouteObject } from 'react-router-dom';
import { PrivateRoute, PublicRoute } from '@/components/auth';
import { RouteErrorBoundary } from '@/components/common/ErrorBoundary';
import { SuspenseWrapper } from '@/components/common/SuspenseWrapper';

// 懒加载页面组件 - 带错误处理
const lazyLoad = (importFunc: () => Promise<{ default: any }>) => {
  return lazy(() => importFunc().then(module => ({ default: module.default || module })));
};

const LoginPage = lazyLoad(() => import('@/pages/LoginPage').then(m => ({ default: m.LoginPage })));
const RegisterPage = lazyLoad(() => import('@/pages/RegisterPage').then(m => ({ default: m.RegisterPage })));
const UnauthorizedPage = lazyLoad(() => import('@/pages/UnauthorizedPage').then(m => ({ default: m.default })));
const SplitScreenPage = lazyLoad(() => import('@/pages/SplitScreenPage').then(m => ({ default: m.default })));
const MainPage = lazyLoad(() => import('@/pages/MainPage').then(m => ({ default: m.default })));
const BaiduSearchPage = lazyLoad(() => import('@/pages/BaiduSearchPage').then(m => ({ default: m.default })));
const ToolsDemoPage = lazyLoad(() => import('@/pages/ToolsDemoPage').then(m => ({ default: m.default })));
const ToolsPage = lazyLoad(() => import('@/pages/ToolsPage').then(m => ({ default: m.default })));
const ProjectsPage = lazyLoad(() => import('@/pages/ProjectsPage').then(m => ({ default: m.default })));
const OCRPage = lazyLoad(() => import('@/pages/OCRPage').then(m => ({ default: m.default })));
const FileSystemPage = lazyLoad(() => import('@/pages/FileSystemPage').then(m => ({ default: m.default })));
const GraphVisualizationPage = lazyLoad(() => import('@/pages/GraphVisualizationPage').then(m => ({ default: m.default })));
const WorkflowMonitorPage = lazyLoad(() => import('@/pages/WorkflowMonitorPage').then(m => ({ default: m.default })));
const AdminPage = lazyLoad(() => import('@/pages/AdminPage').then(m => ({ default: m.default })));
const StatisticsPage = lazyLoad(() => import('@/pages/StatisticsPage').then(m => ({ default: m.default })));

// 新增页面
const NotesPage = lazyLoad(() => import('@/pages/NotesPage').then(m => ({ default: m.default })));
const QualityControlPage = lazyLoad(() => import('@/pages/QualityControlPage').then(m => ({ default: m.default })));
const NovelScreeningPage = lazyLoad(() => import('@/pages/NovelScreeningPage').then(m => ({ default: m.default })));
const ReleaseManagementPage = lazyLoad(() => import('@/pages/ReleaseManagementPage').then(m => ({ default: m.default })));
const PipelineManagementPage = lazyLoad(() => import('@/pages/PipelineManagementPage').then(m => ({ default: m.default })));

// 带错误边界和 Suspense 的路由包装器
const wrapRoute = (element: React.ReactElement) => {
  return (
    <RouteErrorBoundary>
      <SuspenseWrapper>
        {element}
      </SuspenseWrapper>
    </RouteErrorBoundary>
  );
};

// 路由配置
export const routes: RouteObject[] = [
  // 公共路由
  {
    path: '/login',
    element: wrapRoute(
      <PublicRoute>
        <LoginPage />
      </PublicRoute>
    ),
  },
  {
    path: '/register',
    element: wrapRoute(
      <PublicRoute>
        <RegisterPage />
      </PublicRoute>
    ),
  },
  {
    path: '/unauthorized',
    element: wrapRoute(<UnauthorizedPage />),
  },

  // 受保护的路由
  {
    path: '/',
    element: wrapRoute(
      <PrivateRoute>
        <SplitScreenPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/workspace',
    element: wrapRoute(
      <PrivateRoute>
        <SplitScreenPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/chat',
    element: wrapRoute(
      <PrivateRoute>
        <MainPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/baidu',
    element: wrapRoute(
      <PrivateRoute>
        <BaiduSearchPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/tools',
    element: wrapRoute(
      <PrivateRoute>
        <ToolsPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/projects',
    element: wrapRoute(
      <PrivateRoute>
        <ProjectsPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/ocr',
    element: wrapRoute(
      <PrivateRoute>
        <OCRPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/files',
    element: wrapRoute(
      <PrivateRoute>
        <FileSystemPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/graph',
    element: wrapRoute(
      <PrivateRoute>
        <GraphVisualizationPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/workflow',
    element: wrapRoute(
      <PrivateRoute>
        <WorkflowMonitorPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/statistics',
    element: wrapRoute(
      <PrivateRoute>
        <StatisticsPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/admin',
    element: wrapRoute(
      <PrivateRoute requireAdmin>
        <AdminPage />
      </PrivateRoute>
    ),
  },
  // 新增页面路由
  {
    path: '/notes',
    element: wrapRoute(
      <PrivateRoute>
        <NotesPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/quality',
    element: wrapRoute(
      <PrivateRoute>
        <QualityControlPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/novel-screening',
    element: wrapRoute(
      <PrivateRoute>
        <NovelScreeningPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/release',
    element: wrapRoute(
      <PrivateRoute>
        <ReleaseManagementPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/pipelines',
    element: wrapRoute(
      <PrivateRoute>
        <PipelineManagementPage />
      </PrivateRoute>
    ),
  },
  {
    path: '/memory-management',
    element: wrapRoute(
      <PrivateRoute>
        <MemoryManagementPage />
      </PrivateRoute>
    ),
  },
];

export default routes;

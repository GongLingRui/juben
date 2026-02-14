/**
 * 面包屑导航组件
 */

import React from 'react';
import { Link, useLocation } from 'react-router-dom';
import { ChevronRight, Home } from 'lucide-react';

interface BreadcrumbItem {
  label: string;
  path?: string;
}

interface BreadcrumbProps {
  items?: BreadcrumbItem[];
  separator?: React.ReactNode;
  homePath?: string;
}

export const Breadcrumb: React.FC<BreadcrumbProps> = ({
  items,
  separator = <ChevronRight className="w-4 h-4" />,
  homePath = '/workspace',
}) => {
  const location = useLocation();

  // 默认根据路径生成面包屑
  const defaultItems: BreadcrumbItem[] = React.useMemo(() => {
    if (items) return items;

    const pathSegments = location.pathname.split('/').filter(Boolean);
    const breadcrumbs: BreadcrumbItem[] = [];

    pathSegments.forEach((segment, index) => {
      const path = '/' + pathSegments.slice(0, index + 1).join('/');

      // 路径映射到显示名称
      const labelMap: Record<string, string> = {
        workspace: '工作区',
        chat: '聊天',
        baidu: '百度搜索',
        tools: '工具演示',
        projects: '项目管理',
        ocr: 'OCR识别',
        files: '文件系统',
        graph: '图谱可视化',
        workflow: '工作流监控',
        statistics: '统计分析',
        admin: '系统管理',
        login: '登录',
        register: '注册',
      };

      const label = labelMap[segment] || segment;

      breadcrumbs.push({
        label,
        path,
      });
    });

    return breadcrumbs;
  }, [location.pathname, items]);

  if (defaultItems.length === 0) {
    return null;
  }

  return (
    <nav className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
      {/* 首页 */}
      <Link
        to={homePath}
        className="flex items-center gap-1 hover:text-gray-900 dark:hover:text-white transition-colors"
      >
        <Home className="w-4 h-4" />
      </Link>

      {/* 分隔符 */}
      <span className="flex items-center">{separator}</span>

      {/* 面包屑项 */}
      {defaultItems.map((item, index) => (
        <React.Fragment key={index}>
          {index > 0 && <span className="flex items-center">{separator}</span>}
          {item.path ? (
            <Link
              to={item.path}
              className="hover:text-gray-900 dark:hover:text-white transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span className="text-gray-900 dark:text-white font-medium">
              {item.label}
            </span>
          )}
        </React.Fragment>
      ))}
    </nav>
  );
};

export default Breadcrumb;

/**
 * 主页面
 */

import { useUIStore } from '@/store/uiStore';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import ChatContainer from '@/components/chat/ChatContainer';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import AgentDetailModal from '@/components/modals/AgentDetailModal';

export default function MainPage() {
  const { sidebarOpen, sidebarCollapsed, mobileMenuOpen } = useUIStore();

  return (
    <div className="flex h-screen bg-white">
      {/* 移动端菜单 */}
      <MobileMenu />

      {/* 侧边栏 */}
      <Sidebar />

      {/* 主内容区 */}
      <div
        className={`flex flex-col flex-1 transition-all duration-300 ${
          !sidebarOpen ? 'ml-0' : sidebarCollapsed ? 'ml-16' : 'ml-80'
        }`}
      >
        {/* 顶部导航 */}
        <Header />

        {/* 状态栏 */}
        <StatusBar />

        {/* 聊天容器 */}
        <ChatContainer />
      </div>

      {/* 设置弹窗 */}
      <SettingsModal />

      {/* Agent 详情弹窗 */}
      <AgentDetailModal />
    </div>
  );
}

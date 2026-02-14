/**
 * 记忆设置页面
 */
import { useEffect, useState } from 'react';
import Header from '@/components/layout/Header';
import Sidebar from '@/components/layout/Sidebar';
import StatusBar from '@/components/layout/StatusBar';
import MobileMenu from '@/components/common/MobileMenu';
import SettingsModal from '@/components/modals/SettingsModal';
import { useUIStore } from '@/store/uiStore';
import { Database } from 'lucide-react';
import { getMemorySettings, updateMemorySettings } from '@/services/memoryService';

export default function MemorySettingsPage() {
  const { sidebarOpen, sidebarCollapsed } = useUIStore();
  const [settings, setSettings] = useState<any | null>(null);
  const userId = localStorage.getItem('userId') || 'default-user';
  const projectId = localStorage.getItem('projectId') || undefined;

  useEffect(() => {
    const load = async () => {
      try {
        const res = await getMemorySettings({ user_id: userId, project_id: projectId });
        setSettings(res.data || null);
      } catch {
        setSettings(null);
      }
    };
    load();
  }, [userId, projectId]);

  const toggleUser = async () => {
    const next = !settings?.user_enabled;
    const res = await updateMemorySettings({ user_id: userId, project_id: projectId, user_enabled: next });
    if (res.success) setSettings(res.data || null);
  };

  const toggleProject = async () => {
    const next = !settings?.project_enabled;
    const res = await updateMemorySettings({ user_id: userId, project_id: projectId, project_enabled: next });
    if (res.success) setSettings(res.data || null);
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

        <div className="flex-1 overflow-y-auto p-6">
          <div className="max-w-4xl mx-auto space-y-6">
            <div className="flex items-center gap-3">
              <div className="w-12 h-12 bg-black rounded-xl flex items-center justify-center">
                <Database className="w-6 h-6 text-white" />
              </div>
              <div>
                <h1 className="text-2xl font-bold text-gray-900">记忆设置</h1>
                <p className="text-sm text-gray-500">控制记忆是否参与上下文与检索</p>
              </div>
            </div>

            <div className="border border-gray-200 rounded-xl p-6 space-y-4">
              <div className="flex items-center justify-between text-sm">
                <span>用户维度记忆</span>
                <button
                  onClick={toggleUser}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    settings?.user_enabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {settings?.user_enabled ? '已开启' : '已关闭'}
                </button>
              </div>
              <div className="flex items-center justify-between text-sm">
                <span>项目维度记忆</span>
                <button
                  onClick={toggleProject}
                  className={`px-3 py-1 rounded-full text-xs border ${
                    settings?.project_enabled ? 'bg-black text-white border-black' : 'bg-white text-gray-600 border-gray-200'
                  }`}
                >
                  {settings?.project_enabled ? '已开启' : '已关闭'}
                </button>
              </div>
              <div className="text-xs text-gray-500">
                当前生效: {settings?.effective_enabled ? '开启' : '关闭'} {settings?.updated_at ? `| ${settings.updated_at}` : ''}
              </div>
              {!projectId && (
                <div className="text-xs text-gray-400">未选择项目时，项目维度开关不会生效。</div>
              )}
            </div>
          </div>
        </div>
      </div>

      <SettingsModal />
    </div>
  );
}


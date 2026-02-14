/**
 * 分屏主页面
 * 使用 SplitScreenLayout 组件展示左侧工作区和右侧聊天区
 */

import SplitScreenLayout from '@/components/layout/SplitScreenLayout';
import SplitScreenHeader from '@/components/workspace/SplitScreenHeader';
import WorkspacePanel from '@/components/workspace/WorkspacePanel';
import ChatPanel from '@/components/workspace/ChatPanel';
import SettingsModal from '@/components/modals/SettingsModal';
import HelpModal from '@/components/modals/HelpModal';
import { useAgentStore } from '@/store/agentStore';
import { useSearchParams } from 'react-router-dom';
import { useEffect, useState } from 'react';
import { LINKS } from '@/config/links';

export default function SplitScreenPage() {
  const [helpOpen, setHelpOpen] = useState(false);
  const [searchParams] = useSearchParams();
  const { setActiveAgent, agents } = useAgentStore();

  useEffect(() => {
    const agentId = searchParams.get('agent');
    if (agentId && agents.some((agent) => agent.id === agentId)) {
      setActiveAgent(agentId);
    }
  }, [searchParams, agents, setActiveAgent]);

  useEffect(() => {
    const projectId = searchParams.get('project_id') || searchParams.get('projectId');
    if (projectId) {
      localStorage.setItem('projectId', projectId);
    }
  }, [searchParams]);

  const handleHelpClick = () => {
    if (LINKS.help) {
      window.open(LINKS.help, '_blank');
      return;
    }
    setHelpOpen(true);
  };

  return (
    <>
      <SplitScreenLayout
        header={
          <SplitScreenHeader
            projectName="剧本创作 Agent 平台"
            onHelpClick={handleHelpClick}
          />
        }
        workspace={<WorkspacePanel />}
        chat={<ChatPanel />}
      />

      {/* 设置模态框 - 由 UIStore 控制显示 */}
      <SettingsModal />
      <HelpModal isOpen={helpOpen} onClose={() => setHelpOpen(false)} />
    </>
  );
}

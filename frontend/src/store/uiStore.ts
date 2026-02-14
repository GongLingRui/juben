/**
 * UI 状态管理 Store - 带持久化
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

interface UIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  agentListOpen: boolean;
  thoughtChainExpanded: boolean;
  mobileMenuOpen: boolean;

  // Modal states (不持久化，每次刷新重置)
  settingsModalOpen: boolean;
  agentDetailModalOpen: boolean;
  searchOpen: boolean;
  selectedAgentId: string | null;

  // Actions
  setSidebarOpen: (open: boolean) => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setAgentListOpen: (open: boolean) => void;
  setThoughtChainExpanded: (expanded: boolean) => void;
  setMobileMenuOpen: (open: boolean) => void;

  setSettingsModalOpen: (open: boolean) => void;
  setAgentDetailModalOpen: (open: boolean) => void;
  setSearchOpen: (open: boolean) => void;
  setSelectedAgentId: (agentId: string | null) => void;

  // Toggle helpers
  toggleSidebar: () => void;
  toggleSidebarCollapsed: () => void;
  toggleAgentList: () => void;
  toggleThoughtChain: () => void;
  toggleMobileMenu: () => void;
  toggleSearch: () => void;

  // Reset
  resetUI: () => void;
}

// 默认状态（排除模态框状态）
const defaultUIState: Omit<UIState, 'setSidebarOpen' | 'setSidebarCollapsed' | 'setAgentListOpen' | 'setThoughtChainExpanded' | 'setMobileMenuOpen' | 'setSettingsModalOpen' | 'setAgentDetailModalOpen' | 'setSearchOpen' | 'setSelectedAgentId' | 'toggleSidebar' | 'toggleSidebarCollapsed' | 'toggleAgentList' | 'toggleThoughtChain' | 'toggleMobileMenu' | 'toggleSearch' | 'resetUI'> = {
  sidebarOpen: true,
  sidebarCollapsed: false,
  agentListOpen: true,
  thoughtChainExpanded: true,
  mobileMenuOpen: false,
  // 以下状态不持久化，初始化时重置
  settingsModalOpen: false,
  agentDetailModalOpen: false,
  searchOpen: false,
  selectedAgentId: null,
};

// 持久化部分（排除模态框状态）
interface PersistedUIState {
  sidebarOpen: boolean;
  sidebarCollapsed: boolean;
  agentListOpen: boolean;
  thoughtChainExpanded: boolean;
}

export const useUIStore = create<UIState>()(
  devtools(
    (set, get) => ({
      // 合并持久化状态和非持久化状态
      ...defaultUIState,

      // Actions
      setSidebarOpen: (open) => set({ sidebarOpen: open }),
      setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
      setAgentListOpen: (open) => set({ agentListOpen: open }),
      setThoughtChainExpanded: (expanded) => set({ thoughtChainExpanded: expanded }),
      setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),

      setSettingsModalOpen: (open) => set({ settingsModalOpen: open }),
      setAgentDetailModalOpen: (open) => set({ agentDetailModalOpen: open }),
      setSearchOpen: (open) => set({ searchOpen: open }),
      setSelectedAgentId: (agentId) => set({ selectedAgentId: agentId }),

      // Toggle helpers
      toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
      toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
      toggleAgentList: () => set((state) => ({ agentListOpen: !state.agentListOpen })),
      toggleThoughtChain: () => set((state) => ({ thoughtChainExpanded: !state.thoughtChainExpanded })),
      toggleMobileMenu: () => set((state) => ({ mobileMenuOpen: !state.mobileMenuOpen })),
      toggleSearch: () => set((state) => ({ searchOpen: !state.searchOpen })),

      // Reset
      resetUI: () => set({
        ...defaultUIState,
        settingsModalOpen: false,
        agentDetailModalOpen: false,
        searchOpen: false,
        selectedAgentId: null,
      }),
    }),
    { name: 'UIStore' }
  )
);

// 创建持久化中间件
export const createPersistedUIStore = () => {
  const persistedStore = create<UIState>()(
    devtools(
      persist(
        (set, get) => ({
          ...defaultUIState,

          setSidebarOpen: (open) => set({ sidebarOpen: open }),
          setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),
          setAgentListOpen: (open) => set({ agentListOpen: open }),
          setThoughtChainExpanded: (expanded) => set({ thoughtChainExpanded: expanded }),
          setMobileMenuOpen: (open) => set({ mobileMenuOpen: open }),

          setSettingsModalOpen: (open) => set({ settingsModalOpen: open }),
          setAgentDetailModalOpen: (open) => set({ agentDetailModalOpen: open }),
          setSearchOpen: (open) => set({ searchOpen: open }),
          setSelectedAgentId: (agentId) => set({ selectedAgentId: agentId }),

          toggleSidebar: () => set((state) => ({ sidebarOpen: !state.sidebarOpen })),
          toggleSidebarCollapsed: () => set((state) => ({ sidebarCollapsed: !state.sidebarCollapsed })),
          toggleAgentList: () => set((state) => ({ agentListOpen: !state.agentListOpen })),
          toggleThoughtChain: () => set((state) => ({ thoughtChainExpanded: !state.thoughtChainExpanded })),
          toggleMobileMenu: () => set((state) => ({ mobileMenuOpen: !state.mobileMenuOpen })),
          toggleSearch: () => set((state) => ({ searchOpen: !state.searchOpen })),

          resetUI: () => set({
            ...defaultUIState,
            settingsModalOpen: false,
            agentDetailModalOpen: false,
            searchOpen: false,
            selectedAgentId: null,
          }),
        }),
        {
          name: 'juben-ui-storage',
          version: 1,
          // 只持久化部分字段，排除模态框状态
          partialize: (state) => ({
            sidebarOpen: state.sidebarOpen,
            sidebarCollapsed: state.sidebarCollapsed,
            agentListOpen: state.agentListOpen,
            thoughtChainExpanded: state.thoughtChainExpanded,
          }),
        }
      ),
      { name: 'UIStore' }
    )
  );
  return persistedStore;
};

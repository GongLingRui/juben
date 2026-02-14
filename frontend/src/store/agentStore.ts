/**
 * Agent 状态管理 Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import type { Agent, AgentCategory } from '@/types';

interface AgentState {
  agents: Agent[];
  activeAgent: string;
  searchQuery: string;
  selectedCategory: AgentCategory | 'all';

  // Actions
  setAgents: (agents: Agent[]) => void;
  setActiveAgent: (agentId: string) => void;
  setSearchQuery: (query: string) => void;
  setSelectedCategory: (category: AgentCategory | 'all') => void;

  // Getters
  getActiveAgent: () => Agent | undefined;
  getFilteredAgents: () => Agent[];
}

export const useAgentStore = create<AgentState>()(
  devtools(
    (set, get) => ({
      // Initial state
      agents: [],
      activeAgent: 'short_drama_planner',
      searchQuery: '',
      selectedCategory: 'all',

      // Actions
      setAgents: (agents) =>
        set((state) => {
          const currentActive = state.activeAgent;
          const hasActive = agents.some((a) => a.id === currentActive);
          return {
            agents,
            activeAgent: hasActive ? currentActive : agents[0]?.id || currentActive,
          };
        }),
      setActiveAgent: (agentId) => set({ activeAgent: agentId }),
      setSearchQuery: (query) => set({ searchQuery: query }),
      setSelectedCategory: (category) => set({ selectedCategory: category }),

      // Getters
      getActiveAgent: () => {
        const state = get();
        return state.agents.find((a) => a.id === state.activeAgent);
      },

      getFilteredAgents: () => {
        const state = get();
        let filtered = state.agents;

        // Filter by category
        if (state.selectedCategory !== 'all') {
          filtered = filtered.filter((a) => a.category === state.selectedCategory);
        }

        // Filter by search query
        if (state.searchQuery) {
          const query = state.searchQuery.toLowerCase();
          filtered = filtered.filter(
            (a) =>
              a.name.toLowerCase().includes(query) ||
              a.displayName.toLowerCase().includes(query) ||
              a.description.toLowerCase().includes(query)
          );
        }

        return filtered;
      },
    }),
    { name: 'AgentStore' }
  )
);

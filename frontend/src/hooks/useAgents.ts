/**
 * Agents Hook
 */

import { useEffect, useCallback } from 'react';
import { useAgentStore } from '@/store/agentStore';
import { getAgents, searchAgents, getAgentsByCategory } from '@/services/agentService';
import type { Agent, AgentCategory } from '@/types';

export function useAgents() {
  const {
    agents,
    activeAgent,
    searchQuery,
    selectedCategory,
    setAgents,
    setActiveAgent,
    setSearchQuery,
    setSelectedCategory,
    getActiveAgent,
    getFilteredAgents,
  } = useAgentStore();

  /**
   * 加载所有 Agents
   */
  useEffect(() => {
    if (agents.length === 0) {
      getAgents().then(setAgents).catch(console.error);
    }
  }, [agents.length, setAgents]);

  /**
   * 获取激活的 Agent
   */
  const activeAgentData = getActiveAgent();

  /**
   * 获取过滤后的 Agents
   */
  const filteredAgents = getFilteredAgents();

  /**
   * 搜索 Agents
   */
  const search = useCallback(
    async (query: string) => {
      setSearchQuery(query);
      if (query.length > 0) {
        const results = await searchAgents(query);
        setAgents(results);
      } else {
        const allAgents = await getAgents();
        setAgents(allAgents);
      }
    },
    [setSearchQuery, setAgents]
  );

  /**
   * 按分类筛选
   */
  const filterByCategory = useCallback(
    async (category: AgentCategory | 'all') => {
      setSelectedCategory(category);
      if (category !== 'all') {
        const results = await getAgentsByCategory(category);
        setAgents(results);
      } else {
        const allAgents = await getAgents();
        setAgents(allAgents);
      }
    },
    [setSelectedCategory, setAgents]
  );

  return {
    agents,
    filteredAgents,
    activeAgent,
    activeAgentData,
    searchQuery,
    selectedCategory,
    setActiveAgent,
    setSearchQuery,
    setSelectedCategory,
    search,
    filterByCategory,
  };
}

/**
 * 设置状态管理 Store - 增强版
 */

import { create } from 'zustand';
import { devtools, persist } from 'zustand/middleware';

type Theme = 'light' | 'dark';
type FontSize = 'sm' | 'md' | 'lg';
type ModelProvider = 'zhipu' | 'openrouter' | 'openai' | 'local' | 'ollama';

interface SettingsState {
  theme: Theme;
  model: string;
  modelProvider: ModelProvider;
  streamEnabled: boolean;
  showThoughtChain: boolean;
  fontSize: FontSize;
  autoScroll: boolean;
  showTimestamp: boolean;
  enableWebSearch: boolean;
  enableKnowledgeBase: boolean;
  enableRetryOnError: boolean;
  maxRetries: number;
  memoryUserEnabled: boolean;
  memoryProjectEnabled: boolean;

  // Actions
  setTheme: (theme: Theme) => void;
  setModel: (model: string) => void;
  setModelProvider: (provider: ModelProvider) => void;
  setStreamEnabled: (enabled: boolean) => void;
  setShowThoughtChain: (show: boolean) => void;
  setFontSize: (size: FontSize) => void;
  setAutoScroll: (enabled: boolean) => void;
  setShowTimestamp: (show: boolean) => void;
  setEnableWebSearch: (enabled: boolean) => void;
  setEnableKnowledgeBase: (enabled: boolean) => void;
  setEnableRetryOnError: (enabled: boolean) => void;
  setMaxRetries: (count: number) => void;
  setMemoryUserEnabled: (enabled: boolean) => void;
  setMemoryProjectEnabled: (enabled: boolean) => void;

  // Reset
  resetSettings: () => void;
}

const defaultSettings: Omit<SettingsState, 'setTheme' | 'setModel' | 'setModelProvider' | 'setStreamEnabled' | 'setShowThoughtChain' | 'setFontSize' | 'setAutoScroll' | 'setShowTimestamp' | 'setEnableWebSearch' | 'setEnableKnowledgeBase' | 'setEnableRetryOnError' | 'setMaxRetries' | 'setMemoryUserEnabled' | 'setMemoryProjectEnabled' | 'resetSettings'> = {
  theme: 'light',
  model: 'glm-4.7-flash',
  modelProvider: 'zhipu',
  streamEnabled: true,
  showThoughtChain: true,
  fontSize: 'md',
  autoScroll: true,
  showTimestamp: true,
  enableWebSearch: true,
  enableKnowledgeBase: true,
  enableRetryOnError: true,
  maxRetries: 3,
  memoryUserEnabled: true,
  memoryProjectEnabled: true,
};

export const useSettingsStore = create<SettingsState>()(
  devtools(
    persist(
      (set) => ({
        ...defaultSettings,

        // Actions
        setTheme: (theme) => set({ theme }),
        setModel: (model) => set({ model }),
        setModelProvider: (provider) => set({ modelProvider: provider }),
        setStreamEnabled: (enabled) => set({ streamEnabled: enabled }),
        setShowThoughtChain: (show) => set({ showThoughtChain: show }),
        setFontSize: (size) => set({ fontSize: size }),
        setAutoScroll: (enabled) => set({ autoScroll: enabled }),
        setShowTimestamp: (show) => set({ showTimestamp: show }),
        setEnableWebSearch: (enabled) => set({ enableWebSearch: enabled }),
        setEnableKnowledgeBase: (enabled) => set({ enableKnowledgeBase: enabled }),
        setEnableRetryOnError: (enabled) => set({ enableRetryOnError: enabled }),
        setMaxRetries: (count) => set({ maxRetries: count }),
        setMemoryUserEnabled: (enabled) => set({ memoryUserEnabled: enabled }),
        setMemoryProjectEnabled: (enabled) => set({ memoryProjectEnabled: enabled }),

        // Reset
        resetSettings: () => set(defaultSettings),
      }),
      {
        name: 'juben-settings',
        version: 1,
      }
    ),
    { name: 'SettingsStore' }
  )
);

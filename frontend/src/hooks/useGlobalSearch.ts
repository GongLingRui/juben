/**
 * 全局搜索 Hook
 * 处理快捷键触发搜索
 */

import { useEffect, useCallback } from 'react';
import { useUIStore } from '@/store/uiStore';

export const useGlobalSearch = () => {
  const { setSearchOpen } = useUIStore();

  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Cmd/Ctrl + K 触发搜索
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen(true);
      }
    },
    [setSearchOpen]
  );

  useEffect(() => {
    document.addEventListener('keydown', handleKeyDown);
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
    };
  }, [handleKeyDown]);
};

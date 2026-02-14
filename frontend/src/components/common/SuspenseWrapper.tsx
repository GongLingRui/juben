/**
 * Suspense 边界组件
 * 用于处理懒加载的加载状态
 */

import React, { Suspense } from 'react';
import Loading from './Loading';

interface SuspenseWrapperProps {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const SuspenseWrapper: React.FC<SuspenseWrapperProps> = ({
  children,
  fallback,
}) => {
  return (
    <Suspense fallback={fallback || <Loading size="lg" />}>
      {children}
    </Suspense>
  );
};

export default SuspenseWrapper;

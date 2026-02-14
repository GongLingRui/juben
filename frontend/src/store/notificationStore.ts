/**
 * 通知状态管理 Store
 */

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';

export type NotificationType = 'success' | 'error' | 'warning' | 'info';

export interface Notification {
  id: string;
  type: NotificationType;
  title: string;
  message: string;
  duration?: number;
  timestamp: string;
  actions?: NotificationAction[];
  persistent?: boolean;
}

export interface NotificationAction {
  label: string;
  onClick: () => void;
  primary?: boolean;
}

interface NotificationState {
  notifications: Notification[];

  // Actions
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => string;
  removeNotification: (id: string) => void;
  clearAll: () => void;
  clearByType: (type: NotificationType) => void;

  // Helpers
  success: (title: string, message: string, duration?: number) => string;
  error: (title: string, message: string, duration?: number) => string;
  warning: (title: string, message: string, duration?: number) => string;
  info: (title: string, message: string, duration?: number) => string;
}

export const useNotificationStore = create<NotificationState>()(
  devtools(
    (set, get) => ({
      notifications: [],

      addNotification: (notification) => {
        const id = `notification-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
        const newNotification: Notification = {
          ...notification,
          id,
          timestamp: new Date().toISOString(),
        };

        set((state) => ({
          notifications: [...state.notifications, newNotification],
        }));

        // Auto-remove if not persistent and has duration
        if (!notification.persistent && notification.duration !== 0) {
          const duration = notification.duration ?? 5000;
          setTimeout(() => {
            get().removeNotification(id);
          }, duration);
        }

        return id;
      },

      removeNotification: (id) => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.id !== id),
        }));
      },

      clearAll: () => {
        set({ notifications: [] });
      },

      clearByType: (type) => {
        set((state) => ({
          notifications: state.notifications.filter((n) => n.type !== type),
        }));
      },

      // Helpers
      success: (title, message, duration) => {
        return get().addNotification({
          type: 'success',
          title,
          message,
          duration,
        });
      },

      error: (title, message, duration) => {
        return get().addNotification({
          type: 'error',
          title,
          message,
          duration: duration ?? 8000, // Errors stay longer
        });
      },

      warning: (title, message, duration) => {
        return get().addNotification({
          type: 'warning',
          title,
          message,
          duration,
        });
      },

      info: (title, message, duration) => {
        return get().addNotification({
          type: 'info',
          title,
          message,
          duration,
        });
      },
    }),
    { name: 'NotificationStore' }
  )
);

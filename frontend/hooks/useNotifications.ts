"use client";

import { useState, useEffect, useCallback } from "react";
import { useAuth } from "@clerk/nextjs";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001";

export interface NotificationItem {
  id: string;
  notification_type: string;
  title: string;
  message: string;
  link: string | null;
  read: boolean;
  created_at: string;
}

export function useNotifications() {
  const { getToken } = useAuth();
  const [notifications, setNotifications] = useState<NotificationItem[]>([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);

  const fetchNotifications = useCallback(
    async (unreadOnly = false) => {
      try {
        const token = await getToken();
        if (!token) return;
        setLoading(true);
        const res = await fetch(
          `${API_BASE}/notifications?unread_only=${unreadOnly}&limit=50`,
          { headers: { Authorization: `Bearer ${token}` } }
        );
        if (res.ok) {
          const data = await res.json();
          setNotifications(data);
        }
      } catch (e) {
        console.error("Failed to fetch notifications", e);
      } finally {
        setLoading(false);
      }
    },
    [getToken]
  );

  const fetchUnreadCount = useCallback(async () => {
    try {
      const token = await getToken();
      if (!token) return;
      const res = await fetch(`${API_BASE}/notifications/unread-count`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        const data = await res.json();
        setUnreadCount(data.count ?? 0);
      }
    } catch (e) {
      // Silently ignore — will retry on next poll
    }
  }, [getToken]);

  const markRead = useCallback(
    async (id: string) => {
      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE}/notifications/${id}/read`, {
          method: "PATCH",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setNotifications((prev) =>
            prev.map((n) => (n.id === id ? { ...n, read: true } : n))
          );
          setUnreadCount((prev) => Math.max(0, prev - 1));
        }
      } catch (e) {
        console.error("Failed to mark read", e);
      }
    },
    [getToken]
  );

  const markAllRead = useCallback(async () => {
    try {
      const token = await getToken();
      const res = await fetch(`${API_BASE}/notifications/read-all`, {
        method: "PATCH",
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) {
        setNotifications((prev) => prev.map((n) => ({ ...n, read: true })));
        setUnreadCount(0);
      }
    } catch (e) {
      console.error("Failed to mark all read", e);
    }
  }, [getToken]);

  const dismiss = useCallback(
    async (id: string) => {
      try {
        const token = await getToken();
        const res = await fetch(`${API_BASE}/notifications/${id}`, {
          method: "DELETE",
          headers: { Authorization: `Bearer ${token}` },
        });
        if (res.ok) {
          setNotifications((prev) => prev.filter((n) => n.id !== id));
          setUnreadCount((prev) =>
            notifications.find((n) => n.id === id && !n.read)
              ? Math.max(0, prev - 1)
              : prev
          );
        }
      } catch (e) {
        console.error("Failed to dismiss notification", e);
      }
    },
    [getToken, notifications]
  );

  // Poll unread count every 30 seconds
  useEffect(() => {
    fetchUnreadCount();
    const interval = setInterval(fetchUnreadCount, 30000);
    return () => clearInterval(interval);
  }, [fetchUnreadCount]);

  return {
    notifications,
    unreadCount,
    loading,
    fetchNotifications,
    fetchUnreadCount,
    markRead,
    markAllRead,
    dismiss,
  };
}

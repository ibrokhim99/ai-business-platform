'use client';

import { useCallback, useEffect, useState } from 'react';
import type { Conversation, Message } from './types';

const KEY = 'biziq_conversations_v1';
const ACTIVE_KEY = 'biziq_active_conversation_v1';

function load(): Conversation[] {
  if (typeof window === 'undefined') return [];
  try {
    const raw = localStorage.getItem(KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw) as Conversation[];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function save(items: Conversation[]) {
  if (typeof window === 'undefined') return;
  localStorage.setItem(KEY, JSON.stringify(items));
}

const uid = () => Math.random().toString(36).slice(2, 10) + Date.now().toString(36).slice(-4);

export function useConversations() {
  const [items, setItems] = useState<Conversation[]>([]);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    const loaded = load();
    setItems(loaded);
    const stored = typeof window !== 'undefined' ? localStorage.getItem(ACTIVE_KEY) : null;
    setActiveId(stored && loaded.some((c) => c.id === stored) ? stored : null);
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (hydrated) save(items);
  }, [items, hydrated]);

  useEffect(() => {
    if (!hydrated) return;
    if (activeId) localStorage.setItem(ACTIVE_KEY, activeId);
    else localStorage.removeItem(ACTIVE_KEY);
  }, [activeId, hydrated]);

  const active = items.find((c) => c.id === activeId) ?? null;

  const newConversation = useCallback((): Conversation => {
    const c: Conversation = {
      id: uid(),
      title: 'Yangi suhbat',
      createdAt: Date.now(),
      updatedAt: Date.now(),
      messages: [],
    };
    setItems((prev) => [c, ...prev]);
    setActiveId(c.id);
    return c;
  }, []);

  const ensureActive = useCallback((): Conversation => {
    if (active) return active;
    return newConversation();
  }, [active, newConversation]);

  const addMessage = useCallback((conversationId: string, msg: Message) => {
    setItems((prev) =>
      prev.map((c) =>
        c.id === conversationId
          ? {
              ...c,
              messages: [...c.messages, msg],
              updatedAt: Date.now(),
              title: c.messages.length === 0 && msg.role === 'user' && msg.text
                ? msg.text.slice(0, 60)
                : c.title,
            }
          : c
      )
    );
  }, []);

  const updateMessage = useCallback((conversationId: string, messageId: string, patch: Partial<Message>) => {
    setItems((prev) =>
      prev.map((c) =>
        c.id === conversationId
          ? { ...c, messages: c.messages.map((m) => (m.id === messageId ? { ...m, ...patch } : m)), updatedAt: Date.now() }
          : c
      )
    );
  }, []);

  const removeConversation = useCallback((id: string) => {
    setItems((prev) => prev.filter((c) => c.id !== id));
    setActiveId((cur) => (cur === id ? null : cur));
  }, []);

  const renameConversation = useCallback((id: string, title: string) => {
    setItems((prev) => prev.map((c) => (c.id === id ? { ...c, title } : c)));
  }, []);

  const clearAll = useCallback(() => {
    setItems([]);
    setActiveId(null);
  }, []);

  return {
    items,
    active,
    activeId,
    setActiveId,
    newConversation,
    ensureActive,
    addMessage,
    updateMessage,
    removeConversation,
    renameConversation,
    clearAll,
    hydrated,
    newMessageId: uid,
  };
}

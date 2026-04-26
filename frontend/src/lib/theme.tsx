'use client';

import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';

export type ThemeMode = 'light' | 'dark' | 'system';

interface ThemeCtx {
  mode: ThemeMode;
  effective: 'light' | 'dark';
  setMode: (m: ThemeMode) => void;
  toggle: () => void;
}

const Ctx = createContext<ThemeCtx | null>(null);
const STORAGE_KEY = 'biziq_theme';

function systemDark(): boolean {
  if (typeof window === 'undefined') return false;
  return window.matchMedia('(prefers-color-scheme: dark)').matches;
}

function apply(effective: 'light' | 'dark') {
  if (typeof document === 'undefined') return;
  document.documentElement.classList.toggle('dark', effective === 'dark');
  document.documentElement.style.colorScheme = effective;
}

export function ThemeProvider({ children }: { children: React.ReactNode }) {
  const [mode, setModeState] = useState<ThemeMode>('system');
  const [effective, setEffective] = useState<'light' | 'dark'>('light');

  useEffect(() => {
    const stored = (typeof window !== 'undefined' && (localStorage.getItem(STORAGE_KEY) as ThemeMode | null)) || 'system';
    setModeState(stored);
    const eff = stored === 'system' ? (systemDark() ? 'dark' : 'light') : stored;
    setEffective(eff);
    apply(eff);
  }, []);

  // React to OS preference changes when in system mode
  useEffect(() => {
    if (mode !== 'system') return;
    const mq = window.matchMedia('(prefers-color-scheme: dark)');
    const onChange = (e: MediaQueryListEvent) => {
      const eff = e.matches ? 'dark' : 'light';
      setEffective(eff);
      apply(eff);
    };
    mq.addEventListener('change', onChange);
    return () => mq.removeEventListener('change', onChange);
  }, [mode]);

  const setMode = useCallback((m: ThemeMode) => {
    setModeState(m);
    localStorage.setItem(STORAGE_KEY, m);
    const eff = m === 'system' ? (systemDark() ? 'dark' : 'light') : m;
    setEffective(eff);
    apply(eff);
  }, []);

  const toggle = useCallback(() => {
    setMode(effective === 'dark' ? 'light' : 'dark');
  }, [effective, setMode]);

  return <Ctx.Provider value={{ mode, effective, setMode, toggle }}>{children}</Ctx.Provider>;
}

export function useTheme(): ThemeCtx {
  const c = useContext(Ctx);
  if (!c) throw new Error('useTheme must be used inside <ThemeProvider>');
  return c;
}

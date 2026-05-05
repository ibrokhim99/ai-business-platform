'use client';

import React, { createContext, useContext, useCallback } from 'react';

interface User {
  email: string;
  role: string;
}

interface AuthContextType {
  user: User | null;
  token: string | null;
  login: (email: string, password: string) => Promise<void>;
  logout: () => void;
  isAuthenticated: boolean;
  loading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);
const GUEST_USER: User = { email: 'guest@local', role: 'admin' };

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const login = useCallback(async () => {
    return;
  }, []);

  const logout = useCallback(() => {
    return;
  }, []);

  const value: AuthContextType = {
    user: GUEST_USER,
    token: null,
    login,
    logout,
    isAuthenticated: true,
    loading: false,
  };

  return React.createElement(AuthContext.Provider, { value }, children);
}

export function useAuth(): AuthContextType {
  const ctx = useContext(AuthContext);
  if (!ctx) {
    throw new Error('useAuth must be used inside AuthProvider');
  }
  return ctx;
}

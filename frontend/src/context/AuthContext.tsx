import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { api, getToken, setToken } from '../lib/api';
import type { AuthResponse, RegisterInput, User } from '../types';

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<User>;
  register: (input: RegisterInput) => Promise<User>;
  logout: () => Promise<void>;
  verifyEmail: (token: string) => Promise<User>;
  resendVerification: () => Promise<string>;
  refresh: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(() => Boolean(getToken()));

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null);
      setLoading(false);
      return;
    }
    try {
      const response = await api<AuthResponse>('/auth/me');
      setUser(response.data);
    } catch {
      setToken(null);
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const login = useCallback(async (email: string, password: string) => {
    const response = await api<AuthResponse>('/auth/login', {
      method: 'POST',
      body: { email, password },
    });
    if (response.token) setToken(response.token);
    setUser(response.data);
    return response.data;
  }, []);

  const register = useCallback(async (input: RegisterInput) => {
    const response = await api<AuthResponse>('/auth/register', {
      method: 'POST',
      body: {
        name: input.name,
        email: input.email,
        password: input.password,
        password_confirmation: input.passwordConfirmation,
      },
    });
    if (response.token) setToken(response.token);
    setUser(response.data);
    return response.data;
  }, []);

  const logout = useCallback(async () => {
    try {
      await api('/auth/logout', { method: 'POST' });
    } catch {
      // Token may already be invalid — clear locally regardless.
    }
    setToken(null);
    setUser(null);
  }, []);

  const verifyEmail = useCallback(async (token: string) => {
    const response = await api<AuthResponse>('/auth/verify-email', {
      method: 'POST',
      body: { token },
    });
    setUser(response.data);
    return response.data;
  }, []);

  const resendVerification = useCallback(async () => {
    const response = await api<{ message: string }>('/auth/resend-verification', {
      method: 'POST',
    });
    return response.message;
  }, []);

  const value = useMemo(
    () => ({ user, loading, login, register, logout, verifyEmail, resendVerification, refresh }),
    [user, loading, login, register, logout, verifyEmail, resendVerification, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used inside AuthProvider');
  return context;
}

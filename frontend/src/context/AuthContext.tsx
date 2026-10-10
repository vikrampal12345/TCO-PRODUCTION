import React, { createContext, useContext, useEffect, useState } from 'react';
import type { User, AuthState, LoginCredentials, SignupCredentials } from '../types/auth';
import { authService } from '../services/authService';
import { isMockMode } from '../services/api';
import { setAccessToken } from '../services/http';

interface AuthContextType extends AuthState {
  login: (credentials: LoginCredentials) => Promise<void>;
  signup: (credentials: SignupCredentials) => Promise<void>;
  loginWithGoogle: () => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

function readSavedUser(): User | null {
  try {
    if (!isMockMode && !localStorage.getItem('tco_access_token')) {
      localStorage.removeItem('tco_user');
      return null;
    }
    const saved = localStorage.getItem('tco_user');
    return saved ? JSON.parse(saved) as User : null;
  } catch {
    try { localStorage.removeItem('tco_user'); } catch { /* ignore unavailable storage */ }
    return null;
  }
}

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<User | null>(readSavedUser);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    if (user) localStorage.setItem('tco_user', JSON.stringify(user));
    else localStorage.removeItem('tco_user');
  }, [user]);

  const login = async (credentials: LoginCredentials) => {
    setIsLoading(true);
    try {
      if (!isMockMode) {
        const backendUser = await authService.login(credentials);
        setUser(backendUser);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 350));
      setUser({
        id: `demo-${Date.now()}`,
        name: credentials.email.split('@')[0].replace(/[._-]/g, ' ').replace(/\b\w/g, (letter) => letter.toUpperCase()) || 'Teacher',
        email: credentials.email,
        role: 'Teacher',
        school: 'School of Computing & Engineering',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const signup = async (credentials: SignupCredentials) => {
    setIsLoading(true);
    try {
      if (!isMockMode) {
        const backendUser = await authService.signup(credentials);
        setUser(backendUser);
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 350));
      setUser({
        id: `demo-${Date.now()}`,
        name: credentials.name,
        email: credentials.email,
        role: credentials.role,
        school: credentials.school || 'Academic Institution',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loginWithGoogle = async () => {
    setIsLoading(true);
    try {
      if (!isMockMode) {
        setUser(await authService.loginWithGoogle());
        return;
      }
      await new Promise((resolve) => setTimeout(resolve, 350));
      setUser({
        id: 'demo-google-user',
        name: 'Demo Teacher',
        email: 'teacher@example.edu',
        role: 'Teacher',
        school: 'Academic Institution',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const logout = () => {
    setUser(null);
    setAccessToken(null);
    localStorage.removeItem('tco_user');
  };

  return (
    <AuthContext.Provider value={{ user, isAuthenticated: !!user, isLoading, login, signup, loginWithGoogle, logout }}>
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) throw new Error('useAuth must be used within an AuthProvider');
  return context;
};

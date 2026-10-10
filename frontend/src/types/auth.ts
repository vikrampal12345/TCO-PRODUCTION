export type UserRole = 'Teacher' | 'Educator' | 'Administrator';

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  school?: string;
  avatarUrl?: string;
}

export interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
}

export interface LoginCredentials {
  email: string;
  password?: string;
}

export interface SignupCredentials {
  name: string;
  email: string;
  password?: string;
  role: UserRole;
  school?: string;
}

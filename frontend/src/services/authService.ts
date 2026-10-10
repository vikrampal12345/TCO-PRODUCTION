import type { LoginCredentials, SignupCredentials, User, UserRole } from '../types/auth';
import { apiRequest, setAccessToken } from './http';

const loginPath = import.meta.env.VITE_AUTH_LOGIN_PATH || '/auth/login';
const signupPath = import.meta.env.VITE_AUTH_SIGNUP_PATH || '/auth/signup';
const googlePath = import.meta.env.VITE_AUTH_GOOGLE_PATH || '/auth/google';

type UnknownRecord = Record<string, unknown>;

function record(value: unknown): UnknownRecord {
  return value && typeof value === 'object' ? value as UnknownRecord : {};
}

function asString(value: unknown, fallback = ''): string {
  return typeof value === 'string' && value.trim() ? value : fallback;
}

function normalizeUser(raw: unknown, fallback?: Partial<User>): User {
  const outer = record(raw);
  const source = record(outer.user ?? outer.profile ?? raw);
  const rawRole = asString(source.role, fallback?.role || 'Teacher');
  const role: UserRole = rawRole === 'Educator' || rawRole === 'Administrator' ? rawRole : 'Teacher';
  const email = asString(source.email, fallback?.email || '');
  return {
    id: asString(source.id ?? source.user_id ?? source.sub, fallback?.id || email || `user-${Date.now()}`),
    name: asString(source.name ?? source.full_name ?? source.username, fallback?.name || email.split('@')[0] || 'Teacher'),
    email,
    role,
    school: asString(source.school ?? source.institution, fallback?.school || 'Academic Institution'),
    avatarUrl: asString(source.avatarUrl ?? source.avatar_url, fallback?.avatarUrl || '') || undefined,
  };
}

function saveTokenFromResponse(response: unknown): void {
  const payload = record(response);
  const token = payload.access_token ?? payload.token ?? record(payload.data).access_token;
  if (typeof token === 'string' && token) setAccessToken(token);
}

export const authService = {
  async login(credentials: LoginCredentials): Promise<User> {
    const response = await apiRequest<unknown>(loginPath, {
      method: 'POST',
      body: JSON.stringify({ email: credentials.email, username: credentials.email, password: credentials.password }),
    });
    saveTokenFromResponse(response);
    return normalizeUser(response, { email: credentials.email, role: 'Teacher' });
  },

  async signup(credentials: SignupCredentials): Promise<User> {
    const response = await apiRequest<unknown>(signupPath, {
      method: 'POST',
      body: JSON.stringify({
        name: credentials.name,
        full_name: credentials.name,
        email: credentials.email,
        password: credentials.password,
        role: credentials.role,
        school: credentials.school,
        institution: credentials.school,
      }),
    });
    saveTokenFromResponse(response);
    const user = normalizeUser(response, {
      id: credentials.email,
      name: credentials.name,
      email: credentials.email,
      role: credentials.role,
      school: credentials.school,
    });
    return user;
  },

  async loginWithGoogle(): Promise<User> {
    // Real Google OAuth requires the backend to return an OAuth redirect URL or token.
    const response = await apiRequest<unknown>(googlePath, { method: 'POST', body: JSON.stringify({}) });
    const payload = record(response);
    if (typeof payload.authorization_url === 'string') {
      window.location.assign(payload.authorization_url);
      throw new Error('Google sign-in redirect started.');
    }
    saveTokenFromResponse(response);
    return normalizeUser(response);
  },
};

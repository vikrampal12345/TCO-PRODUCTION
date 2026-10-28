const DEFAULT_API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1').replace(/\/$/, '');

export function getApiBaseUrl(): string {
  try {
    const saved = localStorage.getItem('tco_user_preferences');
    if (saved) {
      const preferences = JSON.parse(saved) as { fastApiEndpoint?: string };
      if (preferences.fastApiEndpoint?.trim()) return preferences.fastApiEndpoint.trim().replace(/\/$/, '');
    }
  } catch {
    // Fall back to Vite environment configuration if local preferences are malformed.
  }
  return DEFAULT_API_BASE_URL;
}

export const API_BASE_URL = DEFAULT_API_BASE_URL;

export class ApiError extends Error {
  status: number;
  detail?: unknown;

  constructor(message: string, status: number, detail?: unknown) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

export function getAccessToken(): string | null {
  try {
    return localStorage.getItem('tco_access_token');
  } catch {
    return null;
  }
}

export function setAccessToken(token: string | null): void {
  try {
    if (token) localStorage.setItem('tco_access_token', token);
    else localStorage.removeItem('tco_access_token');
  } catch {
    // localStorage can be unavailable in restricted browser contexts.
  }
}

function extractErrorMessage(payload: unknown, fallback: string): string {
  if (typeof payload === 'string' && payload.trim()) return payload;
  if (payload && typeof payload === 'object') {
    const object = payload as Record<string, unknown>;
    const detail = object.detail ?? object.message ?? object.error;
    if (typeof detail === 'string' && detail.trim()) return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => {
        if (item && typeof item === 'object' && 'msg' in item) return String((item as { msg: unknown }).msg);
        return String(item);
      }).join('; ');
    }
  }
  return fallback;
}

export async function apiRequest<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers || {});
  const isFormData = typeof FormData !== 'undefined' && init.body instanceof FormData;
  if (init.body != null && !isFormData && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json');
  }
  if (!headers.has('Accept')) headers.set('Accept', 'application/json');

  const token = getAccessToken();
  if (token && !headers.has('Authorization')) headers.set('Authorization', `Bearer ${token}`);

  let response: Response;
  try {
    const baseUrl = getApiBaseUrl();
    response = await fetch(`${baseUrl}${path.startsWith('/') ? path : `/${path}`}`, {
      ...init,
      headers,
    });
  } catch (error) {
    throw new ApiError(
      `Backend se connection nahi ho paya. Check karein ki FastAPI ${getApiBaseUrl()} par chal raha hai aur CORS enabled hai.`,
      0,
      error,
    );
  }

  if (response.status === 204) return undefined as T;
  const contentType = response.headers.get('content-type') || '';
  let payload: unknown;
  if (contentType.includes('application/json')) {
    payload = await response.json().catch(() => null);
  } else {
    payload = await response.text().catch(() => '');
  }

  if (!response.ok) {
    throw new ApiError(
      extractErrorMessage(payload, `Backend request failed (${response.status})`),
      response.status,
      payload,
    );
  }
  return payload as T;
}

export function errorMessage(error: unknown): string {
  if (error instanceof Error) return error.message;
  return 'An unexpected error occurred. Please try again.';
}

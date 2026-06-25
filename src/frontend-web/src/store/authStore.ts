import { create } from 'zustand';

export interface User {
  userId: string;
  role: string;
  tenantId: string;
  displayName: string;
}

interface AuthState {
  user: User | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, displayName: string, role?: string) => Promise<void>;
  logout: () => void;
  getAuthHeaders: () => Record<string, string>;
}

const API_BASE = '/api/v1';

function saveSession(token: string, user: User) {
  localStorage.setItem('eci_token', token);
  localStorage.setItem('eci_user', JSON.stringify(user));
}

function clearSession() {
  localStorage.removeItem('eci_token');
  localStorage.removeItem('eci_user');
}

function loadSession(): { token: string | null; user: User | null } {
  const token = localStorage.getItem('eci_token');
  const raw = localStorage.getItem('eci_user');
  let user: User | null = null;
  if (raw) {
    try { user = JSON.parse(raw); } catch { /* ignore */ }
  }
  return { token, user };
}

const saved = loadSession();

export const useAuthStore = create<AuthState>((set, get) => ({
  user: saved.user,
  token: saved.token,
  isAuthenticated: !!saved.token && !!saved.user,

  login: async (email: string, password: string) => {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    const user: User = {
      userId: data.user_id,
      role: data.role,
      tenantId: data.tenant_id,
      displayName: data.display_name,
    };
    saveSession(data.access_token, user);
    set({ user, token: data.access_token, isAuthenticated: true });
  },

  register: async (email: string, password: string, displayName: string, role = 'student') => {
    const res = await fetch(`${API_BASE}/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName, role }),
    });
    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Registration failed');
    }
    const data = await res.json();
    const user: User = {
      userId: data.user_id,
      role: data.role,
      tenantId: data.tenant_id,
      displayName: data.display_name,
    };
    saveSession(data.access_token, user);
    set({ user, token: data.access_token, isAuthenticated: true });
  },

  logout: () => {
    clearSession();
    set({ user: null, token: null, isAuthenticated: false });
  },

  getAuthHeaders: () => {
    const token = get().token;
    return token ? { Authorization: `Bearer ${token}` } : {} as Record<string, string>;
  },
}));

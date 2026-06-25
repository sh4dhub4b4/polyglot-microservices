/**
 * api.js — Shared API helper for Polyglot ECI Dummy Frontend
 * Handles JWT authentication and all REST API calls to the FastAPI backend.
 */

const API_BASE = 'http://127.0.0.1:8000';
const WS_BASE  = 'ws://127.0.0.1:8000';

// ──────────────────────────────────────────────────────
// JWT Auth Store
// ──────────────────────────────────────────────────────
const Auth = {
  getUser() {
    const stored = localStorage.getItem('eci_user');
    return stored ? JSON.parse(stored) : null;
  },

  async login(email, password) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    const user = {
      userId: data.user_id,
      role: data.role,
      displayName: data.display_name,
      token: data.access_token,
      tenantId: data.tenant_id,
    };
    localStorage.setItem('eci_user', JSON.stringify(user));
    return user;
  },

  async register(email, password, displayName, role) {
    const res = await fetch(`${API_BASE}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password, display_name: displayName, role }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Registration failed' }));
      throw new Error(err.detail || 'Registration failed');
    }
    const data = await res.json();
    const user = {
      userId: data.user_id,
      role: data.role,
      displayName: data.display_name,
      token: data.access_token,
      tenantId: data.tenant_id,
    };
    localStorage.setItem('eci_user', JSON.stringify(user));
    return user;
  },

  logout() {
    localStorage.removeItem('eci_user');
    window.location.href = '/static/login.html';
  },

  getToken() {
    const user = this.getUser();
    return user ? user.token : null;
  },

  isLoggedIn() {
    return !!this.getUser() && !!this.getToken();
  },

  getHeaders() {
    const token = this.getToken();
    if (!token) return { 'Content-Type': 'application/json' };
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${token}`,
    };
  }
};

// ──────────────────────────────────────────────────────
// Generic API Call
// ──────────────────────────────────────────────────────
async function apiCall(method, path, body = null) {
  const opts = {
    method,
    headers: Auth.getHeaders(),
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API_BASE}${path}`, opts);

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

const api = {
  // ── Academic — Teacher ──────────────────────────────
  teacher: {
    getCourses:          ()             => apiCall('GET',  '/api/v1/academic/teacher/courses'),
    createCourse:        (body)         => apiCall('POST', '/api/v1/academic/teacher/courses', body),
    createAssignment:    (body)         => apiCall('POST', '/api/v1/academic/teacher/assignments', body),
    getSubmissions:      (assignmentId) => apiCall('GET',  `/api/v1/academic/teacher/assignments/${assignmentId}/submissions`),
    gradeSubmission:     (subId, body)  => apiCall('PATCH',`/api/v1/academic/teacher/submissions/${subId}/grade`, body),
  },

  // ── Academic — Student ──────────────────────────────
  student: {
    getCourses:          ()             => apiCall('GET',  '/api/v1/academic/student/courses'),
    getAssignments:      (courseId)     => apiCall('GET',  `/api/v1/academic/student/courses/${courseId}/assignments`),
    submitAssignment:    (asgId, body)  => apiCall('POST', `/api/v1/academic/student/assignments/${asgId}/submit`, body),
    mySubmissions:       ()             => apiCall('GET',  '/api/v1/academic/student/my-submissions'),
  },

  // ── Enrollment ──────────────────────────────────────
  enrollStudent: (body) => apiCall('POST', '/api/v1/enrollments/', body),

  // ── Pod Catalog ─────────────────────────────────────
  getPodCatalog: () => apiCall('GET', '/api/v1/pods/catalog'),

  // ── Billing ─────────────────────────────────────────
  billing: {
    getCredits: () => apiCall('GET', '/api/v1/academic/billing/credits'),
  },
};

// ──────────────────────────────────────────────────────
// Toast Notification Utility
// ──────────────────────────────────────────────────────
function showToast(message, type = 'info', duration = 4000) {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${icons[type] || ''}</span><span>${message}</span>`;
  container.appendChild(toast);
  setTimeout(() => toast.remove(), duration);
}

// ──────────────────────────────────────────────────────
// WebSocket Execution Helper
// ──────────────────────────────────────────────────────
function createExecutionSocket(payload, callbacks = {}) {
  const ws = new WebSocket(`${WS_BASE}/ws/execute`);

  ws.onopen = () => {
    ws.send(JSON.stringify(payload));
    callbacks.onQueued?.();
  };

  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    const status = data.status;

    if (status === 'queued')       callbacks.onQueued?.(data);
    else if (status === 'provisioning') callbacks.onProvisioning?.(data);
    else if (status === 'executing')    callbacks.onExecuting?.(data);
    else if (status === 'completed')    { callbacks.onComplete?.(data); ws.close(); }
    else if (status === 'error')        { callbacks.onError?.(data); ws.close(); }
    else callbacks.onMessage?.(data);
  };

  ws.onerror = (e) => callbacks.onError?.({ message: 'WebSocket connection error' });
  ws.onclose = () => callbacks.onClose?.();

  return ws;
}

// ──────────────────────────────────────────────────────
// UI Helpers
// ──────────────────────────────────────────────────────
function renderUserPill() {
  const user = Auth.getUser();
  if (!user) return;
  const el = document.getElementById('user-pill');
  if (!el) return;
  el.innerHTML = `
    <div class="user-avatar">${user.displayName?.[0]?.toUpperCase() || '?'}</div>
    <div>
      <div style="font-weight:600;font-size:0.83rem">${user.displayName}</div>
      <div style="color:var(--text-muted);font-size:0.72rem">${user.role} · ${user.tenantId ? 'Tenant: ' + user.tenantId.slice(0,8) : ''}</div>
    </div>
  `;
}

function setActiveNav(sectionId) {
  document.querySelectorAll('.nav-item').forEach(el => el.classList.remove('active'));
  const el = document.querySelector(`[data-section="${sectionId}"]`);
  if (el) el.classList.add('active');
}

function showSection(id) {
  document.querySelectorAll('.content-section').forEach(s => s.classList.add('hidden'));
  const el = document.getElementById(id);
  if (el) el.classList.remove('hidden');
}

// Init
document.addEventListener('DOMContentLoaded', () => {
  renderUserPill();
});

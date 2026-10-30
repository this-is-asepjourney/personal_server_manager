import { formatBytes, formatDuration } from './utils';
export { formatBytes, formatDuration };

const API_BASE = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export function getAuthToken(): string | null {
  if (typeof window === 'undefined') return null;
  return localStorage.getItem('psm_access_token');
}

export function setAuthToken(token: string) {
  if (typeof window !== 'undefined') {
    localStorage.setItem('psm_access_token', token);
  }
}

export function clearAuth() {
  if (typeof window !== 'undefined') {
    localStorage.removeItem('psm_access_token');
    localStorage.removeItem('psm_user');
  }
}

export async function fetchWithAuth(endpoint: string, options: RequestInit = {}) {
  const token = getAuthToken();
  const headers = new Headers(options.headers || {});

  if (token) {
    headers.set('Authorization', `Bearer ${token}`);
  }
  if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json');
  }

  const url = endpoint.startsWith('http') ? endpoint : `${API_BASE}${endpoint}`;
  const response = await fetch(url, { ...options, headers });

  if (response.status === 401 && typeof window !== 'undefined' && !window.location.pathname.includes('/login')) {
    clearAuth();
    window.location.href = '/login';
  }

  return response;
}

export const api = {
  // Auth
  async login(email: string, password: string) {
    const res = await fetch(`${API_BASE}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Authentication failed' }));
      throw new Error(err.detail || 'Login failed');
    }
    const data = await res.json();
    setAuthToken(data.access_token);
    if (typeof window !== 'undefined') {
      localStorage.setItem('psm_user', JSON.stringify(data.user));
    }
    return data;
  },

  async me() {
    const res = await fetchWithAuth('/api/v1/auth/me');
    if (!res.ok) throw new Error('Not authenticated');
    return res.json();
  },

  async logout() {
    try {
      await fetchWithAuth('/api/v1/auth/logout', { method: 'POST' });
    } catch (_) {}
    clearAuth();
    if (typeof window !== 'undefined') {
      window.location.href = '/login';
    }
  },

  // Servers
  async getServers() {
    const res = await fetchWithAuth('/api/v1/servers');
    if (!res.ok) throw new Error('Failed to fetch servers');
    return res.json();
  },

  async getServer(id: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${id}`);
    if (!res.ok) throw new Error('Failed to fetch server');
    return res.json();
  },

  async createServer(data: { name: string; hostname?: string; description?: string }) {
    const res = await fetchWithAuth('/api/v1/servers', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create server');
    return res.json();
  },

  async deleteServer(id: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${id}`, { method: 'DELETE' });
    if (!res.ok) throw new Error('Failed to delete server');
    return res.json();
  },

  async getServerMetrics(id: string, limit = 30) {
    const res = await fetchWithAuth(`/api/v1/servers/${id}/metrics?limit=${limit}`);
    if (!res.ok) return [];
    return res.json();
  },

  async reconnectServer(id: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${id}/reconnect`, { method: 'POST' });
    return res.json();
  },

  // Containers
  async getContainers(serverId: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${serverId}/containers`);
    if (!res.ok) return [];
    return res.json();
  },

  async containerAction(serverId: string, cid: string, action: 'start' | 'stop' | 'restart' | 'remove') {
    const method = action === 'remove' ? 'DELETE' : 'POST';
    const res = await fetchWithAuth(`/api/v1/servers/${serverId}/containers/${cid}/${action}`, { method });
    if (!res.ok) throw new Error(`Failed to ${action} container`);
    return res.json();
  },

  async getImages(serverId: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${serverId}/images`);
    return res.ok ? res.json() : [];
  },

  async getVolumes(serverId: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${serverId}/volumes`);
    return res.ok ? res.json() : [];
  },

  async getNetworks(serverId: string) {
    const res = await fetchWithAuth(`/api/v1/servers/${serverId}/networks`);
    return res.ok ? res.json() : [];
  },

  // Projects
  async getProjects() {
    const res = await fetchWithAuth('/api/v1/projects');
    if (!res.ok) throw new Error('Failed to fetch projects');
    return res.json();
  },

  async getProject(id: string) {
    const res = await fetchWithAuth(`/api/v1/projects/${id}`);
    if (!res.ok) throw new Error('Failed to fetch project');
    return res.json();
  },

  async createProject(data: any) {
    const res = await fetchWithAuth('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error('Failed to create project');
    return res.json();
  },

  async deleteProject(id: string) {
    const res = await fetchWithAuth(`/api/v1/projects/${id}`, { method: 'DELETE' });
    return res.json();
  },

  async getProjectEnvironment(id: string) {
    const res = await fetchWithAuth(`/api/v1/projects/${id}/environment`);
    return res.ok ? res.json() : [];
  },

  async updateProjectEnvironment(id: string, variables: Array<{ key: string; value: string }>) {
    const res = await fetchWithAuth(`/api/v1/projects/${id}/environment`, {
      method: 'PUT',
      body: JSON.stringify({ variables }),
    });
    return res.json();
  },

  // Deployments
  async getDeployments() {
    const res = await fetchWithAuth('/api/v1/deployments');
    return res.ok ? res.json() : [];
  },

  async getDeployment(id: string) {
    const res = await fetchWithAuth(`/api/v1/deployments/${id}`);
    return res.ok ? res.json() : null;
  },

  async triggerGitDeployment(projectId: string, branch = 'main') {
    const res = await fetchWithAuth('/api/v1/deployments/git', {
      method: 'POST',
      body: JSON.stringify({ project_id: projectId, branch }),
    });
    if (!res.ok) throw new Error('Failed to trigger deployment');
    return res.json();
  },

  async uploadZipDeployment(projectId: string, file: File) {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetchWithAuth(`/api/v1/deployments/${projectId}/finalize-upload`, {
      method: 'POST',
      body: formData,
    });
    if (!res.ok) throw new Error('Failed to upload and deploy ZIP');
    return res.json();
  },

  async getDeploymentLogs(id: string) {
    const res = await fetchWithAuth(`/api/v1/deployments/${id}/logs`);
    return res.ok ? res.json() : [];
  },

  async rollbackDeployment(id: string) {
    const res = await fetchWithAuth(`/api/v1/deployments/${id}/rollback`, { method: 'POST' });
    if (!res.ok) throw new Error('Rollback failed');
    return res.json();
  },

  // Monitoring
  async getMonitoringOverview() {
    const res = await fetchWithAuth('/api/v1/monitoring/overview');
    return res.ok ? res.json() : null;
  },

  async getMonitoringHistory(serverId?: string) {
    const qs = serverId ? `?server_id=${serverId}` : '';
    const res = await fetchWithAuth(`/api/v1/monitoring/history${qs}`);
    return res.ok ? res.json() : [];
  },

  // Audit Logs
  async getAuditLogs() {
    const res = await fetchWithAuth('/api/v1/audit-logs');
    return res.ok ? res.json() : [];
  },
};

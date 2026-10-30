'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import {
  Server as ServerIcon,
  Play,
  Square,
  RotateCw,
  Trash2,
  Box,
  Layers,
  HardDrive,
  Network,
  Settings,
  RefreshCw,
  Cpu,
  Activity,
  ArrowLeft,
  Terminal,
  Key,
  ShieldAlert,
  X,
} from 'lucide-react';
import { api } from '../../../lib/api';

export default function ServerDetailPage() {
  const params = useParams();
  const router = useRouter();
  const serverId = params.serverId as string;

  const [server, setServer] = useState<any>(null);
  const [containers, setContainers] = useState<any[]>([]);
  const [images, setImages] = useState<any[]>([]);
  const [volumes, setVolumes] = useState<any[]>([]);
  const [networks, setNetworks] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'containers' | 'images' | 'volumes' | 'networks' | 'settings'>('overview');
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // Container logs modal state
  const [logsModal, setLogsModal] = useState<{ open: boolean; name: string; logs: string[] }>({
    open: false,
    name: '',
    logs: [],
  });

  // Settings form state
  const [editName, setEditName] = useState('');
  const [editHostname, setEditHostname] = useState('');
  const [rotatedToken, setRotatedToken] = useState<string | null>(null);
  const [settingsMsg, setSettingsMsg] = useState<string | null>(null);

  const loadData = async () => {
    try {
      setLoading(true);
      const [s, c, img, vol, net] = await Promise.all([
        api.getServer(serverId),
        api.getContainers(serverId),
        api.getImages(serverId),
        api.getVolumes(serverId),
        api.getNetworks(serverId),
      ]);
      setServer(s);
      setEditName(s.name || '');
      setEditHostname(s.hostname || '');
      setContainers(c);
      setImages(img);
      setVolumes(vol);
      setNetworks(net);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [serverId]);

  const handleContainerAction = async (cid: string, action: 'start' | 'stop' | 'restart' | 'remove') => {
    if (action === 'remove' && !confirm('Are you sure you want to remove this container?')) return;
    try {
      setActionLoading(`${cid}-${action}`);
      await api.containerAction(serverId, cid, action);
      setTimeout(loadData, 800);
    } catch (err: any) {
      alert(err.message || `Failed to ${action} container`);
    } finally {
      setActionLoading(null);
    }
  };

  const handleViewLogs = async (cid: string, name: string) => {
    try {
      const res = await api.getContainerLogs(serverId, cid);
      const lines = Array.isArray(res.logs)
        ? res.logs
        : typeof res.logs === 'string'
        ? res.logs.split('\n')
        : ['No log output available.'];
      setLogsModal({ open: true, name, logs: lines });
    } catch (err: any) {
      alert(err.message || 'Failed to fetch container logs');
    }
  };

  const handleReconnect = async () => {
    try {
      await api.reconnectServer(serverId);
      alert('Ping dispatched to agent.');
    } catch (err: any) {
      alert(err.message || 'Failed to dispatch reconnect ping');
    }
  };

  const handleSaveServerSettings = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await api.updateServer(serverId, { name: editName, hostname: editHostname });
      setSettingsMsg('Server configuration updated successfully.');
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update server');
    }
  };

  const handleRotateToken = async () => {
    if (!confirm('Rotate agent token? Existing agent tokens for this node will be revoked.')) return;
    try {
      const res = await api.rotateAgentToken(serverId);
      setRotatedToken(res.agent_token);
    } catch (err: any) {
      alert(err.message || 'Failed to rotate token');
    }
  };

  const handleRevokeAgent = async () => {
    if (!confirm('Revoke all agent credentials and mark server offline?')) return;
    try {
      await api.revokeAgent(serverId);
      loadData();
      alert('Agent credentials revoked.');
    } catch (err: any) {
      alert(err.message || 'Failed to revoke agent');
    }
  };

  if (!server && !loading) {
    return <div className="p-8 text-center text-gray-500">Server not found.</div>;
  }

  const isOnline = server?.status === 'online';

  return (
    <div className="space-y-6">
      {/* Top Banner */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/servers')}
            className="p-2 rounded-lg border border-border hover:bg-card text-gray-400 hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-foreground">{server?.name || 'Loading...'}</h1>
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                  isOnline
                    ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                    : 'bg-rose-500/10 text-rose-500 border border-rose-500/20'
                }`}
              >
                {server?.status}
              </span>
            </div>
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              {server?.hostname} • {server?.os_name} {server?.os_version}
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReconnect}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border border-border text-xs font-medium hover:bg-card text-foreground transition-all"
          >
            <RefreshCw className="w-3.5 h-3.5 text-blue-500" />
            <span>Ping Agent</span>
          </button>
        </div>
      </div>

      {/* Tabs Header */}
      <div className="flex items-center gap-2 border-b border-border text-sm overflow-x-auto pb-px">
        {[
          { key: 'overview', label: 'Overview', icon: ServerIcon },
          { key: 'containers', label: `Containers (${containers.length})`, icon: Box },
          { key: 'images', label: `Images (${images.length})`, icon: Layers },
          { key: 'volumes', label: `Volumes (${volumes.length})`, icon: HardDrive },
          { key: 'networks', label: `Networks (${networks.length})`, icon: Network },
          { key: 'settings', label: 'Settings', icon: Settings },
        ].map((tab) => {
          const Icon = tab.icon;
          const isActive = activeTab === tab.key;
          return (
            <button
              key={tab.key}
              onClick={() => setActiveTab(tab.key as any)}
              className={`flex items-center gap-2 px-4 py-2.5 font-medium border-b-2 transition-colors whitespace-nowrap text-xs ${
                isActive
                  ? 'border-blue-500 text-blue-600 dark:text-blue-400'
                  : 'border-transparent text-gray-500 hover:text-foreground'
              }`}
            >
              <Icon className="w-4 h-4" />
              <span>{tab.label}</span>
            </button>
          );
        })}
      </div>

      {/* Tab: Overview */}
      {activeTab === 'overview' && (
        <div className="space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            <div className="p-5 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                <span className="font-semibold uppercase tracking-wider">CPU Usage</span>
                <Cpu className="w-4 h-4 text-blue-500" />
              </div>
              <div className="text-2xl font-bold font-mono">
                {server?.latest_metrics?.cpu_usage ?? 24.5}%
              </div>
              <div className="mt-3 h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-blue-500 rounded-full"
                  style={{ width: `${server?.latest_metrics?.cpu_usage ?? 24.5}%` }}
                ></div>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                <span className="font-semibold uppercase tracking-wider">Memory Usage</span>
                <Activity className="w-4 h-4 text-purple-500" />
              </div>
              <div className="text-2xl font-bold font-mono">
                {server?.latest_metrics?.memory_usage ?? 58.2}%
              </div>
              <div className="mt-3 h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-purple-500 rounded-full"
                  style={{ width: `${server?.latest_metrics?.memory_usage ?? 58.2}%` }}
                ></div>
              </div>
            </div>

            <div className="p-5 rounded-xl border border-border bg-card">
              <div className="flex items-center justify-between text-xs text-gray-500 mb-2">
                <span className="font-semibold uppercase tracking-wider">Disk Usage</span>
                <HardDrive className="w-4 h-4 text-emerald-500" />
              </div>
              <div className="text-2xl font-bold font-mono">
                {server?.latest_metrics?.disk_usage ?? 42.0}%
              </div>
              <div className="mt-3 h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 rounded-full"
                  style={{ width: `${server?.latest_metrics?.disk_usage ?? 42.0}%` }}
                ></div>
              </div>
            </div>
          </div>

          {/* System Info Table */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="font-bold text-sm text-foreground mb-4">System Information</h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 text-xs font-mono">
              <div className="p-3 rounded-lg bg-background border border-border">
                <span className="text-gray-400 block mb-1">Architecture</span>
                <span className="text-foreground">{server?.architecture}</span>
              </div>
              <div className="p-3 rounded-lg bg-background border border-border">
                <span className="text-gray-400 block mb-1">Operating System</span>
                <span className="text-foreground">{server?.os_name} {server?.os_version}</span>
              </div>
              <div className="p-3 rounded-lg bg-background border border-border">
                <span className="text-gray-400 block mb-1">Agent Version</span>
                <span className="text-foreground">{server?.agent?.agent_version || '0.1.0'}</span>
              </div>
              <div className="p-3 rounded-lg bg-background border border-border">
                <span className="text-gray-400 block mb-1">Last Seen</span>
                <span className="text-foreground">{server?.last_seen ? new Date(server.last_seen).toLocaleString() : 'Just now'}</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Containers */}
      {activeTab === 'containers' && (
        <div className="rounded-xl border border-border bg-card overflow-hidden">
          <div className="p-4 border-b border-border flex items-center justify-between">
            <h3 className="font-bold text-sm text-foreground">Docker Containers</h3>
            <button
              onClick={loadData}
              className="text-xs text-blue-500 hover:underline flex items-center gap-1"
            >
              <RefreshCw className="w-3 h-3" /> Refresh
            </button>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-background/60 text-gray-400 uppercase tracking-wider border-b border-border">
                <tr>
                  <th className="p-3.5">Name</th>
                  <th className="p-3.5">Image</th>
                  <th className="p-3.5">Status</th>
                  <th className="p-3.5">Ports</th>
                  <th className="p-3.5 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {containers.map((c) => {
                  const running = c.status === 'running';
                  return (
                    <tr key={c.id} className="hover:bg-gray-500/5 transition-colors">
                      <td className="p-3.5 font-semibold text-foreground flex items-center gap-2">
                        <span className={`w-2 h-2 rounded-full ${running ? 'bg-emerald-500' : 'bg-gray-400'}`}></span>
                        {c.name}
                      </td>
                      <td className="p-3.5 font-mono text-gray-400">{c.image}</td>
                      <td className="p-3.5">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                            running
                              ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                              : 'bg-gray-500/10 text-gray-500'
                          }`}
                        >
                          {c.status}
                        </span>
                      </td>
                      <td className="p-3.5 font-mono text-gray-400">
                        {Array.isArray(c.ports) && c.ports.length > 0
                          ? c.ports.map((p: any) => `${p.external || p.internal}:${p.internal}`).join(', ')
                          : '-'}
                      </td>
                      <td className="p-3.5 text-right">
                        <div className="flex items-center justify-end gap-1.5">
                          <button
                            onClick={() => handleViewLogs(c.docker_id || c.id, c.name)}
                            className="p-1.5 rounded hover:bg-gray-500/10 text-gray-400 hover:text-foreground"
                            title="View Logs"
                          >
                            <Terminal className="w-3.5 h-3.5" />
                          </button>
                          {running ? (
                            <button
                              onClick={() => handleContainerAction(c.docker_id || c.id, 'stop')}
                              disabled={actionLoading === `${c.docker_id || c.id}-stop`}
                              className="p-1.5 rounded hover:bg-amber-500/10 text-amber-500"
                              title="Stop"
                            >
                              <Square className="w-3.5 h-3.5" />
                            </button>
                          ) : (
                            <button
                              onClick={() => handleContainerAction(c.docker_id || c.id, 'start')}
                              disabled={actionLoading === `${c.docker_id || c.id}-start`}
                              className="p-1.5 rounded hover:bg-emerald-500/10 text-emerald-500"
                              title="Start"
                            >
                              <Play className="w-3.5 h-3.5" />
                            </button>
                          )}
                          <button
                            onClick={() => handleContainerAction(c.docker_id || c.id, 'restart')}
                            disabled={actionLoading === `${c.docker_id || c.id}-restart`}
                            className="p-1.5 rounded hover:bg-blue-500/10 text-blue-500"
                            title="Restart"
                          >
                            <RotateCw className="w-3.5 h-3.5" />
                          </button>
                          <button
                            onClick={() => handleContainerAction(c.docker_id || c.id, 'remove')}
                            disabled={actionLoading === `${c.docker_id || c.id}-remove`}
                            className="p-1.5 rounded hover:bg-rose-500/10 text-rose-500"
                            title="Remove"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Tab: Images */}
      {activeTab === 'images' && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="font-bold text-sm text-foreground mb-4">Cached Docker Images</h3>
          <div className="space-y-2">
            {images.map((img: any) => (
              <div
                key={img.id}
                className="flex items-center justify-between p-3 rounded-lg border border-border bg-background text-xs font-mono"
              >
                <div>
                  <span className="font-semibold text-foreground">{img.repository}:{img.tag}</span>
                </div>
                <div className="text-gray-400">
                  <span>{img.size}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Volumes */}
      {activeTab === 'volumes' && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="font-bold text-sm text-foreground mb-4">Docker Volumes</h3>
          <div className="space-y-2">
            {volumes.map((vol: any) => (
              <div
                key={vol.id}
                className="p-3 rounded-lg border border-border bg-background text-xs space-y-1"
              >
                <div className="flex items-center justify-between">
                  <span className="font-bold font-mono text-foreground">{vol.name}</span>
                  <span className="text-gray-400 text-[10px] uppercase font-mono">{vol.driver}</span>
                </div>
                <p className="text-gray-500 font-mono text-[11px] truncate">{vol.mountpoint}</p>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Networks */}
      {activeTab === 'networks' && (
        <div className="rounded-xl border border-border bg-card p-5">
          <h3 className="font-bold text-sm text-foreground mb-4">Docker Networks</h3>
          <div className="space-y-2">
            {networks.map((net: any) => (
              <div
                key={net.id}
                className="flex items-center justify-between p-3 rounded-lg border border-border bg-background text-xs"
              >
                <span className="font-bold font-mono text-foreground">{net.name}</span>
                <span className="text-gray-400 font-mono">{net.driver} ({net.scope})</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tab: Settings */}
      {activeTab === 'settings' && (
        <div className="space-y-6">
          <form onSubmit={handleSaveServerSettings} className="rounded-xl border border-border bg-card p-5 space-y-4">
            <h3 className="font-bold text-sm text-foreground">Server Configuration</h3>
            {settingsMsg && (
              <div className="p-2.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 text-xs">
                {settingsMsg}
              </div>
            )}
            <div className="space-y-4 max-w-md">
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Node Identifier</label>
                <input
                  type="text"
                  disabled
                  value={server?.id || ''}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border text-xs font-mono text-gray-400"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Server Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm text-foreground"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1">Hostname / IP</label>
                <input
                  type="text"
                  value={editHostname}
                  onChange={(e) => setEditHostname(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border text-sm font-mono text-foreground"
                />
              </div>
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-medium"
              >
                Save Changes
              </button>
            </div>
          </form>

          {/* Agent Credentials Management */}
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <h3 className="font-bold text-sm text-foreground">Agent Security & Credentials</h3>
            <p className="text-xs text-gray-500">
              Rotate or revoke the authentication token used by the Server Agent on this node.
            </p>
            {rotatedToken && (
              <div className="p-3 rounded-lg bg-amber-500/10 border border-amber-500/20 text-xs font-mono space-y-1">
                <div className="text-amber-500 font-semibold">New Agent Token (save now, shown once):</div>
                <div className="text-foreground break-all select-all">{rotatedToken}</div>
              </div>
            )}
            <div className="flex flex-wrap gap-3">
              <button
                onClick={handleRotateToken}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-border hover:bg-background text-xs font-medium text-amber-500"
              >
                <Key className="w-3.5 h-3.5" />
                <span>Rotate Agent Token</span>
              </button>
              <button
                onClick={handleRevokeAgent}
                className="flex items-center gap-1.5 px-3.5 py-2 rounded-lg border border-rose-500/30 hover:bg-rose-500/10 text-xs font-medium text-rose-500"
              >
                <ShieldAlert className="w-3.5 h-3.5" />
                <span>Revoke Agent Credentials</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Container Logs Modal */}
      {logsModal.open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="w-full max-w-2xl rounded-xl border border-slate-800 bg-slate-950 shadow-2xl overflow-hidden font-mono text-xs">
            <div className="flex items-center justify-between px-4 py-3 bg-slate-900 border-b border-slate-800">
              <div className="flex items-center gap-2 text-slate-200 font-semibold">
                <Terminal className="w-4 h-4 text-blue-400" />
                <span>Container Logs: {logsModal.name}</span>
              </div>
              <button
                onClick={() => setLogsModal({ open: false, name: '', logs: [] })}
                className="text-slate-400 hover:text-white"
              >
                <X className="w-4 h-4" />
              </button>
            </div>
            <div className="p-4 max-h-96 overflow-y-auto space-y-1 text-slate-300">
              {logsModal.logs.map((line, i) => (
                <div key={i} className="py-0.5 border-b border-slate-900/60 break-all">
                  {line}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

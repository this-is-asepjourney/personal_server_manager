'use client';

import React, { useState, useEffect } from 'react';
import {
  Database,
  Download,
  RefreshCw,
  FolderArchive,
  ShieldCheck,
  RotateCcw,
  Trash2,
} from 'lucide-react';
import { api, formatBytes } from '../../lib/api';

export default function StoragePage() {
  const [backups, setBackups] = useState<any[]>([]);
  const [creating, setCreating] = useState(false);
  const [loading, setLoading] = useState(true);

  const loadBackups = async () => {
    try {
      setLoading(true);
      const list = await api.getBackups();
      setBackups(list);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadBackups();
  }, []);

  const handleCreateBackup = async (backupType: string) => {
    try {
      setCreating(true);
      const dateStr = new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-');
      await api.createBackup({
        name: `${backupType}-snapshot-${dateStr}`,
        backup_type: backupType,
      });
      await loadBackups();
    } catch (err: any) {
      alert(err.message || 'Failed to create backup snapshot');
    } finally {
      setCreating(false);
    }
  };

  const handleRestore = async (id: string, name: string) => {
    if (!confirm(`Restore system state from snapshot "${name}"?`)) return;
    try {
      const res = await api.restoreBackup(id);
      alert(res.message || 'Snapshot restored successfully.');
    } catch (err: any) {
      alert(err.message || 'Restore failed');
    }
  };

  const handleDelete = async (id: string) => {
    if (!confirm('Delete this backup snapshot?')) return;
    try {
      await api.deleteBackup(id);
      loadBackups();
    } catch (err: any) {
      alert(err.message || 'Delete failed');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Storage & Backup Center</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Docker volume persistence, database snapshot archives, and disaster recovery.
        </p>
      </div>

      {/* Snapshot Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-blue-500/10 text-blue-500">
              <Database className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-base text-foreground">PostgreSQL Database Snapshot</h3>
              <p className="text-xs text-gray-400">Control plane state, audit logs, and configurations</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">
            Exports all servers, users, projects, encrypted credentials, and historical logs into a compressed archive on the Control Plane volume.
          </p>
          <div className="flex items-center gap-2.5">
            <button
              onClick={() => handleCreateBackup('database')}
              disabled={creating}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all disabled:opacity-50"
            >
              <Download className="w-4 h-4" />
              <span>{creating ? 'Generating Snapshot...' : 'Create DB Snapshot'}</span>
            </button>
            <button
              onClick={() => handleCreateBackup('project_workspace')}
              disabled={creating}
              className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border hover:bg-background text-foreground text-xs font-medium transition-all disabled:opacity-50"
            >
              <FolderArchive className="w-4 h-4 text-purple-500" />
              <span>Snapshot Workspaces</span>
            </button>
          </div>
        </div>

        <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
          <div className="flex items-center gap-3">
            <div className="p-3 rounded-xl bg-purple-500/10 text-purple-500">
              <FolderArchive className="w-6 h-6" />
            </div>
            <div>
              <h3 className="font-bold text-base text-foreground">Docker Volumes Retention</h3>
              <p className="text-xs text-gray-400">Mounted volumes on managed homelab nodes</p>
            </div>
          </div>
          <p className="text-xs text-gray-500 leading-relaxed">
            Persistent storage locations on target nodes:
            <br />• <code>/var/lib/docker/volumes/psm-postgres</code> (Database)
            <br />• <code>/opt/psm/workspaces</code> (Deployments & Releases)
          </p>
          <div className="flex items-center gap-2 text-xs text-emerald-500 font-medium">
            <ShieldCheck className="w-4 h-4" />
            <span>Encrypted at rest with host permissions</span>
          </div>
        </div>
      </div>

      {/* Backup History Table */}
      <div className="rounded-xl border border-border bg-card overflow-hidden">
        <div className="p-4 border-b border-border flex items-center justify-between">
          <h3 className="font-bold text-sm text-foreground">Backup Snapshots ({backups.length})</h3>
          <button
            onClick={loadBackups}
            className="text-xs text-blue-500 hover:underline flex items-center gap-1"
          >
            <RefreshCw className="w-3 h-3" /> Refresh
          </button>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead className="bg-background/60 text-gray-400 uppercase tracking-wider border-b border-border">
              <tr>
                <th className="p-3.5">Archive Name</th>
                <th className="p-3.5">Type</th>
                <th className="p-3.5">Size</th>
                <th className="p-3.5">Status</th>
                <th className="p-3.5">Created At</th>
                <th className="p-3.5 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {backups.length === 0 ? (
                <tr>
                  <td colSpan={6} className="p-8 text-center text-gray-500">
                    {loading ? 'Loading snapshots...' : 'No backup snapshots created yet.'}
                  </td>
                </tr>
              ) : (
                backups.map((b) => (
                  <tr key={b.id} className="hover:bg-gray-500/5 transition-colors">
                    <td className="p-3.5 font-mono font-semibold text-foreground">{b.name}</td>
                    <td className="p-3.5 capitalize text-gray-400">{(b.backup_type || 'database').replace('_', ' ')}</td>
                    <td className="p-3.5 font-mono text-gray-400">{formatBytes(b.size_bytes)}</td>
                    <td className="p-3.5">
                      <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                        {b.status}
                      </span>
                    </td>
                    <td className="p-3.5 text-gray-400">{new Date(b.created_at).toLocaleString()}</td>
                    <td className="p-3.5 text-right">
                      <div className="flex items-center justify-end gap-2">
                        <button
                          onClick={() => api.downloadBackup(b.id, `${b.name}.json`)}
                          className="flex items-center gap-1 px-2.5 py-1 rounded border border-border hover:bg-card text-foreground font-medium"
                          title="Download Snapshot File"
                        >
                          <Download className="w-3 h-3 text-emerald-500" />
                          <span>Download</span>
                        </button>
                        <button
                          onClick={() => handleRestore(b.id, b.name)}
                          className="flex items-center gap-1 px-2.5 py-1 rounded border border-border hover:bg-blue-500/10 text-blue-500 font-medium"
                        >
                          <RotateCcw className="w-3 h-3" />
                          <span>Restore</span>
                        </button>
                        <button
                          onClick={() => handleDelete(b.id)}
                          className="p-1.5 rounded hover:bg-rose-500/10 text-rose-500"
                          title="Delete Snapshot"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

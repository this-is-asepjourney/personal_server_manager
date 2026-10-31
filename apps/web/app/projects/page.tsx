'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  FolderGit2,
  Plus,
  Rocket,
  Server,
  GitBranch,
  X,
  RefreshCw,
  Trash2,
  Upload,
  Database,
} from 'lucide-react';
import { api } from '../../lib/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState<any[]>([]);
  const [servers, setServers] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [modalOpen, setModalOpen] = useState(false);

  // Form states
  const [name, setName] = useState('');
  const [serverId, setServerId] = useState('');
  const [framework, setFramework] = useState('Next.js');
  const [sourceType, setSourceType] = useState<'git' | 'upload'>('git');
  const [repositoryUrl, setRepositoryUrl] = useState('');
  const [branch, setBranch] = useState('main');
  const [zipFile, setZipFile] = useState<File | null>(null);
  const [autoProvisionDb, setAutoProvisionDb] = useState(true);
  const [customDbName, setCustomDbName] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const loadData = async () => {
    try {
      setLoading(true);
      const [p, s] = await Promise.all([
        api.getProjects().catch(() => []),
        api.getServers().catch(() => []),
      ]);
      setProjects(p);
      setServers(s);
      if (s.length > 0 && !serverId) {
        setServerId(s[0].id);
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const derivedDbSlug = (customDbName || name || 'my_project')
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9_]/g, '_')
    .replace(/_+/g, '_')
    .replace(/^_|_$/g, '') || 'psm_app_db';

  const handleCreateProject = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!name || !serverId) return;
    setSubmitting(true);
    try {
      const created = await api.createProject({
        server_id: serverId,
        name,
        framework,
        source_type: sourceType,
        repository_url: repositoryUrl || null,
        branch,
        auto_provision_db: autoProvisionDb,
        database_name: customDbName.trim() || null,
      });

      // If user provided zip right away
      if (sourceType === 'upload' && zipFile) {
        await api.uploadZipDeployment(created.id, zipFile);
      }

      setModalOpen(false);
      setName('');
      setRepositoryUrl('');
      setCustomDbName('');
      setZipFile(null);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to create project');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (id: string, projName: string) => {
    if (!confirm(`Delete project "${projName}"?`)) return;
    try {
      await api.deleteProject(id);
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to delete');
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Project Management</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Deploy apps to servers via Git repository or direct ZIP archives with automatic PostgreSQL database provisioning.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="p-2 rounded-lg border border-border text-gray-500 hover:text-foreground hover:bg-card transition-all"
            title="Refresh"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <button
            onClick={() => setModalOpen(true)}
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium shadow-md shadow-blue-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>New Project</span>
          </button>
        </div>
      </div>

      {/* Projects Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
        {projects.map((p) => {
          const dbSlug = (p.name || 'app')
            .toLowerCase()
            .replace(/[^a-z0-9_]/g, '_')
            .replace(/_+/g, '_')
            .replace(/^_|_$/g, '');
          return (
            <div
              key={p.id}
              className="rounded-xl border border-border bg-card p-5 shadow-sm hover:border-blue-500/40 transition-all flex flex-col justify-between"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-3">
                  <div className="flex items-center gap-3">
                    <div className="p-2.5 rounded-lg border border-blue-500/30 bg-blue-500/10 text-blue-500">
                      <FolderGit2 className="w-5 h-5" />
                    </div>
                    <div>
                      <Link
                        href={`/projects/${p.id}`}
                        className="font-semibold text-sm text-foreground hover:text-blue-500 transition-colors"
                      >
                        {p.name}
                      </Link>
                      <p className="text-xs text-gray-400 font-mono mt-0.5">{p.framework}</p>
                    </div>
                  </div>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                    {p.status}
                  </span>
                </div>

                <div className="space-y-1.5 text-xs text-gray-400 py-3 border-t border-border">
                  <div className="flex items-center gap-1.5">
                    <Server className="w-3.5 h-3.5 text-gray-500" />
                    <span>Target: <span className="text-foreground font-medium">{p.server_name}</span></span>
                  </div>
                  {p.repository_url ? (
                    <div className="flex items-center gap-1.5 font-mono truncate">
                      <GitBranch className="w-3.5 h-3.5 text-gray-500 shrink-0" />
                      <span className="truncate">{p.branch || 'main'}</span>
                    </div>
                  ) : (
                    <div className="flex items-center gap-1.5">
                      <Upload className="w-3.5 h-3.5 text-gray-500" />
                      <span>Source: Uploaded ZIP</span>
                    </div>
                  )}
                  <div className="flex items-center gap-1.5 pt-1 text-emerald-500 font-mono text-[11px]">
                    <Database className="w-3.5 h-3.5 shrink-0" />
                    <span className="truncate">PostgreSQL Auto-DB: {dbSlug}</span>
                  </div>
                </div>
              </div>

              <div className="mt-4 pt-3 border-t border-border flex items-center justify-between">
                <Link
                  href={`/projects/${p.id}`}
                  className="flex items-center gap-1 px-3 py-1.5 rounded-lg bg-blue-600/10 hover:bg-blue-600/20 text-blue-600 dark:text-blue-400 text-xs font-medium transition-colors"
                >
                  <Rocket className="w-3 h-3" />
                  <span>Deploy / Manage</span>
                </Link>
                <button
                  onClick={() => handleDelete(p.id, p.name)}
                  className="p-1.5 text-gray-400 hover:text-rose-500 hover:bg-rose-500/10 rounded transition-colors"
                  title="Delete project"
                >
                  <Trash2 className="w-4 h-4" />
                </button>
              </div>
            </div>
          );
        })}
      </div>

      {/* New Project Modal */}
      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/60 backdrop-blur-sm">
          <div className="w-full max-w-lg rounded-2xl border border-border bg-card p-6 shadow-2xl space-y-4">
            <div className="flex items-center justify-between border-b border-border pb-3">
              <div className="flex items-center gap-2">
                <FolderGit2 className="w-5 h-5 text-blue-500" />
                <h3 className="font-bold text-foreground">Create Project</h3>
              </div>
              <button
                onClick={() => setModalOpen(false)}
                className="p-1 rounded text-gray-400 hover:text-foreground"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleCreateProject} className="space-y-4 text-xs">
              <div>
                <label className="block font-medium text-gray-400 mb-1">Project Name</label>
                <input
                  type="text"
                  required
                  placeholder="e.g. Stock-UMKM, backend-api"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block font-medium text-gray-400 mb-1">Target Server</label>
                <select
                  value={serverId}
                  onChange={(e) => setServerId(e.target.value)}
                  className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  {servers.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.hostname}) - {s.status}
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-medium text-gray-400 mb-1">Framework</label>
                  <select
                    value={framework}
                    onChange={(e) => setFramework(e.target.value)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm"
                  >
                    <option value="Next.js">Next.js</option>
                    <option value="Laravel">Laravel</option>
                    <option value="FastAPI">FastAPI</option>
                    <option value="Docker Compose">Docker Compose</option>
                    <option value="Node.js">Node.js</option>
                  </select>
                </div>

                <div>
                  <label className="block font-medium text-gray-400 mb-1">Source Type</label>
                  <select
                    value={sourceType}
                    onChange={(e) => setSourceType(e.target.value as any)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm"
                  >
                    <option value="git">Git Repository</option>
                    <option value="upload">Upload ZIP</option>
                  </select>
                </div>
              </div>

              {sourceType === 'git' ? (
                <>
                  <div>
                    <label className="block font-medium text-gray-400 mb-1">Repository URL</label>
                    <input
                      type="url"
                      placeholder="https://github.com/username/repo.git"
                      value={repositoryUrl}
                      onChange={(e) => setRepositoryUrl(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm font-mono"
                    />
                  </div>
                  <div>
                    <label className="block font-medium text-gray-400 mb-1">Branch</label>
                    <input
                      type="text"
                      placeholder="main"
                      value={branch}
                      onChange={(e) => setBranch(e.target.value)}
                      className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm font-mono"
                    />
                  </div>
                </>
              ) : (
                <div>
                  <label className="block font-medium text-gray-400 mb-1">Select Project ZIP</label>
                  <input
                    type="file"
                    accept=".zip"
                    onChange={(e) => setZipFile(e.target.files?.[0] || null)}
                    className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-sm file:mr-4 file:py-1 file:px-3 file:rounded file:border-0 file:bg-blue-600 file:text-white file:text-xs"
                  />
                </div>
              )}

              {/* PostgreSQL Auto-Connect & Auto-Create Option */}
              <div className="p-3.5 rounded-xl border border-emerald-500/30 bg-emerald-500/5 space-y-2.5">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoProvisionDb}
                    onChange={(e) => setAutoProvisionDb(e.target.checked)}
                    className="rounded border-border text-emerald-600 focus:ring-emerald-500"
                  />
                  <div className="flex items-center gap-1.5 font-semibold text-foreground">
                    <Database className="w-4 h-4 text-emerald-500" />
                    <span>Auto-Connect & Auto-Create PostgreSQL Database</span>
                  </div>
                </label>
                {autoProvisionDb && (
                  <div className="pl-6 space-y-1.5">
                    <p className="text-[11px] text-gray-400">
                      Otomatis membuat database jika belum ada di PostgreSQL dan menginjeksi variabel koneksi (<code>DATABASE_URL</code>, <code>DB_CONNECTION=pgsql</code>, <code>DB_HOST</code>, dll.) saat deploy.
                    </p>
                    <div>
                      <label className="block text-[11px] text-gray-400 mb-1">Database Name (opsional):</label>
                      <input
                        type="text"
                        placeholder={derivedDbSlug}
                        value={customDbName}
                        onChange={(e) => setCustomDbName(e.target.value)}
                        className="w-full px-2.5 py-1.5 rounded-lg bg-background border border-border text-foreground font-mono text-xs"
                      />
                    </div>
                  </div>
                )}
              </div>

              <div className="flex justify-end gap-3 pt-3 border-t border-border">
                <button
                  type="button"
                  onClick={() => setModalOpen(false)}
                  className="px-4 py-2 rounded-lg border border-border text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800"
                >
                  Cancel
                </button>
                <button
                  type="submit"
                  disabled={submitting}
                  className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium disabled:opacity-50"
                >
                  {submitting ? 'Creating...' : 'Create Project'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}

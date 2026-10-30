'use client';

import React, { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  FolderGit2,
  Rocket,
  Key,
  Settings,
  RefreshCw,
  GitBranch,
  ArrowLeft,
  RotateCcw,
  Plus,
  Trash2,
  Check,
  Upload,
} from 'lucide-react';
import { api } from '../../../lib/api';

export default function ProjectDetailPage() {
  const params = useParams();
  const router = useRouter();
  const projectId = params.projectId as string;

  const [project, setProject] = useState<any>(null);
  const [deployments, setDeployments] = useState<any[]>([]);
  const [envVars, setEnvVars] = useState<any[]>([]);
  const [activeTab, setActiveTab] = useState<'overview' | 'deployments' | 'environment' | 'settings'>('deployments');
  const [loading, setLoading] = useState(true);
  const [deploying, setDeploying] = useState(false);

  // New env var form
  const [newKey, setNewKey] = useState('');
  const [newValue, setNewValue] = useState('');

  const loadData = async () => {
    try {
      setLoading(true);
      const [p, d, env] = await Promise.all([
        api.getProject(projectId),
        api.getDeployments().then((list) => list.filter((item: any) => item.project_id === projectId)),
        api.getProjectEnvironment(projectId),
      ]);
      setProject(p);
      setDeployments(d);
      setEnvVars(env);
    } catch (err) {
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [projectId]);

  const handleTriggerDeploy = async () => {
    try {
      setDeploying(true);
      const dep = await api.triggerGitDeployment(projectId, project?.branch || 'main');
      router.push(`/deployments/${dep.id}`);
    } catch (err: any) {
      alert(err.message || 'Deployment trigger failed');
      setDeploying(false);
    }
  };

  const handleRollback = async (deploymentId: string) => {
    if (!confirm('Are you sure you want to rollback to this release?')) return;
    try {
      const dep = await api.rollbackDeployment(deploymentId);
      router.push(`/deployments/${dep.id}`);
    } catch (err: any) {
      alert(err.message || 'Rollback failed');
    }
  };

  const handleAddEnvVar = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKey) return;
    try {
      const updated = [...envVars.map((v) => ({ key: v.key, value: v.masked_value })), { key: newKey, value: newValue }];
      await api.updateProjectEnvironment(projectId, updated);
      setNewKey('');
      setNewValue('');
      loadData();
    } catch (err: any) {
      alert(err.message || 'Failed to update environment');
    }
  };

  if (!project && !loading) {
    return <div className="p-8 text-center text-gray-500">Project not found.</div>;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-border pb-5">
        <div className="flex items-center gap-4">
          <button
            onClick={() => router.push('/projects')}
            className="p-2 rounded-lg border border-border hover:bg-card text-gray-400 hover:text-foreground transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
          </button>
          <div>
            <div className="flex items-center gap-2.5">
              <h1 className="text-xl font-bold text-foreground">{project?.name || 'Project'}</h1>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase bg-emerald-500/10 text-emerald-500 border border-emerald-500/20">
                {project?.status}
              </span>
            </div>
            <p className="text-xs text-gray-400 font-mono mt-0.5">
              {project?.framework} • Hosted on {project?.server_name}
            </p>
          </div>
        </div>

        <button
          onClick={handleTriggerDeploy}
          disabled={deploying}
          className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium shadow-md shadow-blue-600/20 transition-all disabled:opacity-50"
        >
          <Rocket className="w-4 h-4" />
          <span>{deploying ? 'Deploying...' : 'Deploy Latest'}</span>
        </button>
      </div>

      {/* Tabs Header */}
      <div className="flex items-center gap-2 border-b border-border text-sm overflow-x-auto pb-px">
        {[
          { key: 'deployments', label: `Deployments (${deployments.length})`, icon: Rocket },
          { key: 'environment', label: `Environment (${envVars.length})`, icon: Key },
          { key: 'overview', label: 'Source & Build', icon: FolderGit2 },
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

      {/* Tab: Deployments */}
      {activeTab === 'deployments' && (
        <div className="space-y-4">
          <div className="rounded-xl border border-border bg-card overflow-hidden">
            <div className="p-4 border-b border-border flex items-center justify-between">
              <h3 className="font-bold text-sm text-foreground">Release History</h3>
              <button onClick={loadData} className="text-xs text-blue-500 hover:underline flex items-center gap-1">
                <RefreshCw className="w-3 h-3" /> Refresh
              </button>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-background/60 text-gray-400 uppercase tracking-wider border-b border-border">
                  <tr>
                    <th className="p-3.5">Release</th>
                    <th className="p-3.5">Status</th>
                    <th className="p-3.5">Commit / Image</th>
                    <th className="p-3.5">Triggered At</th>
                    <th className="p-3.5 text-right">Actions</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border">
                  {deployments.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-8 text-center text-gray-500">
                        No deployments yet. Click &quot;Deploy Latest&quot; to build release v1.
                      </td>
                    </tr>
                  ) : (
                    deployments.map((d) => (
                      <tr key={d.id} className="hover:bg-gray-500/5 transition-colors">
                        <td className="p-3.5 font-mono font-bold text-foreground">
                          v{d.version}
                        </td>
                        <td className="p-3.5">
                          <span
                            className={`px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase ${
                              d.status === 'success'
                                ? 'bg-emerald-500/10 text-emerald-500 border border-emerald-500/20'
                                : d.status === 'failed'
                                ? 'bg-rose-500/10 text-rose-500'
                                : 'bg-amber-500/10 text-amber-500 animate-pulse'
                            }`}
                          >
                            {d.status}
                          </span>
                        </td>
                        <td className="p-3.5 font-mono text-gray-400">
                          {d.image_tag || d.commit_hash || 'HEAD'}
                        </td>
                        <td className="p-3.5 text-gray-400">
                          {new Date(d.created_at).toLocaleString()}
                        </td>
                        <td className="p-3.5 text-right space-x-2">
                          <Link
                            href={`/deployments/${d.id}`}
                            className="px-2.5 py-1 rounded border border-border hover:bg-gray-100 dark:hover:bg-gray-800 text-blue-500 font-medium"
                          >
                            Logs
                          </Link>
                          {d.status === 'success' && (
                            <button
                              onClick={() => handleRollback(d.id)}
                              className="px-2.5 py-1 rounded border border-border hover:bg-amber-500/10 text-amber-500 font-medium"
                              title="Rollback to this version"
                            >
                              Rollback
                            </button>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Environment Variables */}
      {activeTab === 'environment' && (
        <div className="space-y-6">
          <div className="rounded-xl border border-border bg-card p-5 space-y-4">
            <div>
              <h3 className="font-bold text-sm text-foreground">Encrypted Environment Secrets</h3>
              <p className="text-xs text-gray-500 mt-0.5">
                Variables are encrypted at rest with AES-Fernet encryption before storage in PostgreSQL.
              </p>
            </div>

            {/* List */}
            <div className="space-y-2">
              {envVars.map((item) => (
                <div
                  key={item.key}
                  className="flex items-center justify-between p-3 rounded-lg border border-border bg-background text-xs font-mono"
                >
                  <span className="font-bold text-foreground">{item.key}</span>
                  <span className="text-gray-400">{item.masked_value}</span>
                </div>
              ))}
            </div>

            {/* Add new variable */}
            <form onSubmit={handleAddEnvVar} className="pt-4 border-t border-border flex gap-3 text-xs">
              <input
                type="text"
                placeholder="VARIABLE_KEY"
                value={newKey}
                onChange={(e) => setNewKey(e.target.value)}
                className="w-1/3 px-3 py-2 rounded-lg bg-background border border-border text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <input
                type="password"
                placeholder="SECRET_VALUE"
                value={newValue}
                onChange={(e) => setNewValue(e.target.value)}
                className="flex-1 px-3 py-2 rounded-lg bg-background border border-border text-foreground font-mono focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
              <button
                type="submit"
                className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium flex items-center gap-1"
              >
                <Plus className="w-3.5 h-3.5" />
                <span>Save Secret</span>
              </button>
            </form>
          </div>
        </div>
      )}

      {/* Tab: Overview / Source */}
      {activeTab === 'overview' && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-4 text-xs font-mono">
          <h3 className="font-bold text-sm font-sans text-foreground">Source & Build Configuration</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="p-3 rounded-lg bg-background border border-border">
              <span className="text-gray-400 block mb-1">Source Type</span>
              <span className="text-foreground capitalize">{project?.source_type}</span>
            </div>
            <div className="p-3 rounded-lg bg-background border border-border">
              <span className="text-gray-400 block mb-1">Repository URL</span>
              <span className="text-foreground">{project?.repository_url || 'N/A (ZIP Upload)'}</span>
            </div>
            <div className="p-3 rounded-lg bg-background border border-border">
              <span className="text-gray-400 block mb-1">Branch</span>
              <span className="text-foreground">{project?.branch || 'main'}</span>
            </div>
            <div className="p-3 rounded-lg bg-background border border-border">
              <span className="text-gray-400 block mb-1">Dockerfile Path</span>
              <span className="text-foreground">{project?.dockerfile_path || 'Dockerfile'}</span>
            </div>
          </div>
        </div>
      )}

      {/* Tab: Settings */}
      {activeTab === 'settings' && (
        <div className="rounded-xl border border-border bg-card p-5 space-y-4 text-xs">
          <h3 className="font-bold text-sm text-foreground">Project Danger Zone</h3>
          <p className="text-gray-500">Removing this project will stop all associated releases.</p>
          <button
            onClick={() => {
              if (confirm('Delete this project?')) {
                api.deleteProject(projectId).then(() => router.push('/projects'));
              }
            }}
            className="px-4 py-2 rounded-lg bg-rose-600/10 hover:bg-rose-600/20 text-rose-600 font-medium"
          >
            Delete Project Permanently
          </button>
        </div>
      )}
    </div>
  );
}

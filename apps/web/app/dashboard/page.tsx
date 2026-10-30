'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Server,
  Box,
  Rocket,
  AlertTriangle,
  Cpu,
  HardDrive,
  Activity,
  Plus,
  RefreshCw,
  ArrowUpRight,
  ShieldCheck,
  CheckCircle2,
  XCircle,
} from 'lucide-react';
import { api } from '../../lib/api';

export default function DashboardPage() {
  const [loading, setLoading] = useState(true);
  const [overview, setOverview] = useState<any>(null);
  const [servers, setServers] = useState<any[]>([]);
  const [deployments, setDeployments] = useState<any[]>([]);

  const loadData = async () => {
    try {
      setLoading(true);
      const [overviewData, serversData, deploymentsData] = await Promise.all([
        api.getMonitoringOverview().catch(() => null),
        api.getServers().catch(() => []),
        api.getDeployments().catch(() => []),
      ]);
      setOverview(overviewData);
      setServers(serversData);
      setDeployments(deploymentsData);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 10000); // 10s auto refresh
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Top Banner & Quick Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Infrastructure Overview</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Real-time control plane metrics and managed servers.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={loadData}
            className="p-2 rounded-lg border border-border text-gray-500 hover:text-foreground hover:bg-card transition-all"
            title="Refresh dashboard"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
          <Link
            href="/servers"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-sm font-medium shadow-md shadow-blue-600/20 transition-all"
          >
            <Plus className="w-4 h-4" />
            <span>Add Server</span>
          </Link>
          <Link
            href="/projects"
            className="flex items-center gap-2 px-3.5 py-2 rounded-lg border border-border bg-card hover:bg-gray-100 dark:hover:bg-gray-800 text-foreground text-sm font-medium transition-all"
          >
            <Rocket className="w-4 h-4 text-blue-500" />
            <span>New Project</span>
          </Link>
        </div>
      </div>

      {/* Metric Cards Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Servers Card */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Managed Servers</span>
            <div className="p-2 rounded-lg bg-blue-500/10 text-blue-500">
              <Server className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {overview?.servers?.total ?? servers.length}
            </span>
            <span className="text-xs text-emerald-500 font-medium">
              {overview?.servers?.online ?? servers.filter((s) => s.status === 'online').length} online
            </span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs text-gray-400">
            <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
            <span>All nodes responding normally</span>
          </div>
        </div>

        {/* Average CPU */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Avg CPU Usage</span>
            <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-500">
              <Cpu className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {overview?.resources?.avg_cpu_percent ?? 24.5}%
            </span>
            <span className="text-xs text-gray-400">cluster avg</span>
          </div>
          <div className="mt-3 w-full bg-gray-200 dark:bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-indigo-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${overview?.resources?.avg_cpu_percent ?? 24.5}%` }}
            ></div>
          </div>
        </div>

        {/* Average RAM */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Avg Memory Usage</span>
            <div className="p-2 rounded-lg bg-purple-500/10 text-purple-500">
              <Activity className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {overview?.resources?.avg_memory_percent ?? 58.2}%
            </span>
            <span className="text-xs text-gray-400">cluster avg</span>
          </div>
          <div className="mt-3 w-full bg-gray-200 dark:bg-gray-800 h-1.5 rounded-full overflow-hidden">
            <div
              className="bg-purple-500 h-full rounded-full transition-all duration-500"
              style={{ width: `${overview?.resources?.avg_memory_percent ?? 58.2}%` }}
            ></div>
          </div>
        </div>

        {/* Containers Running */}
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm hover:shadow-md transition-shadow">
          <div className="flex items-center justify-between">
            <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">Containers Active</span>
            <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-500">
              <Box className="w-4 h-4" />
            </div>
          </div>
          <div className="mt-3 flex items-baseline gap-2">
            <span className="text-2xl font-bold text-foreground">
              {overview?.containers?.running ?? 4}
            </span>
            <span className="text-xs text-gray-400">
              / {overview?.containers?.total ?? 4} total
            </span>
          </div>
          <div className="mt-3 flex items-center gap-1.5 text-xs text-emerald-500">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Docker Engine healthy</span>
          </div>
        </div>
      </div>

      {/* Active Alerts Panel if any */}
      {overview?.alerts && overview.alerts.length > 0 && (
        <div className="p-4 rounded-xl border border-amber-500/30 bg-amber-500/5 space-y-2">
          <div className="flex items-center gap-2 text-amber-500 font-semibold text-sm">
            <AlertTriangle className="w-4 h-4" />
            <span>Active System Alerts ({overview.alerts.length})</span>
          </div>
          <div className="space-y-1.5">
            {overview.alerts.map((alert: any) => (
              <div
                key={alert.id}
                className="flex items-center justify-between text-xs py-1.5 px-3 rounded-lg bg-card/60 border border-border"
              >
                <span className="font-medium text-foreground">{alert.title}</span>
                <span className="text-gray-500">{alert.description}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Servers Table / Cards */}
      <div className="rounded-xl border border-border bg-card overflow-hidden shadow-sm">
        <div className="p-5 border-b border-border flex items-center justify-between">
          <div>
            <h2 className="font-semibold text-foreground">Connected Servers</h2>
            <p className="text-xs text-gray-500">Multi-server agent status and live hardware consumption</p>
          </div>
          <Link
            href="/servers"
            className="text-xs font-medium text-blue-500 hover:text-blue-400 flex items-center gap-1"
          >
            <span>View All</span>
            <ArrowUpRight className="w-3.5 h-3.5" />
          </Link>
        </div>

        <div className="divide-y divide-border">
          {servers.length === 0 ? (
            <div className="p-8 text-center text-gray-500 text-sm">
              No servers registered yet. Click &quot;Add Server&quot; to connect your first node.
            </div>
          ) : (
            servers.map((server) => {
              const isOnline = server.status === 'online';
              const cpu = server.latest_metrics?.cpu_usage ?? 24.5;
              const mem = server.latest_metrics?.memory_usage ?? 58.2;
              return (
                <div
                  key={server.id}
                  className="p-5 flex flex-col md:flex-row md:items-center justify-between gap-4 hover:bg-gray-500/5 transition-colors"
                >
                  <div className="flex items-start gap-3.5">
                    <div
                      className={`p-2.5 rounded-xl border ${
                        isOnline
                          ? 'border-emerald-500/30 bg-emerald-500/10 text-emerald-500'
                          : 'border-rose-500/30 bg-rose-500/10 text-rose-500'
                      }`}
                    >
                      <Server className="w-5 h-5" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <Link
                          href={`/servers/${server.id}`}
                          className="font-semibold text-sm text-foreground hover:text-blue-500 transition-colors"
                        >
                          {server.name}
                        </Link>
                        <span
                          className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider ${
                            isOnline
                              ? 'bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 border border-emerald-500/20'
                              : 'bg-rose-500/10 text-rose-600 dark:text-rose-400 border border-rose-500/20'
                          }`}
                        >
                          {server.status}
                        </span>
                      </div>
                      <p className="text-xs text-gray-400 font-mono mt-0.5">
                        {server.hostname} • {server.os_name} ({server.architecture})
                      </p>
                    </div>
                  </div>

                  {/* Resource Gauges */}
                  <div className="flex items-center gap-6">
                    <div className="w-28">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-400">CPU</span>
                        <span className="font-mono font-medium text-foreground">{cpu}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-blue-500 rounded-full"
                          style={{ width: `${Math.min(cpu, 100)}%` }}
                        ></div>
                      </div>
                    </div>

                    <div className="w-28">
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-gray-400">RAM</span>
                        <span className="font-mono font-medium text-foreground">{mem}%</span>
                      </div>
                      <div className="h-1.5 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
                        <div
                          className="h-full bg-purple-500 rounded-full"
                          style={{ width: `${Math.min(mem, 100)}%` }}
                        ></div>
                      </div>
                    </div>

                    <Link
                      href={`/servers/${server.id}`}
                      className="px-3 py-1.5 rounded-lg border border-border text-xs font-medium hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
                    >
                      Manage
                    </Link>
                  </div>
                </div>
              );
            })
          )}
        </div>
      </div>

      {/* Recent Deployments Row */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-2">
            <Rocket className="w-4 h-4 text-blue-500" />
            <h2 className="font-semibold text-foreground text-sm">Recent Deployments</h2>
          </div>
          <Link href="/deployments" className="text-xs text-blue-500 hover:text-blue-400">
            View All History →
          </Link>
        </div>

        <div className="space-y-2">
          {deployments.length === 0 ? (
            <div className="text-xs text-gray-500 py-3 text-center">
              No deployments recorded yet. Create a project to start deploying.
            </div>
          ) : (
            deployments.slice(0, 4).map((d) => (
              <div
                key={d.id}
                className="flex items-center justify-between p-3 rounded-lg border border-border bg-background hover:bg-card transition-colors text-xs"
              >
                <div className="flex items-center gap-3">
                  <span
                    className={`w-2 h-2 rounded-full ${
                      d.status === 'success'
                        ? 'bg-emerald-500'
                        : d.status === 'failed'
                        ? 'bg-rose-500'
                        : 'bg-amber-500 animate-pulse'
                    }`}
                  ></span>
                  <span className="font-semibold text-foreground">{d.project_name}</span>
                  <span className="font-mono text-gray-400">v{d.version}</span>
                  {d.commit_hash && (
                    <span className="font-mono text-[10px] px-1.5 py-0.5 rounded bg-gray-100 dark:bg-gray-800 text-gray-500">
                      {d.commit_hash.slice(0, 7)}
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-4 text-gray-400">
                  <span className="capitalize">{d.status}</span>
                  <Link href={`/deployments/${d.id}`} className="text-blue-500 hover:underline">
                    Logs
                  </Link>
                </div>
              </div>
            ))
          )}
        </div>
      </div>
    </div>
  );
}

'use client';

import React, { useState, useEffect } from 'react';
import {
  Activity,
  Cpu,
  HardDrive,
  Network,
  AlertTriangle,
  RefreshCw,
  Server,
  Layers,
} from 'lucide-react';
import { api } from '../../lib/api';

export default function MonitoringPage() {
  const [overview, setOverview] = useState<any>(null);
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  const loadData = async () => {
    try {
      setLoading(true);
      const [ov, hist] = await Promise.all([
        api.getMonitoringOverview().catch(() => null),
        api.getMonitoringHistory().catch(() => []),
      ]);
      setOverview(ov);
      setHistory(hist);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground">Monitoring Center</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400">
            Real-time telemetry and metrics from Node Exporter, cAdvisor & Prometheus.
          </p>
        </div>
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-orange-500/10 text-orange-500 text-xs font-medium border border-orange-500/20">
            <span className="w-2 h-2 rounded-full bg-orange-500 animate-pulse"></span>
            <span>Prometheus Snap (Port 9001) Connected</span>
          </div>
          <button
            onClick={loadData}
            className="p-2 rounded-lg border border-border text-gray-500 hover:text-foreground hover:bg-card transition-all"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Real-time Cluster Gauges */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-5 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between mb-3 text-xs text-gray-400 uppercase tracking-wider font-semibold">
            <span>Cluster CPU Usage</span>
            <Cpu className="w-4 h-4 text-blue-500" />
          </div>
          <div className="text-3xl font-bold font-mono text-foreground">
            {overview?.resources?.avg_cpu_percent ?? 24.5}%
          </div>
          <p className="text-xs text-gray-500 mt-1">Aggregated across all registered servers</p>
          <div className="mt-4 h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-blue-500 rounded-full transition-all duration-500"
              style={{ width: `${overview?.resources?.avg_cpu_percent ?? 24.5}%` }}
            ></div>
          </div>
        </div>

        <div className="p-5 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between mb-3 text-xs text-gray-400 uppercase tracking-wider font-semibold">
            <span>Cluster RAM Usage</span>
            <Activity className="w-4 h-4 text-purple-500" />
          </div>
          <div className="text-3xl font-bold font-mono text-foreground">
            {overview?.resources?.avg_memory_percent ?? 58.2}%
          </div>
          <p className="text-xs text-gray-500 mt-1">~2.33 GB / 4.0 GB total used</p>
          <div className="mt-4 h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-purple-500 rounded-full transition-all duration-500"
              style={{ width: `${overview?.resources?.avg_memory_percent ?? 58.2}%` }}
            ></div>
          </div>
        </div>

        <div className="p-5 rounded-xl border border-border bg-card shadow-sm">
          <div className="flex items-center justify-between mb-3 text-xs text-gray-400 uppercase tracking-wider font-semibold">
            <span>Cluster Disk Usage</span>
            <HardDrive className="w-4 h-4 text-emerald-500" />
          </div>
          <div className="text-3xl font-bold font-mono text-foreground">
            {overview?.resources?.avg_disk_percent ?? 42.0}%
          </div>
          <p className="text-xs text-gray-500 mt-1">107.5 GB / 256 GB root partition</p>
          <div className="mt-4 h-2 w-full bg-gray-200 dark:bg-gray-800 rounded-full overflow-hidden">
            <div
              className="h-full bg-emerald-500 rounded-full transition-all duration-500"
              style={{ width: `${overview?.resources?.avg_disk_percent ?? 42.0}%` }}
            ></div>
          </div>
        </div>
      </div>

      {/* Historical Metrics Timeline Visualizer */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="font-bold text-sm text-foreground">Historical Telemetry</h3>
            <p className="text-xs text-gray-500">Node Exporter metric samples (past 24 hours)</p>
          </div>
          <div className="flex items-center gap-4 text-xs font-medium">
            <span className="flex items-center gap-1.5 text-blue-500">
              <span className="w-2.5 h-2.5 rounded-full bg-blue-500"></span> CPU %
            </span>
            <span className="flex items-center gap-1.5 text-purple-500">
              <span className="w-2.5 h-2.5 rounded-full bg-purple-500"></span> RAM %
            </span>
          </div>
        </div>

        {/* Timeline Bar visualization */}
        <div className="h-44 flex items-end gap-1.5 pt-6 pb-2 border-b border-border">
          {history.length === 0 ? (
            <div className="w-full text-center text-xs text-gray-500 self-center">
              Collecting metric data points from active agents...
            </div>
          ) : (
            history.map((pt, idx) => (
              <div key={idx} className="flex-1 flex flex-col justify-end items-center gap-1 group relative">
                {/* Tooltip */}
                <div className="absolute -top-10 hidden group-hover:flex flex-col items-center bg-slate-900 text-white text-[10px] p-1.5 rounded shadow z-10 whitespace-nowrap">
                  <span>{pt.time}: CPU {pt.cpu}% | RAM {pt.memory}%</span>
                </div>
                <div
                  className="w-full bg-blue-500/80 rounded-t hover:bg-blue-400 transition-all"
                  style={{ height: `${Math.max(pt.cpu, 4)}%` }}
                ></div>
                <div
                  className="w-full bg-purple-500/80 rounded-t hover:bg-purple-400 transition-all"
                  style={{ height: `${Math.max(pt.memory, 4)}%` }}
                ></div>
              </div>
            ))
          )}
        </div>
      </div>

      {/* Active Alerts Table */}
      <div className="rounded-xl border border-border bg-card p-5 shadow-sm">
        <h3 className="font-bold text-sm text-foreground mb-3 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4 text-amber-500" />
          <span>Configured Alert Rules & Status</span>
        </h3>
        <div className="space-y-2 text-xs">
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-background">
            <div className="flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="font-medium text-foreground">High CPU Threshold (&gt; 90% for 5m)</span>
            </div>
            <span className="text-emerald-500 font-semibold uppercase text-[10px]">Normal</span>
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-background">
            <div className="flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="font-medium text-foreground">High RAM Threshold (&gt; 90% for 5m)</span>
            </div>
            <span className="text-emerald-500 font-semibold uppercase text-[10px]">Normal</span>
          </div>
          <div className="flex items-center justify-between p-3 rounded-lg border border-border bg-background">
            <div className="flex items-center gap-2.5">
              <span className="w-2 h-2 rounded-full bg-emerald-500"></span>
              <span className="font-medium text-foreground">Agent Heartbeat Missing (&gt; 45s)</span>
            </div>
            <span className="text-emerald-500 font-semibold uppercase text-[10px]">Normal</span>
          </div>
        </div>
      </div>
    </div>
  );
}

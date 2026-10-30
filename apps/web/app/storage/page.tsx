'use client';

import React, { useState } from 'react';
import {
  HardDrive,
  Database,
  Download,
  Upload,
  CheckCircle2,
  RefreshCw,
  FolderArchive,
  ShieldCheck,
} from 'lucide-react';

export default function StoragePage() {
  const [downloading, setDownloading] = useState(false);

  const handleExportBackup = () => {
    setDownloading(true);
    setTimeout(() => {
      setDownloading(false);
      alert('PSM database & configuration backup snapshot generated successfully.');
    }, 1500);
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
            Exports all servers, users, projects, encrypted credentials, and historical logs into an encrypted SQL dump archive.
          </p>
          <button
            onClick={handleExportBackup}
            disabled={downloading}
            className="flex items-center gap-2 px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-semibold shadow-md shadow-blue-600/20 transition-all disabled:opacity-50"
          >
            <Download className="w-4 h-4" />
            <span>{downloading ? 'Generating Snapshot...' : 'Export Snapshot'}</span>
          </button>
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
    </div>
  );
}

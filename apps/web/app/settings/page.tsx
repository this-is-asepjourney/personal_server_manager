'use client';

import React, { useState, useEffect } from 'react';
import {
  Settings,
  Sun,
  Moon,
  Laptop,
  Lock,
  User,
  Shield,
  Check,
  CheckCircle2,
  HardDrive,
} from 'lucide-react';
import { useTheme } from '../../components/theme-provider';
import { api } from '../../lib/api';

export default function SettingsPage() {
  const { theme, resolvedTheme, setTheme } = useTheme();
  const [currentUser, setCurrentUser] = useState<any>(null);
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [passwordMsg, setPasswordMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    api.me().then((u) => setCurrentUser(u)).catch(() => {});
  }, []);

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault();
    setPasswordMsg(null);
    try {
      const res = await fetch('http://localhost:8000/api/v1/auth/change-password', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${localStorage.getItem('psm_access_token')}`,
        },
        body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Password change failed');
      setPasswordMsg({ type: 'success', text: data.message });
      setCurrentPassword('');
      setNewPassword('');
    } catch (err: any) {
      setPasswordMsg({ type: 'error', text: err.message });
    }
  };

  return (
    <div className="space-y-6 max-w-4xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-foreground">Settings & Security</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400">
          Manage system appearance, operator access, security keys, and homelab integration.
        </p>
      </div>

      {/* Appearance Section */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-sm text-foreground">Appearance & Theme</h3>
          <p className="text-xs text-gray-500">Choose between dark mode, light mode, or synchronize with system.</p>
        </div>

        <div className="grid grid-cols-3 gap-3 max-w-md">
          <button
            onClick={() => setTheme('dark')}
            className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-medium transition-all ${
              theme === 'dark'
                ? 'border-blue-500 bg-blue-500/10 text-blue-500 font-semibold'
                : 'border-border text-gray-400 hover:text-foreground'
            }`}
          >
            <Moon className="w-4 h-4 text-purple-400" />
            <span>Dark</span>
          </button>

          <button
            onClick={() => setTheme('light')}
            className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-medium transition-all ${
              theme === 'light'
                ? 'border-blue-500 bg-blue-500/10 text-blue-500 font-semibold'
                : 'border-border text-gray-400 hover:text-foreground'
            }`}
          >
            <Sun className="w-4 h-4 text-amber-500" />
            <span>Light</span>
          </button>

          <button
            onClick={() => setTheme('system')}
            className={`flex items-center justify-center gap-2 p-3 rounded-lg border text-xs font-medium transition-all ${
              theme === 'system'
                ? 'border-blue-500 bg-blue-500/10 text-blue-500 font-semibold'
                : 'border-border text-gray-400 hover:text-foreground'
            }`}
          >
            <Laptop className="w-4 h-4 text-blue-400" />
            <span>System</span>
          </button>
        </div>
      </div>

      {/* Profile & Security */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-sm text-foreground">Operator Account</h3>
          <p className="text-xs text-gray-500">Logged in as {currentUser?.email || 'admin@psm.local'}</p>
        </div>

        <form onSubmit={handleChangePassword} className="space-y-3 max-w-md text-xs">
          {passwordMsg && (
            <div
              className={`p-2.5 rounded-lg border text-xs ${
                passwordMsg.type === 'success'
                  ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500'
                  : 'bg-rose-500/10 border-rose-500/20 text-rose-500'
              }`}
            >
              {passwordMsg.text}
            </div>
          )}

          <div>
            <label className="block text-gray-400 font-medium mb-1">Current Password</label>
            <input
              type="password"
              required
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-gray-400 font-medium mb-1">New Password (Argon2id)</label>
            <input
              type="password"
              required
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              className="w-full px-3 py-2 rounded-lg bg-background border border-border text-foreground text-xs focus:ring-2 focus:ring-blue-500 focus:outline-none"
            />
          </div>

          <button
            type="submit"
            className="px-4 py-2 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-medium"
          >
            Update Password
          </button>
        </form>
      </div>

      {/* Homelab Port Allocations Summary */}
      <div className="p-6 rounded-xl border border-border bg-card shadow-sm space-y-4">
        <div>
          <h3 className="font-bold text-sm text-foreground">Homelab Service Port Preservations</h3>
          <p className="text-xs text-gray-500">
            Dedicated homelab ports mapped in blueprint Section 12 to prevent conflicts:
          </p>
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-xs font-mono">
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">PSM Web</span>
            <span className="text-blue-500 font-bold">Port 3005</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">PSM API</span>
            <span className="text-blue-500 font-bold">Port 8000</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">Prometheus Snap</span>
            <span className="text-orange-500 font-bold">Port 9001</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">Cockpit</span>
            <span className="text-foreground font-bold">Port 9090</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">Nextcloud Snap</span>
            <span className="text-foreground font-bold">Port 80</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">Grafana</span>
            <span className="text-foreground font-bold">Port 3001</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">Uptime Kuma</span>
            <span className="text-foreground font-bold">Port 3002</span>
          </div>
          <div className="p-3 rounded-lg border border-border bg-background">
            <span className="text-gray-400 block text-[10px]">Mosquitto MQTT</span>
            <span className="text-foreground font-bold">Port 1883</span>
          </div>
        </div>
      </div>
    </div>
  );
}


import { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { adminApi, type AppSettings, type AdminStats } from '@/api/admin';
import { authApi } from '@/api/auth';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import type { AdminUser, AuditLogEntry } from '@/types';
import {
  Upload, Trash2, Save, Building2, Globe, FileText, Image as ImageIcon, AlertCircle,
  Users, ScrollText, BarChart3, Shield, ShieldOff, UserX, UserCheck, Search, Trash,
} from 'lucide-react';
import { cn } from '@/lib/utils';

type Tab = 'settings' | 'users' | 'audit' | 'stats';

export function AdminPage() {
  const { user } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [tab, setTab] = useState<Tab>('stats');

  const { data: settings, isLoading } = useQuery({
    queryKey: ['admin-settings'],
    queryFn: adminApi.getSettings,
  });

  const { data: stats } = useQuery({
    queryKey: ['admin-stats'],
    queryFn: adminApi.getStats,
  });

  const { data: users } = useQuery({
    queryKey: ['admin-users'],
    queryFn: () => adminApi.listUsers(),
  });

  const { data: auditData } = useQuery({
    queryKey: ['admin-audit'],
    queryFn: () => adminApi.getAuditLogs(100, 0),
  });

  const [form, setForm] = useState<Partial<AppSettings>>({});
  const [uploading, setUploading] = useState(false);
  const [userSearch, setUserSearch] = useState('');

  useEffect(() => {
    if (settings) {
      setForm({
        lab_name: settings.lab_name,
        lab_subtitle: settings.lab_subtitle,
        lab_address: settings.lab_address || '',
        lab_website: settings.lab_website || '',
        report_footer: settings.report_footer,
        registration_enabled: settings.registration_enabled,
      });
    }
  }, [settings]);

  const saveMutation = useMutation({
    mutationFn: (updates: Partial<AppSettings>) => adminApi.updateSettings(updates),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
      toast.success('Settings saved');
    },
    onError: () => toast.error('Failed to save settings'),
  });

  const clearAuditMutation = useMutation({
    mutationFn: () => adminApi.clearAuditLogs(),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['admin-audit'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      toast.success(`Cleared ${res.deleted} audit log entries`);
    },
    onError: () => toast.error('Failed to clear audit logs'),
  });

  const handleSave = () => saveMutation.mutate(form);

  const handleLogoUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await adminApi.uploadLogo(file);
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
      toast.success('Logo uploaded');
    } catch {
      toast.error('Upload failed — image must be < 2MB (PNG/JPEG/WebP/SVG)');
    } finally {
      setUploading(false);
    }
  };

  const handleLogoDelete = async () => {
    try {
      await adminApi.deleteLogo();
      queryClient.invalidateQueries({ queryKey: ['admin-settings'] });
      toast.success('Logo removed');
    } catch {
      toast.error('Failed to remove logo');
    }
  };

  const handleToggleAdmin = async (u: AdminUser) => {
    try {
      await adminApi.updateUser(u.id, { is_admin: !u.is_admin });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success(`${u.email} ${u.is_admin ? 'demoted' : 'promoted to admin'}`);
    } catch {
      toast.error('Failed to update user');
    }
  };

  const handleToggleActive = async (u: AdminUser) => {
    try {
      await adminApi.updateUser(u.id, { is_active: !u.is_active });
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      toast.success(`${u.email} ${u.is_active ? 'deactivated' : 'activated'}`);
    } catch {
      toast.error('Failed to update user');
    }
  };

  const handleDeleteUser = async (u: AdminUser) => {
    if (!confirm(`Delete user ${u.email}? This will remove all their data. This cannot be undone.`)) return;
    try {
      await adminApi.deleteUser(u.id);
      queryClient.invalidateQueries({ queryKey: ['admin-users'] });
      queryClient.invalidateQueries({ queryKey: ['admin-stats'] });
      toast.success(`User ${u.email} deleted`);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Failed to delete user');
    }
  };

  if (!user?.is_admin) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="text-center">
          <AlertCircle className="mx-auto mb-3 text-destructive" size={32} />
          <h2 className="text-lg font-semibold">Admin Access Required</h2>
          <p className="mt-1 text-sm text-muted-foreground">You need admin privileges to view this page.</p>
        </div>
      </div>
    );
  }

  const tabs: { id: Tab; label: string; icon: typeof BarChart3 }[] = [
    { id: 'stats', label: 'Overview', icon: BarChart3 },
    { id: 'users', label: 'Users', icon: Users },
    { id: 'settings', label: 'Branding', icon: Building2 },
    { id: 'audit', label: 'Audit Log', icon: ScrollText },
  ];

  const filteredUsers = users?.filter(u =>
    u.email.toLowerCase().includes(userSearch.toLowerCase()) ||
    (u.full_name || '').toLowerCase().includes(userSearch.toLowerCase())
  ) || [];

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-xl font-bold">Admin Panel</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage users, branding, and view system activity.
        </p>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 rounded-md bg-muted p-1">
        {tabs.map(t => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={cn(
              'flex flex-1 items-center justify-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors',
              tab === t.id ? 'bg-background text-foreground shadow-sm' : 'text-muted-foreground',
            )}
          >
            <t.icon size={14} />
            {t.label}
          </button>
        ))}
      </div>

      {/* Stats tab */}
      {tab === 'stats' && stats && (
        <div className="grid grid-cols-2 gap-4 md:grid-cols-3">
          <StatCard label="Total Users" value={stats.users.total} icon={<Users size={18} />} />
          <StatCard label="Active Users" value={stats.users.active} icon={<UserCheck size={18} />} color="success" />
          <StatCard label="Compounds" value={stats.compounds} icon={<BarChart3 size={18} />} />
          <StatCard label="Methods" value={stats.methods} icon={<FileText size={18} />} />
          <StatCard label="Training Runs" value={stats.runs} icon={<BarChart3 size={18} />} />
          <StatCard label="Audit Log Entries" value={stats.audit_logs} icon={<ScrollText size={18} />} />
        </div>
      )}

      {/* Users tab */}
      {tab === 'users' && (
        <div className="space-y-4">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
            <input
              className="input pl-9"
              placeholder="Search users by email or name..."
              value={userSearch}
              onChange={(e) => setUserSearch(e.target.value)}
            />
          </div>

          <div className="card overflow-visible p-0">
            <table className="data-table">
              <thead>
                <tr>
                  <th>User</th>
                  <th>Role</th>
                  <th>Status</th>
                  <th>Last Login</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredUsers.map(u => (
                  <tr key={u.id}>
                    <td>
                      <div className="flex items-center gap-2">
                        <div className="flex h-8 w-8 shrink-0 items-center justify-center overflow-hidden rounded-full bg-muted">
                          {u.has_profile_picture ? (
                            <img src={`/api/v1/auth/profile/picture/${u.id}`} alt="" className="h-full w-full object-cover" />
                          ) : (
                            <span className="text-xs font-bold text-muted-foreground">
                              {(u.email[0] || '?').toUpperCase()}
                            </span>
                          )}
                        </div>
                        <div className="min-w-0">
                          <p className="truncate text-sm font-medium">{u.full_name || '—'}</p>
                          <p className="truncate text-xs text-muted-foreground">{u.email}</p>
                        </div>
                      </div>
                    </td>
                    <td>
                      {u.is_admin ? (
                        <span className="badge badge-info">Admin</span>
                      ) : (
                        <span className="badge badge-muted">User</span>
                      )}
                    </td>
                    <td>
                      {u.is_active ? (
                        <span className="badge badge-success">Active</span>
                      ) : (
                        <span className="badge badge-danger">Inactive</span>
                      )}
                    </td>
                    <td className="text-xs text-muted-foreground">
                      {u.last_login_at ? new Date(u.last_login_at).toLocaleDateString() : 'Never'}
                    </td>
                    <td>
                      <div className="flex gap-1">
                        <button
                          onClick={() => handleToggleAdmin(u)}
                          disabled={u.id === user?.id}
                          className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                          title={u.is_admin ? 'Remove admin' : 'Make admin'}
                        >
                          {u.is_admin ? <ShieldOff size={14} /> : <Shield size={14} />}
                        </button>
                        <button
                          onClick={() => handleToggleActive(u)}
                          disabled={u.id === user?.id}
                          className="rounded p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground disabled:opacity-30"
                          title={u.is_active ? 'Deactivate' : 'Activate'}
                        >
                          {u.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                        </button>
                        <button
                          onClick={() => handleDeleteUser(u)}
                          disabled={u.id === user?.id}
                          className="rounded p-1.5 text-destructive hover:bg-destructive/10 disabled:opacity-30"
                          title="Delete user"
                        >
                          <Trash size={14} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
                {filteredUsers.length === 0 && (
                  <tr>
                    <td colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                      No users found.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Settings tab */}
      {tab === 'settings' && (isLoading || !settings) ? (
        <div className="py-20 text-center text-sm text-muted-foreground">Loading settings...</div>
      ) : tab === 'settings' && settings && (
        <div className="space-y-6">
          {/* Logo */}
          <div className="card-scientific">
            <div className="flex items-center gap-2">
              <ImageIcon size={16} className="text-accent" />
              <h2 className="text-sm font-semibold">Logo</h2>
            </div>
            <p className="mt-1 text-xs text-muted-foreground">
              Appears in PDF report headers. Max 2MB. PNG, JPEG, WebP, or SVG.
            </p>
            <div className="mt-4 flex items-center gap-4">
              <div className="flex h-20 w-32 items-center justify-center rounded-lg border border-border bg-muted/50">
                {settings.has_logo ? (
                  <img src="/api/v1/admin/logo" alt="Logo" className="max-h-16 max-w-28 object-contain" />
                ) : (
                  <div className="text-center text-xs text-muted-foreground">
                    <ImageIcon className="mx-auto mb-1" size={20} /> No logo
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-2">
                <input ref={fileInputRef} type="file" accept="image/png,image/jpeg,image/webp,image/svg+xml" onChange={handleLogoUpload} className="hidden" />
                <button onClick={() => fileInputRef.current?.click()} disabled={uploading} className="btn-outline btn-sm">
                  <Upload size={14} /> {uploading ? 'Uploading...' : 'Upload Logo'}
                </button>
                {settings.has_logo && (
                  <button onClick={handleLogoDelete} className="btn-ghost btn-sm text-destructive hover:bg-destructive/10">
                    <Trash2 size={14} /> Remove
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Branding */}
          <div className="card-scientific">
            <div className="flex items-center gap-2">
              <Building2 size={16} className="text-accent" />
              <h2 className="text-sm font-semibold">Organization Branding</h2>
            </div>
            <div className="mt-4 space-y-4">
              <div>
                <label className="label">Lab / Organization Name</label>
                <input className="input mt-1" value={form.lab_name || ''} onChange={(e) => setForm({ ...form, lab_name: e.target.value })} />
              </div>
              <div>
                <label className="label">Subtitle</label>
                <input className="input mt-1" value={form.lab_subtitle || ''} onChange={(e) => setForm({ ...form, lab_subtitle: e.target.value })} />
              </div>
              <div>
                <label className="label"><Globe size={12} className="mr-1 inline" /> Website</label>
                <input className="input mt-1" value={form.lab_website || ''} onChange={(e) => setForm({ ...form, lab_website: e.target.value })} />
              </div>
              <div>
                <label className="label">Address</label>
                <textarea className="input mt-1 h-16 text-xs" value={form.lab_address || ''} onChange={(e) => setForm({ ...form, lab_address: e.target.value })} />
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="card-scientific">
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-accent" />
              <h2 className="text-sm font-semibold">Report Footer Text</h2>
            </div>
            <textarea className="input mt-3 h-20 text-xs" value={form.report_footer || ''} onChange={(e) => setForm({ ...form, report_footer: e.target.value })} />
          </div>

          {/* Security */}
          <div className="card-scientific">
            <div className="flex items-center gap-2">
              <Shield size={16} className="text-accent" />
              <h2 className="text-sm font-semibold">Security</h2>
            </div>
            <label className="mt-4 flex items-center justify-between cursor-pointer">
              <div>
                <span className="text-sm font-medium">Allow New User Registration</span>
                <p className="text-xs text-muted-foreground">
                  {form.registration_enabled
                    ? 'New users can self-register accounts'
                    : 'Registration is disabled — only admins can create accounts'}
                </p>
              </div>
              <button
                type="button"
                role="switch"
                aria-checked={form.registration_enabled ?? true}
                onClick={() => setForm({ ...form, registration_enabled: !form.registration_enabled })}
                className={`relative h-5 w-9 shrink-0 rounded-full transition-colors ${form.registration_enabled ? 'bg-accent' : 'bg-muted'}`}
              >
                <span
                  className={`absolute top-0.5 h-4 w-4 rounded-full bg-white transition-transform ${form.registration_enabled ? 'translate-x-4' : 'translate-x-0.5'}`}
                />
              </button>
            </label>
          </div>

          <div className="flex justify-end">
            <button onClick={handleSave} disabled={saveMutation.isPending} className="btn-primary">
              <Save size={16} /> {saveMutation.isPending ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      )}

      {/* Audit log tab */}
      {tab === 'audit' && (
        <div className="card p-0 overflow-visible">
          <div className="flex items-center justify-between border-b border-border p-3">
            <div className="flex items-center gap-2">
              <ScrollText size={16} className="text-muted-foreground" />
              <span className="text-sm font-semibold">
                Audit Logs {auditData?.total != null && `(${auditData.total})`}
              </span>
            </div>
            <button
              onClick={() => {
                if (confirm('Clear ALL audit log entries? This cannot be undone.')) {
                  clearAuditMutation.mutate();
                }
              }}
              disabled={clearAuditMutation.isPending || !auditData?.logs?.length}
              className="btn-outline btn-sm text-destructive"
            >
              <Trash2 size={14} className="mr-1" />
              {clearAuditMutation.isPending ? 'Clearing...' : 'Clear All Logs'}
            </button>
          </div>
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User</th>
                <th>Action</th>
                <th>Resource</th>
                <th>Detail</th>
              </tr>
            </thead>
            <tbody>
              {auditData?.logs.map((log: AuditLogEntry) => (
                <tr key={log.id}>
                  <td className="whitespace-nowrap text-xs text-muted-foreground">
                    {log.created_at ? new Date(log.created_at).toLocaleString() : '—'}
                  </td>
                  <td className="text-xs">{log.user_email || '—'}</td>
                  <td>
                    <span className="badge badge-muted">{log.action}</span>
                  </td>
                  <td className="text-xs">
                    {log.resource_type ? `${log.resource_type}${log.resource_id ? ':' + log.resource_id.slice(0, 8) : ''}` : '—'}
                  </td>
                  <td className="max-w-xs truncate text-xs text-muted-foreground">{log.detail || '—'}</td>
                </tr>
              ))}
              {(!auditData?.logs || auditData.logs.length === 0) && (
                <tr>
                  <td colSpan={5} className="py-8 text-center text-sm text-muted-foreground">
                    No audit log entries yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

function StatCard({ label, value, icon, color = 'accent' }: { label: string; value: number; icon: React.ReactNode; color?: 'accent' | 'success' }) {
  return (
    <div className="stat-card" style={{ ['--stat-color' as string]: color === 'success' ? 'hsl(var(--success))' : 'hsl(var(--accent))' }}>
      <div className="flex items-center gap-2 text-muted-foreground">
        {icon}
        <span className="text-xs font-medium">{label}</span>
      </div>
      <p className="mt-2 text-2xl font-bold">{value.toLocaleString()}</p>
    </div>
  );
}

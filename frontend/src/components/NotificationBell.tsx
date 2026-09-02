import { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { Bell, AlertTriangle, Info, X } from 'lucide-react';
import { notificationsApi } from '@/api/notifications';
import type { Notification } from '@/types';
import { cn } from '@/lib/utils';

export function NotificationBell() {
  const [notifications, setNotifications] = useState<Notification[]>([]);
  const [open, setOpen] = useState(false);
  const [dismissed, setDismissed] = useState<Set<string>>(new Set());
  const dropdownRef = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  useEffect(() => {
    const load = async () => {
      try {
        const data = await notificationsApi.list();
        setNotifications(data);
      } catch {
        // Silent fail — notifications are non-critical
      }
    };
    load();
    const interval = setInterval(load, 60000);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const activeNotifications = notifications.filter((n) => !dismissed.has(n.id));
  const count = activeNotifications.length;

  const dismiss = (id: string) => {
    setDismissed((prev) => new Set(prev).add(id));
    notificationsApi.dismiss(id).catch(() => {});
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setOpen(!open)}
        className="relative inline-flex h-9 w-9 items-center justify-center rounded-md border border-input bg-background transition-colors hover:bg-muted"
        aria-label={`Notifications (${count})`}
      >
        <Bell size={16} />
        {count > 0 && (
          <span className="absolute -right-1 -top-1 flex h-4 min-w-4 items-center justify-center rounded-full bg-destructive px-1 text-[10px] font-bold text-white">
            {count}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 top-11 z-50 w-80 overflow-hidden rounded-lg border border-border bg-card shadow-lg animate-slide-down">
          <div className="flex items-center justify-between border-b border-border px-3 py-2">
            <span className="text-sm font-semibold">Notifications</span>
            {count > 0 && <span className="badge badge-info">{count} new</span>}
          </div>

          {activeNotifications.length === 0 ? (
            <div className="py-8 text-center text-sm text-muted-foreground">
              No notifications
            </div>
          ) : (
            <div className="max-h-80 overflow-y-auto">
              {activeNotifications.map((n) => (
                <div
                  key={n.id}
                  className={cn(
                    'flex items-start gap-2.5 border-b border-border p-3 last:border-0',
                    n.severity === 'warning' ? 'bg-warning/5' : 'bg-info/5',
                  )}
                >
                  <div className={cn(
                    'mt-0.5 shrink-0 rounded-md p-1.5',
                    n.severity === 'warning' ? 'bg-warning/10 text-warning' : 'bg-info/10 text-info',
                  )}>
                    {n.severity === 'warning' ? <AlertTriangle size={14} /> : <Info size={14} />}
                  </div>
                  <div className="min-w-0 flex-1">
                    <p className="text-xs font-medium">{n.message}</p>
                    <div className="mt-1.5 flex items-center gap-2">
                      <button
                        onClick={() => {
                          navigate(`/data?column=${n.column_type}`);
                          setOpen(false);
                        }}
                        className="btn-sm btn-primary"
                      >
                        Retrain Now
                      </button>
                      <button
                        onClick={() => dismiss(n.id)}
                        className="text-xs text-muted-foreground hover:text-foreground"
                      >
                        Dismiss
                      </button>
                    </div>
                  </div>
                  <button
                    onClick={() => dismiss(n.id)}
                    className="text-muted-foreground hover:text-foreground"
                  >
                    <X size={14} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

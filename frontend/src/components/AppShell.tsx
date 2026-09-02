import { useState, type ReactNode } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  LayoutDashboard,
  FlaskConical,
  BookMarked,
  Upload,
  BarChart3,
  Layers,
  GitCompare,
  Database,
  LayoutTemplate,
  LogOut,
  Menu,
  X,
} from 'lucide-react';
import { useAuth } from '@/context/AuthContext';
import { ThemeToggle } from '@/components/ThemeToggle';
import { Logo } from '@/components/Logo';
import { cn } from '@/lib/utils';

interface NavItem {
  to: string;
  label: string;
  icon: typeof LayoutDashboard;
}

interface NavSection {
  title: string;
  items: NavItem[];
}

const navSections: NavSection[] = [
  {
    title: 'Main',
    items: [
      { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
      { to: '/', label: 'Predictor', icon: FlaskConical },
      { to: '/methods', label: 'Method Library', icon: BookMarked },
    ],
  },
  {
    title: 'Data & Models',
    items: [
      { to: '/data', label: 'Data Upload', icon: Upload },
      { to: '/models', label: 'ML Models', icon: BarChart3 },
    ],
  },
  {
    title: 'Tools',
    items: [
      { to: '/batch', label: 'Batch Analysis', icon: Layers },
      { to: '/compare', label: 'Method Comparison', icon: GitCompare },
      { to: '/columns', label: 'Column Database', icon: Database },
      { to: '/templates', label: 'Templates', icon: LayoutTemplate },
    ],
  },
];

const pageTitles: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/': 'Predictor',
  '/methods': 'Method Library',
  '/data': 'Data & Models',
  '/models': 'ML Models',
  '/batch': 'Batch Analysis',
  '/compare': 'Method Comparison',
  '/columns': 'Column Database',
  '/templates': 'Method Templates',
};

export function AppShell({ children }: { children: ReactNode }) {
  const { logout, user } = useAuth();
  const location = useLocation();
  const [collapsed, setCollapsed] = useState(false);

  const pageTitle = pageTitles[location.pathname] || 'IsotopiQ LC-MS Suite';
  const initials = user?.email
    ? user.email
        .split('@')[0]
        .split(/[._-]/)
        .map((s) => s[0])
        .slice(0, 2)
        .join('')
        .toUpperCase()
    : '?';

  return (
    <div className="flex min-h-screen bg-background">
      {/* Sidebar */}
      <aside
        className={cn(
          'fixed left-0 top-0 z-40 flex h-screen flex-col bg-sidebar text-sidebar-foreground transition-all duration-200',
          collapsed ? 'w-16' : 'w-60',
        )}
      >
        {/* Logo */}
        <div className="flex h-14 items-center justify-between border-b border-sidebar-muted px-3">
          {!collapsed && (
            <a href="/dashboard" className="flex items-center">
              <img
                src="/isotopiq-logo-white.png"
                alt="IsotopiQ"
                className="h-7 w-auto"
                style={{ maxHeight: '28px' }}
              />
            </a>
          )}
          {collapsed && (
            <a href="/dashboard" className="mx-auto">
              <img
                src="/isotopiq-logo-white.png"
                alt="IsotopiQ"
                className="h-7 w-auto"
                style={{ maxHeight: '28px', objectFit: 'contain' }}
              />
            </a>
          )}
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="rounded-md p-1 text-sidebar-muted-foreground hover:bg-sidebar-muted hover:text-sidebar-foreground"
          >
            {collapsed ? <Menu size={16} /> : <X size={16} />}
          </button>
        </div>

        {/* Nav sections */}
        <nav className="flex-1 overflow-y-auto px-2 py-3">
          {navSections.map((section) => (
            <div key={section.title} className="mb-4">
              {!collapsed && (
                <p className="mb-1.5 px-3 text-[10px] font-semibold uppercase tracking-wider text-sidebar-muted-foreground">
                  {section.title}
                </p>
              )}
              <div className="space-y-0.5">
                {section.items.map((item) => (
                  <NavLink
                    key={item.to}
                    to={item.to}
                    end={item.to === '/'}
                    className={({ isActive }) =>
                      cn(
                        'flex items-center gap-2.5 rounded-md px-3 py-2 text-sm font-medium transition-colors',
                        collapsed && 'justify-center px-2',
                        isActive
                          ? 'bg-sidebar-muted text-sidebar-foreground border-l-[3px] border-accent'
                          : 'text-sidebar-muted-foreground hover:bg-sidebar-muted/50 hover:text-sidebar-foreground',
                      )
                    }
                    title={collapsed ? item.label : undefined}
                  >
                    <item.icon size={16} className="shrink-0" />
                    {!collapsed && <span>{item.label}</span>}
                  </NavLink>
                ))}
              </div>
            </div>
          ))}
        </nav>

        {/* User info at bottom */}
        <div className="border-t border-sidebar-muted p-2">
          <div className={cn('flex items-center gap-2 rounded-md p-2', collapsed && 'justify-center')}>
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent text-xs font-bold text-accent-foreground">
              {initials}
            </div>
            {!collapsed && (
              <div className="min-w-0 flex-1">
                <p className="truncate text-xs font-medium">{user?.email}</p>
                {user?.is_admin && (
                  <span className="badge badge-info mt-0.5 text-[10px]">Admin</span>
                )}
              </div>
            )}
            <button
              onClick={logout}
              className={cn(
                'rounded-md p-1.5 text-sidebar-muted-foreground hover:bg-sidebar-muted hover:text-sidebar-foreground',
                collapsed && 'mx-auto',
              )}
              aria-label="Logout"
              title="Logout"
            >
              <LogOut size={16} />
            </button>
          </div>
        </div>
      </aside>

      {/* Main content area */}
      <div className={cn('flex flex-1 flex-col transition-all duration-200', collapsed ? 'ml-16' : 'ml-60')}>
        {/* Topbar */}
        <header className="sticky top-0 z-30 flex h-14 items-center justify-between border-b border-border bg-card/80 px-4 backdrop-blur-sm">
          <div className="flex items-center gap-3">
            <h1 className="text-base font-semibold">{pageTitle}</h1>
          </div>
          <div className="flex items-center gap-2">
            <kbd className="hidden items-center gap-1 rounded border border-border bg-muted px-1.5 py-0.5 text-[10px] text-muted-foreground sm:flex">
              <span>⌘K</span>
            </kbd>
            <ThemeToggle />
          </div>
        </header>

        {/* Page content */}
        <main className="flex-1 overflow-x-hidden">{children}</main>
      </div>
    </div>
  );
}

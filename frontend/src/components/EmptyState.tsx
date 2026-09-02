import type { ReactNode } from 'react';

interface EmptyStateProps {
  icon: ReactNode;
  title: string;
  description?: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, description, action }: EmptyStateProps) {
  return (
    <div className="card flex flex-col items-center gap-3 py-12 text-center">
      <div className="rounded-full bg-muted p-4 text-muted-foreground">{icon}</div>
      <div>
        <p className="text-sm font-semibold">{title}</p>
        {description && (
          <p className="mt-1 text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  );
}

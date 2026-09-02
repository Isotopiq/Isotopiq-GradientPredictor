import { cn } from '@/lib/utils';

interface SkeletonProps {
  className?: string;
  lines?: number;
}

export function Skeleton({ className, lines = 1 }: SkeletonProps) {
  if (lines > 1) {
    return (
      <div className={cn('space-y-2', className)}>
        {Array.from({ length: lines }).map((_, i) => (
          <div
            key={i}
            className="h-4 rounded bg-muted"
            style={{ width: `${100 - i * 10}%` }}
          />
        ))}
      </div>
    );
  }
  return <div className={cn('h-4 w-full rounded bg-muted', className)} />;
}

export function SkeletonCard({ className }: { className?: string }) {
  return (
    <div className={cn('card space-y-3', className)}>
      <Skeleton className="h-5 w-32" />
      <Skeleton lines={4} />
    </div>
  );
}

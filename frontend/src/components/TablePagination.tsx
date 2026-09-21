import { useEffect, useState } from 'react';
import { ChevronLeft, ChevronRight } from 'lucide-react';

interface TablePaginationProps {
  /** Total row count (unpaginated) */
  total: number;
  /** Current page, 0-based */
  page: number;
  /** Rows per page */
  pageSize: number;
  onPage: (page: number) => void;
}

/**
 * Compact footer pager for data tables. Renders nothing when the
 * data fits on one page.
 */
export function TablePagination({ total, page, pageSize, onPage }: TablePaginationProps) {
  const pages = Math.ceil(total / pageSize);
  if (pages <= 1) return null;
  const from = page * pageSize + 1;
  const to = Math.min(total, (page + 1) * pageSize);
  return (
    <div className="flex items-center justify-between border-t border-border px-1 pt-2 text-xs text-muted-foreground">
      <span className="tabular-nums">
        {from}–{to} of {total}
      </span>
      <div className="flex items-center gap-1">
        <button
          type="button"
          className="btn-outline btn-sm px-1.5"
          disabled={page === 0}
          onClick={() => onPage(page - 1)}
          aria-label="Previous page"
        >
          <ChevronLeft size={14} />
        </button>
        <span className="tabular-nums">
          {page + 1}/{pages}
        </span>
        <button
          type="button"
          className="btn-outline btn-sm px-1.5"
          disabled={page >= pages - 1}
          onClick={() => onPage(page + 1)}
          aria-label="Next page"
        >
          <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}

/**
 * Paginate a row list: returns the current page's slice plus the
 * pager state. Resets to page 0 whenever `rows` identity changes.
 */
export function useTablePagination<T>(rows: T[] | null | undefined, pageSize = 10) {
  const [page, setPage] = useState(0);
  useEffect(() => setPage(0), [rows]);
  const safe = rows ?? [];
  const maxPage = Math.max(0, Math.ceil(safe.length / pageSize) - 1);
  const clamped = Math.min(page, maxPage);
  return {
    page: clamped,
    setPage,
    pageRows: safe.slice(clamped * pageSize, clamped * pageSize + pageSize),
    total: safe.length,
    pageSize,
  };
}

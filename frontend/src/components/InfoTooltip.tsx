import { useState } from 'react';
import { HelpCircle } from 'lucide-react';

interface InfoTooltipProps {
  content: string;
  title?: string;
  size?: number;
}

export function InfoTooltip({ content, title, size = 14 }: InfoTooltipProps) {
  const [show, setShow] = useState(false);

  return (
    <span className="relative inline-flex">
      <button
        type="button"
        onMouseEnter={() => setShow(true)}
        onMouseLeave={() => setShow(false)}
        onClick={() => setShow(!show)}
        className="text-muted-foreground hover:text-foreground"
        aria-label={title || 'More info'}
      >
        <HelpCircle size={size} />
      </button>
      {show && (
        <span className="absolute bottom-full left-1/2 z-50 mb-2 w-64 -translate-x-1/2 rounded-md border border-border bg-popover p-3 text-xs shadow-lg">
          {title && (
            <span className="mb-1 block font-semibold text-foreground">{title}</span>
          )}
          <span className="block text-muted-foreground">{content}</span>
          <span className="absolute left-1/2 top-full -translate-x-1/2 border-4 border-transparent border-t-border" />
        </span>
      )}
    </span>
  );
}

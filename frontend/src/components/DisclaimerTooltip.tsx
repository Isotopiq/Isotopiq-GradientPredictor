import { Info } from 'lucide-react';
import { useEffect, useState } from 'react';

export function DisclaimerTooltip() {
  const [show, setShow] = useState(false);

  useEffect(() => {
    const dismissed = localStorage.getItem('disclaimer_dismissed');
    if (!dismissed) {
      setShow(true);
    }
  }, []);

  const dismiss = () => {
    localStorage.setItem('disclaimer_dismissed', '1');
    setShow(false);
  };

  if (!show) {
    return (
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Info size={12} />
        <span>Predictions are estimates — verify experimentally.</span>
      </div>
    );
  }

  return (
    <div className="fixed inset-x-0 bottom-0 z-50 p-4">
      <div className="mx-auto max-w-2xl rounded-lg border border-border bg-card p-4 shadow-lg">
        <div className="flex items-start gap-3">
          <Info className="mt-0.5 shrink-0 text-warning" size={20} />
          <div className="flex-1">
            <h3 className="text-sm font-semibold">Scientific Disclaimer</h3>
            <p className="mt-1 text-sm text-muted-foreground">
              Predictions from this tool are estimates derived from physicochemical heuristics
              and statistical models. They require experimental verification before use in
              regulated or production analytical work. pKa and logP values from RDKit are
              approximate.
            </p>
            <button onClick={dismiss} className="btn-primary mt-3 text-xs">
              Got it
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

import { useEffect, useRef, useState, useCallback } from 'react';
import { Loader2 } from 'lucide-react';

interface KetcherEditorProps {
  smiles?: string;
  onSmilesChange?: (smiles: string) => void;
}

let ketcherInstance: any = null;

export function getKetcherInstance(): any {
  return ketcherInstance;
}

export function KetcherEditor({ smiles, onSmilesChange }: KetcherEditorProps) {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [EditorComponent, setEditorComponent] = useState<any>(null);
  const lastSmilesRef = useRef<string>('');
  const onSmilesChangeRef = useRef(onSmilesChange);
  onSmilesChangeRef.current = onSmilesChange;
  const pendingSmilesRef = useRef<string | null>(null);

  // Load the Editor component and CSS dynamically
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const mod = await import('ketcher-react');
        await import('ketcher-react/dist/index.css');
        if (!cancelled) {
          setEditorComponent(() => mod.Editor);
        }
      } catch (err) {
        console.error('Failed to load Ketcher Editor:', err);
        if (!cancelled) {
          setError('Failed to load Ketcher editor module');
          setLoading(false);
        }
      }
    })();
    return () => { cancelled = true; };
  }, []);

  const handleInit = useCallback((ketcher: any) => {
    ketcherInstance = ketcher;
    (window as any).ketcher = ketcher;
    setLoading(false);

    // Load pending SMILES if any
    if (pendingSmilesRef.current) {
      ketcher.setMolecule(pendingSmilesRef.current).catch(() => {});
      lastSmilesRef.current = pendingSmilesRef.current;
      pendingSmilesRef.current = null;
    }
  }, []);

  // Load SMILES when it changes externally
  useEffect(() => {
    if (!smiles || smiles === lastSmilesRef.current) return;
    if (ketcherInstance) {
      lastSmilesRef.current = smiles;
      ketcherInstance.setMolecule(smiles).catch(() => {});
    } else {
      pendingSmilesRef.current = smiles;
    }
  }, [smiles]);

  // Poll for SMILES changes from the editor
  useEffect(() => {
    if (loading || !ketcherInstance) return;
    const interval = setInterval(async () => {
      if (!ketcherInstance || !onSmilesChangeRef.current) return;
      try {
        const result = await ketcherInstance.getSmiles(true);
        if (result && result !== lastSmilesRef.current) {
          lastSmilesRef.current = result;
          onSmilesChangeRef.current(result);
        }
      } catch {
        // Empty canvas — ignore
      }
    }, 1500);
    return () => clearInterval(interval);
  }, [loading]);

  if (error) {
    return (
      <div className="flex h-[400px] items-center justify-center rounded-md border border-destructive/30 bg-destructive/5 text-sm text-destructive">
        <div className="text-center">
          <p>{error}</p>
        </div>
      </div>
    );
  }

  return (
    <div className="relative" style={{ height: '450px' }}>
      {loading && (
        <div className="absolute inset-0 z-10 flex items-center justify-center rounded-md bg-background/80">
          <div className="flex items-center gap-2 text-sm text-muted-foreground">
            <Loader2 size={16} className="animate-spin" />
            Loading Ketcher editor...
          </div>
        </div>
      )}
      {EditorComponent && (
        <EditorComponent
          staticResourcesUrl="/ketcher/"
          onInit={handleInit}
          errorHandler={(err: unknown) => console.error('Ketcher error:', err)}
        />
      )}
    </div>
  );
}

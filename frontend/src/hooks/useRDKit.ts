import { useEffect, useState, useRef } from 'react';

// RDKit.js type is loose since the package doesn't ship great TS types
interface RDKitModule {
  get_mol: (smiles: string) => {
    get_svg: (width: number, height: number) => string;
    get_svg_with_highlights?: (width: number, height: number, details: string) => string;
    is_valid: () => boolean;
    delete: () => void;
  };
}

let rdkitPromise: Promise<RDKitModule> | null = null;

async function loadRDKit(): Promise<RDKitModule> {
  if (rdkitPromise) return rdkitPromise;

  rdkitPromise = (async () => {
    // Dynamic import of @rdkit/rdkit — loads WASM module
    const mod = await import('@rdkit/rdkit');
    const init = (mod as unknown as { init: () => Promise<RDKitModule> }).init;
    const rdkit = await init();
    return rdkit;
  })();

  return rdkitPromise;
}

export function useRDKit() {
  const [rdkit, setRdkit] = useState<RDKitModule | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    loadRDKit()
      .then((r) => {
        if (mountedRef.current) {
          setRdkit(r);
          setLoading(false);
        }
      })
      .catch((e) => {
        if (mountedRef.current) {
          setError(String(e));
          setLoading(false);
        }
      });
    return () => {
      mountedRef.current = false;
    };
  }, []);

  return { rdkit, loading, error };
}

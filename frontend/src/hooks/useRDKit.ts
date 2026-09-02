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
    // The package uses CommonJS (module.exports.default = initRDKitModule).
    // Vite wraps this so the init function may be at mod.default, mod.init,
    // or nested differently depending on the build. Handle all cases.
    const modAny = mod as unknown as Record<string, unknown>;
    const initFn: ((opts?: { locateFile?: (path: string) => string }) => Promise<RDKitModule>) | undefined =
      typeof modAny.init === 'function'
        ? modAny.init as typeof modAny.init & (() => Promise<RDKitModule>)
        : typeof modAny.default === 'function'
          ? modAny.default as typeof modAny.default & (() => Promise<RDKitModule>)
          : typeof (modAny.default as Record<string, unknown> | undefined)?.init === 'function'
            ? (modAny.default as Record<string, unknown>).init as (opts?: { locateFile?: (path: string) => string }) => Promise<RDKitModule>
            : undefined;

    if (!initFn) {
      throw new Error('RDKit init function not found in module exports');
    }

    // The WASM file is copied to the public directory by the build.
    // We need to tell RDKit where to find it, because Vite renames
    // the JS bundle (e.g. RDKit_minimal-Dz-YEtpT.js) but the WASM
    // file keeps its original name in the public dir.
    const rdkit = await initFn({
      locateFile: (path: string) => `/${path}`,
    });
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

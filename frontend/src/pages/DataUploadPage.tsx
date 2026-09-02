import { DataUpload } from '@/components/DataUpload';
import { ModelsPage } from '@/pages/ModelsPage';
import { useState } from 'react';

export function DataUploadPage() {
  const [refreshKey, setRefreshKey] = useState(0);

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border">
        <div className="mx-auto max-w-7xl px-4 py-3">
          <h1 className="text-lg font-bold">Data & Models</h1>
        </div>
      </header>
      <main className="mx-auto max-w-7xl px-4 py-6">
        <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
          <div className="lg:col-span-1">
            <DataUpload onTrained={() => setRefreshKey((k) => k + 1)} />
          </div>
          <div className="lg:col-span-2">
            <div key={refreshKey}>
              <ModelsPage />
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

import { DataUpload } from '@/components/DataUpload';
import { useSearchParams } from 'react-router-dom';

export function DataUploadPage() {
  const [searchParams] = useSearchParams();
  const preselectedColumn = searchParams.get('column');

  return (
    <div className="mx-auto max-w-4xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Data Upload & Model Training</h1>
        <p className="text-sm text-muted-foreground">
          Upload experimental run data as CSV to train retention prediction models.
          {preselectedColumn && (
            <span className="mt-1 block text-warning">
              Recommended: retrain {preselectedColumn} model with new data
            </span>
          )}
        </p>
      </div>
      <DataUpload onTrained={() => {}} defaultColumn={preselectedColumn || undefined} />
    </div>
  );
}

import { useState } from 'react';
import { useQuery, useMutation } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { LayoutTemplate, Check } from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { MethodTemplate } from '@/types';

export function TemplatesPage() {
  const [category, setCategory] = useState('');
  const navigate = useNavigate();

  const { data: templates, isLoading } = useQuery({
    queryKey: ['templates', category],
    queryFn: () => methodsApi.listTemplates(category || undefined),
  });

  const { data: categories } = useQuery({
    queryKey: ['template-categories'],
    queryFn: () => methodsApi.templateCategories(),
  });

  const applyMutation = useMutation({
    mutationFn: ({ templateId, name }: { templateId: string; name?: string }) =>
      methodsApi.applyTemplate(templateId, name),
    onSuccess: (method) => {
      toast.success(`Method "${method.name}" created from template`);
      navigate('/methods');
    },
    onError: () => toast.error('Failed to create method from template'),
  });

  return (
    <div className="mx-auto max-w-6xl p-6">
      <div className="mb-6">
        <h1 className="text-xl font-bold">Method Templates</h1>
        <p className="text-sm text-muted-foreground">
          Pre-built LC method templates for common compound classes
        </p>
      </div>

      {/* Category filter */}
      <div className="mb-6 flex flex-wrap gap-2">
        <button
          className={`badge ${!category ? 'badge-info' : 'badge-muted cursor-pointer'}`}
          onClick={() => setCategory('')}
        >
          All
        </button>
        {(categories || []).map((c) => (
          <button
            key={c}
            className={`badge ${category === c ? 'badge-info' : 'badge-muted cursor-pointer'}`}
            onClick={() => setCategory(c)}
          >
            {c}
          </button>
        ))}
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {[1, 2, 3].map((i) => <Skeleton key={i} className="h-64" />)}
        </div>
      ) : !templates || templates.length === 0 ? (
        <EmptyState
          icon={<LayoutTemplate size={24} />}
          title="No templates found"
          description="Templates will appear here"
        />
      ) : (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
          {templates.map((t: MethodTemplate) => (
            <div key={t.id} className="card-scientific flex flex-col">
              <div className="flex items-start justify-between">
                <div>
                  <h3 className="text-sm font-bold">{t.name}</h3>
                  <span className="badge badge-muted mt-1">{t.category}</span>
                </div>
                <span className="badge badge-info">{t.column_type}</span>
              </div>

              <p className="mt-2 flex-1 text-xs text-muted-foreground">{t.description}</p>

              <div className="mt-3 grid grid-cols-2 gap-1.5 text-xs">
                <Param label="pH" value={t.ph.toFixed(1)} />
                <Param label="Flow" value={`${t.flow_rate_ml_min} mL/min`} />
                <Param label="Gradient" value={`${t.gradient_time_min} min`} />
                <Param label="Temp" value={`${t.temperature_c}°C`} />
                <Param label="%B Start" value={`${t.percent_b_start}%`} />
                <Param label="%B End" value={`${t.percent_b_end}%`} />
              </div>

              <div className="mt-2 text-xs text-muted-foreground">
                <p>Column: {t.column_length_mm}mm, {t.particle_size_um}µm</p>
                <p className="truncate">A: {t.mobile_phase_a}</p>
                <p className="truncate">B: {t.mobile_phase_b}</p>
              </div>

              <button
                className="btn-primary btn-sm mt-3 w-full"
                onClick={() => applyMutation.mutate({ templateId: t.id, name: t.name })}
                disabled={applyMutation.isPending}
              >
                {applyMutation.isPending && applyMutation.variables?.templateId === t.id ? (
                  <>Creating...</>
                ) : (
                  <><Check size={14} className="mr-1" /> Use Template</>
                )}
              </button>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function Param({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded border border-border px-2 py-1">
      <span className="text-muted-foreground">{label}: </span>
      <span className="font-medium">{value}</span>
    </div>
  );
}

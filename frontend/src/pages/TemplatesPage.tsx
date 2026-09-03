import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Plus, Trash2, Edit3, Check, X, FlaskConical, Share2, Copy,
  Layers, ChevronDown, ChevronRight,
} from 'lucide-react';
import { methodsApi } from '@/api/methods';
import { EmptyState } from '@/components/EmptyState';
import { Skeleton } from '@/components/Skeleton';
import { toast } from 'sonner';
import type { MethodTemplate, UserMethodTemplate, UserTemplateCreate } from '@/types';

export function TemplatesPage() {
  const [showBuiltIn, setShowBuiltIn] = useState(true);
  const [showUser, setShowUser] = useState(true);
  const [editing, setEditing] = useState<UserMethodTemplate | null>(null);
  const [showCreate, setShowCreate] = useState(false);
  const navigate = useNavigate();
  const queryClient = useQueryClient();

  const { data: builtInTemplates, isLoading: loadingBuiltIn } = useQuery({
    queryKey: ['templates'],
    queryFn: () => methodsApi.listTemplates(),
  });

  const { data: userTemplates, isLoading: loadingUser } = useQuery({
    queryKey: ['user-templates'],
    queryFn: () => methodsApi.listUserTemplates(),
  });

  const { data: categories } = useQuery({
    queryKey: ['template-categories'],
    queryFn: () => methodsApi.templateCategories(),
  });

  const applyMutation = useMutation({
    mutationFn: ({ id, name }: { id: string; name?: string }) =>
      methodsApi.applyTemplate(id, name),
    onSuccess: (method) => {
      toast.success(`Method "${method.name}" created from template`);
      navigate('/');
    },
    onError: () => toast.error('Failed to apply template'),
  });

  const deleteMutation = useMutation({
    mutationFn: (id: string) => methodsApi.deleteUserTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['user-templates'] });
      toast.success('Template deleted');
    },
    onError: () => toast.error('Failed to delete template'),
  });

  const handleDelete = (id: string, name: string) => {
    if (confirm(`Delete template "${name}"?`)) {
      deleteMutation.mutate(id);
    }
  };

  return (
    <div className="mx-auto max-w-7xl p-6">
      <div className="mb-6 flex items-center justify-between">
        <div>
          <h1 className="text-xl font-bold">Method Templates</h1>
          <p className="text-sm text-muted-foreground">
            Pre-built and custom LC-MS method templates — apply to create a method or create your own
          </p>
        </div>
        <button
          type="button"
          onClick={() => { setEditing(null); setShowCreate(true); }}
          className="btn-primary btn-sm"
        >
          <Plus size={14} /> New Template
        </button>
      </div>

      {/* Create/Edit form */}
      {(showCreate || editing) && (
        <TemplateEditor
          key={editing?.id || 'new'}
          template={editing}
          onClose={() => { setShowCreate(false); setEditing(null); }}
          onSaved={() => {
            queryClient.invalidateQueries({ queryKey: ['user-templates'] });
            setShowCreate(false);
            setEditing(null);
          }}
        />
      )}

      {/* Built-in templates */}
      <div className="mb-4">
        <button
          onClick={() => setShowBuiltIn(!showBuiltIn)}
          className="mb-2 flex items-center gap-1 text-sm font-semibold"
        >
          {showBuiltIn ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <Layers size={16} className="text-accent" />
          Built-in Templates ({builtInTemplates?.length ?? 0})
        </button>
        {showBuiltIn && (
          loadingBuiltIn ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[...Array(6)].map((_, i) => <Skeleton key={i} className="h-40 w-full rounded-lg" />)}
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {builtInTemplates?.map((t) => (
                <BuiltInTemplateCard
                  key={t.id}
                  template={t}
                  onApply={() => applyMutation.mutate({ id: t.id, name: t.name })}
                  applying={applyMutation.isPending}
                />
              ))}
            </div>
          )
        )}
      </div>

      {/* User-created templates */}
      <div>
        <button
          onClick={() => setShowUser(!showUser)}
          className="mb-2 flex items-center gap-1 text-sm font-semibold"
        >
          {showUser ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
          <FlaskConical size={16} className="text-accent" />
          My Templates ({userTemplates?.length ?? 0})
        </button>
        {showUser && (
          loadingUser ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {[...Array(3)].map((_, i) => <Skeleton key={i} className="h-40 w-full rounded-lg" />)}
            </div>
          ) : userTemplates && userTemplates.length > 0 ? (
            <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {userTemplates.map((t) => (
                <UserTemplateCard
                  key={t.id}
                  template={t}
                  onApply={() => applyMutation.mutate({ id: t.id, name: t.name })}
                  onEdit={() => setEditing(t)}
                  onDelete={() => handleDelete(t.id, t.name)}
                  applying={applyMutation.isPending}
                />
              ))}
            </div>
          ) : (
            <EmptyState
              icon={<Plus size={24} />}
              title="No custom templates yet"
              description="Create your own reusable method templates with custom gradients, solvents, and column parameters."
            />
          )
        )}
      </div>
    </div>
  );
}

function BuiltInTemplateCard({
  template,
  onApply,
  applying,
}: {
  template: MethodTemplate;
  onApply: () => void;
  applying: boolean;
}) {
  return (
    <div className="card-scientific flex flex-col gap-2">
      <div>
        <span className="badge badge-info text-[10px]">{template.category}</span>
      </div>
      <h3 className="text-sm font-semibold">{template.name}</h3>
      <p className="text-xs text-muted-foreground line-clamp-2">{template.description}</p>
      <div className="grid grid-cols-2 gap-1 text-xs">
        <div><span className="text-muted-foreground">Column:</span> {template.column_type}</div>
        <div><span className="text-muted-foreground">pH:</span> {template.ph}</div>
        <div><span className="text-muted-foreground">%B:</span> {template.percent_b_start}→{template.percent_b_end}</div>
        <div><span className="text-muted-foreground">Time:</span> {template.gradient_time_min} min</div>
        <div><span className="text-muted-foreground">Flow:</span> {template.flow_rate_ml_min} mL/min</div>
        <div><span className="text-muted-foreground">Temp:</span> {template.temperature_c}°C</div>
      </div>
      <button
        onClick={onApply}
        disabled={applying}
        className="btn-outline btn-sm mt-auto"
      >
        <Copy size={12} /> Apply Template
      </button>
    </div>
  );
}

function UserTemplateCard({
  template,
  onApply,
  onEdit,
  onDelete,
  applying,
}: {
  template: UserMethodTemplate;
  onApply: () => void;
  onEdit: () => void;
  onDelete: () => void;
  applying: boolean;
}) {
  return (
    <div className="card-scientific flex flex-col gap-2">
      <div className="flex items-start justify-between gap-2">
        <div>
          <span className="badge badge-info text-[10px]">{template.category}</span>
          {template.is_shared && (
            <span className="badge badge-success text-[10px] ml-1">
              <Share2 size={8} className="mr-0.5" /> Shared
            </span>
          )}
        </div>
      </div>
      <h3 className="text-sm font-semibold">{template.name}</h3>
      {template.description && (
        <p className="text-xs text-muted-foreground line-clamp-2">{template.description}</p>
      )}
      <div className="grid grid-cols-2 gap-1 text-xs">
        <div><span className="text-muted-foreground">Column:</span> {template.column_type}</div>
        <div><span className="text-muted-foreground">pH:</span> {template.ph ?? '—'}</div>
        <div><span className="text-muted-foreground">%B:</span> {template.percent_b_start}→{template.percent_b_end}</div>
        <div><span className="text-muted-foreground">Time:</span> {template.gradient_time_min} min</div>
        <div><span className="text-muted-foreground">Flow:</span> {template.flow_rate_ml_min} mL/min</div>
        <div><span className="text-muted-foreground">Temp:</span> {template.temperature_c}°C</div>
      </div>
      <div className="flex items-center gap-2 mt-auto pt-1">
        <button
          onClick={onApply}
          disabled={applying}
          className="btn-outline btn-sm flex-1"
        >
          <Copy size={12} /> Apply
        </button>
        <button onClick={onEdit} className="btn-ghost btn-sm" title="Edit">
          <Edit3 size={14} />
        </button>
        <button
          onClick={onDelete}
          className="btn-ghost btn-sm text-destructive hover:bg-destructive/10"
          title="Delete"
        >
          <Trash2 size={14} />
        </button>
      </div>
    </div>
  );
}

function TemplateEditor({
  template,
  onClose,
  onSaved,
}: {
  template: UserMethodTemplate | null;
  onClose: () => void;
  onSaved: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState<UserTemplateCreate>({
    name: template?.name || '',
    category: template?.category || 'Custom',
    description: template?.description || '',
    column_type: template?.column_type || 'C18',
    mobile_phase_a: template?.mobile_phase_a || '',
    mobile_phase_b: template?.mobile_phase_b || '',
    additive: template?.additive || '',
    ph: template?.ph ?? 2.7,
    percent_b_start: template?.percent_b_start ?? 5,
    percent_b_end: template?.percent_b_end ?? 95,
    gradient_time_min: template?.gradient_time_min ?? 20,
    flow_rate_ml_min: template?.flow_rate_ml_min ?? 0.4,
    temperature_c: template?.temperature_c ?? 30,
    column_length_mm: template?.column_length_mm ?? 100,
    particle_size_um: template?.particle_size_um ?? 1.8,
    is_shared: template?.is_shared ?? false,
  });

  const saveMutation = useMutation({
    mutationFn: async () => {
      if (template) {
        return methodsApi.updateUserTemplate(template.id, form);
      } else {
        return methodsApi.createUserTemplate(form);
      }
    },
    onSuccess: () => {
      toast.success(template ? 'Template updated' : 'Template created');
      onSaved();
    },
    onError: () => toast.error('Failed to save template'),
  });

  const set = <K extends keyof UserTemplateCreate>(key: K, value: UserTemplateCreate[K]) => {
    setForm((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <div className="card-scientific mb-4">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold">
          {template ? 'Edit Template' : 'Create New Template'}
        </h3>
        <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
          <X size={16} />
        </button>
      </div>

      <div className="mt-3 grid grid-cols-1 gap-3 md:grid-cols-2 lg:grid-cols-3">
        <div className="lg:col-span-2">
          <label className="label">Name</label>
          <input
            className="input mt-1 text-xs"
            value={form.name}
            onChange={(e) => set('name', e.target.value)}
            placeholder="e.g. My Custom C18 Method"
          />
        </div>
        <div>
          <label className="label">Category</label>
          <input
            className="input mt-1 text-xs"
            value={form.category}
            onChange={(e) => set('category', e.target.value)}
            placeholder="e.g. Custom"
          />
        </div>
        <div className="lg:col-span-3">
          <label className="label">Description</label>
          <textarea
            className="input mt-1 h-16 text-xs"
            value={form.description}
            onChange={(e) => set('description', e.target.value)}
            placeholder="Describe what this template is optimized for..."
          />
        </div>
        <div>
          <label className="label">Column Type</label>
          <select
            className="input mt-1 text-xs"
            value={form.column_type}
            onChange={(e) => set('column_type', e.target.value)}
          >
            <option value="C18">C18</option>
            <option value="C30">C30</option>
            <option value="phenyl">Phenyl</option>
            <option value="HILIC">HILIC</option>
            <option value="ion_pair">Ion Pair</option>
          </select>
        </div>
        <div>
          <label className="label">pH</label>
          <input
            type="number"
            step="0.1"
            className="input mt-1 text-xs"
            value={form.ph}
            onChange={(e) => set('ph', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">Temperature (°C)</label>
          <input
            type="number"
            className="input mt-1 text-xs"
            value={form.temperature_c}
            onChange={(e) => set('temperature_c', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">%B Start</label>
          <input
            type="number"
            className="input mt-1 text-xs"
            value={form.percent_b_start}
            onChange={(e) => set('percent_b_start', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">%B End</label>
          <input
            type="number"
            className="input mt-1 text-xs"
            value={form.percent_b_end}
            onChange={(e) => set('percent_b_end', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">Gradient Time (min)</label>
          <input
            type="number"
            className="input mt-1 text-xs"
            value={form.gradient_time_min}
            onChange={(e) => set('gradient_time_min', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">Flow Rate (mL/min)</label>
          <input
            type="number"
            step="0.05"
            className="input mt-1 text-xs"
            value={form.flow_rate_ml_min}
            onChange={(e) => set('flow_rate_ml_min', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">Column Length (mm)</label>
          <input
            type="number"
            className="input mt-1 text-xs"
            value={form.column_length_mm}
            onChange={(e) => set('column_length_mm', parseInt(e.target.value) || 0)}
          />
        </div>
        <div>
          <label className="label">Particle Size (µm)</label>
          <input
            type="number"
            step="0.1"
            className="input mt-1 text-xs"
            value={form.particle_size_um}
            onChange={(e) => set('particle_size_um', parseFloat(e.target.value) || 0)}
          />
        </div>
        <div className="lg:col-span-3">
          <label className="label">Mobile Phase A</label>
          <input
            className="input mt-1 text-xs"
            value={form.mobile_phase_a}
            onChange={(e) => set('mobile_phase_a', e.target.value)}
            placeholder="e.g. Water + 0.1% Formic Acid"
          />
        </div>
        <div className="lg:col-span-3">
          <label className="label">Mobile Phase B</label>
          <input
            className="input mt-1 text-xs"
            value={form.mobile_phase_b}
            onChange={(e) => set('mobile_phase_b', e.target.value)}
            placeholder="e.g. Acetonitrile"
          />
        </div>
        <div className="lg:col-span-3">
          <label className="label">Additive</label>
          <input
            className="input mt-1 text-xs"
            value={form.additive}
            onChange={(e) => set('additive', e.target.value)}
            placeholder="e.g. 0.1% Formic Acid"
          />
        </div>
        <div className="lg:col-span-3 flex items-center gap-2">
          <input
            type="checkbox"
            id="template-shared"
            checked={form.is_shared}
            onChange={(e) => set('is_shared', e.target.checked)}
            className="accent-accent"
          />
          <label htmlFor="template-shared" className="text-xs">
            Share with all users
          </label>
        </div>
      </div>

      <div className="mt-3 flex justify-end gap-2">
        <button onClick={onClose} className="btn-ghost btn-sm">Cancel</button>
        <button
          onClick={() => saveMutation.mutate()}
          disabled={!form.name.trim() || saveMutation.isPending}
          className="btn-primary btn-sm"
        >
          <Check size={12} /> {template ? 'Update' : 'Create'}
        </button>
      </div>
    </div>
  );
}

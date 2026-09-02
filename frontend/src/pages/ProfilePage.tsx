import { useState, useRef, useCallback, useEffect } from 'react';
import { useMutation, useQueryClient } from '@tanstack/react-query';
import { authApi } from '@/api/auth';
import { useAuth } from '@/context/AuthContext';
import { toast } from 'sonner';
import Cropper, { type Area } from 'react-easy-crop';
import { User as UserIcon, Save, Upload, Trash2, Camera, Check, X } from 'lucide-react';

function cropImage(imageSrc: string, pixelCrop: Area): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const image = new Image();
    image.onload = () => {
      const canvas = document.createElement('canvas');
      const ctx = canvas.getContext('2d');
      if (!ctx) return reject(new Error('No canvas context'));
      canvas.width = pixelCrop.width;
      canvas.height = pixelCrop.height;
      ctx.drawImage(
        image,
        pixelCrop.x, pixelCrop.y,
        pixelCrop.width, pixelCrop.height,
        0, 0,
        pixelCrop.width, pixelCrop.height,
      );
      canvas.toBlob((blob) => {
        if (blob) resolve(blob);
        else reject(new Error('Failed to crop'));
      }, 'image/png');
    };
    image.onerror = () => reject(new Error('Failed to load image'));
    image.src = imageSrc;
  });
}

export function ProfilePage() {
  const { user, setUser } = useAuth();
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [saving, setSaving] = useState(false);

  // Sync local form state when user loads asynchronously (e.g. on page reload)
  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEmail(user.email || '');
    }
  }, [user]);

  // Crop state
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  const [crop, setCrop] = useState({ x: 0, y: 0 });
  const [zoom, setZoom] = useState(1);
  const [croppedAreaPixels, setCroppedAreaPixels] = useState<Area | null>(null);
  const [uploadingPic, setUploadingPic] = useState(false);

  const onCropComplete = useCallback((_: Area, pixels: Area) => {
    setCroppedAreaPixels(pixels);
  }, []);

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error('Image too large (max 10MB before crop)');
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setImageSrc(reader.result as string);
    reader.readAsDataURL(file);
  };

  const handleCropConfirm = async () => {
    if (!imageSrc || !croppedAreaPixels) return;
    setUploadingPic(true);
    try {
      const blob = await cropImage(imageSrc, croppedAreaPixels);
      if (blob.size > 10 * 1024 * 1024) {
        toast.error('Cropped image too large (max 10MB). Try a smaller crop or lower-resolution image.');
        return;
      }
      const file = new File([blob], 'profile.png', { type: 'image/png' });
      const updated = await authApi.uploadProfilePicture(file);
      setUser(updated);
      queryClient.invalidateQueries({ queryKey: ['user'] });
      toast.success('Profile picture updated');
      setImageSrc(null);
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Failed to upload picture');
    } finally {
      setUploadingPic(false);
    }
  };

  const handleDeletePic = async () => {
    try {
      const updated = await authApi.deleteProfilePicture();
      setUser(updated);
      toast.success('Profile picture removed');
    } catch {
      toast.error('Failed to remove picture');
    }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await authApi.updateProfile({
        full_name: fullName.trim() || undefined,
        email: email.trim() && email.trim() !== user?.email ? email.trim() : undefined,
      });
      setUser(updated);
      toast.success('Profile updated');
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      toast.error(msg || 'Failed to update profile');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-xl font-bold">My Profile</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage your account details and profile picture.</p>
      </div>

      {/* Profile picture */}
      <div className="card-scientific">
        <div className="flex items-center gap-2">
          <Camera size={16} className="text-accent" />
          <h2 className="text-sm font-semibold">Profile Picture</h2>
        </div>

        <div className="mt-4 flex items-center gap-4">
          {/* Avatar */}
          <div className="relative">
            <div className="flex h-24 w-24 items-center justify-center overflow-hidden rounded-full border-2 border-border bg-muted">
              {user?.has_profile_picture ? (
                <img
                  src={`/api/v1/auth/profile/picture/${user.id}`}
                  alt="Profile"
                  className="h-full w-full object-cover"
                />
              ) : (
                <UserIcon size={32} className="text-muted-foreground" />
              )}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <input
              ref={fileInputRef}
              type="file"
              accept="image/png,image/jpeg,image/webp"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              className="btn-outline btn-sm"
            >
              <Upload size={14} /> Choose Image
            </button>
            {user?.has_profile_picture && (
              <button
                onClick={handleDeletePic}
                className="btn-ghost btn-sm text-destructive hover:bg-destructive/10"
              >
                <Trash2 size={14} /> Remove
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Crop modal */}
      {imageSrc && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center bg-black/70 p-4">
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-2xl">
            <div className="mb-4 flex items-center justify-between">
              <h3 className="text-sm font-semibold">Crop Profile Picture</h3>
              <button onClick={() => setImageSrc(null)} className="text-muted-foreground hover:text-foreground">
                <X size={18} />
              </button>
            </div>

            <div className="relative h-64 w-full overflow-hidden rounded-lg bg-muted">
              <Cropper
                image={imageSrc}
                crop={crop}
                zoom={zoom}
                aspect={1}
                onCropChange={setCrop}
                onZoomChange={setZoom}
                onCropComplete={onCropComplete}
                cropShape="round"
                showGrid={false}
              />
            </div>

            <div className="mt-4">
              <label className="label">Zoom</label>
              <input
                type="range"
                min={1}
                max={3}
                step={0.1}
                value={zoom}
                onChange={(e) => setZoom(Number(e.target.value))}
                className="slider-scientific mt-1"
              />
            </div>

            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setImageSrc(null)} className="btn-ghost btn-sm">
                Cancel
              </button>
              <button
                onClick={handleCropConfirm}
                disabled={uploadingPic}
                className="btn-primary btn-sm"
              >
                <Check size={14} /> {uploadingPic ? 'Uploading...' : 'Confirm & Upload'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Account details */}
      <div className="card-scientific">
        <div className="flex items-center gap-2">
          <UserIcon size={16} className="text-accent" />
          <h2 className="text-sm font-semibold">Account Details</h2>
        </div>

        <div className="mt-4 space-y-4">
          <div>
            <label className="label">Full Name</label>
            <input
              className="input mt-1"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
              placeholder="Your name"
            />
          </div>
          <div>
            <label className="label">Email</label>
            <input
              type="email"
              className="input mt-1"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
            />
          </div>
          {user?.last_login_at && (
            <div>
              <label className="label">Last Login</label>
              <p className="mt-1 text-sm text-muted-foreground">
                {new Date(user.last_login_at).toLocaleString()}
              </p>
            </div>
          )}
        </div>

        <div className="mt-4 flex justify-end">
          <button onClick={handleSave} disabled={saving} className="btn-primary">
            <Save size={16} /> {saving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>
    </div>
  );
}

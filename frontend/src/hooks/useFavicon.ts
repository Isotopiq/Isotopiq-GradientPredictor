import { useEffect } from 'react';

/**
 * On mount, check if a custom favicon has been uploaded by the admin.
 * If so, replace the browser tab favicon with the custom one.
 * If not (404), leave the default Vite favicon in place.
 */
export function useFavicon() {
  useEffect(() => {
    const faviconUrl = '/api/v1/admin/favicon';
    // Probe the endpoint — if it returns 200, swap the favicon link
    fetch(faviconUrl, { method: 'GET' })
      .then((res) => {
        if (!res.ok) return;
        const mime = res.headers.get('content-type') || 'image/png';
        // Convert to blob URL so the browser can render it
        return res.blob().then((blob) => {
          const url = URL.createObjectURL(blob);
          // Remove existing favicon links
          document.querySelectorAll("link[rel='icon'], link[rel='shortcut icon']").forEach((el) => el.remove());
          // Create new favicon link
          const link = document.createElement('link');
          link.rel = 'icon';
          link.type = mime;
          link.href = url;
          document.head.appendChild(link);
        });
      })
      .catch(() => {
        // No custom favicon — leave default
      });
  }, []);
}

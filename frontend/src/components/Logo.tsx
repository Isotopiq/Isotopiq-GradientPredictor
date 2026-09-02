import { useTheme } from '@/context/ThemeContext';

interface LogoProps {
  className?: string;
  variant?: 'auto' | 'light' | 'dark';
}

export function Logo({ className = '', variant = 'auto' }: LogoProps) {
  const { resolvedTheme } = useTheme();
  const isDark = variant === 'dark' || (variant === 'auto' && resolvedTheme === 'dark');
  const src = isDark ? '/isotopiq-logo-white.png' : '/isotopiq-logo.png';

  return (
    <div className={`flex items-center ${className}`}>
      <img
        src={src}
        alt="IsotopiQ"
        className="h-8 w-auto object-contain"
        style={{ maxHeight: '32px' }}
      />
    </div>
  );
}

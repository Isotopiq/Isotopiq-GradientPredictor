import logoDark from '@/assets/isotopiq-logo.png';
import logoLight from '@/assets/isotopiq-logo-white.png';
import { useTheme } from '@/context/ThemeContext';

interface LogoProps {
  className?: string;
  showText?: boolean;
}

export function Logo({ className = '', showText = false }: LogoProps) {
  const { theme } = useTheme();
  const logo = theme === 'dark' ? logoLight : logoDark;

  return (
    <div className={`flex items-center gap-2 ${className}`}>
      <img
        src={logo}
        alt="IsotopiQ"
        className="h-8 w-auto object-contain"
        style={{ maxHeight: '36px' }}
      />
      {showText && (
        <span className="text-sm font-semibold text-muted-foreground">
          LC-MS Suite
        </span>
      )}
    </div>
  );
}

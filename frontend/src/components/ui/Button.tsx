import type { ButtonHTMLAttributes, ReactNode } from 'react';
import Spinner from './Spinner';
import styles from './Button.module.scss';

type Variant = 'primary' | 'secondary' | 'danger' | 'ghost';
type Size = 'sm' | 'md' | 'lg';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  loading?: boolean;
  icon?: ReactNode;
}

export function Button({
  variant = 'primary',
  size = 'md',
  loading = false,
  icon,
  children,
  disabled,
  className,
  ...rest
}: ButtonProps) {
  return (
    <button
      className={`${styles.btn} ${styles[variant]} ${styles[size]} ${className ?? ''}`}
      disabled={disabled || loading}
      {...rest}
    >
      {loading ? (
        <Spinner size="sm" />
      ) : icon ? (
        <span className={styles.icon}>{icon}</span>
      ) : null}
      {children && <span>{children}</span>}
    </button>
  );
}

export default Button;

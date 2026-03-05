import type { ReactNode } from 'react';
import styles from './Badge.module.scss';

type BadgeVariant = 'success' | 'warning' | 'danger' | 'info' | 'neutral';

interface BadgeProps {
  variant?: BadgeVariant;
  children: ReactNode;
}

export function Badge({ variant = 'neutral', children }: BadgeProps) {
  return (
    <span className={`${styles.badge} ${styles[variant]}`}>{children}</span>
  );
}

export default Badge;

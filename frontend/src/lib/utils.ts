/* ─── EduTrack — Utility Functions ─── */
import { format, formatDistanceToNow } from 'date-fns';
import type { ApiError } from '@/types';

/** Format ISO date to human-readable */
export function formatDate(iso: string, fmt = 'MMM d, yyyy'): string {
  return format(new Date(iso), fmt);
}

export function formatDateTime(iso: string): string {
  return format(new Date(iso), 'MMM d, yyyy HH:mm');
}

export function timeAgo(iso: string): string {
  return formatDistanceToNow(new Date(iso), { addSuffix: true });
}

/** Format seconds to mm:ss or hh:mm:ss */
export function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = seconds % 60;
  const pad = (n: number) => String(n).padStart(2, '0');
  return h > 0 ? `${pad(h)}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
}

/** Extract error message from API error */
export function getErrorMessage(err: unknown): string {
  if (typeof err === 'object' && err !== null) {
    const e = err as { response?: { data?: ApiError | { message?: string; detail?: unknown } } };
    const data = e.response?.data;
    if (data) {
      if ('message' in data && typeof data.message === 'string') return data.message;
      if ('detail' in data) {
        if (typeof data.detail === 'string') return data.detail;
        if (typeof data.detail === 'object' && data.detail && 'message' in (data.detail as Record<string, unknown>))
          return (data.detail as Record<string, string>).message;
      }
    }
    if ('message' in err && typeof (err as Error).message === 'string')
      return (err as Error).message;
  }
  return 'An unexpected error occurred';
}

/** Clamp number between min and max */
export function clamp(value: number, min: number, max: number): number {
  return Math.min(Math.max(value, min), max);
}

/** Generate initials from full name */
export function getInitials(name: string): string {
  return name
    .split(' ')
    .map((w) => w[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);
}

/** Construct CSS class names (simple cn helper) */
export function cn(...classes: (string | false | null | undefined)[]): string {
  return classes.filter(Boolean).join(' ');
}

/** Score color based on percentage */
export function scoreColor(score: number | null): string {
  if (score === null) return 'var(--color-muted)';
  if (score >= 80) return 'var(--color-success)';
  if (score >= 50) return 'var(--color-warning)';
  return 'var(--color-danger)';
}

/** Grade letter from percentage */
export function gradeFromScore(score: number): string {
  if (score >= 90) return 'A';
  if (score >= 80) return 'B';
  if (score >= 70) return 'C';
  if (score >= 60) return 'D';
  return 'F';
}

/* ─── useAutoSave — Auto-save answers every 30s ─── */
import { useEffect, useRef, useCallback } from 'react';

interface UseAutoSaveOptions {
  /** Function that performs the save */
  saveFn: () => Promise<void>;
  /** Interval in ms (default 30000 = 30s) */
  interval?: number;
  /** Whether auto-save is active */
  enabled?: boolean;
}

export function useAutoSave({
  saveFn,
  interval = 30_000,
  enabled = true,
}: UseAutoSaveOptions) {
  const lastSavedRef = useRef<Date | null>(null);
  const saveFnRef = useRef(saveFn);

  useEffect(() => {
    saveFnRef.current = saveFn;
  }, [saveFn]);

  useEffect(() => {
    if (!enabled) return;

    const timer = setInterval(async () => {
      try {
        await saveFnRef.current();
        lastSavedRef.current = new Date();
      } catch {
        // Auto-save failure is non-fatal; will retry on next interval
      }
    }, interval);

    return () => clearInterval(timer);
  }, [interval, enabled]);

  const saveNow = useCallback(async () => {
    try {
      await saveFnRef.current();
      lastSavedRef.current = new Date();
    } catch {
      // ignore
    }
  }, []);

  return { lastSaved: lastSavedRef, saveNow };
}

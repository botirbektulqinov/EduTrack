/* ─── useTimer — Assessment countdown timer ─── */
import { useState, useEffect, useCallback, useRef } from 'react';

const WARNING_THRESHOLDS = [600, 300, 60]; // 10min, 5min, 1min

interface UseTimerOptions {
  initialSeconds: number;
  onExpire: () => void;
  onWarning?: (remaining: number) => void;
  enabled?: boolean;
}

export function useTimer({
  initialSeconds,
  onExpire,
  onWarning,
  enabled = true,
}: UseTimerOptions) {
  const [remaining, setRemaining] = useState(initialSeconds);
  const warningFired = useRef<Set<number>>(new Set());
  const expireFired = useRef(false);
  const onExpireRef = useRef(onExpire);
  const onWarningRef = useRef(onWarning);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    onExpireRef.current = onExpire;
    onWarningRef.current = onWarning;
  }, [onExpire, onWarning]);

  const triggerExpire = useCallback(() => {
    if (expireFired.current) return;
    expireFired.current = true;
    onExpireRef.current();
  }, []);

  // Re-sync remaining when initialSeconds changes (e.g. attempt loaded asynchronously)
  useEffect(() => {
    if (initialSeconds > 0) {
      // Resync local countdown when the active attempt is loaded or restored.
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setRemaining(initialSeconds);
      warningFired.current.clear();
      expireFired.current = false;
    }
  }, [initialSeconds]);

  useEffect(() => {
    if (!enabled || remaining <= 0) return;

    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 1;

        // Check warnings
        if (onWarningRef.current) {
          for (const threshold of WARNING_THRESHOLDS) {
            if (next === threshold && !warningFired.current.has(threshold)) {
              warningFired.current.add(threshold);
              onWarningRef.current(threshold);
            }
          }
        }

        if (next <= 0) {
          clearInterval(intervalRef.current!);
          triggerExpire();
          return 0;
        }
        return next;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [enabled, remaining, triggerExpire]);

  const deductTime = useCallback((seconds: number) => {
    setRemaining((prev) => {
      const next = Math.max(0, prev - seconds);
      if (next <= 0) {
        triggerExpire();
      }
      return next;
    });
  }, [triggerExpire]);

  const syncTime = useCallback((serverRemaining: number) => {
    setRemaining(serverRemaining);
    if (serverRemaining > 0) {
      expireFired.current = false;
    }
  }, []);

  return { remaining, deductTime, syncTime };
}

/* ─── useTimer — Assessment countdown timer ─── */
import { useState, useEffect, useCallback, useRef } from 'react';

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
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const WARNING_THRESHOLDS = [600, 300, 60]; // 10min, 5min, 1min

  // Re-sync remaining when initialSeconds changes (e.g. attempt loaded asynchronously)
  useEffect(() => {
    if (initialSeconds > 0) {
      setRemaining(initialSeconds);
    }
  }, [initialSeconds]);

  useEffect(() => {
    if (!enabled || remaining <= 0) return;

    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        const next = prev - 1;

        // Check warnings
        if (onWarning) {
          for (const threshold of WARNING_THRESHOLDS) {
            if (next === threshold && !warningFired.current.has(threshold)) {
              warningFired.current.add(threshold);
              onWarning(threshold);
            }
          }
        }

        if (next <= 0) {
          clearInterval(intervalRef.current!);
          onExpire();
          return 0;
        }
        return next;
      });
    }, 1000);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const deductTime = useCallback((seconds: number) => {
    setRemaining((prev) => {
      const next = Math.max(0, prev - seconds);
      if (next <= 0) {
        onExpire();
      }
      return next;
    });
  }, [onExpire]);

  const syncTime = useCallback((serverRemaining: number) => {
    setRemaining(serverRemaining);
  }, []);

  return { remaining, deductTime, syncTime };
}

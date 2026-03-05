/* ─── useProctoring — Anti-cheat hook (§6, §11.2) ─── */
import { useRef, useEffect, useCallback } from 'react';
import { ProctoringSDK } from '@/lib/proctoring-sdk';
import type { ProctoringConfig, ViolationEvent } from '@/types';

interface UseProctoringOptions {
  config: ProctoringConfig;
  onViolation: (event: ViolationEvent) => void;
  onTerminate: () => void;
  enabled?: boolean;
}

export function useProctoring({
  config,
  onViolation,
  onTerminate,
  enabled = true,
}: UseProctoringOptions) {
  const sdkRef = useRef<ProctoringSDK | null>(null);

  useEffect(() => {
    if (!enabled) return;

    const sdk = new ProctoringSDK(config, { onViolation, onTerminate });
    sdkRef.current = sdk;
    sdk.init();

    return () => {
      sdk.destroy();
      sdkRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [enabled]);

  const enterFullscreen = useCallback(async () => {
    // If SDK is ready, delegate to it
    if (sdkRef.current) {
      return sdkRef.current.enterFullscreen();
    }
    // Fallback: request fullscreen directly (SDK not yet initialized, e.g. preview phase)
    try {
      await document.documentElement.requestFullscreen();
      return true;
    } catch {
      return false;
    }
  }, []);

  return { enterFullscreen, sdk: sdkRef };
}

import { act, renderHook } from '@testing-library/react';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { useTimer } from './useTimer';

describe('useTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('counts down and calls onExpire once', () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() =>
      useTimer({
        initialSeconds: 2,
        onExpire,
        enabled: true,
      }),
    );

    act(() => {
      vi.advanceTimersByTime(3000);
    });

    expect(result.current.remaining).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });

  it('syncs server time and applies penalties without going negative', () => {
    const onExpire = vi.fn();
    const { result } = renderHook(() =>
      useTimer({
        initialSeconds: 120,
        onExpire,
        enabled: false,
      }),
    );

    act(() => {
      result.current.syncTime(90);
      result.current.deductTime(100);
    });

    expect(result.current.remaining).toBe(0);
    expect(onExpire).toHaveBeenCalledTimes(1);
  });
});

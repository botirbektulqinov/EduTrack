/* ─── useWebSocket — WebSocket connection for proctoring ─── */
import { useRef, useEffect, useCallback, useState } from 'react';
import type { WSServerMessage } from '@/types';

interface UseWebSocketOptions {
  attemptId: string;
  serverToken: string;
  onMessage: (msg: WSServerMessage) => void;
  enabled?: boolean;
}

export function useWebSocket({
  attemptId,
  serverToken,
  onMessage,
  enabled = true,
}: UseWebSocketOptions) {
  const wsRef = useRef<WebSocket | null>(null);
  const [connected, setConnected] = useState(false);

  useEffect(() => {
    if (!enabled || !attemptId || !serverToken) return;

    const configuredBase = import.meta.env.VITE_WS_BASE_URL as string | undefined;
    const defaultBase =
      `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}`;
    const wsBaseURL = (configuredBase || defaultBase).replace(/\/$/, '');
    const url = `${wsBaseURL}/ws/attempt/${attemptId}?token=${serverToken}`;
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as WSServerMessage;
        onMessage(data);
      } catch {
        // ignore malformed messages
      }
    };

    ws.onclose = () => setConnected(false);
    ws.onerror = () => setConnected(false);

    return () => {
      ws.close();
      wsRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [attemptId, serverToken, enabled]);

  const send = useCallback((data: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(data));
    }
  }, []);

  return { send, connected };
}

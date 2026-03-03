'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { apiConfig, getAccessToken } from '@/lib/api/config';

/**
 * Connects to backend WebSocket for real-time material processing updates.
 *
 * @param {string|null} userId  – current user's ID (skip if null)
 * @param {(msg: object) => void} onMessage – handler for incoming messages
 * @returns {{ connected: boolean }}
 */
export default function useMaterialUpdates(userId, onMessage) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimer = useRef(null);
  const reconnectAttempts = useRef(0);
  const onMessageRef = useRef(onMessage);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  // Stable ref to the connect function so ws.onclose can schedule a reconnect
  // without creating a circular self-reference inside the useCallback.
  const connectRef = useRef(null);

  const connect = useCallback(() => {
    if (!userId) return;

    const token = getAccessToken();
    if (!token) return;

    // Derive WS URL from API base (http→ws, https→wss)
    const base = apiConfig.baseUrl.replace(/^http/, 'ws');
    const url = `${base}/ws/jobs/${userId}`;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        ws.send(JSON.stringify({ type: 'auth', token }));
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }
          if (msg.type === 'connected') return;
          onMessageRef.current?.(msg);
        } catch {
          // ignore malformed messages
        }
      };

      ws.onclose = () => {
        setConnected(false);
        wsRef.current = null;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current += 1;
        // Use the ref to schedule reconnection — avoids a self-referential closure
        // that the linter would flag as accessing `connect` before it is declared.
        reconnectTimer.current = setTimeout(() => connectRef.current?.(), delay);
      };

      ws.onerror = () => {
        // onclose fires after onerror
      };

      wsRef.current = ws;
    } catch {
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current += 1;
      reconnectTimer.current = setTimeout(() => connectRef.current?.(), delay);
    }
  }, [userId]);

  // Keep the ref current so ws.onclose always calls the latest version
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    connect();

    return () => {
      clearTimeout(reconnectTimer.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; // prevent reconnect on intentional close
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [connect]);

  return { connected, wsRef };
}

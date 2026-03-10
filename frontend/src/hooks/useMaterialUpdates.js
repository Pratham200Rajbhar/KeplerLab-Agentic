'use client';

import { useEffect, useRef, useCallback, useState } from 'react';
import { apiConfig, getAccessToken } from '@/lib/api/config';


export default function useMaterialUpdates(userId, onMessage) {
  const wsRef = useRef(null);
  const [connected, setConnected] = useState(false);
  const reconnectTimerRef = useRef(null);
  const reconnectAttempts = useRef(0);
  const onMessageRef = useRef(onMessage);
  const mountedRef = useRef(true);

  useEffect(() => {
    onMessageRef.current = onMessage;
  }, [onMessage]);

  
  const connectRef = useRef(null);

  const connect = useCallback(() => {
    if (!userId || !mountedRef.current) return;

    const token = getAccessToken();
    if (!token) return;

    
    const base = apiConfig.baseUrl.replace(/^http/, 'ws');
    const url = `${base}/ws/jobs/${userId}`;

    try {
      const ws = new WebSocket(url);

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        ws.send(JSON.stringify({ type: 'auth', token }));
        setConnected(true);
        reconnectAttempts.current = 0;
      };

      ws.onmessage = (event) => {
        if (!mountedRef.current) return;
        try {
          const msg = JSON.parse(event.data);
          if (msg.type === 'ping') {
            ws.send(JSON.stringify({ type: 'pong' }));
            return;
          }
          if (msg.type === 'connected') return;
          onMessageRef.current?.(msg);
        } catch {
          
        }
      };

      ws.onclose = () => {
        if (!mountedRef.current) return;
        setConnected(false);
        wsRef.current = null;
        const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
        reconnectAttempts.current += 1;
        
        clearTimeout(reconnectTimerRef.current);
        reconnectTimerRef.current = setTimeout(() => {
          if (mountedRef.current) connectRef.current?.();
        }, delay);
      };

      ws.onerror = () => {
        
      };

      wsRef.current = ws;
    } catch {
      if (!mountedRef.current) return;
      const delay = Math.min(1000 * Math.pow(2, reconnectAttempts.current), 30000);
      reconnectAttempts.current += 1;
      clearTimeout(reconnectTimerRef.current);
      reconnectTimerRef.current = setTimeout(() => {
        if (mountedRef.current) connectRef.current?.();
      }, delay);
    }
  }, [userId]);

  
  useEffect(() => {
    connectRef.current = connect;
  }, [connect]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      clearTimeout(reconnectTimerRef.current);
      if (wsRef.current) {
        wsRef.current.onclose = null; 
        wsRef.current.close();
        wsRef.current = null;
      }
      setConnected(false);
    };
  }, [connect]);

  return { connected, wsRef };
}

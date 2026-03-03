'use client';

import { useEffect, useRef } from 'react';
import usePodcastStore from '@/stores/usePodcastStore';

/**
 * Hooks into an existing WebSocket connection and routes
 * podcast-specific events into usePodcastStore.
 *
 * @param {React.MutableRefObject<WebSocket|null>} wsRef
 */
export default function usePodcastWebSocket(wsRef) {
  const handleWsEvent = usePodcastStore((s) => s.handleWsEvent);
  const handlerRef = useRef(handleWsEvent);
  handlerRef.current = handleWsEvent;

  useEffect(() => {
    const ws = wsRef?.current;
    if (!ws) return;

    const onMessage = (event) => {
      try {
        const msg = JSON.parse(event.data);
        if (msg.type && msg.type.startsWith('podcast_')) {
          handlerRef.current(msg);
        }
      } catch {
        // Not JSON or not a podcast event — ignore
      }
    };

    ws.addEventListener('message', onMessage);
    return () => ws.removeEventListener('message', onMessage);
  }, [wsRef]);
}

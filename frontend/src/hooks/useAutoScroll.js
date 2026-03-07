'use client';

import { useRef, useEffect, useCallback, useState } from 'react';

/**
 * useAutoScroll — scrolls to bottom when new messages arrive,
 * unless the user has manually scrolled up.
 *
 * @param {Array} deps - Dependencies that trigger auto-scroll check (e.g. messages, isStreaming)
 * @returns {{ containerRef, scrollToBottom, isAtBottom }}
 */
export default function useAutoScroll(deps = []) {
  const containerRef = useRef(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const userScrolledRef = useRef(false);

  const checkIsAtBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return true;
    // Consider "at bottom" if within 100px of the bottom
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }, []);

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    userScrolledRef.current = false;
    setIsAtBottom(true);
  }, []);

  // Listen for user scroll events
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;

    const handleScroll = () => {
      const atBottom = checkIsAtBottom();
      setIsAtBottom(atBottom);
      if (!atBottom) {
        userScrolledRef.current = true;
      } else {
        userScrolledRef.current = false;
      }
    };

    el.addEventListener('scroll', handleScroll, { passive: true });
    return () => el.removeEventListener('scroll', handleScroll);
  }, [checkIsAtBottom]);

  // Auto-scroll when deps change, if user hasn't scrolled up
  useEffect(() => {
    if (!userScrolledRef.current) {
      scrollToBottom('smooth');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);

  return { containerRef, scrollToBottom, isAtBottom };
}

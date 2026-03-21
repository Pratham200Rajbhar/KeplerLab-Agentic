'use client';

import { useRef, useEffect, useCallback, useState } from 'react';


export default function useAutoScroll(deps = []) {
  const containerRef = useRef(null);
  const [isAtBottom, setIsAtBottom] = useState(true);
  const userScrolledRef = useRef(false);

  const checkIsAtBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return true;
    
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }, []);

  const scrollToBottom = useCallback((behavior = 'smooth') => {
    const el = containerRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior });
    userScrolledRef.current = false;
  }, []);

  
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

  /* eslint-disable react-hooks/exhaustive-deps */
  useEffect(() => {
    if (!userScrolledRef.current) {
      scrollToBottom('smooth');
    }
  }, [...deps, scrollToBottom]);
  /* eslint-enable react-hooks/exhaustive-deps */

  return { containerRef, scrollToBottom, isAtBottom };
}

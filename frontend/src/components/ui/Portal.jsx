'use client';

import { useEffect, useState } from 'react';
import { createPortal } from 'react-dom';

/**
 * A simple Portal component that renders its children into document.body
 * This avoids CSS stacking context and transform constraints.
 */
export default function Portal({ children }) {
  const [mounted, setMounted] = useState(false);

  useEffect(() => {
    setMounted(true);
    return () => setMounted(false);
  }, []);

  if (!mounted) return null;

  return createPortal(children, document.body);
}

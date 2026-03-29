'use client';

import { createPortal } from 'react-dom';

/**
 * A simple Portal component that renders its children into document.body
 * This avoids CSS stacking context and transform constraints.
 */
export default function Portal({ children }) {
  if (typeof document === 'undefined') return null;

  return createPortal(children, document.body);
}

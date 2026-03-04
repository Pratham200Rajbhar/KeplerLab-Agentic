'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { PANEL } from '@/lib/utils/constants';

/**
 * Handles drag-to-resize for Sidebar and StudioPanel.
 *
 * @param {'left'|'right'} side - Which edge to resize from
 * @param {object} opts
 * @param {number} opts.defaultWidth - Initial width
 * @param {number} [opts.minWidth] - Minimum width
 * @param {number} [opts.maxWidth] - Maximum width
 * @param {boolean} [opts.collapsible] - Allow collapsing below min threshold
 * @param {number} [opts.collapseThreshold] - Width below which it collapses
 * @returns {{ width, collapsed, startDrag, toggle, setWidth }}
 */
export default function useResizablePanel(
  side = 'left',
  {
    defaultWidth = PANEL.SIDEBAR.DEFAULT_WIDTH,
    minWidth = PANEL.SIDEBAR.MIN_WIDTH,
    maxWidth = PANEL.SIDEBAR.MAX_WIDTH,
    collapsible = true,
    collapseThreshold = PANEL.SIDEBAR.MIN_WIDTH - 40,
  } = {},
) {
  const [width, setWidth] = useState(defaultWidth);
  const [collapsed, setCollapsed] = useState(false);
  const dragRef = useRef(null);

  const startDrag = useCallback(
    (e) => {
      e.preventDefault();
      const startX = e.clientX;
      const startWidth = collapsed ? 0 : width;

      const onMouseMove = (e2) => {
        const delta = side === 'left' ? e2.clientX - startX : startX - e2.clientX;
        const newWidth = Math.max(0, startWidth + delta);

        if (collapsible && newWidth < collapseThreshold) {
          setCollapsed(true);
          setWidth(minWidth);
        } else {
          setCollapsed(false);
          setWidth(Math.min(Math.max(newWidth, minWidth), maxWidth));
        }
      };

      const onMouseUp = () => {
        document.removeEventListener('mousemove', onMouseMove);
        document.removeEventListener('mouseup', onMouseUp);
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
      };

      document.body.style.cursor = 'col-resize';
      document.body.style.userSelect = 'none';
      document.addEventListener('mousemove', onMouseMove);
      document.addEventListener('mouseup', onMouseUp);

      dragRef.current = { startX, startWidth };
    },
    [width, collapsed, side, minWidth, maxWidth, collapsible, collapseThreshold],
  );

  const toggle = useCallback(() => {
    setCollapsed((c) => !c);
  }, []);

  return { width: collapsed ? 0 : width, collapsed, startDrag, toggle, setWidth };
}

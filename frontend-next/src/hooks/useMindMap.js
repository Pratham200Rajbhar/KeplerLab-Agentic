'use client';

import { useState, useEffect, useCallback, useMemo, useRef } from 'react';
import { getMindMap, generateMindMap } from '@/lib/api/mindmap';

/**
 * Manages mind map lifecycle: check cached → generate → regenerate.
 */
export default function useMindMap({ notebookId, selectedSources, onGenerated }) {
  const [status, setStatus] = useState('idle'); // idle | checking | generating | ready | error
  const [mapData, setMapData] = useState(null);
  const [isCanvasOpen, setIsCanvasOpen] = useState(false);
  const [errorMessage, setErrorMessage] = useState(null);
  const abortControllerRef = useRef(null);

  // Stabilize the selectedSources array reference
  const sourcesKey = useMemo(
    () => (selectedSources ? [...selectedSources].sort().join(',') : ''),
    [selectedSources],
  );
  const stableSources = useMemo(
    () => selectedSources || [],
    // eslint-disable-next-line react-hooks/exhaustive-deps
    [sourcesKey],
  );

  const sortedIds = (ids) => [...ids].sort().join(',');

  const checkAndGenerate = useCallback(async () => {
    if (!notebookId || stableSources.length === 0) {
      setStatus('idle');
      return;
    }

    setStatus('checking');
    setErrorMessage(null);

    try {
      const response = await getMindMap(notebookId);

      const savedIds = sortedIds(response.material_ids || []);
      const currentIds = sortedIds(stableSources);

      if (savedIds === currentIds) {
        setMapData(response);
        setStatus('ready');
        return;
      }
      // Stale — fall through to regenerate
    } catch (err) {
      const msg = (err.message || '').toLowerCase();
      if (!msg.includes('404') && !msg.includes('not found')) {
        setStatus('error');
        setErrorMessage(err.message || 'Failed to check saved mind map');
        return;
      }
    }

    // Generate new mind map
    setStatus('generating');
    abortControllerRef.current = new AbortController();
    try {
      const response = await generateMindMap({
        notebookId,
        materialIds: stableSources,
        signal: abortControllerRef.current.signal,
      });
      setMapData(response);
      setStatus('ready');
      onGenerated?.(response);
    } catch (err) {
      if (err.name === 'AbortError') {
        setStatus('idle');
        setErrorMessage(null);
      } else {
        setStatus('error');
        setErrorMessage(err.message || 'Failed to generate mind map');
      }
    } finally {
      abortControllerRef.current = null;
    }
  }, [notebookId, stableSources, onGenerated]);

  useEffect(() => {
    checkAndGenerate();
  }, [checkAndGenerate]);

  const cancel = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  const regenerate = useCallback(async () => {
    if (!notebookId || stableSources.length === 0) return;

    abortControllerRef.current?.abort();
    setStatus('generating');
    setErrorMessage(null);
    abortControllerRef.current = new AbortController();

    try {
      const response = await generateMindMap({
        notebookId,
        materialIds: stableSources,
        signal: abortControllerRef.current.signal,
      });
      setMapData(response);
      setStatus('ready');
      onGenerated?.(response);
    } catch (err) {
      if (err.name === 'AbortError') {
        setStatus('idle');
        setErrorMessage(null);
      } else {
        setStatus('error');
        setErrorMessage(err.message || 'Failed to regenerate mind map');
      }
    } finally {
      abortControllerRef.current = null;
    }
  }, [notebookId, stableSources, onGenerated]);

  const openCanvas = useCallback(() => setIsCanvasOpen(true), []);
  const closeCanvas = useCallback(() => setIsCanvasOpen(false), []);

  return {
    status,
    mapData,
    isCanvasOpen,
    errorMessage,
    cancel,
    regenerate,
    openCanvas,
    closeCanvas,
  };
}

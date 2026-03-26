'use client';

import { useState, useEffect, useCallback, useRef, memo } from 'react';
import { BookOpen, Loader2, RefreshCw } from 'lucide-react';
import { getEmptySuggestions } from '@/lib/api/chat';
import useAppStore from '@/stores/useAppStore';

const EmptyState = memo(function EmptyState({ onSend }) {
  const selectedSources = useAppStore((s) => s.selectedSources);
  const materials = useAppStore((s) => s.materials);

  const [topics, setTopics] = useState(null);
  const [suggestions, setSuggestions] = useState([]);
  const [loading, setLoading] = useState(true);

  const completedSelected = selectedSources.filter((id) => {
    const mat = materials.find((m) => m.id === id);
    return mat && mat.status === 'completed';
  });
  const hasResources = completedSelected.length > 0;

  const selectionKey = completedSelected.slice().sort().join(',');
  const prevKeyRef = useRef(null);

  const loadSuggestions = useCallback(async (ids) => {
    setLoading(true);
    try {
      const data = await getEmptySuggestions(ids);
      setTopics(data?.topics ?? null);
      setSuggestions(data?.suggestions ?? []);
    } catch {
      setTopics(null);
      setSuggestions(
        ids.length > 0
          ? [
              'Explain the main concept in these documents',
              'Summarize the key ideas from the materials',
              'What are the important topics in these files?',
              'Create flashcards from these resources',
            ]
          : [
              'Explain how neural networks work',
              'How does reinforcement learning work?',
              'What are the basics of data analysis?',
              'How can I build an AI model?',
            ],
      );
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (prevKeyRef.current === selectionKey) return;
    prevKeyRef.current = selectionKey;
    loadSuggestions(hasResources ? completedSelected : []);
  }, [selectionKey, loadSuggestions, hasResources, completedSelected]);

  const handleSuggestionClick = (text) => {
    onSend?.(text);
  };

  return (
    <div className="flex flex-col items-center justify-center flex-1 px-6 py-16 select-none overflow-y-auto">
      <div className="max-w-lg w-full">
        <div className="text-center mb-8">
          <h2 className="text-2xl font-semibold text-text-primary mb-2 tracking-tight">
            How can I help you?
          </h2>
          {!hasResources && (
            <p className="text-text-muted text-sm leading-relaxed">
              You can start by asking a question or exploring topics below.
            </p>
          )}
        </div>

        {hasResources && (
          <div
            className="rounded-xl border p-4 mb-6"
            style={{
              background: 'var(--surface-raised, rgba(255,255,255,0.04))',
              borderColor: 'rgba(255,255,255,0.07)',
            }}
          >
            <div className="flex items-center gap-2 mb-3">
              <div
                className="w-6 h-6 rounded-md flex items-center justify-center shrink-0"
                style={{ background: 'var(--accent-subtle)' }}
              >
                <BookOpen size={13} className="text-accent" />
              </div>
              <span className="text-sm font-medium text-text-primary">
                Selected Resources Overview
              </span>
              <div className="ml-auto flex items-center gap-1.5 shrink-0">
                <div className="w-1.5 h-1.5 bg-success rounded-full animate-pulse" />
                <span className="text-xs text-text-muted">
                  {completedSelected.length} source{completedSelected.length !== 1 ? 's' : ''}
                </span>
              </div>
            </div>

            {loading ? (
              <div className="flex items-center gap-2 text-sm text-text-muted">
                <Loader2 size={13} className="animate-spin" />
                <span>Analysing resources…</span>
              </div>
            ) : topics && topics.length > 0 ? (
              <div>
                <p className="text-xs text-text-muted mb-2">These documents appear to cover:</p>
                <ul className="space-y-1">
                  {topics.map((topic, i) => (
                    <li key={i} className="flex items-center gap-2 text-sm text-text-secondary">
                      <span className="w-1 h-1 rounded-full bg-accent shrink-0" />
                      {topic}
                    </li>
                  ))}
                </ul>
              </div>
            ) : (
              <p className="text-xs text-text-muted">
                {completedSelected.length > 1
                  ? `${completedSelected.length} sources ready to explore.`
                  : `Ready to explore ${
                      materials.find((m) => m.id === completedSelected[0])?.filename ||
                      'your source'
                    }.`}
              </p>
            )}
          </div>
        )}

        <div>
          <div className="flex items-center justify-between mb-3">
            <p className="text-xs font-medium text-text-muted uppercase tracking-wider">
              Suggested Questions
            </p>
            {!loading && (
              <button
                onClick={() => loadSuggestions(hasResources ? completedSelected : [])}
                className="text-xs text-text-muted hover:text-text-secondary transition-colors flex items-center gap-1"
                title="Refresh suggestions"
              >
                <RefreshCw size={11} />
                Refresh
              </button>
            )}
          </div>

          {loading ? (
            <div className="flex items-center gap-2 text-sm text-text-muted">
              <Loader2 size={13} className="animate-spin" />
              <span>Generating suggestions…</span>
            </div>
          ) : (
            <div className="flex flex-col gap-2">
              {suggestions.map((s, i) => (
                <button
                  key={i}
                  onClick={() => handleSuggestionClick(s)}
                  className="text-left px-4 py-2.5 rounded-lg border text-sm text-text-secondary hover:text-text-primary hover:bg-accent/5 transition-all"
                  style={{
                    background: 'var(--surface-raised, rgba(255,255,255,0.03))',
                    borderColor: 'rgba(255,255,255,0.06)',
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(var(--color-accent-rgb, 99,102,241),0.3)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)';
                  }}
                >
                  {s}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
});

export default EmptyState;

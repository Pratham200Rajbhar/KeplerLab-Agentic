'use client';

import { useState, useEffect, useCallback } from 'react';
import { Sparkles, Copy, Check, RefreshCw, Flame } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import { optimizePrompts } from '@/lib/api/chat';

function confidenceColor(score) {
  if (score >= 90) return { bar: 'bg-success', text: 'text-success' };
  if (score >= 70) return { bar: 'bg-warning', text: 'text-warning' };
  return { bar: 'bg-danger', text: 'text-danger' };
}

function PromptCard({ prompt, isBest, onUse }) {
  const [copied, setCopied] = useState(false);
  const colors = confidenceColor(prompt.confidence);

  const handleCopy = useCallback(() => {
    navigator.clipboard.writeText(prompt.optimized_prompt);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [prompt.optimized_prompt]);

  return (
    <div
      className="relative rounded-xl p-4 transition-colors"
      style={{
        background: isBest ? 'var(--accent-subtle)' : 'var(--surface-overlay)',
        border: `1px solid ${isBest ? 'var(--accent-border)' : 'var(--border)'}`,
      }}
    >
      {isBest && (
        <span
          className="absolute -top-2.5 right-3 inline-flex items-center gap-1 text-[11px] font-semibold px-2.5 py-0.5 rounded-full"
          style={{ background: 'var(--warning-subtle)', border: '1px solid var(--warning-light)', color: 'var(--warning)' }}
        >
          <Flame size={11} /> Best Match
        </span>
      )}

      <p className="text-sm leading-relaxed whitespace-pre-wrap mb-3" style={{ color: 'var(--text-primary)' }}>
        {prompt.optimized_prompt}
      </p>

      <div className="flex items-center gap-3 mb-2">
        <div className="flex-1 h-1.5 rounded-full overflow-hidden" style={{ background: 'var(--border-strong)' }}>
          <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${prompt.confidence}%` }} />
        </div>
        <span className={`text-xs font-semibold tabular-nums ${colors.text}`}>{prompt.confidence}%</span>
      </div>

      <p className="text-xs mb-4" style={{ color: 'var(--text-secondary)' }}>{prompt.explanation}</p>

      <div className="flex items-center gap-2">
        <button
          onClick={() => onUse(prompt.optimized_prompt)}
          className="px-3.5 py-1.5 text-xs font-semibold rounded-lg text-white transition-opacity hover:opacity-85"
          style={{ background: 'var(--accent)' }}
        >
          Use Prompt
        </button>
        <button
          onClick={handleCopy}
          className="px-3.5 py-1.5 text-xs font-medium rounded-lg inline-flex items-center gap-1.5 transition-colors hover:border-border-strong"
          style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
        >
          {copied ? <Check size={12} /> : <Copy size={12} />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  );
}

export default function PromptOptimizerDialog({ originalPrompt, onSelect, onClose }) {
  const [prompts, setPrompts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOptimized = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await optimizePrompts(originalPrompt, 4);
      setPrompts(data.prompts);
    } catch (err) {
      setError(err.message || 'Failed to optimize prompts');
    } finally {
      setLoading(false);
    }
  }, [originalPrompt]);

  useEffect(() => {
    fetchOptimized();
  }, [fetchOptimized]);

  const handleUse = useCallback(
    (text) => {
      onSelect(text);
      onClose();
    },
    [onSelect, onClose],
  );

  return (
    <Modal
      onClose={onClose}
      maxWidth="2xl"
      title="Prompt Optimizer"
      icon={<Sparkles size={16} style={{ color: 'var(--accent)' }} />}
      footer={
        <div className="flex items-center justify-between">
          <button
            onClick={fetchOptimized}
            disabled={loading}
            className="inline-flex items-center gap-2 text-xs font-medium px-3.5 py-1.5 rounded-lg transition-colors disabled:opacity-40"
            style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Regenerate
          </button>
          <button
            onClick={onClose}
            className="text-xs font-medium px-3.5 py-1.5 rounded-lg transition-colors"
            style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
          >
            Cancel
          </button>
        </div>
      }
    >
      <div className="space-y-4">
        {/* Original prompt */}
        <div className="rounded-lg p-3" style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)' }}>
          <p className="text-[11px] uppercase tracking-widest font-semibold mb-1" style={{ color: 'var(--text-secondary)' }}>
            Original Prompt
          </p>
          <p className="text-sm" style={{ color: 'var(--text-primary)' }}>{originalPrompt}</p>
        </div>

        <p className="text-[11px] uppercase tracking-widest font-semibold" style={{ color: 'var(--text-secondary)' }}>
          Choose the best optimized prompt
        </p>

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-12 gap-3">
            <RefreshCw size={22} className="animate-spin" style={{ color: 'var(--accent)' }} />
            <p className="text-sm" style={{ color: 'var(--text-secondary)' }}>Optimizing your prompt…</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="text-center py-10">
            <p className="text-sm mb-3" style={{ color: 'var(--danger)' }}>{error}</p>
            <button
              onClick={fetchOptimized}
              className="text-xs font-medium px-3.5 py-1.5 rounded-lg transition-colors"
              style={{ background: 'var(--surface-overlay)', border: '1px solid var(--border)', color: 'var(--text-secondary)' }}
            >
              Try Again
            </button>
          </div>
        )}

        {/* Cards */}
        {!loading && !error && prompts && (
          <div className="space-y-3">
            {prompts.map((p, idx) => (
              <PromptCard key={idx} prompt={p} isBest={idx === 0} onUse={handleUse} />
            ))}
          </div>
        )}
      </div>
    </Modal>
  );
}

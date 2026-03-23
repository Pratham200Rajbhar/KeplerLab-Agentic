'use client';

import { useState, useEffect, useCallback } from 'react';
import { Sparkles, Copy, Check, RefreshCw, Flame } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import { optimizePrompts } from '@/lib/api/chat';

function confidenceColor(score) {
  if (score >= 90) return { bar: 'bg-[#10B981]', text: 'text-[#10B981]' };
  if (score >= 70) return { bar: 'bg-[#F59E0B]', text: 'text-[#F59E0B]' };
  return { bar: 'bg-[#EF4444]', text: 'text-[#EF4444]' };
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
      className={`relative rounded-xl p-5 transition-all duration-200 border ${
        isBest
          ? 'bg-[#1A1A1C] border-[#10B981]/30 shadow-[0_0_15px_rgba(16,185,129,0.05)]'
          : 'bg-[#131415] border-[#2A2A2E] hover:border-[#3A3A3E]'
      }`}
    >
      {isBest && (
        <span className="absolute -top-3 right-4 inline-flex items-center gap-1.5 text-[10px] uppercase font-bold tracking-wider px-2.5 py-1 rounded-full bg-[#10B981]/15 text-[#10B981] border border-[#10B981]/20">
          <Flame size={12} fill="currentColor" className="opacity-80" /> Best Match
        </span>
      )}

      <p className="text-[13px] leading-relaxed whitespace-pre-wrap mb-4 font-medium text-[#EDEDED]">
        {prompt.optimized_prompt}
      </p>

      <div className="flex items-center gap-3 mb-3">
        <div className="flex-1 h-1.5 rounded-full bg-[#2A2A2E] overflow-hidden">
          <div className={`h-full rounded-full ${colors.bar}`} style={{ width: `${prompt.confidence}%` }} />
        </div>
        <span className={`text-[11px] font-bold tabular-nums tracking-wide ${colors.text}`}>
          {prompt.confidence}% CONFIDENCE
        </span>
      </div>

      <p className="text-[12px] leading-snug mb-5 text-[#A1A1AA]">
        {prompt.explanation}
      </p>

      <div className="flex items-center gap-2.5">
        <button
          onClick={() => onUse(prompt.optimized_prompt)}
          className="flex-1 py-2 text-xs font-semibold rounded-lg bg-[#E4E4E6] text-[#131314] hover:bg-white transition-colors"
        >
          Use This Prompt
        </button>
        <button
          onClick={handleCopy}
          className="px-4 py-2 text-xs font-medium rounded-lg inline-flex items-center justify-center gap-2 bg-[#2A2A2E] text-[#EDEDED] border border-[#3A3A3E] hover:bg-[#323236] transition-colors"
        >
          {copied ? <Check size={14} className="text-[#10B981]" /> : <Copy size={14} className="opacity-70" />}
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </div>
  );
}

export default function PromptOptimizerDialog({ originalPrompt, materialIds, onSelect, onClose }) {
  const [prompts, setPrompts] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchOptimized = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await optimizePrompts(originalPrompt, 4, materialIds);
      setPrompts(data.prompts);
    } catch (err) {
      setError(err.message || 'Failed to optimize prompts');
    } finally {
      setLoading(false);
    }
  }, [originalPrompt, materialIds]);

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
      icon={<Sparkles size={16} className="text-[#10B981]" />}
      footer={
        <div className="flex items-center justify-between w-full">
          <button
            onClick={fetchOptimized}
            disabled={loading}
            className="inline-flex items-center gap-2 text-xs font-semibold px-4 py-2 rounded-lg transition-colors border border-[#2A2A2E] bg-[#131415] text-[#A1A1AA] hover:bg-[#1A1A1C] hover:text-[#EDEDED] disabled:opacity-40"
          >
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
            Regenerate
          </button>
          <button
            onClick={onClose}
            className="text-xs font-semibold px-4 py-2 rounded-lg transition-colors bg-[#2A2A2E] text-[#EDEDED] border border-[#3A3A3E] hover:bg-[#323236]"
          >
            Cancel
          </button>
        </div>
      }
    >
      <div className="space-y-6">
        {/* Original prompt */}
        <div className="rounded-xl p-4 bg-[#131415] border border-[#2A2A2E]">
          <p className="text-[10px] uppercase tracking-widest font-bold mb-2 text-[#71717A]">
            Original Prompt
          </p>
          <p className="text-[13px] text-[#EDEDED] leading-relaxed">
            {originalPrompt}
          </p>
        </div>

        <div className="relative">
          <div className="absolute inset-0 flex items-center" aria-hidden="true">
            <div className="w-full border-t border-[#2A2A2E]" />
          </div>
          <div className="relative flex justify-center">
            <span className="bg-[#1A1A1C] px-3 text-[10px] uppercase tracking-widest font-bold text-[#A1A1AA]">
              Optimized Suggestions
            </span>
          </div>
        </div>

        {/* Loading */}
        {loading && (
          <div className="flex flex-col items-center justify-center py-16 gap-4">
            <RefreshCw size={24} className="animate-spin text-[#10B981]" />
            <p className="text-sm text-[#A1A1AA] font-medium">Analyzing context and optimizing your prompt…</p>
          </div>
        )}

        {/* Error */}
        {error && !loading && (
          <div className="text-center py-12 bg-[#131415] rounded-xl border border-[#EF4444]/20">
            <p className="text-[13px] mb-4 text-[#EF4444] font-medium">{error}</p>
            <button
              onClick={fetchOptimized}
              className="text-xs font-semibold px-4 py-2 rounded-lg transition-colors border border-[#EF4444]/30 bg-[#EF4444]/10 text-[#EF4444] hover:bg-[#EF4444]/20"
            >
              Try Again
            </button>
          </div>
        )}

        {/* Cards */}
        {!loading && !error && prompts && prompts.length > 0 && (
          <div className="space-y-4">
            {prompts.map((p, idx) => (
              <PromptCard key={idx} prompt={p} isBest={idx === 0} onUse={handleUse} />
            ))}
          </div>
        )}

        {!loading && !error && prompts && prompts.length === 0 && (
          <div className="text-center py-12 bg-[#131415] rounded-xl border border-[#2A2A2E]">
            <p className="text-[13px] text-[#A1A1AA] font-medium">No optimizations could be verified for this prompt.</p>
          </div>
        )}
      </div>
    </Modal>
  );
}

'use client';

import { useState } from 'react';
import { Loader2, Sparkles, Wand2 } from 'lucide-react';
import Modal from '@/components/ui/Modal';

export default function SkillAIDraftDialog({
  isOpen,
  isLoading,
  onClose,
  onGenerate,
}) {
  const [prompt, setPrompt] = useState('');

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!prompt.trim()) return;
    await onGenerate?.(prompt.trim());
  };

  const footer = (
    <div className="flex items-center justify-end gap-2">
      <button
        type="button"
        onClick={onClose}
        className="skills-btn-secondary px-4 py-2 rounded-lg text-sm"
      >
        Cancel
      </button>
      <button
        type="submit"
        form="skill-ai-draft-form"
        disabled={!prompt.trim() || isLoading}
        className="skills-btn-primary inline-flex items-center gap-1.5 px-4 py-2 rounded-lg text-sm font-semibold disabled:opacity-50"
      >
        {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
        Generate
      </button>
    </div>
  );

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      maxWidth="lg"
      title="AI Skill Builder"
      icon={<Wand2 className="w-4 h-4 text-accent" />}
      footer={footer}
    >
      <form id="skill-ai-draft-form" onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label className="studio-dialog-v3-label block mb-1.5">Describe your skill goal</label>
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            rows={5}
            placeholder="Example: Create a skill that turns my uploaded material into last-minute exam notes with key points, mnemonics, and likely questions."
            className="studio-dialog-v3-textarea"
            required
          />
          <p className="text-[11px] text-text-muted mt-2">
            AI will decide the right workflow and number of steps.
          </p>
        </div>
      </form>
    </Modal>
  );
}

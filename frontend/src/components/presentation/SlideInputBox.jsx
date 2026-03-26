import { useState } from 'react';
import useAppStore from '@/stores/useAppStore';

export default function SlideInputBox({ onSubmit, loading }) {
  const [instruction, setInstruction] = useState('');
  const presentationUpdateProgress = useAppStore(s => s.presentationUpdateProgress);

  const handleSubmit = (e) => {
    e.preventDefault();
    const value = instruction.trim();
    if (!value || loading) return;
    onSubmit(value);
    setInstruction('');
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-2">
      <label className="text-xs text-[var(--text-muted)]">Edit with AI instruction</label>
      <textarea
        value={instruction}
        onChange={(e) => setInstruction(e.target.value)}
        rows={4}
        placeholder="add more images and simplify slide 3 bullets"
        className="w-full min-h-[110px] rounded-lg border border-[var(--border)] bg-[var(--surface)] p-3 text-sm resize-none"
      />
      <button
        type="submit"
        disabled={loading || !instruction.trim()}
        className="w-full py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium disabled:opacity-50"
      >
        {loading ? (presentationUpdateProgress || 'Updating...') : 'Apply Instruction'}
      </button>
    </form>
  );
}

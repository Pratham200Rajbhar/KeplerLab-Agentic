'use client';

import { useState } from 'react';
import Modal from '@/components/ui/Modal';
import { X } from 'lucide-react';

export default function HistoryRenameModal({ item, onConfirm, onClose }) {
  const [title, setTitle] = useState(item?.title || '');

  const handleSubmit = (e) => {
    e.preventDefault();
    if (title.trim()) {
      onConfirm(title.trim());
    }
  };

  return (
    <Modal onClose={onClose} maxWidth="sm">
      <form onSubmit={handleSubmit}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">Rename</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors" aria-label="Close rename dialog">
            <X className="w-4 h-4 text-[var(--text-muted)]" />
          </button>
        </div>

        <div className="p-5">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter a new title"
            autoFocus
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[var(--border)]">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim()}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </form>
    </Modal>
  );
}

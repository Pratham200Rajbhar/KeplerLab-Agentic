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
        <div className="flex items-center justify-between px-5 py-4 border-b border-(--border)">
          <h3 className="text-sm font-semibold text-(--text-primary)">Rename</h3>
          <button type="button" onClick={onClose} className="p-1 rounded-lg hover:bg-(--surface-overlay) transition-colors">
            <X className="w-4 h-4 text-(--text-muted)" />
          </button>
        </div>

        <div className="p-5">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Enter a new title"
            autoFocus
            className="w-full px-3 py-2 text-sm rounded-lg bg-(--surface) border border-(--border) text-(--text-primary) placeholder:text-(--text-muted) focus:outline-none focus:ring-1 focus:ring-(--accent)"
          />
        </div>

        <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-(--border)">
          <button type="button" onClick={onClose} className="px-4 py-2 text-sm text-(--text-secondary) hover:text-(--text-primary) transition-colors">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim()}
            className="px-4 py-2 text-sm font-medium rounded-lg bg-(--accent) text-white hover:bg-(--accent-light) transition-colors disabled:opacity-40"
          >
            Save
          </button>
        </div>
      </form>
    </Modal>
  );
}

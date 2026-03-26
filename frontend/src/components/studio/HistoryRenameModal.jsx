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
      <form onSubmit={handleSubmit} className="studio-dialog-v3">
        <div className="studio-dialog-v3-header">
          <div className="studio-dialog-v3-icon">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>edit_note</span>
          </div>
          <div>
            <h3 className="studio-dialog-v3-title">Rename Item</h3>
            <p className="studio-dialog-v3-subtitle">Give this generation a clear, memorable title</p>
          </div>
          <button type="button" onClick={onClose} className="studio-dialog-v3-close" aria-label="Close rename dialog">
            <X className="w-4 h-4" />
          </button>
        </div>

        <div className="studio-dialog-v3-body">
          <div className="studio-dialog-v3-grid">
            <div className="studio-dialog-v3-section">
              <div className="studio-dialog-v3-label-row">
                <label className="studio-dialog-v3-label">Title</label>
              </div>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder="Enter a new title"
                autoFocus
                className="studio-dialog-v3-input"
              />
            </div>
          </div>
        </div>

        <div className="studio-dialog-v3-footer">
          <button type="button" onClick={onClose} className="studio-dialog-v3-btn ghost">
            Cancel
          </button>
          <button
            type="submit"
            disabled={!title.trim()}
            className="studio-dialog-v3-btn primary"
          >
            Save
          </button>
        </div>
      </form>
    </Modal>
  );
}

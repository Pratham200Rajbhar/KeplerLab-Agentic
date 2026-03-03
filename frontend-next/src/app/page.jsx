'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/stores/useAuthStore';
import { useToast } from '@/stores/useToastStore';
import { getNotebooks, deleteNotebook, updateNotebook } from '@/lib/api/notebooks';
import { formatRelativeDate } from '@/lib/utils/helpers';
import { useTheme } from 'next-themes';
import {
  Layers,
  Sun,
  Moon,
  LogOut,
  Plus,
  BookOpen,
  MoreVertical,
  Pencil,
  Trash2,
  X,
  Sparkles,
  ArrowRight,
} from 'lucide-react';

/* ═══════════════════════════════════════════════════════
   HOME / DASHBOARD — Production-grade layout
   ═══════════════════════════════════════════════════════ */

export default function HomePage() {
  const { user, logout, isAuthenticated, isLoading } = useAuthStore();
  const { theme, setTheme } = useTheme();
  const isDark = theme === 'dark';
  const toggleTheme = () => setTheme(isDark ? 'light' : 'dark');
  const router = useRouter();
  const toast = useToast();

  const [notebooks, setNotebooks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [showMenu, setShowMenu] = useState(false);
  const [activeMenu, setActiveMenu] = useState(null);
  const [editingNotebook, setEditingNotebook] = useState(null);
  const [editName, setEditName] = useState('');
  const [editDescription, setEditDescription] = useState('');
  const [saving, setSaving] = useState(false);
  const [deletingNotebook, setDeletingNotebook] = useState(null);
  const menuRef = useRef(null);

  /* ── Data Loading ── */
  const loadNotebooks = useCallback(async () => {
    try {
      setError(null);
      const data = await getNotebooks();
      setNotebooks(data);
    } catch (err) {
      console.error('Failed to load notebooks:', err);
      setError('Failed to load notebooks. Please try again.');
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (!isLoading && !isAuthenticated) {
      router.replace('/auth');
      return;
    }
    if (!isLoading && isAuthenticated) loadNotebooks();
  }, [isAuthenticated, isLoading, loadNotebooks, router]);

  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  /* ── Actions ── */
  const handleDelete = (notebookId, e) => {
    e?.stopPropagation();
    setActiveMenu(null);
    setDeletingNotebook(notebookId);
  };

  const confirmDelete = async () => {
    const id = deletingNotebook;
    setDeletingNotebook(null);
    if (!id) return;
    try {
      await deleteNotebook(id);
      setNotebooks((prev) => prev.filter((n) => n.id !== id));
    } catch {
      toast.error('Failed to delete notebook.');
    }
  };

  const openRenameModal = (notebook, e) => {
    e?.stopPropagation();
    setActiveMenu(null);
    setEditingNotebook(notebook);
    setEditName(notebook.name);
    setEditDescription(notebook.description || '');
  };

  const handleLogout = async () => {
    setShowMenu(false);
    await logout();
    router.replace('/auth');
  };

  const handleRename = async (e) => {
    e?.preventDefault();
    if (!editName.trim()) return;
    setSaving(true);
    try {
      const updated = await updateNotebook(editingNotebook.id, editName.trim(), editDescription.trim() || null);
      setNotebooks((prev) => prev.map((n) => (n.id === editingNotebook.id ? updated : n)));
      setEditingNotebook(null);
    } catch {
      toast.error('Failed to rename notebook.');
    }
    setSaving(false);
  };

  const userInitial = user?.username?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'U';

  /* ── Loading & Auth Guards ── */
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--surface)' }}>
        <div className="loading-spinner w-6 h-6" />
      </div>
    );
  }
  if (!isAuthenticated) return null;

  /* ═══ RENDER ═══ */
  return (
    <div className="min-h-screen" style={{ background: 'var(--surface)' }}>
      {/* Ambient gradient glow */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-[600px] z-0"
        style={{ background: 'radial-gradient(ellipse 60% 40% at 50% -10%, rgba(16,185,129,0.06) 0%, transparent 70%)' }}
      />

      {/* ── Header ── */}
      <header
        className="z-30 sticky top-0 flex items-center justify-between h-14 px-6"
        style={{
          background: 'rgba(10,10,11,0.7)',
          backdropFilter: 'blur(16px) saturate(180%)',
          WebkitBackdropFilter: 'blur(16px) saturate(180%)',
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'var(--accent)' }}>
            <Layers className="w-4 h-4" style={{ color: 'var(--text-inverse)' }} />
          </div>
          <span className="text-sm font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>KeplerLab</span>
        </div>

        <div className="flex items-center gap-1">
          <button onClick={toggleTheme} className="btn-icon-sm" title={isDark ? 'Light mode' : 'Dark mode'}>
            {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          <div className="relative" ref={menuRef}>
            <button
              onClick={() => setShowMenu(!showMenu)}
              className="w-8 h-8 rounded-lg flex items-center justify-center text-xs font-semibold ml-1 transition-colors duration-200"
              style={{
                background: 'var(--accent-subtle)',
                color: 'var(--accent)',
                border: '1px solid var(--accent-border)',
              }}
            >
              {userInitial}
            </button>

            {showMenu && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setShowMenu(false)} />
                <div
                  className="absolute right-0 top-full mt-2 w-56 rounded-xl overflow-hidden z-50 animate-scale-in"
                  style={{
                    background: 'var(--surface-raised)',
                    border: '1px solid var(--border-strong)',
                    boxShadow: 'var(--shadow-glass)',
                  }}
                >
                  <div className="px-4 py-3 border-b" style={{ borderColor: 'var(--border)', background: 'var(--surface-overlay)' }}>
                    <p className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{user?.username || 'User'}</p>
                    <p className="text-xs truncate" style={{ color: 'var(--text-muted)' }}>{user?.email}</p>
                  </div>
                  <div className="p-1.5">
                    <button
                      onClick={handleLogout}
                      className="w-full px-3 py-2 text-left text-sm rounded-lg flex items-center gap-3 transition-colors duration-200"
                      style={{ color: 'var(--danger)' }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--danger-subtle)')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      <LogOut className="w-4 h-4" />
                      Sign out
                    </button>
                  </div>
                </div>
              </>
            )}
          </div>
        </div>
      </header>

      {/* ── Main Content ── */}
      <main className="relative z-10 max-w-[1200px] mx-auto px-6 pt-10 pb-16">
        {/* Hero */}
        <section className="mb-10">
          <div
            className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium mb-4"
            style={{
              background: 'var(--accent-subtle)',
              color: 'var(--accent)',
              border: '1px solid var(--accent-border)',
            }}
          >
            <Sparkles className="w-3 h-3" />
            AI-powered workspace
          </div>
          <h1
            className="text-3xl md:text-4xl font-semibold tracking-tight mb-2"
            style={{ color: 'var(--text-primary)', lineHeight: 1.2 }}
          >
            Welcome back{user?.username ? `, ${user.username}` : ''}
          </h1>
          <p className="text-sm max-w-md" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Upload documents, generate study materials, and explore ideas with AI.
          </p>
        </section>

        {/* Section Header */}
        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              My Notebooks
            </h2>
            <span
              className="text-2xs px-2 py-0.5 rounded-md font-medium"
              style={{ background: 'var(--surface-overlay)', color: 'var(--text-muted)' }}
            >
              {notebooks.length}
            </span>
          </div>
        </div>

        {/* Content States */}
        {loading ? (
          <div className="flex items-center justify-center py-24">
            <div className="loading-spinner w-6 h-6" />
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center py-24 gap-4">
            <p className="text-sm" style={{ color: 'var(--text-muted)' }}>{error}</p>
            <button onClick={loadNotebooks} className="btn-primary text-sm px-5 py-2">Retry</button>
          </div>
        ) : notebooks.length === 0 ? (
          /* Empty State */
          <div className="mt-20 text-center">
            <div
              className="w-16 h-16 mx-auto mb-5 rounded-2xl flex items-center justify-center"
              style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}
            >
              <Sparkles className="w-7 h-7" style={{ color: 'var(--accent)' }} />
            </div>
            <h3 className="text-lg font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>
              Create your first notebook
            </h3>
            <p className="text-sm mb-6 max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
              Upload documents and let AI help you study, research, and create content.
            </p>
            <button
              onClick={() => router.push('/notebook/draft')}
              className="btn-primary inline-flex items-center gap-2"
            >
              Get started
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {/* New Notebook Card */}
            <button
              onClick={() => router.push('/notebook/draft')}
              className="notebook-card border-dashed flex flex-col items-center justify-center gap-3 group cursor-pointer transition-all duration-200"
              style={{ borderColor: 'var(--border-strong)' }}
              onMouseEnter={(e) => (e.currentTarget.style.borderColor = 'var(--accent-border)')}
              onMouseLeave={(e) => (e.currentTarget.style.borderColor = 'var(--border-strong)')}
            >
              <div
                className="w-10 h-10 rounded-xl flex items-center justify-center transition-all duration-300"
                style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}
              >
                <Plus className="w-5 h-5" style={{ color: 'var(--accent)' }} />
              </div>
              <div className="text-center">
                <span className="text-sm font-medium block" style={{ color: 'var(--text-secondary)' }}>
                  New notebook
                </span>
                <span className="text-2xs mt-0.5 block" style={{ color: 'var(--text-muted)' }}>
                  Start a new project
                </span>
              </div>
            </button>

            {/* Existing Notebooks */}
            {notebooks.map((notebook, i) => (
              <div
                key={notebook.id}
                onClick={() => router.push(`/notebook/${notebook.id}`)}
                className="notebook-card group cursor-pointer animate-fade-up"
                style={{ animationDelay: `${i * 30}ms`, animationFillMode: 'backwards' }}
              >
                <div className="flex-1 p-4 flex flex-col">
                  <div
                    className="w-9 h-9 rounded-lg flex items-center justify-center mb-auto"
                    style={{
                      background: 'var(--accent-subtle)',
                      border: '1px solid var(--accent-border)',
                    }}
                  >
                    <BookOpen className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                  </div>
                  <div className="mt-auto pt-3">
                    <h3 className="font-medium text-sm truncate" style={{ color: 'var(--text-primary)' }}>
                      {notebook.name}
                    </h3>
                    {notebook.description && (
                      <p className="text-xs truncate mt-0.5" style={{ color: 'var(--text-muted)' }}>
                        {notebook.description}
                      </p>
                    )}
                    <p className="text-2xs mt-2 opacity-50" style={{ color: 'var(--text-muted)' }}>
                      {formatRelativeDate(notebook.updated_at)}
                    </p>
                  </div>
                </div>

                {/* Context Menu Trigger */}
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setActiveMenu(activeMenu === notebook.id ? null : notebook.id);
                  }}
                  className="absolute top-3 right-3 p-1.5 rounded-lg opacity-0 group-hover:opacity-100 transition-all duration-200"
                  style={{ background: 'var(--surface-overlay)', color: 'var(--text-muted)' }}
                >
                  <MoreVertical className="w-3.5 h-3.5" />
                </button>

                {/* Context Menu Dropdown */}
                {activeMenu === notebook.id && (
                  <>
                    <div className="fixed inset-0 z-40" onClick={(e) => { e.stopPropagation(); setActiveMenu(null); }} />
                    <div
                      className="absolute top-10 right-3 w-36 rounded-lg overflow-hidden z-50 animate-scale-in"
                      style={{
                        background: 'var(--surface-raised)',
                        border: '1px solid var(--border-strong)',
                        boxShadow: 'var(--shadow-glass)',
                      }}
                    >
                      <div className="p-1">
                        <button
                          onClick={(e) => openRenameModal(notebook, e)}
                          className="w-full px-3 py-2 text-left text-sm rounded-md flex items-center gap-2.5 transition-colors duration-200"
                          style={{ color: 'var(--text-secondary)' }}
                          onMouseEnter={(e) => { e.currentTarget.style.background = 'var(--accent-subtle)'; e.currentTarget.style.color = 'var(--accent)'; }}
                          onMouseLeave={(e) => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
                        >
                          <Pencil className="w-3.5 h-3.5" />
                          Rename
                        </button>
                        <button
                          onClick={(e) => handleDelete(notebook.id, e)}
                          className="w-full px-3 py-2 text-left text-sm rounded-md flex items-center gap-2.5 transition-colors duration-200"
                          style={{ color: 'var(--danger)' }}
                          onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--danger-subtle)')}
                          onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                          Delete
                        </button>
                      </div>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        )}
      </main>

      {/* ── Rename Modal ── */}
      {editingNotebook && (
        <div className="modal-backdrop" onClick={() => setEditingNotebook(null)}>
          <div className="modal w-full max-w-md mx-4 animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-header">
              <h3 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Rename Notebook</h3>
              <button onClick={() => setEditingNotebook(null)} className="btn-icon-sm">
                <X className="w-4 h-4" />
              </button>
            </div>
            <form onSubmit={handleRename} className="modal-body space-y-4">
              <div>
                <label className="form-label">Notebook Name</label>
                <input
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                  placeholder="Notebook name"
                  className="input w-full"
                  autoFocus
                  required
                />
              </div>
              <div>
                <label className="form-label">
                  Description <span className="form-label-hint">(optional)</span>
                </label>
                <textarea
                  value={editDescription}
                  onChange={(e) => setEditDescription(e.target.value)}
                  placeholder="Brief description..."
                  rows={2}
                  className="textarea w-full"
                />
              </div>
            </form>
            <div className="modal-footer">
              <button onClick={() => setEditingNotebook(null)} className="btn-secondary">Cancel</button>
              <button onClick={handleRename} disabled={saving || !editName.trim()} className="btn-primary">
                {saving ? 'Saving...' : 'Save'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Delete Confirmation ── */}
      {deletingNotebook && (
        <div className="modal-backdrop" onClick={() => setDeletingNotebook(null)}>
          <div className="modal w-full max-w-sm mx-4 animate-scale-in" onClick={(e) => e.stopPropagation()}>
            <div className="modal-body py-8 text-center">
              <div
                className="w-12 h-12 mx-auto mb-4 rounded-2xl flex items-center justify-center"
                style={{ background: 'var(--danger-subtle)', border: '1px solid var(--danger-border)' }}
              >
                <Trash2 className="w-5 h-5" style={{ color: 'var(--danger)' }} />
              </div>
              <h3 className="text-base font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>Delete notebook?</h3>
              <p className="text-sm max-w-xs mx-auto" style={{ color: 'var(--text-secondary)' }}>
                This will permanently delete the notebook and all its materials.
              </p>
            </div>
            <div className="modal-footer justify-center gap-3">
              <button onClick={() => setDeletingNotebook(null)} className="btn-secondary">Cancel</button>
              <button
                onClick={confirmDelete}
                className="btn px-4 py-2 text-sm font-medium rounded-xl transition-colors"
                style={{ background: 'var(--danger-subtle)', color: 'var(--danger)' }}
                onMouseEnter={(e) => (e.currentTarget.style.background = 'var(--danger-border)')}
                onMouseLeave={(e) => (e.currentTarget.style.background = 'var(--danger-subtle)')}
              >
                Delete
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

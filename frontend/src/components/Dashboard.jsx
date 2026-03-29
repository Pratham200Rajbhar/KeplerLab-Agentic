'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import useAuthStore from '@/stores/useAuthStore';
import { useToast } from '@/stores/useToastStore';
import { getNotebooks, deleteNotebook, updateNotebook, ensureNotebookThumbnail } from '@/lib/api/notebooks';
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
  Activity,
  Clock3,
  FolderOpen,
  ArrowUpRight,
  ImageIcon,
  BrainCircuit,
} from 'lucide-react';


export default function Dashboard() {
  const { user, logout, isAuthenticated, isLoading } = useAuthStore();
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
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
  const [failedThumbnails, setFailedThumbnails] = useState({});
  const menuRef = useRef(null);
  const thumbnailInFlightRef = useRef(new Set());
  const hydratedNotebookIdsRef = useRef(new Set());

  
  const hydrateNotebookThumbnails = useCallback(async (sourceNotebooks) => {
    const pending = sourceNotebooks.filter(
      (n) =>
        !n.thumbnail_url &&
        !thumbnailInFlightRef.current.has(n.id) &&
        !hydratedNotebookIdsRef.current.has(n.id)
    ).slice(0, 4);
    if (!pending.length) return;

    const runOne = async (notebook) => {
      thumbnailInFlightRef.current.add(notebook.id);
      try {
        const thumbnail = await ensureNotebookThumbnail(notebook.id);
        hydratedNotebookIdsRef.current.add(notebook.id);
        if (!thumbnail?.thumbnail_url) return;
        setNotebooks((prev) =>
          prev.map((item) =>
            item.id === notebook.id
              ? {
                  ...item,
                  thumbnail_url: thumbnail.thumbnail_url,
                  thumbnail_query: thumbnail.thumbnail_query || item.thumbnail_query,
                }
              : item
          )
        );
      } catch (err) {
        console.warn('Thumbnail generation failed for notebook:', notebook.id, err);
      } finally {
        thumbnailInFlightRef.current.delete(notebook.id);
      }
    };

    const workers = [[], []];
    pending.forEach((item, index) => {
      workers[index % workers.length].push(item);
    });

    await Promise.all(
      workers.map(async (batch) => {
        for (const notebook of batch) {
          // Run a small bounded queue to avoid request spikes.
          await runOne(notebook);
        }
      })
    );
  }, []);

  const loadNotebooks = useCallback(async () => {
    try {
      const data = await getNotebooks();
      setError(null);
      setNotebooks(data);
      hydrateNotebookThumbnails(data);
    } catch (err) {
      console.error('Failed to load notebooks:', err);
      setError('Failed to load notebooks. Please try again.');
    } finally {
      setLoading(false);
    }
  }, [hydrateNotebookThumbnails]);

  useEffect(() => {
    if (isLoading) return;
    if (!isAuthenticated) {
      router.replace('/auth');
      return;
    }
    
    loadNotebooks();
  }, [isAuthenticated, isLoading, loadNotebooks, router]);

  useEffect(() => {
    const handler = (e) => {
      if (menuRef.current && !menuRef.current.contains(e.target)) setShowMenu(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  useEffect(() => {
    const handleNotebookNameUpdate = (e) => {
      const { id, name } = e.detail;
      setNotebooks((prev) =>
        prev.map((n) => (n.id === id ? { ...n, name } : n))
      );
    };

    window.addEventListener('notebookNameUpdate', handleNotebookNameUpdate);
    return () => {
      window.removeEventListener('notebookNameUpdate', handleNotebookNameUpdate);
    };
  }, []);

  
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

  const handleThumbnailError = useCallback((notebookId) => {
    setFailedThumbnails((prev) => {
      if (prev[notebookId]) return prev;
      return { ...prev, [notebookId]: true };
    });
  }, []);

  const sortedNotebooks = [...notebooks].sort(
    (a, b) => new Date(b.updated_at || 0).getTime() - new Date(a.updated_at || 0).getTime()
  );
  const latestNotebook = sortedNotebooks[0] || null;
  const activeTodayCount = notebooks.filter((n) => {
    const updated = new Date(n.updated_at || 0).getTime();
    return Number.isFinite(updated) && Date.now() - updated < 24 * 60 * 60 * 1000;
  }).length;

  
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--surface)' }}>
        <div className="loading-spinner w-6 h-6" />
      </div>
    );
  }
  if (!isAuthenticated) return null;

  
  return (
    <div className="min-h-screen" style={{ background: 'var(--surface)' }}>
      {/* Background Graphic */}
      <div
        className="pointer-events-none fixed inset-x-0 top-0 h-[600px] z-0"
        style={{ background: 'radial-gradient(ellipse 60% 40% at 50% -10%, rgba(16,185,129,0.06) 0%, transparent 70%)' }}
      />

      {/* Header */}
      <header
        className="z-30 sticky top-0"
        style={{
          background: isDark ? 'rgba(11,14,19,0.72)' : 'rgba(248,250,252,0.84)',
          backdropFilter: 'blur(18px) saturate(160%)',
          WebkitBackdropFilter: 'blur(18px) saturate(160%)',
          borderBottom: '1px solid var(--border)',
          boxShadow: isDark ? '0 10px 30px rgba(0,0,0,0.2)' : '0 10px 28px rgba(15,23,42,0.07)',
        }}
      >
        <div className="max-w-[1280px] mx-auto px-5 md:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div
              className="w-9 h-9 rounded-xl flex items-center justify-center shadow-sm"
              style={{
                background: 'linear-gradient(135deg, var(--accent), color-mix(in srgb, var(--accent) 70%, #ffffff 30%))',
              }}
            >
              <Layers className="w-4 h-4" style={{ color: 'var(--text-inverse)' }} />
            </div>
            <div className="flex flex-col leading-tight">
              <span className="text-[15px] font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>KeplerLab</span>
              <span className="text-[11px]" style={{ color: 'var(--text-muted)' }}>AI Workspace</span>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button onClick={toggleTheme} className="btn-icon-sm" title={isDark ? 'Light mode' : 'Dark mode'}>
              {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <div className="relative" ref={menuRef}>
              <button
                onClick={() => setShowMenu(!showMenu)}
                className="w-9 h-9 rounded-xl flex items-center justify-center text-xs font-semibold ml-1 transition-colors duration-200"
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
        </div>
      </header>

      {/* Main Content */}
      <main className="relative z-10 max-w-[1280px] mx-auto px-5 md:px-8 pt-8 pb-16">
        <section className="grid lg:grid-cols-[1.45fr_1fr] gap-4 mb-8">
          <div
            className="rounded-3xl p-5 md:p-6"
            style={{
              background:
                'radial-gradient(120% 140% at -10% -20%, rgba(16,185,129,0.14), transparent 58%), linear-gradient(160deg, color-mix(in srgb, var(--surface-raised) 86%, transparent), color-mix(in srgb, var(--surface-overlay) 72%, transparent))',
              border: '1px solid var(--border-strong)',
              boxShadow: 'var(--shadow-card, 0 10px 30px rgba(0,0,0,0.2))',
            }}
          >
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
              style={{ color: 'var(--text-primary)', lineHeight: 1.15, fontFamily: 'var(--font-headline)' }}
            >
              Welcome back{user?.username ? `, ${user.username}` : ''}
            </h1>
            <p className="text-sm md:text-[15px] max-w-2xl" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Build notes, run AI workflows, and convert source material into useful outputs from one command center.
            </p>

            <div className="mt-5 flex flex-wrap gap-2.5">
              <button
                onClick={() => router.push('/notebook/draft')}
                className="btn-primary inline-flex items-center gap-2 px-4 py-2.5"
              >
                New notebook
                <ArrowRight className="w-4 h-4" />
              </button>
              {latestNotebook && (
                <button
                  onClick={() => router.push(`/notebook/${latestNotebook.id}`)}
                  className="btn-secondary inline-flex items-center gap-2 px-4 py-2.5"
                >
                  Open latest
                  <ArrowUpRight className="w-4 h-4" />
                </button>
              )}
              <button
                onClick={() => router.push('/learning')}
                className="btn-secondary inline-flex items-center gap-2 px-4 py-2.5"
              >
                AI Learning Studio
                <BrainCircuit className="w-4 h-4" />
              </button>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="rounded-2xl p-4" style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Total notebooks</span>
                <FolderOpen className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              </div>
              <p className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>{notebooks.length}</p>
            </div>

            <div className="rounded-2xl p-4" style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Active today</span>
                <Activity className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              </div>
              <p className="text-2xl font-semibold" style={{ color: 'var(--text-primary)' }}>{activeTodayCount}</p>
            </div>

            <div className="rounded-2xl p-4 col-span-2" style={{ background: 'var(--surface-raised)', border: '1px solid var(--border)' }}>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Latest update</span>
                <Clock3 className="w-4 h-4" style={{ color: 'var(--accent)' }} />
              </div>
              <p className="text-sm font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                {latestNotebook?.name || 'No notebooks yet'}
              </p>
              <p className="text-xs mt-1" style={{ color: 'var(--text-muted)' }}>
                {latestNotebook ? formatRelativeDate(latestNotebook.updated_at) : 'Create your first notebook to get started'}
              </p>
            </div>
          </div>
        </section>

        <div className="flex items-center justify-between mb-5">
          <div className="flex items-center gap-2.5">
            <h2 className="text-xs font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
              Notebooks
            </h2>
            <span
              className="text-2xs px-2 py-0.5 rounded-md font-medium"
              style={{ background: 'var(--surface-overlay)', color: 'var(--text-muted)' }}
            >
              {notebooks.length}
            </span>
          </div>
          <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
            Recently active: {activeTodayCount}
          </p>
        </div>

        {/* Notebooks Grid */}
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
          <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-4">
            {/* New Notebook Card */}
            <button
              onClick={() => router.push('/notebook/draft')}
              className="notebook-card border-dashed flex flex-col items-center justify-center gap-3 group cursor-pointer transition-all duration-200 min-h-[220px]"
              style={{
                borderColor: 'var(--accent-border)',
                background:
                  'radial-gradient(90% 90% at 12% 8%, rgba(16,185,129,0.12), transparent 52%), color-mix(in srgb, var(--surface-raised) 88%, transparent)',
              }}
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

            {/* Existing Notebook Cards */}
            {notebooks.map((notebook, i) => {
              const hasWorkingThumbnail = Boolean(notebook.thumbnail_url) && !failedThumbnails[notebook.id];
              return (
                <div
                  key={notebook.id}
                  onClick={() => router.push(`/notebook/${notebook.id}`)}
                  className="notebook-card notebook-card-lux group cursor-pointer animate-fade-up min-h-[228px]"
                  style={{ animationDelay: `${i * 30}ms`, animationFillMode: 'backwards' }}
                >
                <div className="relative h-[120px] w-full overflow-hidden">
                  {hasWorkingThumbnail ? (
                    // eslint-disable-next-line @next/next/no-img-element
                    <img
                      src={notebook.thumbnail_url}
                      alt=""
                      className="h-full w-full object-cover notebook-thumb-image"
                      loading="lazy"
                      onError={() => handleThumbnailError(notebook.id)}
                    />
                  ) : (
                    <div
                      className="h-full w-full flex items-center justify-center notebook-thumb-fallback"
                      style={{
                        background:
                          'radial-gradient(100% 120% at 10% 10%, rgba(16,185,129,0.22), transparent 55%), linear-gradient(120deg, color-mix(in srgb, var(--surface-overlay) 78%, transparent), color-mix(in srgb, var(--surface-raised) 95%, transparent))',
                      }}
                    >
                      <div
                        className="w-11 h-11 rounded-xl flex items-center justify-center"
                        style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}
                      >
                        <ImageIcon className="w-5 h-5" style={{ color: 'var(--accent)' }} />
                      </div>
                    </div>
                  )}

                  <div
                    className="absolute inset-0"
                    style={{
                      background:
                        'linear-gradient(180deg, rgba(0,0,0,0.02) 20%, rgba(0,0,0,0.55) 100%)',
                    }}
                  />

                  <div className="absolute top-3 left-3">
                    <div
                      className="w-9 h-9 rounded-lg flex items-center justify-center backdrop-blur-sm"
                      style={{
                        background: 'color-mix(in srgb, var(--surface-overlay) 76%, transparent)',
                        border: '1px solid var(--accent-border)',
                      }}
                    >
                      <BookOpen className="w-4 h-4" style={{ color: 'var(--accent)' }} />
                    </div>
                  </div>

                  <span
                    className="absolute top-3 right-11 text-2xs px-2 py-1 rounded-md notebook-time-chip"
                    style={{
                      background: 'rgba(0, 0, 0, 0.38)',
                      color: '#e9eaee',
                      border: '1px solid rgba(255,255,255,0.16)',
                      backdropFilter: 'blur(8px)',
                    }}
                  >
                    {formatRelativeDate(notebook.updated_at)}
                  </span>
                </div>

                <div className="flex-1 p-4 flex flex-col">
                  <div className="mt-auto">
                    <h3 className="font-semibold text-[15px] mb-1 pr-8 truncate" style={{ color: 'var(--text-primary)' }}>
                      {notebook.name}
                    </h3>
                    <p
                      className="text-xs min-h-[32px]"
                      style={{
                        color: 'var(--text-muted)',
                        display: '-webkit-box',
                        WebkitLineClamp: 2,
                        WebkitBoxOrient: 'vertical',
                        overflow: 'hidden',
                      }}
                    >
                      {notebook.description || 'Created from chat'}
                    </p>
                    {notebook.thumbnail_query && (
                      <div className="mt-2.5">
                        <span className="notebook-cover-chip" title={notebook.thumbnail_query}>
                          {notebook.thumbnail_query}
                        </span>
                      </div>
                    )}
                  </div>
                </div>

                {/* Options Menu Button */}
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

                {/* Dropdown Menu */}
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
              );
            })}
          </div>
        )}
      </main>

      {/* Rename Modal */}
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

      {/* Delete Confirmation Modal */}
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

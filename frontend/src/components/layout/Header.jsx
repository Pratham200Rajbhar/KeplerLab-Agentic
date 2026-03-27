'use client';

import { useState, useRef, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import { useTheme } from 'next-themes';
import useAuthStore from '@/stores/useAuthStore';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import {
  ChevronLeft,
  Layers,
  BookOpen,
  Sun,
  Moon,
  Share2,
  HelpCircle,
  Settings,
  LogOut,
} from 'lucide-react';

export default function Header({ user, onBack }) {
  const router = useRouter();
  const [showMenu, setShowMenu] = useState(false);
  const menuRef = useRef(null);
  const { logout } = useAuthStore();
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const { resolvedTheme, setTheme } = useTheme();
  const isDark = resolvedTheme === 'dark';
  const toggleTheme = () => setTheme(isDark ? 'light' : 'dark');
  const toast = useToast();

  useEffect(() => {
    const handleClickOutside = (event) => {
      if (menuRef.current && !menuRef.current.contains(event.target)) {
        setShowMenu(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleLogout = async () => {
    setShowMenu(false);
    await logout();
    router.replace('/auth');
  };

  const handleBackClick = () => {
    if (onBack) onBack();
    else router.push('/');
  };

  const userInitial = user?.username?.charAt(0)?.toUpperCase() || user?.email?.charAt(0)?.toUpperCase() || 'U';

  return (
    <header className="h-[52px] flex items-center justify-between px-4 shrink-0 relative z-40 bg-surface/80 backdrop-blur-xl">
      {}
      <div className="flex items-center gap-3">
        {onBack && (
          <button onClick={handleBackClick} className="btn-icon-sm hover:bg-accent-subtle" title="Back to notebooks">
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}

        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-gradient-to-br from-accent to-accent-dark flex items-center justify-center shadow-glow-sm">
            <Layers className="w-3.5 h-3.5 text-white" />
          </div>
          <span className="text-sm font-bold text-text-primary tracking-tight">KeplerLab</span>
        </div>

        <div className="w-px h-4 bg-text-muted/10 ml-0.5" />

        <div className="flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-text-muted" />
          <h1 className="text-sm text-text-secondary truncate max-w-[200px]">
            {currentNotebook?.name || 'Notebook'}
          </h1>
        </div>
      </div>

      {}
      <div className="flex items-center gap-0.5">
        <button onClick={toggleTheme} className="btn-icon-sm" title={isDark ? 'Light mode' : 'Dark mode'}>
          {isDark ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
        </button>

        <button onClick={() => toast.info('Sharing coming soon!')} className="btn-ghost text-xs py-1.5 px-3">
          <Share2 className="w-3.5 h-3.5" />
          Share
        </button>

        <button onClick={() => toast.info('Help center coming soon!')} className="btn-icon-sm" title="Help">
          <HelpCircle className="w-4 h-4" />
        </button>

        {}
        <div className="relative ml-1" ref={menuRef}>
          <button
            className="w-7 h-7 rounded-lg bg-accent/15 flex items-center justify-center text-accent text-xs font-semibold hover:bg-accent/25 transition-all duration-200"
            onClick={() => setShowMenu(!showMenu)}
            aria-label="User menu"
          >
            {userInitial}
          </button>

          {showMenu && (
            <div
              className="absolute right-0 top-full mt-2 w-56 rounded-2xl overflow-hidden animate-scale-in z-50 bg-surface shadow-[0_20px_50px_rgba(0,0,0,0.5)]"
            >
              <div className="px-4 py-3.5 bg-surface-raised/50 backdrop-blur-md">
                <p className="text-sm font-semibold text-text-primary mb-0.5">{user?.username || 'User'}</p>
                <p className="text-[11px] text-text-muted truncate">{user?.email || 'user@example.com'}</p>
              </div>
              <div className="p-1.5">
                <button
                  onClick={() => { setShowMenu(false); toast.info('Settings coming soon!'); }}
                  className="w-full px-3 py-2.5 text-left text-sm text-text-secondary hover:bg-accent-subtle hover:text-accent rounded-xl flex items-center gap-3 transition-all duration-200"
                >
                  <div className="w-7 h-7 rounded-lg bg-surface-overlay flex items-center justify-center">
                    <Settings className="w-3.5 h-3.5" />
                  </div>
                  <span>Settings</span>
                </button>
                <button
                  onClick={handleLogout}
                  className="w-full px-3 py-2.5 text-left text-sm text-text-secondary hover:bg-danger-subtle hover:text-danger rounded-xl flex items-center gap-3 transition-all duration-200"
                >
                  <div className="w-7 h-7 rounded-lg bg-surface-overlay flex items-center justify-center">
                    <LogOut className="w-3.5 h-3.5" />
                  </div>
                  <span>Sign out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}

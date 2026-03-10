'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAuthStore from '@/stores/useAuthStore';
import { Layers, CheckCircle, Brain, GraduationCap, Sparkles, BookOpen, ArrowRight, Eye, EyeOff } from 'lucide-react';


const features = [
  {
    icon: Brain,
    title: 'AI Chat',
    desc: 'Ask questions about your documents and get instant answers.',
  },
  {
    icon: GraduationCap,
    title: 'Podcast Generation',
    desc: 'Turn any document into a podcast-style audio summary.',
  },
  {
    icon: BookOpen,
    title: 'Smart Notebooks',
    desc: 'Organize, annotate, and collaborate on your study materials.',
  },
];

function AuthLeftPanel() {
  return (
    <div className="auth-split-left">
      {}
      <div className="relative z-10 mb-10">
        <div className="flex items-center gap-3 mb-6">
          <div
            className="w-10 h-10 rounded-xl flex items-center justify-center"
            style={{ background: 'var(--accent)' }}
          >
            <Layers className="w-5 h-5" style={{ color: 'var(--text-inverse)' }} />
          </div>
          <span className="text-lg font-semibold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            KeplerLab
          </span>
        </div>

        <h2
          className="text-2xl md:text-3xl font-semibold tracking-tight mb-3"
          style={{ color: 'var(--text-primary)', lineHeight: 1.25 }}
        >
          Your AI-powered<br />learning workspace
        </h2>
        <p className="text-sm max-w-xs" style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Upload documents, generate podcasts, and study smarter with AI assistance.
        </p>
      </div>

      {}
      <div className="relative z-10 space-y-4">
        {features.map(({ icon: Icon, title, desc }) => (
          <div
            key={title}
            className="flex items-start gap-3.5 p-3.5 rounded-xl transition-colors duration-200"
            style={{ background: 'rgba(255,255,255,0.02)', border: '1px solid var(--border-light)' }}
          >
            <div
              className="w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0"
              style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}
            >
              <Icon className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            </div>
            <div>
              <h4 className="text-sm font-medium mb-0.5" style={{ color: 'var(--text-primary)' }}>{title}</h4>
              <p className="text-xs leading-relaxed" style={{ color: 'var(--text-muted)' }}>{desc}</p>
            </div>
          </div>
        ))}
      </div>

      {}
      <div className="mt-10 relative z-10">
        <div
          className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-xs font-medium"
          style={{ background: 'var(--accent-subtle)', color: 'var(--accent)', border: '1px solid var(--accent-border)' }}
        >
          <Sparkles className="w-3 h-3" />
          Powered by AI
        </div>
      </div>
    </div>
  );
}

function AuthForm() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const isSignupParam = searchParams.get('mode') === 'signup';
  const sessionExpired = searchParams.get('reason') === 'expired';

  const { login, signup, error, setError, clearError, isLoading: authGlobalLoading, isAuthenticated } = useAuthStore();

  const [isLogin, setIsLogin] = useState(!isSignupParam);
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [signupDone, setSignupDone] = useState(false);

  const redirectTo = searchParams.get('redirect') || '/';

  useEffect(() => {
    if (!authGlobalLoading && isAuthenticated) router.replace(redirectTo);
  }, [isAuthenticated, authGlobalLoading, router, redirectTo]);

  useEffect(() => clearError(), [clearError]);

  const switchMode = () => {
    setIsLogin(!isLogin);
    clearError();
    setSignupDone(false);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();

    if (!isLogin && password.length < 6) {
      setError('Password must be at least 6 characters.');
      setLoading(false);
      return;
    }

    setLoading(true);
    if (isLogin) {
      const ok = await login(email, password);
      if (ok) router.replace(redirectTo);
    } else {
      const ok = await signup(email, username, password);
      if (ok) {
        setSignupDone(true);
        setIsLogin(true);
      }
    }
    setLoading(false);
  };

  if (authGlobalLoading) {
    return (
      <div className="flex items-center justify-center flex-1" style={{ background: 'var(--surface)' }}>
        <div className="loading-spinner w-6 h-6" />
      </div>
    );
  }

  if (isAuthenticated) return null;

  
  return (
    <div className="auth-split-right">
      <div className="w-full max-w-sm mx-auto">
        {}
        {signupDone && (
          <div
            className="mb-6 p-3.5 rounded-xl flex items-start gap-2.5 text-sm animate-fade-in"
            style={{
              background: 'var(--success-subtle)',
              border: '1px solid var(--success-border)',
              color: 'var(--success)',
            }}
          >
            <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>Account created successfully. Please sign in.</span>
          </div>
        )}

        {}
        {sessionExpired && !signupDone && (
          <div
            className="mb-6 p-3.5 rounded-xl flex items-start gap-2.5 text-sm animate-fade-in"
            style={{
              background: 'var(--warning-subtle, rgba(234,179,8,0.08))',
              border: '1px solid var(--warning-border, rgba(234,179,8,0.25))',
              color: 'var(--warning, #ca8a04)',
            }}
          >
            <span className="flex-shrink-0 mt-0.5">⚠️</span>
            <span>Your session has expired. Please sign in again to continue.</span>
          </div>
        )}

        {}
        <div className="mb-6">
          <h2 className="text-xl font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
            {isLogin ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="text-sm" style={{ color: 'var(--text-muted)' }}>
            {isLogin ? 'Sign in to continue to KeplerLab' : 'Get started with a free account'}
          </p>
        </div>

        {}
        {error && (
          <div
            className="mb-4 p-3 rounded-xl text-sm animate-fade-in"
            style={{
              background: 'var(--danger-subtle)',
              border: '1px solid var(--danger-border)',
              color: 'var(--danger-light)',
            }}
          >
            {typeof error === 'object' ? error.message || 'An error occurred' : error}
          </div>
        )}

        {}
        <form onSubmit={handleSubmit} className="space-y-3.5">
          <div>
            <label className="form-label">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="input w-full"
              required
            />
          </div>

          {!isLogin && (
            <div className="animate-fade-in">
              <label className="form-label">Username</label>
              <input
                type="text"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Choose a username"
                className="input w-full"
                required
              />
            </div>
          )}

          <div>
            <label className="form-label">Password</label>
            <div className="relative">
              <input
                type={showPassword ? 'text' : 'password'}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                className="input w-full pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2"
                style={{ color: 'var(--text-muted)' }}
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="btn-primary w-full flex items-center justify-center gap-2 py-2.5"
          >
            {loading ? (
              <>
                <div className="loading-spinner w-4 h-4" />
                {isLogin ? 'Signing in...' : 'Creating account...'}
              </>
            ) : (
              <>
                {isLogin ? 'Sign in' : 'Create account'}
                <ArrowRight className="w-4 h-4" />
              </>
            )}
          </button>
        </form>

        {}
        <p className="text-center mt-5 text-sm" style={{ color: 'var(--text-muted)' }}>
          {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            onClick={switchMode}
            className="font-medium transition-colors"
            style={{ color: 'var(--accent)' }}
            onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--accent-light)')}
            onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--accent)')}
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </button>
        </p>
      </div>
    </div>
  );
}

export default function AuthPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen flex items-center justify-center" style={{ background: 'var(--surface)' }}>
          <div className="loading-spinner w-6 h-6" />
        </div>
      }
    >
      <div className="auth-split min-h-screen">
        <AuthLeftPanel />
        <AuthForm />
      </div>
    </Suspense>
  );
}

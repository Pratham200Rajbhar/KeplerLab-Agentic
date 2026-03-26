'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import useAuthStore from '@/stores/useAuthStore';
import {
  Layers,
  CheckCircle,
  Brain,
  GraduationCap,
  Sparkles,
  BookOpen,
  Presentation,
  FlaskConical,
  Network,
  Compass,
  Search,
  FileText,
  ArrowRight,
  Eye,
  EyeOff,
  AlertTriangle,
} from 'lucide-react';


const features = [
  {
    icon: Brain,
    title: 'AI Chat',
    desc: 'Document-aware answers',
  },
  {
    icon: GraduationCap,
    title: 'Podcast Studio',
    desc: 'Audio summaries from notes',
  },
  {
    icon: BookOpen,
    title: 'Smart Notebooks',
    desc: 'Organize and annotate',
  },
  {
    icon: FileText,
    title: 'Flashcards',
    desc: 'Auto-generated study cards',
  },
  {
    icon: FlaskConical,
    title: 'Quizzes',
    desc: 'Practice tests in one click',
  },
  {
    icon: Network,
    title: 'Mind Maps',
    desc: 'Visual concept linking',
  },
  {
    icon: Presentation,
    title: 'PPT Builder',
    desc: 'Slides from your sources',
  },
  {
    icon: Compass,
    title: 'Research Agent',
    desc: 'Guided deep research',
  },
  {
    icon: Search,
    title: 'Web Search',
    desc: 'Fetch fresh references',
  },
];

function AuthLeftPanel() {
  const featureSizeClass = (index) => {
    if (index < 2) return 'auth-orbit-feature-xl';
    if (index < 5) return 'auth-orbit-feature-md';
    return 'auth-orbit-feature-lg';
  };

  return (
    <div className="auth-orbit-left">
      <div className="auth-orbit-noise" />

      <div className="auth-orbit-brand animate-slide-up">
        <div className="auth-orbit-logo">
          <Layers className="w-5 h-5" style={{ color: 'var(--text-inverse)' }} />
        </div>
        <div>
          <p className="auth-orbit-kicker">KeplerLab AI Notebook</p>
          <p className="auth-orbit-subkicker">Study OS</p>
        </div>
      </div>

      <div className="auth-orbit-hero animate-slide-up" style={{ animationDelay: '90ms' }}>
        <div className="auth-orbit-hero-chip">AI Study Workspace</div>
        <h2 className="auth-orbit-title">
          Learn faster with an AI workspace built like a mission control room.
        </h2>
        <p className="auth-orbit-description">
          Upload class notes, generate podcasts, and map concepts in one focused workflow.
        </p>
      </div>

      <div className="auth-orbit-grid">
        {features.map(({ icon: Icon, title, desc }, idx) => (
          <div
            key={title}
            className={`auth-orbit-feature ${featureSizeClass(idx)} animate-slide-up`}
            style={{ animationDelay: `${90 + idx * 35}ms` }}
          >
            <div className="auth-orbit-feature-icon" aria-hidden="true">
              <Icon className="w-4 h-4" style={{ color: 'var(--accent)' }} />
            </div>
            <div className="auth-orbit-feature-copy">
              <h4>{title}</h4>
              <p>{desc}</p>
            </div>
          </div>
        ))}
      </div>

      <div className="auth-orbit-badge animate-slide-up" style={{ animationDelay: '340ms' }}>
        <Sparkles className="w-3.5 h-3.5" />
        Adaptive AI assistance enabled
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
    <div className="auth-orbit-right">
      <div className="auth-orbit-card animate-slide-up">
        <div className="auth-orbit-card-glow" />

        <div className="auth-orbit-topbar">
          <button
            type="button"
            onClick={() => setIsLogin(true)}
            className={`auth-orbit-mode ${isLogin ? 'active' : ''}`}
          >
            Sign in
          </button>
          <button
            type="button"
            onClick={() => setIsLogin(false)}
            className={`auth-orbit-mode ${!isLogin ? 'active' : ''}`}
          >
            Create account
          </button>
        </div>

        {signupDone && (
          <div className="auth-orbit-alert success animate-fade-in">
            <CheckCircle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>Account created successfully. Please sign in.</span>
          </div>
        )}

        {sessionExpired && !signupDone && (
          <div className="auth-orbit-alert warn animate-fade-in">
            <AlertTriangle className="w-4 h-4 flex-shrink-0 mt-0.5" />
            <span>Your session has expired. Please sign in again to continue.</span>
          </div>
        )}

        <div className="mb-5">
          <h2 className="auth-orbit-form-title">
            {isLogin ? 'Welcome back' : 'Create account'}
          </h2>
          <p className="auth-orbit-form-subtitle">
            {isLogin ? 'Sign in to continue to KeplerLab' : 'Get started with a free account'}
          </p>
        </div>

        {error && (
          <div className="auth-orbit-alert danger animate-fade-in">
            {typeof error === 'object' ? error.message || 'An error occurred' : error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-3.5 relative z-10">
          <div>
            <label className="form-label">Email</label>
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@example.com"
              className="input auth-orbit-input w-full"
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
                className="input auth-orbit-input w-full"
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
                className="input auth-orbit-input w-full pr-10"
                required
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 auth-orbit-eye"
              >
                {showPassword ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
          </div>

          <button
            type="submit"
            disabled={loading}
            className="auth-orbit-submit w-full"
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

        <p className="text-center mt-5 text-sm auth-orbit-switch-copy">
          {isLogin ? "Don't have an account?" : 'Already have an account?'}{' '}
          <button
            onClick={switchMode}
            className="font-medium transition-colors auth-orbit-switch"
          >
            {isLogin ? 'Sign up' : 'Sign in'}
          </button>
        </p>

        <p className="auth-orbit-legal">By continuing, you agree to secure session handling and encrypted credential flow.</p>
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
      <div className="auth-orbit-shell min-h-screen">
        <AuthLeftPanel />
        <AuthForm />
      </div>
    </Suspense>
  );
}

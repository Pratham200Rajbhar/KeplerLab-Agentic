'use client';

import { useEffect, useState } from 'react';
import { X, Mic, Globe, BookOpen, Search, PlayCircle, Layers3, Brain, Scale, MessagesSquare } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import VoicePicker from './VoicePicker';
import { getLanguages, getVoicesForLanguage } from '@/lib/api/podcast';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';

const NATIVE_LANGUAGE_NAMES = {
  en: 'English', hi: 'हिन्दी', gu: 'ગુજરાતી', bn: 'বাংলা', ta: 'தமிழ்', te: 'తెలుగు',
  mr: 'मराठी', kn: 'ಕನ್ನಡ', ml: 'മലയാളം', pa: 'ਪੰਜਾਬੀ', ur: 'اردو', or: 'ଓଡିଆ',
  es: 'Espanol', fr: 'Francais', de: 'Deutsch', ar: 'العربية', ja: '日本語', zh: '中文', pt: 'Portugues',
};

const MODES = [
  { id: 'overview', label: 'Overview', desc: 'Broad tour of all material', Icon: Layers3 },
  { id: 'deep-dive', label: 'Deep Dive', desc: 'In-depth concept analysis', Icon: Brain },
  { id: 'debate', label: 'Debate', desc: 'Hosts take opposing views', Icon: Scale },
  { id: 'q-and-a', label: 'Q & A', desc: 'Interview-style discussion', Icon: MessagesSquare },
];

const DEFAULT_LANGUAGES = [
  { code: 'en', name: 'English' }, { code: 'hi', name: 'Hindi' }, { code: 'gu', name: 'Gujarati' },
  { code: 'bn', name: 'Bengali' }, { code: 'ta', name: 'Tamil' }, { code: 'te', name: 'Telugu' },
  { code: 'mr', name: 'Marathi' }, { code: 'kn', name: 'Kannada' }, { code: 'ml', name: 'Malayalam' },
  { code: 'pa', name: 'Punjabi' }, { code: 'ur', name: 'Urdu' }, { code: 'or', name: 'Odia' },
  { code: 'es', name: 'Spanish' }, { code: 'fr', name: 'French' }, { code: 'de', name: 'German' },
  { code: 'ja', name: 'Japanese' }, { code: 'zh', name: 'Chinese' }, { code: 'pt', name: 'Portuguese' }, { code: 'ar', name: 'Arabic' },
];

export default function PodcastConfigDialog({ onClose }) {
  const toast = useToast();
  const create = usePodcastStore((s) => s.create);
  const startGeneration = usePodcastStore((s) => s.startGeneration);
  const loading = usePodcastStore((s) => s.loading);
  const error = usePodcastStore((s) => s.error);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);

  const [scope, setScope] = useState('full');
  const [mode, setMode] = useState('overview');
  const [topic, setTopic] = useState('');
  const [language, setLanguage] = useState('en');
  const [hostVoice, setHostVoice] = useState('');
  const [guestVoice, setGuestVoice] = useState('');
  const [languages, setLanguages] = useState([]);
  const [, setDefaultVoices] = useState({ host: '', guest: '' });
  const [voiceIdsForLanguage, setVoiceIdsForLanguage] = useState([]);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error, toast]);

  useEffect(() => {
    getLanguages()
      .then((data) => {
        if (Array.isArray(data)) setLanguages(data);
        else if (Array.isArray(data?.languages)) setLanguages(data.languages);
        else setLanguages([]);
      })
      .catch(() => setLanguages([]));
  }, []);

  useEffect(() => {
    getVoicesForLanguage(language)
      .then((data) => {
        const voices = Array.isArray(data) ? data : Array.isArray(data?.voices) ? data.voices : [];
        const ids = voices.map((v) => v.id || v.voice_id || v.voiceId).filter(Boolean);
        setVoiceIdsForLanguage(ids);

        const defaults = data?.defaults || {};
        const nextHost = defaults.host || ids[0] || '';
        const nextGuest = defaults.guest || ids.find((id) => id !== nextHost) || '';

        setDefaultVoices({
          host: nextHost,
          guest: nextGuest,
        });

        setHostVoice((prev) => (prev && ids.includes(prev) ? prev : nextHost));
        setGuestVoice((prev) => {
          const fallback = nextGuest || ids.find((id) => id !== nextHost) || '';
          if (prev && ids.includes(prev) && prev !== nextHost) return prev;
          return fallback;
        });
      })
      .catch(() => {
        setVoiceIdsForLanguage([]);
        setDefaultVoices({ host: '', guest: '' });
        setHostVoice('');
        setGuestVoice('');
      });
  }, [language]);

  const handleHostVoiceChange = (voiceId) => {
    setHostVoice(voiceId);
    if (voiceId && voiceId === guestVoice) {
      const alternative = voiceIdsForLanguage.find((id) => id !== voiceId) || '';
      setGuestVoice(alternative);
    }
  };

  const handleGuestVoiceChange = (voiceId) => {
    setGuestVoice(voiceId);
    if (voiceId && voiceId === hostVoice) {
      const alternative = voiceIdsForLanguage.find((id) => id !== voiceId) || '';
      setHostVoice(alternative);
    }
  };

  const availableLanguages = (() => {
    // Prefer backend-supported languages to avoid selecting options
    // that later fall back to English voices.
    if (Array.isArray(languages) && languages.length > 0) return languages;
    return DEFAULT_LANGUAGES;
  })();

  const selectedLanguageNative = NATIVE_LANGUAGE_NAMES[language] || availableLanguages.find((l) => l.code === language)?.name || language;

  const canGenerate =
    selectedSources.length > 0 &&
    !loading &&
    (scope === 'full' || topic.trim().length > 0) &&
    !(hostVoice && guestVoice && hostVoice === guestVoice);

  const handleGenerate = async () => {
    if (hostVoice && guestVoice && hostVoice === guestVoice) {
      toast.error('Choose different voices for Host and Guest.');
      return;
    }

    try {
      const config = {
        mode,
        topic: scope === 'topic' ? topic.trim() : '',
        language,
        hostVoice: hostVoice || undefined,
        guestVoice: guestVoice || undefined,
      };
      const session = await create(config, currentNotebook?.id, selectedSources);
      if (session?.id) await startGeneration(session.id);
      onClose?.();
    } catch {
      // handled in store
    }
  };

  return (
    <Modal onClose={onClose} maxWidth="max-w-[1120px]">
      <div className="flex items-center gap-3 border-b border-[var(--border)] px-6 py-4">
        <div className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-[var(--accent-border)] bg-[var(--accent-subtle)]">
          <Mic className="h-4 w-4 text-[var(--accent)]" />
        </div>
        <div>
          <h3 className="text-lg font-semibold text-[var(--text-primary)]">New AI Podcast</h3>
          <p className="text-xs text-[var(--text-muted)]">Configure your two-host AI podcast</p>
        </div>
        <button onClick={onClose} className="ml-auto rounded-lg p-1.5 hover:bg-[var(--surface-overlay)]" aria-label="Close dialog">
          <X className="h-4 w-4 text-[var(--text-muted)]" />
        </button>
      </div>

      <div
        className="space-y-5 px-6 py-5"
        style={{
          backgroundImage:
            'radial-gradient(1200px 220px at 50% -80px, rgba(16,185,129,0.08), transparent), linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)',
          backgroundSize: 'auto, 24px 24px, 24px 24px',
          backgroundPosition: 'center top, 0 0, 0 0',
        }}
      >
        <div className="grid gap-4 lg:grid-cols-2">
          <section
            className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4 space-y-4"
            style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
          >
            <div>
              <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">What to Cover</p>
              <div className="grid gap-2 sm:grid-cols-2">
                <button
                  type="button"
                  onClick={() => setScope('full')}
                  className={`rounded-lg border p-3 text-left transition-colors ${scope === 'full' ? 'border-[var(--accent)] bg-[var(--accent-subtle)]' : 'border-[var(--border)] hover:bg-[var(--surface-overlay)]'}`}
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]"><BookOpen className="h-4 w-4" /> Full Resource</span>
                  <span className="mt-1 block text-xs text-[var(--text-muted)]">Cover all material</span>
                </button>

                <button
                  type="button"
                  onClick={() => setScope('topic')}
                  className={`rounded-lg border p-3 text-left transition-colors ${scope === 'topic' ? 'border-[var(--accent)] bg-[var(--accent-subtle)]' : 'border-[var(--border)] hover:bg-[var(--surface-overlay)]'}`}
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]"><Search className="h-4 w-4" /> Specific Topic</span>
                  <span className="mt-1 block text-xs text-[var(--text-muted)]">Focus on one area</span>
                </button>
              </div>
              {scope === 'topic' && (
                <input
                  type="text"
                  value={topic}
                  onChange={(e) => setTopic(e.target.value)}
                  placeholder="e.g. Chapter 3: Neural Networks"
                  className="podcast-text-field mt-2.5 w-full rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] px-3 py-2 text-sm text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
                />
              )}
            </div>

            <div>
              <p className="mb-2 flex items-center gap-1.5 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]"><Globe className="h-3 w-3" /> Language</p>
              <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] px-3 py-2">
                <select
                  value={language}
                  onChange={(e) => setLanguage(e.target.value)}
                  className="podcast-language-select w-full bg-transparent text-sm text-[var(--text-primary)] focus:outline-none"
                >
                  {availableLanguages.map((l) => {
                    const native = NATIVE_LANGUAGE_NAMES[l.code];
                    const label = native && native !== l.name ? `${l.name} (${native})` : l.name;
                    return (
                      <option key={l.code} value={l.code}>
                        {label}
                      </option>
                    );
                  })}
                </select>
              </div>
              <p className="mt-1.5 text-[10px] text-[var(--text-muted)]">Selected script: {selectedLanguageNative}</p>
            </div>
          </section>

          <section
            className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
            style={{ boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)' }}
          >
            <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Podcast Style</p>
            <div className="grid gap-2 sm:grid-cols-2">
              {MODES.map((m) => (
                <button
                  key={m.id}
                  type="button"
                  onClick={() => setMode(m.id)}
                  className={`rounded-lg border p-3 text-left transition-colors ${mode === m.id ? 'border-[var(--accent)] bg-[var(--accent-subtle)]' : 'border-[var(--border)] hover:bg-[var(--surface-overlay)]'}`}
                >
                  <span className="flex items-center gap-2 text-sm font-medium text-[var(--text-primary)]">
                    <m.Icon className="h-4 w-4 text-[var(--text-secondary)]" />
                    {m.label}
                  </span>
                  <span className="mt-1 block text-xs text-[var(--text-muted)]">{m.desc}</span>
                </button>
              ))}
            </div>
          </section>
        </div>

        <section
          className="rounded-xl border border-[var(--border)] bg-[var(--surface)] p-4"
          style={{
            boxShadow: 'inset 0 1px 0 rgba(255,255,255,0.03)',
            backgroundImage: 'radial-gradient(420px 140px at 100% 0%, rgba(16,185,129,0.08), transparent)',
          }}
        >
          <p className="mb-3 text-[11px] font-semibold uppercase tracking-wider text-[var(--text-muted)]">Host Voices</p>
          <div className="grid gap-4 lg:grid-cols-2">
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)]/55 p-3">
              <VoicePicker
                label="Host"
                language={language}
                value={hostVoice}
                onChange={handleHostVoiceChange}
                excludeVoiceId={guestVoice}
                disabled={loading}
              />
            </div>
            <div className="rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)]/55 p-3">
              <VoicePicker
                label="Guest"
                language={language}
                value={guestVoice}
                onChange={handleGuestVoiceChange}
                excludeVoiceId={hostVoice}
                disabled={loading}
              />
            </div>
          </div>
        </section>
      </div>

      <div className="flex items-center gap-2.5 border-t border-[var(--border)] px-6 py-4">
        <button
          onClick={onClose}
          disabled={loading}
          className="flex-1 rounded-lg border border-[var(--border)] px-4 py-2 text-sm font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] disabled:opacity-40"
        >
          Cancel
        </button>

        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className="flex-1 inline-flex items-center justify-center gap-2 rounded-lg bg-[var(--accent)] px-4 py-2 text-sm font-semibold text-white hover:opacity-90 disabled:opacity-40"
        >
          {loading ? (
            <>
              <div className="loading-spinner h-4 w-4" /> Generating...
            </>
          ) : (
            <>
              <PlayCircle className="h-4 w-4" /> Generate Podcast
            </>
          )}
        </button>
      </div>
    </Modal>
  );
}

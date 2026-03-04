'use client';

import { useState, useEffect } from 'react';
import { X, PlayCircle, Mic, BookOpen, Search, Globe } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import VoicePicker from './VoicePicker';
import { getLanguages } from '@/lib/api/podcast';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';

const MODES = [
  { id: 'overview',  label: 'Overview',   desc: 'Broad tour of all material',      emoji: '🗺️' },
  { id: 'deep-dive', label: 'Deep Dive',  desc: 'In-depth concept analysis',        emoji: '🔬' },
  { id: 'debate',    label: 'Debate',     desc: 'Hosts take opposing views',        emoji: '⚖️' },
  { id: 'q-and-a',  label: 'Q & A',      desc: 'Interview-style discussion',       emoji: '💬' },
];

const DEFAULT_LANGUAGES = [
  { code: 'en', name: 'English' },
  { code: 'hi', name: 'Hindi' },
  { code: 'es', name: 'Spanish' },
  { code: 'fr', name: 'French' },
  { code: 'de', name: 'German' },
  { code: 'ja', name: 'Japanese' },
  { code: 'zh', name: 'Chinese' },
  { code: 'pt', name: 'Portuguese' },
  { code: 'ar', name: 'Arabic' },
];

export default function PodcastConfigDialog({ onClose }) {
  const toast = useToast();
  const create = usePodcastStore((s) => s.create);
  const startGeneration = usePodcastStore((s) => s.startGeneration);
  const loading = usePodcastStore((s) => s.loading);
  const error = usePodcastStore((s) => s.error);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error, toast]);

  const [scope, setScope]         = useState('full');   // 'full' | 'topic'
  const [mode, setMode]           = useState('overview');
  const [topic, setTopic]         = useState('');
  const [language, setLanguage]   = useState('en');
  const [hostVoice, setHostVoice] = useState('');
  const [guestVoice, setGuestVoice] = useState('');
  const [languages, setLanguages] = useState([]);

  useEffect(() => {
    getLanguages()
      .then((data) => {
        if (Array.isArray(data)) setLanguages(data);
        else if (data?.languages) setLanguages(data.languages);
        else setLanguages([]);
      })
      .catch(() => setLanguages([]));
  }, []);

  const availableLanguages = languages.length > 0 ? languages : DEFAULT_LANGUAGES;

  const handleGenerate = async () => {
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
      // error handled by store
    }
  };

  const canGenerate = selectedSources.length > 0 && !loading && (scope === 'full' || topic.trim().length > 0);

  return (
    <Modal onClose={onClose} maxWidth="lg">
      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b border-[var(--border)]">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center" style={{ background: 'var(--accent-subtle)', border: '1px solid var(--accent-border)' }}>
          <Mic className="w-4 h-4 text-[var(--accent)]" />
        </div>
        <div>
          <h3 className="text-sm font-semibold text-[var(--text-primary)]">New AI Podcast</h3>
          <p className="text-[11px] text-[var(--text-muted)]">Configure your two-host AI podcast</p>
        </div>
        <button onClick={onClose} className="ml-auto p-1.5 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors">
          <X className="w-4 h-4 text-[var(--text-muted)]" />
        </button>
      </div>

      <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">

        {/* What to cover */}
        <div>
          <label className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2 block">What to Cover</label>
          <div className="grid grid-cols-2 gap-2.5">
            <button
              type="button"
              onClick={() => setScope('full')}
              disabled={loading}
              className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                scope === 'full'
                  ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
                  : 'border-[var(--border)] hover:border-[var(--text-muted)]'
              }`}
            >
              <div className={`p-2 rounded-lg shrink-0 ${scope === 'full' ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface-overlay)] text-[var(--text-muted)]'}`}>
                <BookOpen className="w-4 h-4" />
              </div>
              <div>
                <span className={`text-xs font-semibold block ${scope === 'full' ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>Full Resource</span>
                <span className="text-[10px] text-[var(--text-muted)]">Cover all material</span>
              </div>
            </button>
            <button
              type="button"
              onClick={() => setScope('topic')}
              disabled={loading}
              className={`flex items-center gap-3 p-3 rounded-xl border-2 transition-all text-left ${
                scope === 'topic'
                  ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
                  : 'border-[var(--border)] hover:border-[var(--text-muted)]'
              }`}
            >
              <div className={`p-2 rounded-lg shrink-0 ${scope === 'topic' ? 'bg-[var(--accent)] text-white' : 'bg-[var(--surface-overlay)] text-[var(--text-muted)]'}`}>
                <Search className="w-4 h-4" />
              </div>
              <div>
                <span className={`text-xs font-semibold block ${scope === 'topic' ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>Specific Topic</span>
                <span className="text-[10px] text-[var(--text-muted)]">Focus on one area</span>
              </div>
            </button>
          </div>

          {scope === 'topic' && (
            <div className="mt-2.5 animate-fade-in">
              <input
                type="text"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="e.g. Chapter 3: Neural Networks, Photosynthesis..."
                autoFocus
                disabled={loading}
                className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] transition-shadow"
              />
            </div>
          )}
        </div>

        {/* Style / Mode */}
        <div>
          <label className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2 block">Podcast Style</label>
          <div className="grid grid-cols-2 gap-2">
            {MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                disabled={loading}
                className={`text-left p-2.5 rounded-xl border-2 transition-all ${
                  mode === m.id
                    ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
                    : 'border-[var(--border)] hover:border-[var(--text-muted)]'
                }`}
              >
                <span className="text-base block mb-0.5">{m.emoji}</span>
                <span className={`text-xs font-semibold block ${mode === m.id ? 'text-[var(--text-primary)]' : 'text-[var(--text-secondary)]'}`}>{m.label}</span>
                <span className="text-[10px] text-[var(--text-muted)] block leading-tight">{m.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Language */}
        <div>
          <label className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Globe className="w-3 h-3" /> Language
          </label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            disabled={loading}
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)] transition-shadow"
          >
            {availableLanguages.map((l) => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
        </div>

        {/* Voice Selection — both always visible */}
        <div>
          <label className="text-[11px] font-semibold text-[var(--text-muted)] uppercase tracking-wider mb-2 flex items-center gap-1.5">
            <Mic className="w-3 h-3" /> Host Voices
          </label>
          <div className="rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] overflow-hidden divide-y divide-[var(--border)]">
            <div className="p-3">
              <VoicePicker label="Host" language={language} value={hostVoice} onChange={setHostVoice} />
            </div>
            <div className="p-3">
              <VoicePicker label="Guest" language={language} value={guestVoice} onChange={setGuestVoice} />
            </div>
          </div>
        </div>
      </div>

      {/* Footer */}
      <div className="flex items-center gap-2.5 px-5 py-4 border-t border-[var(--border)]">
        <button
          onClick={onClose}
          disabled={loading}
          className="flex-1 px-4 py-2 text-sm font-medium rounded-lg border border-[var(--border)] text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors disabled:opacity-40"
        >
          Cancel
        </button>
        <button
          onClick={handleGenerate}
          disabled={!canGenerate}
          className="flex-1 flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg bg-[var(--accent)] text-white hover:opacity-90 transition-opacity disabled:opacity-40"
        >
          {loading ? (
            <><div className="loading-spinner w-4 h-4" /> Generating…</>
          ) : (
            <><PlayCircle className="w-4 h-4" /> Generate Podcast</>
          )}
        </button>
      </div>
    </Modal>
  );
}

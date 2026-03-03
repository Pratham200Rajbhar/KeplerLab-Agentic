'use client';

import { useState, useEffect } from 'react';
import { X, ChevronDown, ChevronRight, PlayCircle } from 'lucide-react';
import Modal from '@/components/ui/Modal';
import VoicePicker from './VoicePicker';
import { getLanguages } from '@/lib/api/podcast';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';

const MODES = [
  { id: 'overview', label: 'Overview', desc: 'A broad tour of all uploaded material' },
  { id: 'deep-dive', label: 'Deep Dive', desc: 'In-depth analysis of key concepts' },
  { id: 'debate', label: 'Debate', desc: 'Two hosts take opposing perspectives' },
  { id: 'q-and-a', label: 'Q & A', desc: 'Interview-style question and answer' },
];

export default function PodcastConfigDialog({ onClose }) {
  const create = usePodcastStore((s) => s.create);
  const startGeneration = usePodcastStore((s) => s.startGeneration);
  const loading = usePodcastStore((s) => s.loading);
  const error = usePodcastStore((s) => s.error);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);

  const [mode, setMode] = useState('overview');
  const [topic, setTopic] = useState('');
  const [language, setLanguage] = useState('en');
  const [hostVoice, setHostVoice] = useState('');
  const [guestVoice, setGuestVoice] = useState('');
  const [languages, setLanguages] = useState([]);
  const [showVoices, setShowVoices] = useState(false);

  useEffect(() => {
    getLanguages().then(setLanguages).catch(() => {});
  }, []);

  const handleGenerate = async () => {
    try {
      const config = { mode, topic, language, hostVoice, guestVoice };
      const session = await create(config, currentNotebook?.id, selectedSources);
      if (session?.id) {
        await startGeneration(session.id);
      }
      onClose?.();
    } catch {
      // error is set in store
    }
  };

  return (
    <Modal onClose={onClose} maxWidth="md">
      <div className="flex items-center justify-between px-5 py-4 border-b border-[var(--border)]">
        <h3 className="text-base font-semibold text-[var(--text-primary)]">Podcast Settings</h3>
        <button onClick={onClose} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors">
          <X className="w-4 h-4 text-[var(--text-muted)]" />
        </button>
      </div>

      <div className="p-5 space-y-4">
        {/* Mode */}
        <div>
          <label className="text-xs font-medium text-[var(--text-secondary)] mb-2 block">Style</label>
          <div className="grid grid-cols-2 gap-2">
            {MODES.map((m) => (
              <button
                key={m.id}
                onClick={() => setMode(m.id)}
                className={`text-left p-2.5 rounded-lg border transition-all ${
                  mode === m.id
                    ? 'border-[var(--accent)] bg-[var(--accent)] text-[var(--text-primary)]'
                    : 'border-[var(--border)] hover:border-[var(--text-muted)] text-[var(--text-secondary)]'
                }`}
              >
                <span className="text-xs font-medium block">{m.label}</span>
                <span className="text-[10px] text-[var(--text-muted)] block mt-0.5">{m.desc}</span>
              </button>
            ))}
          </div>
        </div>

        {/* Topic */}
        <div>
          <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
            Focus Topic <span className="text-[var(--text-muted)]">(optional)</span>
          </label>
          <input
            type="text"
            value={topic}
            onChange={(e) => setTopic(e.target.value)}
            placeholder="e.g. Chapter 3: Neural Networks"
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          />
        </div>

        {/* Language */}
        <div>
          <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Language</label>
          <select
            value={language}
            onChange={(e) => setLanguage(e.target.value)}
            className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
          >
            {languages.length > 0 ? (
              languages.map((l) => (
                <option key={l.code} value={l.code}>{l.name}</option>
              ))
            ) : (
              <>
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="ja">Japanese</option>
              </>
            )}
          </select>
        </div>

        {/* Voice toggle */}
        <div>
          <button
            onClick={() => setShowVoices(!showVoices)}
            className="flex items-center gap-2 text-xs text-[var(--accent)] hover:opacity-80 transition-opacity"
          >
            {showVoices ? <ChevronDown className="w-3.5 h-3.5" /> : <ChevronRight className="w-3.5 h-3.5" />}
            {showVoices ? 'Hide voice options' : 'Choose voices'}
          </button>

          {showVoices && (
            <div className="mt-3 space-y-3 animate-fade-in">
              <VoicePicker label="Host Voice" language={language} value={hostVoice} onChange={setHostVoice} />
              <VoicePicker label="Guest Voice" language={language} value={guestVoice} onChange={setGuestVoice} />
            </div>
          )}
        </div>

        {error && (
          <div className="p-2.5 rounded-lg bg-red-500/10 border border-red-500/20 text-xs text-red-400">
            {error}
          </div>
        )}
      </div>

      <div className="flex items-center justify-end gap-2 px-5 py-4 border-t border-[var(--border)]">
        <button onClick={onClose} className="px-4 py-2 text-sm text-[var(--text-secondary)]">Cancel</button>
        <button
          onClick={handleGenerate}
          disabled={selectedSources.size === 0 || loading}
          className="flex items-center gap-2 px-4 py-2 text-sm font-medium rounded-lg bg-[var(--accent)] text-white hover:bg-[var(--accent-light)] transition-colors disabled:opacity-40"
        >
          {loading ? (
            <>
              <div className="loading-spinner w-4 h-4" />
              Creating...
            </>
          ) : (
            <>
              <PlayCircle className="w-4 h-4" />
              Generate
            </>
          )}
        </button>
      </div>
    </Modal>
  );
}

'use client';

import { useState, useEffect } from 'react';
import { ChevronLeft, ChevronDown, ChevronRight, PlayCircle } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';
import useAppStore from '@/stores/useAppStore';
import VoicePicker from './VoicePicker';
import { getLanguages } from '@/lib/api/podcast';
import { useToast } from '@/stores/useToastStore';

const MODES = [
  { id: 'overview', label: 'Overview', desc: 'A broad tour of all uploaded material' },
  { id: 'deep-dive', label: 'Deep Dive', desc: 'In-depth analysis of key concepts' },
  { id: 'debate', label: 'Debate', desc: 'Two hosts take opposing perspectives' },
  { id: 'q-and-a', label: 'Q & A', desc: 'Interview-style question and answer' },
];

export default function PodcastModeSelector() {
  const toast = useToast();
  const create = usePodcastStore((s) => s.create);
  const startGeneration = usePodcastStore((s) => s.startGeneration);
  const setPhase = usePodcastStore((s) => s.setPhase);
  const error = usePodcastStore((s) => s.error);
  const loading = usePodcastStore((s) => s.loading);
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);

  useEffect(() => {
    if (error) toast.error(error);
  }, [error, toast]);

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
    } catch {
      
    }
  };

  const hasSources = selectedSources.length > 0;

  return (
    <div className="space-y-5 animate-fade-in">
      {}
      <button
        onClick={() => setPhase('idle')}
        className="flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors"
      >
        <ChevronLeft className="w-4 h-4" /> Back
      </button>

      <div>
        <h3 className="text-sm font-semibold text-[var(--text-primary)] mb-1">New Podcast</h3>
        <p className="text-xs text-[var(--text-muted)]">
          {hasSources
            ? `Using ${selectedSources.length} selected source${selectedSources.length > 1 ? 's' : ''}`
            : 'Select sources in the sidebar first'}
        </p>
      </div>

      {}
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

      {}
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

      {}
      <div>
        <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Language</label>
        <select
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
          className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)] focus:outline-none focus:ring-1 focus:ring-[var(--accent)]"
        >
          {languages.length > 0 ? (
            languages.map((l) => <option key={l.code} value={l.code}>{l.name}</option>)
          ) : (
            <>
              <option value="en">English</option>
              <option value="hi">Hindi</option>
              <option value="es">Spanish</option>
              <option value="fr">French</option>
              <option value="de">German</option>
              <option value="ja">Japanese</option>
              <option value="zh">Chinese</option>
              <option value="pt">Portuguese</option>
              <option value="ar">Arabic</option>
              <option value="gu">Gujarati</option>
            </>
          )}
        </select>
      </div>

      {}
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

      {}
      <button
        onClick={handleGenerate}
        disabled={!hasSources || loading}
        className="w-full py-2.5 rounded-lg bg-[var(--accent)] hover:bg-[var(--accent-light)] text-white text-sm font-medium transition-colors disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-2"
      >
        {loading ? (
          <>
            <div className="loading-spinner w-4 h-4" />
            Creating...
          </>
        ) : (
          <>
            <PlayCircle className="w-4 h-4" />
            Generate Podcast
          </>
        )}
      </button>
    </div>
  );
}

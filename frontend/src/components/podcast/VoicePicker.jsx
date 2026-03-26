'use client';

import { useEffect, useMemo, useRef, useState } from 'react';
import { Play, Pause, Volume2, User, UserRound } from 'lucide-react';
import { getVoicesForLanguage, fetchVoicePreviewAudioUrl } from '@/lib/api/podcast';

export default function VoicePicker({
  label,
  language,
  value,
  onChange,
  excludeVoiceId = null,
  disabled = false,
}) {
  const [voices, setVoices] = useState([]);
  const [loadedLanguage, setLoadedLanguage] = useState('');
  const [previewingId, setPreviewingId] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const audioRef = useRef(typeof window !== 'undefined' ? new Audio() : null);
  const loading = loadedLanguage !== language;

  useEffect(() => {
    const audio = audioRef.current;
    return () => {
      if (audio) {
        audio.pause();
        audio.src = '';
      }
      if (previewUrl) URL.revokeObjectURL(previewUrl);
    };
  }, [previewUrl]);

  useEffect(() => {
    getVoicesForLanguage(language)
      .then((data) => {
        if (Array.isArray(data)) setVoices(data);
        else if (Array.isArray(data?.voices)) setVoices(data.voices);
        else setVoices([]);
        setLoadedLanguage(language);
      })
      .catch(() => {
        setVoices([]);
        setLoadedLanguage(language);
      });
  }, [language]);

  const normalizedVoices = useMemo(
    () =>
      voices
        .map((v) => ({
          ...v,
          id: v.id || v.voice_id || v.voiceId,
          name: v.name || v.label || v.id || v.voice_id || 'Voice',
        }))
        .filter((v) => Boolean(v.id)),
    [voices]
  );

  const selectableVoices = normalizedVoices;

  const selectedVoice = selectableVoices.find((v) => v.id === value) || null;

  const handlePreview = async () => {
    if (!audioRef.current || !selectedVoice) return;

    if (previewingId === selectedVoice.id) {
      audioRef.current.pause();
      setPreviewingId(null);
      return;
    }

    try {
      if (previewUrl) {
        URL.revokeObjectURL(previewUrl);
        setPreviewUrl('');
      }
      const url = await fetchVoicePreviewAudioUrl(selectedVoice.id, language);
      setPreviewUrl(url);
      audioRef.current.src = url;
      await audioRef.current.play();
      setPreviewingId(selectedVoice.id);
      audioRef.current.onended = () => setPreviewingId(null);
    } catch {
      setPreviewingId(null);
    }
  };

  const LabelIcon = label.toLowerCase().includes('guest') ? UserRound : User;

  return (
    <div className="space-y-2">
      <label className="text-xs font-semibold text-[var(--text-secondary)] inline-flex items-center gap-1.5">
        <LabelIcon className="h-3.5 w-3.5 text-[var(--text-muted)]" />
        {label}
      </label>
      <div className="flex items-center gap-2">
        <div className="flex-1 rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] px-3 py-2">
          <select
            value={selectedVoice?.id || ''}
            onChange={(e) => onChange(e.target.value)}
            disabled={disabled || loading || selectableVoices.length === 0}
            className="podcast-language-select w-full bg-transparent text-sm text-[var(--text-primary)] focus:outline-none"
          >
            {selectableVoices.map((v) => (
              <option key={v.id} value={v.id}>
                {v.name}{v.gender ? ` (${v.gender})` : ''}
              </option>
            ))}
          </select>
        </div>
        <button
          type="button"
          disabled={disabled || !selectedVoice}
          onClick={handlePreview}
          className="inline-flex h-9 min-w-9 items-center justify-center rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] px-2 text-[var(--text-secondary)] hover:border-[var(--accent-border)] disabled:opacity-50"
          title="Test voice"
        >
          {previewingId === selectedVoice?.id ? <Pause className="h-4 w-4" /> : <Play className="h-4 w-4" />}
        </button>
      </div>
      <div className="text-[11px] text-[var(--text-muted)] flex items-center gap-1">
        <Volume2 className="h-3.5 w-3.5" />
        {loading
          ? 'Loading voices...'
          : selectedVoice
            ? selectedVoice.description || 'Voice selected'
            : 'No voice available for this language'}
      </div>
    </div>
  );
}

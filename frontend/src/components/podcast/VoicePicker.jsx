'use client';

import { useState, useEffect, useRef } from 'react';
import { Pause, Play, Check } from 'lucide-react';
import { getVoicesForLanguage, getVoicePreviewUrl } from '@/lib/api/podcast';


export default function VoicePicker({ label, language, value, onChange }) {
  const [voices, setVoices] = useState([]);
  const [previewingId, setPreviewingId] = useState(null);
  const audioRef = useRef(typeof window !== 'undefined' ? new Audio() : null);

  
  useEffect(() => {
    
    
    const audio = audioRef.current;
    return () => {
      if (audio) {
        audio.pause();
        audio.src = '';
      }
    };
  }, []);

  useEffect(() => {
    getVoicesForLanguage(language)
      .then((data) => {
        if (Array.isArray(data)) setVoices(data);
        else if (data && Array.isArray(data.voices)) setVoices(data.voices);
        else setVoices([]);
      })
      .catch(() => setVoices([]));
  }, [language]);

  const handlePreview = (voiceId) => {
    if (!audioRef.current) return;
    if (previewingId === voiceId) {
      audioRef.current.pause();
      setPreviewingId(null);
      return;
    }
    audioRef.current.src = getVoicePreviewUrl(voiceId, language);
    audioRef.current.play().catch(() => {});
    setPreviewingId(voiceId);
    audioRef.current.onended = () => setPreviewingId(null);
  };

  return (
    <div>
      <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">{label}</label>
      <div className="space-y-1 max-h-32 overflow-y-auto">
        {voices.length === 0 && (
          <p className="text-[10px] text-[var(--text-muted)] py-1">Loading voices...</p>
        )}
        {voices.map((v) => (
          <div
            key={v.id}
            onClick={() => onChange(v.id)}
            className={`flex items-center gap-2 p-2 rounded-lg cursor-pointer transition-all ${
              value === v.id
                ? 'bg-[var(--accent)] border border-[var(--accent)]'
                : 'hover:bg-[var(--surface-overlay)] border border-transparent'
            }`}
          >
            <div className="flex-1 min-w-0">
              <span className="text-xs text-[var(--text-primary)] block truncate">{v.name || v.id}</span>
              {v.gender && <span className="text-[9px] text-[var(--text-muted)] capitalize">{v.gender}</span>}
            </div>

            <button
              onClick={(e) => {
                e.stopPropagation();
                handlePreview(v.id);
              }}
              className="p-1 rounded hover:bg-[var(--surface-overlay)] transition-colors shrink-0"
              title="Preview voice"
            >
              {previewingId === v.id ? (
                <Pause className="w-3.5 h-3.5 text-[var(--accent)]" fill="currentColor" />
              ) : (
                <Play className="w-3.5 h-3.5 text-[var(--text-muted)]" fill="currentColor" />
              )}
            </button>

            {value === v.id && <Check className="w-3.5 h-3.5 text-[var(--accent)] shrink-0" strokeWidth={2.5} />}
          </div>
        ))}
      </div>
    </div>
  );
}

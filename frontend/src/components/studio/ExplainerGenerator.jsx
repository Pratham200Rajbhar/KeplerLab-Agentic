'use client';

import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  Video,
  AlertTriangle,
  Clock3,
  FileText,
  Presentation,
  RefreshCw,
  Upload,
  FileUp,
  Mic,
  MessageSquare,
  ChevronDown,
  Loader2,
  Check,
  X,
  Play,
  BookOpen,
} from 'lucide-react';

import usePresentationStore from '@/stores/usePresentationStore';
import { useToast } from '@/stores/useToastStore';
import { getPresentation, explainPptxUpload } from '@/lib/api/presentation';
import { getLanguages, getVoicesForLanguage } from '@/lib/api/podcast';
import { apiConfig } from '@/lib/api/config';

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatTimestamp(ms) {
  const total = Math.max(0, Math.floor((ms || 0) / 1000));
  const m = Math.floor(total / 60);
  const s = String(total % 60).padStart(2, '0');
  return `${m}:${s}`;
}

function resolveVideoPhase(status) {
  if (status === 'completed') return 'done';
  if (status === 'failed') return 'error';
  if (['scripting', 'generating_script'].includes(status)) return 'scripting';
  if (['audio', 'generating_audio'].includes(status)) return 'audio';
  if (['rendering', 'merging', 'composing_video'].includes(status)) return 'rendering';
  return 'idle';
}

const NARRATION_STYLES = [
  { id: 'teacher', label: '🎓 Teacher', desc: 'Warm, clear, step-by-step' },
  { id: 'storyteller', label: '📖 Storyteller', desc: 'Narrative & engaging' },
  { id: 'expert_analyst', label: '📊 Analyst', desc: 'Data-driven, precise' },
  { id: 'conversational', label: '💬 Conversational', desc: 'Casual & direct' },
  { id: 'professional', label: '🎙️ Professional', desc: 'Polished executive style' },
];

// ── VoiceSelector ─────────────────────────────────────────────────────────────

function VoiceSelector({ language, onLanguageChange, voiceId, onVoiceChange }) {
  const [languages, setLanguages] = useState([]);
  const [voices, setVoices] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getLanguages().then(data => {
      setLanguages(data || []);
      setLoading(false);
    }).catch(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (!language) return;
    getVoicesForLanguage(language).then(data => {
      const list = data || [];
      setVoices(list);
      if (list.length > 0 && !list.find(v => v.id === voiceId)) {
        onVoiceChange(list[0].id);
      }
    }).catch(() => {});
  }, [language]);

  if (loading) return <div className="text-[11px] text-[var(--text-muted)]">Loading voices…</div>;

  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="space-y-1">
        <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
          Language
        </label>
        <div className="relative">
          <select
            value={language}
            onChange={e => onLanguageChange(e.target.value)}
            className="w-full appearance-none px-2.5 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] text-[12px] text-[var(--text-primary)] pr-7 focus:outline-none focus:border-[var(--accent)]"
          >
            {languages.map(l => (
              <option key={l.code} value={l.code}>{l.name}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)] pointer-events-none" />
        </div>
      </div>
      <div className="space-y-1">
        <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
          Voice
        </label>
        <div className="relative">
          <select
            value={voiceId}
            onChange={e => onVoiceChange(e.target.value)}
            className="w-full appearance-none px-2.5 py-2 rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)] text-[12px] text-[var(--text-primary)] pr-7 focus:outline-none focus:border-[var(--accent)]"
          >
            {voices.map(v => (
              <option key={v.id} value={v.id}>{v.name || v.id}</option>
            ))}
          </select>
          <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-[var(--text-muted)] pointer-events-none" />
        </div>
      </div>
    </div>
  );
}

// ── StylePicker ───────────────────────────────────────────────────────────────

function StylePicker({ value, onChange }) {
  return (
    <div className="space-y-1">
      <label className="text-[10px] font-medium text-[var(--text-secondary)] uppercase tracking-wider">
        Narration Style
      </label>
      <div className="grid grid-cols-1 gap-1">
        {NARRATION_STYLES.map(s => (
          <button
            key={s.id}
            onClick={() => onChange(s.id)}
            className={`flex items-center gap-2 px-2.5 py-2 rounded-lg border text-left transition-all ${
              value === s.id
                ? 'border-[var(--accent)] bg-[var(--accent-subtle)] text-[var(--accent)]'
                : 'border-[var(--border)] text-[var(--text-secondary)] hover:border-[var(--accent-border,var(--accent))]'
            }`}
          >
            <span className="text-[12px] font-medium flex-1">{s.label}</span>
            <span className="text-[10px] text-[var(--text-muted)]">{s.desc}</span>
            {value === s.id && <Check className="w-3 h-3 text-[var(--accent)] shrink-0" />}
          </button>
        ))}
      </div>
    </div>
  );
}

// ── UploadTab — PPTX upload + explain ────────────────────────────────────────

function UploadTab({ onStarted }) {
  const toast = useToast();
  const dropRef = useRef(null);
  const [file, setFile] = useState(null);
  const [dragging, setDragging] = useState(false);
  const [language, setLanguage] = useState('en');
  const [voiceId, setVoiceId] = useState('');
  const [style, setStyle] = useState('teacher');
  const [notes, setNotes] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleDrop = useCallback((e) => {
    e.preventDefault();
    setDragging(false);
    const f = e.dataTransfer.files?.[0];
    if (f && /\.(pptx?|ppt)$/i.test(f.name)) setFile(f);
    else toast.error('Please upload a .pptx or .ppt file');
  }, [toast]);

  const handleFile = (e) => {
    const f = e.target.files?.[0];
    if (f) setFile(f);
  };

  const handleExplain = async () => {
    if (!file || !voiceId) return;
    setLoading(true);
    try {
      const result = await explainPptxUpload({
        file,
        voiceId,
        narrationLanguage: language,
        narrationStyle: style,
        narrationNotes: notes,
      });
      toast.success('Extraction started! Video will be ready soon.');
      onStarted?.(result);
    } catch (err) {
      toast.error(err.message || 'Failed to start explanation');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      {/* Drop zone */}
      <div
        ref={dropRef}
        onDrop={handleDrop}
        onDragOver={e => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        className={`relative rounded-2xl border-2 border-dashed p-8 text-center transition-all cursor-pointer ${
          dragging
            ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
            : file
            ? 'border-[var(--accent)] bg-[var(--accent-subtle)]'
            : 'border-[var(--border)] hover:border-[var(--accent-border,var(--accent))] hover:bg-[var(--surface-overlay)]'
        }`}
        onClick={() => document.getElementById('pptx-file-input').click()}
      >
        <input
          id="pptx-file-input"
          type="file"
          accept=".pptx,.ppt"
          className="hidden"
          onChange={handleFile}
        />
        {file ? (
          <div className="flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-[var(--accent-subtle)] border border-[var(--accent-border,var(--accent))] flex items-center justify-center">
              <FileUp className="w-5 h-5 text-[var(--accent)]" />
            </div>
            <span className="text-[13px] font-semibold text-[var(--accent)]">{file.name}</span>
            <span className="text-[11px] text-[var(--text-muted)]">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </span>
            <button
              onClick={e => { e.stopPropagation(); setFile(null); }}
              className="text-[10px] text-[var(--text-muted)] hover:text-[var(--danger)] flex items-center gap-1"
            >
              <X className="w-3 h-3" /> Remove
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center gap-2">
            <div className="w-10 h-10 rounded-xl bg-[var(--surface-overlay)] border border-[var(--border)] flex items-center justify-center">
              <Upload className="w-5 h-5 text-[var(--text-muted)]" />
            </div>
            <p className="text-[13px] font-semibold text-[var(--text-primary)]">
              Drop your PPTX here
            </p>
            <p className="text-[11px] text-[var(--text-muted)]">
              or click to browse (.pptx, .ppt · max 100MB)
            </p>
          </div>
        )}
      </div>

      {/* Voice config */}
      <VoiceSelector
        language={language}
        onLanguageChange={setLanguage}
        voiceId={voiceId}
        onVoiceChange={setVoiceId}
      />

      {/* Narration style */}
      <StylePicker value={style} onChange={setStyle} />

      {/* Advanced notes */}
      <div>
        <button
          onClick={() => setShowAdvanced(v => !v)}
          className="text-[11px] text-[var(--accent)] hover:underline flex items-center gap-1"
        >
          <ChevronDown className={`w-3 h-3 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
          Additional instructions {showAdvanced ? '(hide)' : '(optional)'}
        </button>
        {showAdvanced && (
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="e.g., Focus on practical implications for engineering teams. Avoid jargon."
            rows={3}
            className="mt-2 w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] text-[12px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] resize-none"
          />
        )}
      </div>

      {/* Submit button */}
      <button
        id="explain-pptx-btn"
        onClick={handleExplain}
        disabled={!file || !voiceId || loading}
        className="w-full py-3 px-4 rounded-xl font-semibold text-[13px] text-white flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg transition-all"
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-light, var(--accent)))' }}
      >
        {loading
          ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</>
          : <><Play className="w-4 h-4" /> Explain This Deck</>
        }
      </button>

      {/* Info note */}
      <div className="rounded-xl bg-[var(--surface-overlay)] border border-[var(--border)] p-3 text-[11px] text-[var(--text-muted)] space-y-1">
        <p className="font-medium text-[var(--text-secondary)] flex items-center gap-1.5">
          <BookOpen className="w-3.5 h-3.5 text-[var(--accent)]" />
          How it works
        </p>
        <ul className="space-y-0.5 list-none pl-0">
          <li className="flex items-start gap-1.5"><span className="text-[var(--accent)] shrink-0">1.</span> LibreOffice renders each slide to 1280×720</li>
          <li className="flex items-start gap-1.5"><span className="text-[var(--accent)] shrink-0">2.</span> Vision AI analyzes each slide image (charts, diagrams, text)</li>
          <li className="flex items-start gap-1.5"><span className="text-[var(--accent)] shrink-0">3.</span> Educator-quality narration is generated per slide</li>
          <li className="flex items-start gap-1.5"><span className="text-[var(--accent)] shrink-0">4.</span> TTS voice + ffmpeg produce a polished explainer video</li>
        </ul>
      </div>
    </div>
  );
}

// ── VideoTab ──────────────────────────────────────────────────────────────────

function VideoTab({
  videoPlaybackUrl,
  subtitleTrackUrl,
  persistedVideo,
  resolvedPhase,
  resolvedError,
  videoProgress,
  resolvedDurationMs,
  resolvedTranscriptSegments,
  resolvedSubtitleTracks,
  transcriptRows,
  resolvedTranscriptStatus,
  resolvedTranscriptError,
  resolvedTranscriptText,
}) {
  const [expandedScript, setExpandedScript] = useState(null);

  const scripts = persistedVideo?.scripts || [];

  return (
    <div className="space-y-4">
      {/* Video player */}
      <div className="rounded-2xl overflow-hidden border border-[var(--border)] bg-black">
        {videoPlaybackUrl ? (
          <video
            src={videoPlaybackUrl}
            controls
            className="w-full aspect-video"
            preload="metadata"
          >
            {subtitleTrackUrl && (
              <track
                kind="subtitles"
                src={subtitleTrackUrl}
                srcLang={persistedVideo?.transcriptLanguage || 'en'}
                label="Subtitles"
                default
              />
            )}
          </video>
        ) : (
          <div className="w-full aspect-video flex items-center justify-center px-4">
            {resolvedPhase === 'error' ? (
              <div className="flex flex-col items-center gap-2 text-[var(--danger)]">
                <AlertTriangle className="w-8 h-8" />
                <span className="text-[12px] text-center">{resolvedError || 'Generation failed'}</span>
              </div>
            ) : resolvedPhase === 'scripting' ? (
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="loading-spinner w-8 h-8 text-[var(--accent)]" />
                <div>
                  <p className="text-[13px] font-semibold text-white mb-0.5">
                    {videoProgress?.vision ? '🔍 Vision AI reading slide images…' : '✍️ Writing narration scripts…'}
                  </p>
                  <p className="text-[11px] text-white/50">{videoProgress?.message || ''}</p>
                </div>
              </div>
            ) : resolvedPhase === 'audio' ? (
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="loading-spinner w-8 h-8 text-[var(--accent)]" />
                <p className="text-[13px] font-semibold text-white">🎙️ Synthesizing voice audio…</p>
                <p className="text-[11px] text-white/50">{videoProgress?.message || ''}</p>
              </div>
            ) : resolvedPhase === 'rendering' ? (
              <div className="flex flex-col items-center gap-3 text-center">
                <div className="loading-spinner w-8 h-8 text-[var(--accent)]" />
                <p className="text-[13px] font-semibold text-white">🎬 Composing final video…</p>
              </div>
            ) : (
              <p className="text-[12px] text-white/40 text-center">
                No explainer video yet.<br/>Configure and generate one below.
              </p>
            )}
          </div>
        )}
      </div>

      {/* Duration + subtitle downloads */}
      <div className="flex items-center gap-3 flex-wrap">
        {resolvedDurationMs > 0 && (
          <span className="text-[11px] text-[var(--text-muted)] inline-flex items-center gap-1.5">
            <Clock3 className="w-3.5 h-3.5" />
            {formatTimestamp(resolvedDurationMs)}
          </span>
        )}
        {resolvedSubtitleTracks.map((track, i) => (
          <a
            key={i}
            href={`${apiConfig.baseUrl}${track.url}`}
            target="_blank"
            rel="noreferrer"
            className="text-[11px] text-[var(--accent)] hover:underline inline-flex items-center gap-1"
          >
            <FileText className="w-3 h-3" />
            {track.format.toUpperCase()} subtitles
          </a>
        ))}
      </div>

      {/* AI Scripts preview */}
      {scripts.length > 0 && (
        <div className="space-y-1.5">
          <p className="text-[11px] font-semibold text-[var(--text-secondary)] flex items-center gap-1.5">
            <MessageSquare className="w-3.5 h-3.5 text-[var(--accent)]" />
            AI Narration Scripts ({scripts.length} slides)
          </p>
          <div className="space-y-1 max-h-[220px] overflow-y-auto pr-1">
            {scripts.map((script, i) => (
              <div
                key={i}
                className="rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)]/50 overflow-hidden"
              >
                <button
                  onClick={() => setExpandedScript(expandedScript === i ? null : i)}
                  className="w-full flex items-center justify-between px-3 py-2 text-left"
                >
                  <span className="text-[11px] font-medium text-[var(--text-secondary)]">
                    Slide {i + 1} narration
                  </span>
                  <ChevronDown className={`w-3 h-3 text-[var(--text-muted)] transition-transform ${expandedScript === i ? 'rotate-180' : ''}`} />
                </button>
                {expandedScript === i && (
                  <div className="px-3 pb-2.5">
                    <p className="text-[11px] text-[var(--text-muted)] leading-relaxed italic">
                      "{script}"
                    </p>
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Transcript */}
      <div className="space-y-1.5">
        <p className="text-[11px] font-semibold text-[var(--text-secondary)] flex items-center gap-1.5">
          <FileText className="w-3.5 h-3.5 text-[var(--accent)]" />
          Transcript
        </p>
        {transcriptRows.length > 0 ? (
          <div className="space-y-1.5 max-h-[280px] overflow-y-auto pr-1">
            {transcriptRows.map((row, i) => (
              <div
                key={row.key || i}
                className="rounded-lg border border-[var(--border)] bg-[var(--surface-overlay)]/40 px-2.5 py-2"
              >
                <div className="flex items-start gap-2">
                  <span className="shrink-0 text-[10px] font-semibold text-[var(--accent)] bg-[var(--accent-subtle)] border border-[var(--accent-border)] rounded-md px-1.5 py-0.5 mt-0.5">
                    {row.timestamp}–{row.endTimestamp}
                  </span>
                  <p className="text-[11px] text-[var(--text-primary)] leading-snug">{row.transcript}</p>
                </div>
              </div>
            ))}
          </div>
        ) : resolvedTranscriptText ? (
          <p className="text-[11px] text-[var(--text-muted)] leading-relaxed whitespace-pre-wrap">
            {resolvedTranscriptText}
          </p>
        ) : resolvedTranscriptStatus === 'failed' ? (
          <p className="text-[11px] text-red-300">
            Whisper transcription failed{resolvedTranscriptError ? `: ${resolvedTranscriptError}` : '.'}
          </p>
        ) : (
          <p className="text-[11px] text-[var(--text-muted)]">
            Transcript will appear after Whisper processing completes.
          </p>
        )}
      </div>
    </div>
  );
}

// ── ExistingTab ───────────────────────────────────────────────────────────────

function ExistingTab({ historyItems, onOpenPresentation, selectedItem, activePresentationId, onHydrate, loadingPresentation, onStartVideo }) {
  const [language, setLanguage] = useState('en');
  const [voiceId, setVoiceId] = useState('');
  const [style, setStyle] = useState('teacher');
  const [notes, setNotes] = useState('');
  const [showAdvanced, setShowAdvanced] = useState(false);

  if (!historyItems.length) {
    return (
      <div className="flex flex-col items-center justify-center py-12 text-center gap-4">
        <div className="w-14 h-14 rounded-2xl bg-[var(--surface-overlay)] border border-[var(--border)] flex items-center justify-center">
          <Presentation className="w-7 h-7 text-[var(--text-muted)]" />
        </div>
        <div>
          <p className="text-[13px] font-semibold text-[var(--text-primary)] mb-1">No presentations yet</p>
          <p className="text-[11px] text-[var(--text-muted)]">
            Generate a presentation first, then explain it here.
          </p>
        </div>
        <button onClick={onOpenPresentation} className="text-[12px] text-[var(--accent)] hover:underline">
          Open Presentation Builder →
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Selected presentation info */}
      {selectedItem && (
        <div className="flex items-start justify-between gap-2 p-3 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)]">
          <div className="min-w-0">
            <p className="text-[12px] font-semibold text-[var(--text-primary)] truncate">{selectedItem.title || 'Presentation'}</p>
            <p className="text-[10px] text-[var(--text-muted)]">
              {selectedItem.data?.slides?.length || '?'} slides
            </p>
          </div>
          <button
            onClick={() => activePresentationId && onHydrate(activePresentationId)}
            disabled={loadingPresentation}
            className="p-1.5 rounded-lg border border-[var(--border)] text-[var(--text-muted)] hover:text-[var(--accent)] transition-colors"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loadingPresentation ? 'animate-spin' : ''}`} />
          </button>
        </div>
      )}

      {/* Voice config */}
      <VoiceSelector
        language={language}
        onLanguageChange={setLanguage}
        voiceId={voiceId}
        onVoiceChange={setVoiceId}
      />

      {/* Style picker */}
      <StylePicker value={style} onChange={setStyle} />

      {/* Advanced */}
      <div>
        <button
          onClick={() => setShowAdvanced(v => !v)}
          className="text-[11px] text-[var(--accent)] hover:underline flex items-center gap-1"
        >
          <ChevronDown className={`w-3 h-3 transition-transform ${showAdvanced ? 'rotate-180' : ''}`} />
          Additional instructions (optional)
        </button>
        {showAdvanced && (
          <textarea
            value={notes}
            onChange={e => setNotes(e.target.value)}
            placeholder="e.g. Focus on technical depth. Assume CS background."
            rows={2}
            className="mt-2 w-full px-3 py-2 rounded-xl border border-[var(--border)] bg-[var(--surface-overlay)] text-[12px] text-[var(--text-primary)] placeholder:text-[var(--text-muted)] focus:outline-none focus:border-[var(--accent)] resize-none"
          />
        )}
      </div>

      <button
        id="explain-existing-btn"
        onClick={() => onStartVideo({ presentationId: activePresentationId, voiceId, narrationLanguage: language, narrationStyle: style, narrationNotes: notes })}
        disabled={!activePresentationId || !voiceId}
        className="w-full py-3 px-4 rounded-xl font-semibold text-[13px] text-white flex items-center justify-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg transition-all"
        style={{ background: 'linear-gradient(135deg, var(--accent), var(--accent-light, var(--accent)))' }}
      >
        <Mic className="w-4 h-4" />
        Generate Explainer Video
      </button>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ExplainerGenerator({ onSaved, onOpenPresentation, historyItems = [], onStartVideo }) {
  const toast = useToast();

  const presentationId = usePresentationStore(s => s.presentationId);
  const setPresentationId = usePresentationStore(s => s.setPresentationId);
  const setPresentationData = usePresentationStore(s => s.setPresentationData);
  const setVideoData = usePresentationStore(s => s.setVideoData);
  const videoPhase = usePresentationStore(s => s.videoPhase);
  const videoProgress = usePresentationStore(s => s.videoProgress);
  const videoUrl = usePresentationStore(s => s.videoUrl);
  const videoDurationMs = usePresentationStore(s => s.videoDurationMs);
  const videoError = usePresentationStore(s => s.videoError);

  const [activeTab, setActiveTab] = useState('video'); // 'existing' | 'upload' | 'video'
  const [loadingPresentation, setLoadingPresentation] = useState(false);
  const [selectedPresentationData, setSelectedPresentationData] = useState(null);

  const presentationItems = useMemo(
    () => historyItems.filter(item => item.content_type === 'presentation' && !item.processing),
    [historyItems],
  );

  const activePresentationId = useMemo(() => {
    if (presentationId && presentationItems.some(item => item.id === presentationId)) {
      return presentationId;
    }
    const withVideo = presentationItems.find(item => Boolean(item.data?.video?.videoUrl));
    return withVideo?.id || presentationItems[0]?.id || null;
  }, [presentationId, presentationItems]);

  const selectedItem = useMemo(
    () => presentationItems.find(item => item.id === activePresentationId) || null,
    [presentationItems, activePresentationId],
  );

  const hydratePresentation = useCallback(async (id, silent = false) => {
    if (!id) return;
    try {
      setLoadingPresentation(true);
      const payload = await getPresentation(id);
      setSelectedPresentationData(payload);
      setPresentationData(payload);
      if (payload?.video) setVideoData(payload.video);
    } catch (err) {
      if (!silent) toast.error(err.message || 'Failed to load presentation');
    } finally {
      setLoadingPresentation(false);
    }
  }, [setPresentationData, setVideoData, toast]);

  useEffect(() => {
    if (!activePresentationId) return;
    if (presentationId !== activePresentationId) setPresentationId(activePresentationId);
    hydratePresentation(activePresentationId, true);
  }, [activePresentationId]);

  useEffect(() => {
    if (videoPhase === 'done') {
      onSaved?.();
      if (activePresentationId) hydratePresentation(activePresentationId, true);
      setActiveTab('video');
    }
  }, [videoPhase]);

  const persistedVideo =
    selectedPresentationData?.video ||
    selectedPresentationData?.data?.video ||
    selectedItem?.data?.video ||
    null;

  const resolvedTranscriptSegments = useMemo(() => {
    const raw = persistedVideo?.transcriptSegments;
    if (!Array.isArray(raw)) return [];
    return raw
      .map(s => ({ start: Number(s?.start) || 0, end: Number(s?.end) || 0, text: String(s?.text || '').trim() }))
      .filter(s => s.text);
  }, [persistedVideo?.transcriptSegments]);

  const resolvedSubtitleTracks = useMemo(() => {
    return (persistedVideo?.subtitleTracks || [])
      .map(t => ({ format: String(t?.format || '').toLowerCase(), url: t?.url || null }))
      .filter(t => t.url);
  }, [persistedVideo?.subtitleTracks]);

  const vttTrack = resolvedSubtitleTracks.find(t => t.format === 'vtt') || null;
  const isActive = Boolean(activePresentationId && activePresentationId === presentationId);

  const resolvedVideoUrl = isActive
    ? (videoUrl || persistedVideo?.videoUrl || null)
    : (persistedVideo?.videoUrl || null);

  const fallbackDurationMs = resolvedTranscriptSegments.length
    ? Math.round((resolvedTranscriptSegments[resolvedTranscriptSegments.length - 1]?.end || 0) * 1000)
    : 0;

  const resolvedDurationMs = isActive
    ? (videoDurationMs || persistedVideo?.durationMs || fallbackDurationMs)
    : (persistedVideo?.durationMs || fallbackDurationMs);

  const resolvedPhase = isActive ? videoPhase : resolveVideoPhase(persistedVideo?.status);
  const resolvedError = isActive ? videoError : (persistedVideo?.error || null);

  const videoPlaybackUrl = resolvedVideoUrl ? `${apiConfig.baseUrl}${resolvedVideoUrl}` : null;
  const subtitleTrackUrl = vttTrack?.url ? `${apiConfig.baseUrl}${vttTrack.url}` : null;

  const transcriptRows = useMemo(() => {
    return resolvedTranscriptSegments.map((s, i) => ({
      timestamp: formatTimestamp(Math.round(s.start * 1000)),
      endTimestamp: formatTimestamp(Math.round(s.end * 1000)),
      transcript: s.text,
      key: `${s.start}-${i}`,
    }));
  }, [resolvedTranscriptSegments]);



  const handleUploadStarted = (result) => {
    setActiveTab('video');
    toast.info('Processing your deck — video will appear here when ready.');
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto" id="explainer-generator-panel">

      {/* Tab content */}
      <div className="flex-1 overflow-y-auto p-4">
        {activeTab === 'video' && (
          <VideoTab
            videoPlaybackUrl={videoPlaybackUrl}
            subtitleTrackUrl={subtitleTrackUrl}
            persistedVideo={persistedVideo}
            resolvedPhase={resolvedPhase}
            resolvedError={resolvedError}
            videoProgress={videoProgress}
            resolvedDurationMs={resolvedDurationMs}
            resolvedTranscriptSegments={resolvedTranscriptSegments}
            resolvedSubtitleTracks={resolvedSubtitleTracks}
            transcriptRows={transcriptRows}
            resolvedTranscriptStatus={persistedVideo?.transcriptStatus || 'idle'}
            resolvedTranscriptError={persistedVideo?.transcriptError || null}
            resolvedTranscriptText={String(persistedVideo?.transcriptText || '').trim()}
          />
        )}

        {activeTab === 'existing' && (
          <ExistingTab
            historyItems={presentationItems}
            onOpenPresentation={onOpenPresentation}
            selectedItem={selectedItem}
            activePresentationId={activePresentationId}
            onHydrate={hydratePresentation}
            loadingPresentation={loadingPresentation}
            onStartVideo={(opts) => {
              setActiveTab('video');
              onStartVideo?.(opts);
            }}
          />
        )}

        {activeTab === 'upload' && (
          <UploadTab onStarted={handleUploadStarted} />
        )}
      </div>
    </div>
  );
}

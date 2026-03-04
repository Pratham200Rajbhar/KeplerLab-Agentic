'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import {
  X, ChevronRight, ChevronLeft, Loader2, Check, FileText, Presentation,
  Globe, Mic, Wand2
} from 'lucide-react';
import Modal from '@/components/ui/Modal';
import { checkExplainerPresentations, generateExplainer, getExplainerStatus } from '@/lib/api/explainer';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';

const STEPS = ['select', 'configure', 'generating', 'complete'];

export default function ExplainerDialog({ onClose, onComplete }) {
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);
  const toast = useToast();

  const [step, setStep] = useState('select'); // select | configure | generating | complete
  const [presentations, setPresentations] = useState([]);
  const [selectedPptId, setSelectedPptId] = useState(null);
  const [createNewPpt, setCreateNewPpt] = useState(false);
  const [loadingPpts, setLoadingPpts] = useState(true);

  // Config
  const [pptLanguage, setPptLanguage] = useState('en');
  const [narrationLanguage, setNarrationLanguage] = useState('en');
  const [voiceGender, setVoiceGender] = useState('female');

  // Generation
  const [progress, setProgress] = useState({ message: 'Starting...', pct: 0 });
  const [explainerId, setExplainerId] = useState(null);
  const [result, setResult] = useState(null);
  const pollRef = useRef(null);
  const abortRef = useRef(null);

  // Load presentations for the selected sources.
  // All setState calls happen inside async .then/.catch callbacks — never synchronously
  // in the effect body — to avoid cascading renders.
  useEffect(() => {
    if (!currentNotebook?.id) return;

    const materialIds = [...selectedSources];
    const controller = new AbortController();
    abortRef.current = controller;

    // If no sources are selected resolve immediately with an empty list
    const fetchPromise = materialIds.length
      ? checkExplainerPresentations(materialIds, currentNotebook.id, { signal: controller.signal })
      : Promise.resolve({ presentations: [] });

    fetchPromise
      .then((data) => {
        setPresentations(data?.presentations || []);
        setLoadingPpts(false);
      })
      .catch((err) => {
        if (err.name !== 'AbortError') {
          setLoadingPpts(false);
        }
      });

    return () => controller.abort();
  }, [currentNotebook?.id, selectedSources]);

  // Poll status during generation
  useEffect(() => {
    if (step !== 'generating' || !explainerId) return;

    const poll = async () => {
      try {
        const status = await getExplainerStatus(explainerId);
        if (status.status === 'completed') {
          setResult(status);
          setStep('complete');
          clearInterval(pollRef.current);
        } else if (status.status === 'failed') {
          toast.error(status.error || 'Explainer generation failed');
          setStep('configure');
          clearInterval(pollRef.current);
        } else {
          setProgress({
            message: status.message || 'Processing...',
            pct: (status.progress || 0) * 100,
          });
        }
      } catch {
        // transient error, keep polling
      }
    };

    pollRef.current = setInterval(poll, 3000);
    poll();

    return () => clearInterval(pollRef.current);
  }, [step, explainerId, toast]);

  const handleGenerate = async () => {
    try {
      setStep('generating');
      const controller = new AbortController();
      abortRef.current = controller;

      const data = await generateExplainer({
        materialIds: [...selectedSources],
        notebookId: currentNotebook.id,
        pptLanguage,
        narrationLanguage,
        voiceGender,
        createNewPpt: createNewPpt || !selectedPptId,
        presentationId: selectedPptId || undefined,
        signal: controller.signal,
      });

      if (data?.explainer_id) {
        setExplainerId(data.explainer_id);
      } else {
        toast.error('Failed to start explainer generation');
        setStep('configure');
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        toast.error(err.message || 'Generation failed');
        setStep('configure');
      }
    }
  };

  const handleComplete = () => {
    onComplete?.(result);
    onClose();
  };

  const handleCancel = () => {
    abortRef.current?.abort();
    clearInterval(pollRef.current);
    onClose();
  };

  return (
    <Modal onClose={handleCancel} maxWidth="lg">
      <div className="flex items-center justify-between px-6 py-4 border-b border-[var(--border)]">
        <div className="flex items-center gap-2">
          <Wand2 className="w-5 h-5 text-[var(--accent)]" />
          <h3 className="text-base font-semibold text-[var(--text-primary)]">AI Explainer</h3>
        </div>
        <button onClick={handleCancel} className="p-1 rounded-lg hover:bg-[var(--surface-overlay)] transition-colors" aria-label="Close explainer dialog">
          <X className="w-4 h-4 text-[var(--text-muted)]" />
        </button>
      </div>

      {/* Step indicator */}
      <div className="flex items-center gap-1 px-6 pt-4">
        {STEPS.map((s, i) => (
          <div key={s} className="flex items-center gap-1">
            <div className={`w-2 h-2 rounded-full ${
              STEPS.indexOf(step) >= i ? 'bg-[var(--accent)]' : 'bg-[var(--border)]'
            }`} />
            {i < STEPS.length - 1 && <div className="w-6 h-px bg-[var(--border)]" />}
          </div>
        ))}
      </div>

      <div className="px-6 py-5 min-h-[300px]">
        {/* Step: Select Presentation */}
        {step === 'select' && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h4 className="text-sm font-medium text-[var(--text-primary)] mb-1">Presentation Source</h4>
              <p className="text-xs text-[var(--text-muted)]">Choose an existing presentation or create a new one</p>
            </div>

            {loadingPpts ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-[var(--accent)] animate-spin" />
              </div>
            ) : (
              <div className="space-y-2">
                {/* Create new option */}
                <button
                  onClick={() => { setCreateNewPpt(true); setSelectedPptId(null); }}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
                    createNewPpt
                      ? 'border-[var(--accent)] bg-[var(--accent)]'
                      : 'border-[var(--border)] hover:border-[var(--text-muted)]'
                  }`}
                >
                  <Presentation className="w-5 h-5 text-[var(--accent)]" />
                  <div className="text-left">
                    <p className="text-sm font-medium text-[var(--text-primary)]">Create new presentation</p>
                    <p className="text-[10px] text-[var(--text-muted)]">AI will generate slides from selected sources</p>
                  </div>
                  {createNewPpt && <Check className="w-4 h-4 text-[var(--accent)] ml-auto" />}
                </button>

                {/* Existing presentations */}
                {presentations.map((ppt) => (
                  <button
                    key={ppt.id}
                    onClick={() => { setSelectedPptId(ppt.id); setCreateNewPpt(false); }}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
                      selectedPptId === ppt.id
                        ? 'border-[var(--accent)] bg-[var(--accent)]'
                        : 'border-[var(--border)] hover:border-[var(--text-muted)]'
                    }`}
                  >
                    <FileText className="w-5 h-5 text-[var(--text-muted)]" />
                    <div className="text-left flex-1 min-w-0">
                      <p className="text-sm font-medium text-[var(--text-primary)] truncate">{ppt.title || ppt.id}</p>
                      <p className="text-[10px] text-[var(--text-muted)]">{ppt.slide_count || '?'} slides</p>
                    </div>
                    {selectedPptId === ppt.id && <Check className="w-4 h-4 text-[var(--accent)]" />}
                  </button>
                ))}
              </div>
            )}

            <div className="flex justify-end">
              <button
                onClick={() => setStep('configure')}
                disabled={!createNewPpt && !selectedPptId}
                className="flex items-center gap-1 px-4 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-light)] transition-colors disabled:opacity-40"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {/* Step: Configure */}
        {step === 'configure' && (
          <div className="space-y-4 animate-fade-in">
            <div>
              <h4 className="text-sm font-medium text-[var(--text-primary)] mb-1">Configuration</h4>
              <p className="text-xs text-[var(--text-muted)]">Customize your explainer video</p>
            </div>

            {/* PPT Language */}
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
                <Globe className="inline w-3.5 h-3.5 mr-1" /> Slide Language
              </label>
              <select
                value={pptLanguage}
                onChange={(e) => setPptLanguage(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)]"
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>

            {/* Narration Language */}
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">
                <Mic className="inline w-3.5 h-3.5 mr-1" /> Narration Language
              </label>
              <select
                value={narrationLanguage}
                onChange={(e) => setNarrationLanguage(e.target.value)}
                className="w-full px-3 py-2 text-sm rounded-lg bg-[var(--surface)] border border-[var(--border)] text-[var(--text-primary)]"
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
            </div>

            {/* Voice */}
            <div>
              <label className="text-xs font-medium text-[var(--text-secondary)] mb-1.5 block">Voice</label>
              <div className="flex gap-2">
                {['female', 'male'].map((v) => (
                  <button
                    key={v}
                    onClick={() => setVoiceGender(v)}
                    className={`flex-1 py-2 rounded-lg text-xs font-medium capitalize transition-all ${
                      voiceGender === v
                        ? 'bg-[var(--accent)] text-white'
                        : 'bg-[var(--surface)] border border-[var(--border)] text-[var(--text-secondary)]'
                    }`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => setStep('select')}
                className="flex items-center gap-1 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)]"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleGenerate}
                className="px-5 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-light)] transition-colors"
              >
                Generate Explainer
              </button>
            </div>
          </div>
        )}

        {/* Step: Generating */}
        {step === 'generating' && (
          <div className="flex flex-col items-center justify-center py-10 animate-fade-in">
            <Loader2 className="w-8 h-8 text-[var(--accent)] animate-spin mb-4" />
            <p className="text-sm font-medium text-[var(--text-primary)] mb-1">{progress.message}</p>
            <div className="w-48 h-1.5 rounded-full bg-[var(--surface)] mt-3 overflow-hidden">
              <div
                className="h-full rounded-full bg-[var(--accent)] transition-all"
                style={{ width: `${progress.pct}%` }}
              />
            </div>
            <p className="text-[10px] text-[var(--text-muted)] mt-2">{Math.round(progress.pct)}% complete</p>
          </div>
        )}

        {/* Step: Complete */}
        {step === 'complete' && (
          <div className="flex flex-col items-center justify-center py-10 animate-fade-in">
            <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
              <Check className="w-6 h-6 text-green-400" />
            </div>
            <p className="text-sm font-medium text-[var(--text-primary)] mb-1">Explainer Ready!</p>
            <p className="text-xs text-[var(--text-muted)]">Your video explainer has been generated</p>
            <button
              onClick={handleComplete}
              className="mt-6 px-5 py-2 rounded-lg bg-[var(--accent)] text-white text-sm font-medium hover:bg-[var(--accent-light)] transition-colors"
            >
              View Explainer
            </button>
          </div>
        )}
      </div>
    </Modal>
  );
}

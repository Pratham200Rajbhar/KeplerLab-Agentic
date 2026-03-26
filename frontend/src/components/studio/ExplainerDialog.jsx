'use client';

import { useState, useEffect, useRef } from 'react';
import {
  X, ChevronRight, ChevronLeft, Loader2, Check, FileText, Presentation,
  Globe, Mic, Sparkles
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

  const [step, setStep] = useState('select'); 
  const [presentations, setPresentations] = useState([]);
  const [selectedPptId, setSelectedPptId] = useState(null);
  const [createNewPpt, setCreateNewPpt] = useState(false);
  const [loadingPpts, setLoadingPpts] = useState(true);

  
  const [pptLanguage, setPptLanguage] = useState('en');
  const [narrationLanguage, setNarrationLanguage] = useState('en');
  const [voiceGender, setVoiceGender] = useState('female');

  
  const [progress, setProgress] = useState({ message: 'Starting...', pct: 0 });
  const [explainerId, setExplainerId] = useState(null);
  const [result, setResult] = useState(null);
  const pollRef = useRef(null);
  const abortRef = useRef(null);

  
  useEffect(() => {
    if (!currentNotebook?.id) return;

    const materialIds = [...selectedSources];
    const controller = new AbortController();
    abortRef.current = controller;

    
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
            pct: status.progress || 0,
          });
        }
      } catch {
        
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
      <div className="studio-dialog-v3">
        <div className="studio-dialog-v3-header">
          <div className="studio-dialog-v3-icon">
            <span className="material-symbols-outlined" style={{ fontSize: 18 }}>auto_awesome</span>
          </div>
          <div>
            <h3 className="studio-dialog-v3-title">AI Explainer</h3>
            <p className="studio-dialog-v3-subtitle">Build narrated explainers from your selected sources</p>
          </div>
          <button onClick={handleCancel} className="studio-dialog-v3-close" aria-label="Close explainer dialog">
            <X className="w-4 h-4" />
          </button>
        </div>

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

        <div className="studio-dialog-v3-body min-h-[320px]">
        {step === 'select' && (
          <div className="space-y-4 animate-fade-in">
              <div className="studio-dialog-v3-note flex items-center gap-2">
                <Sparkles className="w-3.5 h-3.5 text-[var(--accent)]" />
                <span>Choose a source presentation or let AI create a fresh one.</span>
              </div>

            {loadingPpts ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-[var(--accent)] animate-spin" />
              </div>
            ) : (
                <div className="space-y-2 studio-dialog-v3-section">
                <button
                  onClick={() => { setCreateNewPpt(true); setSelectedPptId(null); }}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
                    createNewPpt
                        ? 'border-[var(--accent-border)] bg-[var(--accent-subtle)]'
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

                {presentations.map((ppt) => (
                  <button
                    key={ppt.id}
                    onClick={() => { setSelectedPptId(ppt.id); setCreateNewPpt(false); }}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all ${
                      selectedPptId === ppt.id
                          ? 'border-[var(--accent-border)] bg-[var(--accent-subtle)]'
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
                className="studio-dialog-v3-btn primary inline-flex items-center gap-1 disabled:opacity-40"
              >
                Next <ChevronRight className="w-4 h-4" />
              </button>
            </div>
          </div>
        )}

        {step === 'configure' && (
          <div className="space-y-4 animate-fade-in">
              <div className="studio-dialog-v3-grid two-col">
                <div className="studio-dialog-v3-section">
                  <div className="studio-dialog-v3-label-row">
                    <label className="studio-dialog-v3-label">
                <Globe className="inline w-3.5 h-3.5 mr-1" /> Slide Language
              </label>
                  </div>
              <select
                value={pptLanguage}
                onChange={(e) => setPptLanguage(e.target.value)}
                    className="studio-dialog-v3-select"
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
                </div>

                <div className="studio-dialog-v3-section">
                  <div className="studio-dialog-v3-label-row">
                    <label className="studio-dialog-v3-label">
                <Mic className="inline w-3.5 h-3.5 mr-1" /> Narration Language
              </label>
                  </div>
              <select
                value={narrationLanguage}
                onChange={(e) => setNarrationLanguage(e.target.value)}
                    className="studio-dialog-v3-select"
              >
                <option value="en">English</option>
                <option value="hi">Hindi</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
              </select>
                </div>
              </div>

              <div className="studio-dialog-v3-section">
                <div className="studio-dialog-v3-label-row">
                  <label className="studio-dialog-v3-label">Voice</label>
                </div>
                <div className="studio-dialog-v3-segments" style={{ gridTemplateColumns: 'repeat(2, minmax(0, 1fr))' }}>
                {['female', 'male'].map((v) => (
                  <button
                    key={v}
                    onClick={() => setVoiceGender(v)}
                      className={`studio-dialog-v3-segment ${voiceGender === v ? 'active' : ''}`}
                  >
                    {v}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center justify-between pt-2">
              <button
                onClick={() => setStep('select')}
                  className="studio-dialog-v3-btn ghost inline-flex items-center gap-1"
              >
                <ChevronLeft className="w-4 h-4" /> Back
              </button>
              <button
                onClick={handleGenerate}
                  className="studio-dialog-v3-btn primary"
              >
                Generate Explainer
              </button>
            </div>
          </div>
        )}

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

        {step === 'complete' && (
          <div className="flex flex-col items-center justify-center py-10 animate-fade-in">
            <div className="w-12 h-12 rounded-full bg-green-500/20 flex items-center justify-center mb-4">
              <Check className="w-6 h-6 text-green-400" />
            </div>
            <p className="text-sm font-medium text-[var(--text-primary)] mb-1">Explainer Ready!</p>
            <p className="text-xs text-[var(--text-muted)]">Your video explainer has been generated</p>
            <button
              onClick={handleComplete}
                className="studio-dialog-v3-btn primary mt-6"
            >
              View Explainer
            </button>
          </div>
        )}
      </div>
      </div>
    </Modal>
  );
}

'use client';

import { useMemo, useState } from 'react';
import { useRouter } from 'next/navigation';
import { CheckCircle2, ExternalLink, Loader2, Sparkles } from 'lucide-react';
import { useToast } from '@/stores/useToastStore';
import useAppStore from '@/stores/useAppStore';
import useMaterialStore from '@/stores/useMaterialStore';

function resourceBadge(type) {
  if (type === 'pdf') return 'PDF';
  if (type === 'youtube') return 'YouTube';
  if (type === 'audio') return 'Audio';
  if (type === 'video') return 'Video';
  if (type === 'document') return 'Doc';
  if (type === 'slides') return 'Slides';
  return 'Article';
}

export default function AIResourceBuilder({
  currentNotebook,
  draftMode,
  onMaterialAdded,
  setCurrentNotebook,
  setDraftMode,
  onClose,
}) {
  const router = useRouter();
  const toast = useToast();
  const setNewlyCreatedNotebookId = useAppStore((s) => s.setNewlyCreatedNotebookId);

  const generateAIResources = useMaterialStore((s) => s.generateAIResources);
  const uploadAIResources = useMaterialStore((s) => s.uploadAIResources);

  const [query, setQuery] = useState('');
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [result, setResult] = useState(null);

  const canGenerate = query.trim().length >= 5 && !loading;
  const resources = result?.resources || [];
  const hasPreview = resources.length > 0 || (result?.notes || '').trim().length > 0;

  const notesTitle = useMemo(() => {
    const compact = query.trim().slice(0, 64);
    return compact ? `AI Notes - ${compact}` : 'AI Resource Builder Notes';
  }, [query]);

  const handleGenerate = async () => {
    if (!canGenerate) return;
    setLoading(true);
    try {
      const response = await generateAIResources(query.trim(), currentNotebook?.isDraft ? null : currentNotebook?.id || null);
      setResult(response);
      if (!response?.resources?.length && !response?.notes) {
        toast.info('No resources found. Try a more specific query.');
      }
    } catch (error) {
      toast.error(error.message || 'Failed to generate resources');
    } finally {
      setLoading(false);
    }
  };

  const handleUploadAll = async () => {
    if (!hasPreview || uploading) return;
    setUploading(true);
    try {
      const autoCreate = !currentNotebook || currentNotebook.isDraft || draftMode;
      const notebookId = autoCreate ? null : currentNotebook.id;

      const uploadResult = await uploadAIResources({
        result,
        notebookId,
        autoCreateNotebook: autoCreate,
        notesTitle,
      });

      let routedNotebookId = null;
      if (uploadResult?.notebook) {
        routedNotebookId = uploadResult.notebook.id;
        setNewlyCreatedNotebookId(uploadResult.notebook.id);
        setCurrentNotebook(uploadResult.notebook);
        setDraftMode(false);
      }

      for (const item of uploadResult?.uploads || []) {
        const response = item?.response;
        if (!response?.material_id) continue;
        onMaterialAdded({
          id: response.material_id,
          filename: response.filename,
          title: response.title || response.filename,
          chunkCount: response.chunk_count,
          status: response.status,
          sourceType: response.source_type || (item.kind === 'notes' ? 'text' : 'url'),
        });
      }

      if (routedNotebookId) {
        router.replace(`/notebook/${routedNotebookId}`);
      }
      toast.success('AI resources uploaded successfully');
      onClose();
    } catch (error) {
      toast.error(error.message || 'Failed to upload generated resources');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="block text-xs font-medium text-text-secondary mb-2">Describe what you need</label>
        <textarea
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          rows={4}
          placeholder="prepare materials for class 10 english subject from chapter 1 to 5"
          className="input resize-none leading-relaxed"
        />
      </div>

      <button
        onClick={handleGenerate}
        disabled={!canGenerate || uploading}
        className="workspace-upload-primary btn-primary w-full justify-center py-2.5"
      >
        {loading ? <><Loader2 className="w-4 h-4 animate-spin" /> Generating…</> : <><Sparkles className="w-4 h-4" /> Generate</>}
      </button>

      {hasPreview && (
        <div className="space-y-4 rounded-xl border border-border bg-surface-overlay/50 p-3.5">
          <div>
            <p className="text-xs font-semibold text-text-secondary mb-2">Resources</p>
            <div className="max-h-40 overflow-y-auto space-y-2 pr-1">
              {resources.map((resource, idx) => (
                <a
                  key={`${resource.url}-${idx}`}
                  href={resource.url}
                  target="_blank"
                  rel="noreferrer"
                  className="flex items-start justify-between gap-2 rounded-lg bg-surface-raised/70 px-3 py-2 hover:bg-surface-raised transition-colors"
                >
                  <div className="min-w-0">
                    <p className="text-sm text-text-primary truncate">{resource.title}</p>
                    <p className="text-2xs text-text-muted truncate">{resource.url}</p>
                  </div>
                  <div className="shrink-0 flex items-center gap-2 text-2xs text-text-muted">
                    <span className="px-2 py-0.5 rounded bg-accent/15 text-accent font-semibold">{resourceBadge(resource.type)}</span>
                    <ExternalLink className="w-3.5 h-3.5" />
                  </div>
                </a>
              ))}
            </div>
          </div>

          <div>
            <p className="text-xs font-semibold text-text-secondary mb-2">Notes preview</p>
            <div className="max-h-40 overflow-y-auto rounded-lg bg-surface-raised/70 px-3 py-2 text-xs text-text-secondary whitespace-pre-wrap leading-relaxed">
              {result?.notes || 'No notes generated.'}
            </div>
          </div>

          <button
            onClick={handleUploadAll}
            disabled={uploading}
            className="workspace-upload-primary btn-primary w-full justify-center py-2.5"
          >
            {uploading ? <><Loader2 className="w-4 h-4 animate-spin" /> Uploading…</> : <><CheckCircle2 className="w-4 h-4" /> Upload All</>}
          </button>
        </div>
      )}
    </div>
  );
}

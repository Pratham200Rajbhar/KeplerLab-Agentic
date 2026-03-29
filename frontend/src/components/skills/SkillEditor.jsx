'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  Save, CheckCircle2, XCircle, Loader2, Eye, Code2,
  AlertTriangle, Wand2, Tag, Sparkles,
} from 'lucide-react';
import useSkillStore from '@/stores/useSkillStore';
import { useToast } from '@/stores/useToastStore';
import SkillAIDraftDialog from './SkillAIDraftDialog';

export default function SkillEditor({ skill, notebookId, onSaved, onCancel }) {
  const toast = useToast();
  const editorContent = useSkillStore((s) => s.editorContent);
  const editorValid = useSkillStore((s) => s.editorValid);
  const isLoading = useSkillStore((s) => s.isLoading);
  const isSuggestingTags = useSkillStore((s) => s.isSuggestingTags);
  const isGeneratingDraft = useSkillStore((s) => s.isGeneratingDraft);
  const setEditorContent = useSkillStore((s) => s.setEditorContent);
  const validateEditor = useSkillStore((s) => s.validateEditor);
  const suggestTags = useSkillStore((s) => s.suggestTags);
  const generateDraft = useSkillStore((s) => s.generateDraft);
  const createSkillAction = useSkillStore((s) => s.createSkill);
  const updateSkillAction = useSkillStore((s) => s.updateSkill);

  const [isGlobal, setIsGlobal] = useState(skill?.is_global ?? false);
  const [tags, setTags] = useState(skill?.tags?.join(', ') || '');
  const [suggestedTags, setSuggestedTags] = useState(skill?.tags || []);
  const [showPreview, setShowPreview] = useState(false);
  const [showAIDraftDialog, setShowAIDraftDialog] = useState(false);
  const textareaRef = useRef(null);
  const debounceRef = useRef(null);
  const tagDebounceRef = useRef(null);

  // Auto-validate on content change
  useEffect(() => {
    if (!editorContent.trim()) return;
    clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      validateEditor();
    }, 800);
    return () => clearTimeout(debounceRef.current);
  }, [editorContent, validateEditor]);

  useEffect(() => {
    clearTimeout(tagDebounceRef.current);
    if (!editorContent.trim() || tags.trim()) return;
    if (editorContent.trim().length < 80) return;

    tagDebounceRef.current = setTimeout(async () => {
      try {
        const autoTags = await suggestTags(editorContent, 6);
        if (autoTags?.length > 0) {
          setSuggestedTags(autoTags);
          setTags(autoTags.join(', '));
        }
      } catch {
        // Silently fallback; manual regenerate button remains available.
      }
    }, 1200);

    return () => clearTimeout(tagDebounceRef.current);
  }, [editorContent, tags, suggestTags]);

  const handleSuggestTags = useCallback(async () => {
    if (!editorContent.trim()) {
      toast.info('Add skill content first to generate tags');
      return;
    }
    try {
      const aiTags = await suggestTags(editorContent, 6);
      if (aiTags?.length > 0) {
        setSuggestedTags(aiTags);
        setTags(aiTags.join(', '));
        toast.success('Tags generated with AI');
      } else {
        toast.info('No tags generated yet, try again after refining your skill');
      }
    } catch (err) {
      toast.error(err.message || 'Failed to generate tags');
    }
  }, [editorContent, suggestTags, toast]);

  const handleSave = useCallback(async () => {
    const valid = await validateEditor();
    if (!valid) {
      toast.error('Please fix validation errors before saving');
      return;
    }

    let tagList = tags.split(',').map((t) => t.trim()).filter(Boolean);
    if (tagList.length === 0) {
      try {
        const aiTags = await suggestTags(editorContent, 6);
        if (aiTags?.length > 0) {
          tagList = aiTags;
          setSuggestedTags(aiTags);
          setTags(aiTags.join(', '));
        }
      } catch {
        // Non-blocking. Save can proceed without tags.
      }
    }

    try {
      if (skill?.id) {
        await updateSkillAction(skill.id, { markdown: editorContent, tags: tagList });
        toast.success('Skill updated');
      } else {
        await createSkillAction({
          markdown: editorContent,
          notebookId,
          isGlobal,
          tags: tagList,
        });
        toast.success('Skill created');
      }
      onSaved?.();
    } catch (err) {
      toast.error(err.message || 'Failed to save skill');
    }
  }, [editorContent, tags, isGlobal, skill, notebookId, validateEditor, suggestTags, createSkillAction, updateSkillAction, onSaved, toast]);

  const handleGenerateDraft = useCallback(async (prompt) => {
    try {
      const draft = await generateDraft(prompt);
      if (!draft?.markdown?.trim()) {
        toast.error('AI could not generate a valid skill draft');
        return;
      }

      setEditorContent(draft.markdown);

      const aiTags = Array.isArray(draft.tags)
        ? draft.tags.map((t) => String(t || '').trim()).filter(Boolean)
        : [];

      if (aiTags.length > 0) {
        setSuggestedTags(aiTags);
        setTags(aiTags.join(', '));
      }

      setShowAIDraftDialog(false);
      toast.success('AI draft ready. Review and save your skill.');
    } catch (err) {
      toast.error(err.message || 'Failed to generate AI skill draft');
    }
  }, [generateDraft, setEditorContent, toast]);

  const handleInsertTemplate = useCallback((section) => {
    const templates = {
      input: '\n## Input\ntopic: {user_input}\n',
      steps: '\n## Steps\n1. Search uploaded documents for {topic}\n2. Summarize findings\n',
      output: '\n## Output\n- Summary report\n',
      rules: '\n## Rules\n- Be concise\n',
    };
    setEditorContent(editorContent + (templates[section] || ''));
    toast.info(`${section} section added`);
  }, [editorContent, setEditorContent, toast]);

  const parsed = editorValid?.parsed;

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Toolbar */}
      <div className="skills-editor-toolbar px-3 py-2.5 flex items-center gap-2 border-b border-border shrink-0 flex-wrap">
        <div className="flex items-center gap-1">
          {['input', 'steps', 'output', 'rules'].map((section) => (
            <button
              key={section}
              onClick={() => handleInsertTemplate(section)}
              className="skills-editor-section-btn text-[10px] font-semibold px-2 py-1 rounded-md transition-all capitalize"
            >
              + {section}
            </button>
          ))}
        </div>

        <div className="flex-1" />

        <button
          onClick={() => setShowAIDraftDialog(true)}
          disabled={isLoading || isGeneratingDraft}
          className="skills-btn-secondary inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all disabled:opacity-50"
          title="Describe your goal and let AI build a complete skill draft"
        >
          {isGeneratingDraft ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Wand2 className="w-3.5 h-3.5" />}
          Build with AI
        </button>

        <button
          onClick={() => setShowPreview(!showPreview)}
          className={`skills-editor-toggle flex items-center gap-1 px-2 py-1 rounded-md text-[11px] font-medium transition-all ${showPreview ? 'skills-editor-toggle-active' : ''}`}
        >
          <Eye className="w-3 h-3" /> Preview
        </button>

        {/* Validation indicator */}
        {editorValid && (
          <div className={`flex items-center gap-1 text-[11px] font-medium ${editorValid.valid ? 'text-emerald-400' : 'text-red-400'}`}>
            {editorValid.valid ? (
              <><CheckCircle2 className="w-3.5 h-3.5" /> Valid</>
            ) : (
              <><XCircle className="w-3.5 h-3.5" /> Invalid</>
            )}
          </div>
        )}
      </div>

      <div className="flex-1 flex overflow-hidden">
        {/* Editor */}
        <div className={`flex-1 flex flex-col ${showPreview ? 'border-r border-border' : ''}`}>
          <textarea
            ref={textareaRef}
            value={editorContent}
            onChange={(e) => setEditorContent(e.target.value)}
            className="skills-editor-textarea flex-1 w-full p-4 resize-none outline-none bg-transparent text-text-primary text-[13px] leading-relaxed font-mono custom-scrollbar"
            placeholder="# Skill: My Skill&#10;&#10;## Input&#10;topic: {user_input}&#10;&#10;## Steps&#10;1. Search documents for {topic}&#10;2. Summarize findings&#10;&#10;## Output&#10;- Summary report"
            spellCheck={false}
          />
        </div>

        {/* Preview Panel */}
        {showPreview && (
          <div className="skills-editor-preview w-[280px] p-4 overflow-y-auto custom-scrollbar">
            <h4 className="text-[12px] font-bold text-text-primary mb-3 flex items-center gap-1.5">
              <Code2 className="w-3.5 h-3.5 text-accent" /> Parsed Structure
            </h4>

            {editorValid?.valid === false && (
              <div className="skills-editor-error flex items-start gap-2 p-2.5 rounded-lg mb-3">
                <AlertTriangle className="w-3.5 h-3.5 text-red-400 shrink-0 mt-0.5" />
                <p className="text-[11px] text-red-300 leading-relaxed">{editorValid.error}</p>
              </div>
            )}

            {parsed && (
              <div className="space-y-3">
                <div>
                  <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Title</h5>
                  <p className="text-[12px] text-text-primary font-medium">{parsed.title}</p>
                </div>

                {parsed.inputs?.length > 0 && (
                  <div>
                    <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Inputs</h5>
                    {parsed.inputs.map((inp) => (
                      <div key={inp.name} className="skills-preview-item flex items-center gap-1.5 p-1.5 rounded-md mb-1">
                        <Tag className="w-3 h-3 text-accent-light" />
                        <span className="text-[11px] text-text-primary font-mono">{inp.name}</span>
                        {inp.description && (
                          <span className="text-[10px] text-text-muted truncate">· {inp.description}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}

                {parsed.steps?.length > 0 && (
                  <div>
                    <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Steps ({parsed.steps.length})</h5>
                    {parsed.steps.map((step) => (
                      <div key={step.index} className="skills-preview-item flex items-start gap-1.5 p-1.5 rounded-md mb-1">
                        <span className="text-[10px] text-accent font-bold shrink-0 mt-0.5">{step.index}</span>
                        <div className="min-w-0">
                          <p className="text-[11px] text-text-primary leading-snug">{step.instruction}</p>
                          {step.tool_hint && (
                            <span className="text-[9px] text-accent-light font-bold uppercase mt-0.5 inline-block">→ {step.tool_hint}</span>
                          )}
                        </div>
                      </div>
                    ))}
                  </div>
                )}

                {parsed.all_variables?.length > 0 && (
                  <div>
                    <h5 className="text-[10px] font-bold text-text-muted uppercase tracking-wider mb-1.5">Variables</h5>
                    <div className="flex flex-wrap gap-1">
                      {parsed.all_variables.map((v) => (
                        <span key={v} className="skills-var-badge text-[10px] font-mono px-1.5 py-0.5 rounded">
                          {`{${v}}`}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Footer */}
      <div className="skills-editor-footer px-4 py-3 border-t border-border flex items-center gap-3 shrink-0">
        <label className="flex items-center gap-2 text-[11px] text-text-secondary cursor-pointer">
          <input
            type="checkbox"
            checked={isGlobal}
            onChange={(e) => setIsGlobal(e.target.checked)}
            className="skills-checkbox w-3.5 h-3.5 rounded"
          />
          Global skill
        </label>

        <input
          type="text"
          value={tags}
          onChange={(e) => {
            setTags(e.target.value);
            setSuggestedTags(
              e.target.value.split(',').map((t) => t.trim()).filter(Boolean)
            );
          }}
          placeholder="Tags (comma separated)"
          className="skills-tags-input flex-1 text-[11px] px-2.5 py-1.5 rounded-lg bg-transparent outline-none"
        />

        <button
          onClick={handleSuggestTags}
          disabled={isSuggestingTags || isLoading}
          className="skills-btn-secondary inline-flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all disabled:opacity-50"
          title="Generate tags from your skill content"
        >
          {isSuggestingTags ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
          Auto tags
        </button>

        <div className="flex items-center gap-2">
          <button
            onClick={onCancel}
            className="skills-btn-secondary px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all"
          >
            Cancel
          </button>
          <button
            onClick={handleSave}
            disabled={isLoading}
            className="skills-btn-primary flex items-center gap-1.5 px-4 py-1.5 rounded-lg text-[12px] font-semibold transition-all disabled:opacity-50"
          >
            {isLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Save className="w-3.5 h-3.5" />
            )}
            {skill?.id ? 'Update' : 'Create'}
          </button>
        </div>
      </div>

      {suggestedTags.length > 0 && (
        <div className="px-4 pb-3 -mt-1 flex items-center gap-1.5 flex-wrap">
          {suggestedTags.map((tag) => (
            <span key={tag} className="skills-var-badge text-[10px] font-medium px-2 py-0.5 rounded-full">
              {tag}
            </span>
          ))}
        </div>
      )}

      <SkillAIDraftDialog
        isOpen={showAIDraftDialog}
        isLoading={isGeneratingDraft}
        onClose={() => setShowAIDraftDialog(false)}
        onGenerate={handleGenerateDraft}
      />
    </div>
  );
}

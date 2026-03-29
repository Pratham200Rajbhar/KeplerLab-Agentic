'use client';

import { useState, useEffect, useCallback } from 'react';
import {
  Wand2, Plus, Play, Clock, ChevronLeft, Trash2, Edit3,
  CheckCircle2, XCircle, Loader2, Globe2, FileText, Zap,
  Copy, Tag, BookOpen, RotateCcw, Code2, Search,
} from 'lucide-react';
import useSkillStore from '@/stores/useSkillStore';
import useAppStore from '@/stores/useAppStore';
import { useToast } from '@/stores/useToastStore';
import { useConfirm } from '@/stores/useConfirmStore';
import SkillEditor from './SkillEditor';
import SkillRunner from './SkillRunner';
import SkillRunLog from './SkillRunLog';
import SkillTemplates from './SkillTemplates';

const TAB_ITEMS = [
  { id: 'skills', label: 'My Skills', icon: Wand2 },
  { id: 'templates', label: 'Templates', icon: BookOpen },
  { id: 'runs', label: 'History', icon: Clock },
];

const TOOL_ICONS = {
  rag: Search,
  web_search: Globe2,
  research: Globe2,
  python_auto: Code2,
  llm: Zap,
};

export default function SkillsPanel({ onClose }) {
  const toast = useToast();
  const confirm = useConfirm();
  const currentNotebook = useAppStore((s) => s.currentNotebook);
  const selectedSources = useAppStore((s) => s.selectedSources);

  const skills = useSkillStore((s) => s.skills);
  const templates = useSkillStore((s) => s.templates);
  const activeSkill = useSkillStore((s) => s.activeSkill);
  const isLoading = useSkillStore((s) => s.isLoading);
  const isRunning = useSkillStore((s) => s.isRunning);
  const currentRun = useSkillStore((s) => s.currentRun);
  const skillRuns = useSkillStore((s) => s.skillRuns);
  const loadSkills = useSkillStore((s) => s.loadSkills);
  const loadTemplates = useSkillStore((s) => s.loadTemplates);
  const loadRuns = useSkillStore((s) => s.loadRuns);
  const setActiveSkill = useSkillStore((s) => s.setActiveSkill);
  const deleteSkillAction = useSkillStore((s) => s.deleteSkill);
  const executeSkill = useSkillStore((s) => s.executeSkill);
  const clearRun = useSkillStore((s) => s.clearRun);

  const [activeTab, setActiveTab] = useState('skills');
  const [view, setView] = useState('list'); // 'list' | 'editor' | 'runner' | 'runlog'
  const [selectedRunId, setSelectedRunId] = useState(null);

  useEffect(() => {
    if (currentNotebook?.id && !currentNotebook.isDraft) {
      loadSkills(currentNotebook.id);
    }
    loadTemplates();
  }, [currentNotebook?.id, currentNotebook?.isDraft, loadSkills, loadTemplates]);

  useEffect(() => {
    if (activeTab === 'runs') {
      loadRuns();
    }
  }, [activeTab, loadRuns]);

  const handleCreateNew = useCallback(() => {
    setActiveSkill(null);
    useSkillStore.getState().setEditorContent(
      `# Skill: My New Skill\n\n## Input\ntopic: {user_input}\n\n## Steps\n1. Search uploaded documents for information about {topic}\n2. Summarize the findings into a clear report\n\n## Output\n- Summary report\n\n## Rules\n- Be concise and clear\n`
    );
    setView('editor');
  }, [setActiveSkill]);

  const handleEditSkill = useCallback((skill) => {
    setActiveSkill(skill);
    setView('editor');
  }, [setActiveSkill]);

  const handleRunSkill = useCallback((skill) => {
    setActiveSkill(skill);
    clearRun();
    setView('runner');
  }, [setActiveSkill, clearRun]);

  const handleDeleteSkill = useCallback(async (skill) => {
    const ok = await confirm({
      title: 'Delete Skill?',
      message: `"${skill.title}" will be permanently deleted along with its run history.`,
      confirmLabel: 'Delete',
      variant: 'danger',
    });
    if (!ok) return;
    try {
      await deleteSkillAction(skill.id);
      toast.success('Skill deleted');
    } catch (err) {
      toast.error(err.message || 'Failed to delete skill');
    }
  }, [confirm, deleteSkillAction, toast]);

  const handleImportTemplate = useCallback((template) => {
    setActiveSkill(null);
    useSkillStore.getState().setEditorContent(template.markdown);
    setView('editor');
    setActiveTab('skills');
    toast.success(`Template "${template.title}" loaded into editor`);
  }, [setActiveSkill, toast]);

  const handleViewRun = useCallback((run) => {
    setSelectedRunId(run.id);
    setView('runlog');
  }, []);

  const handleEditorSaved = useCallback(() => {
    loadSkills(currentNotebook?.id);
    setView('list');
  }, [loadSkills, currentNotebook?.id]);

  // ── Render Views ────────────────────────────────────────

  if (view === 'editor') {
    return (
      <div className="skills-panel h-full flex flex-col">
        <div className="skills-panel-header px-4 py-3 flex items-center gap-3 border-b border-border shrink-0">
          <button onClick={() => setView('list')} className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <h3 className="text-sm font-semibold text-text-primary">
            {activeSkill ? 'Edit Skill' : 'Create Skill'}
          </h3>
        </div>
        <SkillEditor
          skill={activeSkill}
          notebookId={currentNotebook?.id}
          onSaved={handleEditorSaved}
          onCancel={() => setView('list')}
        />
      </div>
    );
  }

  if (view === 'runner') {
    return (
      <div className="skills-panel h-full flex flex-col">
        <div className="skills-panel-header px-4 py-3 flex items-center gap-3 border-b border-border shrink-0">
          <button onClick={() => { clearRun(); setView('list'); }} className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <Wand2 className="w-4 h-4 text-accent" />
          <h3 className="text-sm font-semibold text-text-primary truncate">
            {activeSkill?.title || 'Run Skill'}
          </h3>
        </div>
        <SkillRunner
          skill={activeSkill}
          notebookId={currentNotebook?.id}
          materialIds={selectedSources}
          onBack={() => { clearRun(); setView('list'); }}
        />
      </div>
    );
  }

  if (view === 'runlog') {
    return (
      <div className="skills-panel h-full flex flex-col">
        <div className="skills-panel-header px-4 py-3 flex items-center gap-3 border-b border-border shrink-0">
          <button onClick={() => setView('list')} className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </button>
          <Clock className="w-4 h-4 text-text-secondary" />
          <h3 className="text-sm font-semibold text-text-primary">Run Details</h3>
        </div>
        <SkillRunLog key={selectedRunId || 'runlog'} runId={selectedRunId} onBack={() => setView('list')} />
      </div>
    );
  }

  // ── List View ───────────────────────────────────────────

  return (
    <div className="skills-panel h-full flex flex-col">
      {/* Header */}
      <div className="skills-panel-header px-4 py-3 flex items-center justify-between border-b border-border shrink-0">
        <div className="flex items-center gap-2.5">
          <div className="skills-header-icon w-7 h-7 rounded-lg flex items-center justify-center">
            <Wand2 className="w-4 h-4" />
          </div>
          <h3 className="text-[13px] font-bold text-text-primary tracking-wide">Agent Skills</h3>
        </div>
        {onClose && (
          <button onClick={onClose} className="p-1.5 rounded-lg text-text-muted hover:text-text-primary hover:bg-surface-raised transition-colors">
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Tabs */}
      <div className="skills-tabs px-3 pt-3 flex gap-1 shrink-0">
        {TAB_ITEMS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
            onClick={() => setActiveTab(id)}
            className={`skills-tab flex items-center gap-1.5 px-3 py-2 rounded-lg text-[12px] font-semibold transition-all ${
              activeTab === id
                ? 'skills-tab-active'
                : 'text-text-muted hover:text-text-primary hover:bg-surface-raised'
            }`}
          >
            <Icon className="w-3.5 h-3.5" />
            {label}
          </button>
        ))}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-3 custom-scrollbar">
        {activeTab === 'skills' && (
          <div className="space-y-2">
            {/* Create Button */}
            <button
              onClick={handleCreateNew}
              className="skills-create-btn w-full py-3 px-4 rounded-xl font-medium flex items-center justify-center gap-2 transition-all"
            >
              <Plus className="w-4 h-4" />
              <span className="text-[13px]">Create New Skill</span>
            </button>

            {/* Skills List */}
            {isLoading ? (
              <div className="flex items-center justify-center py-8">
                <Loader2 className="w-5 h-5 text-text-muted animate-spin" />
              </div>
            ) : skills.length === 0 ? (
              <div className="skills-empty-state text-center py-8 px-4">
                <div className="w-12 h-12 rounded-full bg-surface-raised flex items-center justify-center mx-auto mb-3">
                  <Wand2 className="w-5 h-5 text-text-muted" />
                </div>
                <p className="text-[13px] font-semibold text-text-primary mb-1">No skills yet</p>
                <p className="text-[12px] text-text-muted leading-relaxed">
                  Create custom AI workflows or import from templates
                </p>
              </div>
            ) : (
              skills.map((skill) => (
                <div key={skill.id} className="skills-card group rounded-xl p-3 transition-all">
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <div className="min-w-0 flex-1">
                      <h4 className="text-[13px] font-semibold text-text-primary truncate">
                        {skill.title}
                      </h4>
                      {skill.description && (
                        <p className="text-[11px] text-text-muted mt-0.5 line-clamp-2">
                          {skill.description}
                        </p>
                      )}
                    </div>
                    {skill.is_global && (
                      <span className="skills-global-badge text-[10px] font-bold px-1.5 py-0.5 rounded shrink-0">
                        Global
                      </span>
                    )}
                  </div>

                  {/* Tags */}
                  {skill.tags?.length > 0 && (
                    <div className="flex items-center gap-1 mb-2 flex-wrap">
                      {skill.tags.slice(0, 3).map((tag) => (
                        <span key={tag} className="skills-tag text-[10px] px-1.5 py-0.5 rounded font-medium">
                          {tag}
                        </span>
                      ))}
                    </div>
                  )}

                  {/* Meta */}
                  <div className="flex items-center gap-1.5 mb-2">
                    {skill.parsed && (
                      <>
                        <span className="text-[10px] text-text-muted flex items-center gap-1">
                          <FileText className="w-3 h-3" />
                          {skill.parsed.steps_count} steps
                        </span>
                        {skill.parsed.inputs?.length > 0 && (
                          <span className="text-[10px] text-text-muted flex items-center gap-1">
                            <Tag className="w-3 h-3" />
                            {skill.parsed.inputs.length} inputs
                          </span>
                        )}
                      </>
                    )}
                    <span className="text-[10px] text-text-muted/50">v{skill.version}</span>
                  </div>

                  {/* Actions */}
                  <div className="flex items-center gap-1.5 opacity-0 group-hover:opacity-100 transition-opacity">
                    <button
                      onClick={() => handleRunSkill(skill)}
                      className="skills-action-btn skills-action-run flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all"
                    >
                      <Play className="w-3 h-3" /> Run
                    </button>
                    <button
                      onClick={() => handleEditSkill(skill)}
                      className="skills-action-btn flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[11px] font-medium transition-all"
                    >
                      <Edit3 className="w-3 h-3" /> Edit
                    </button>
                    <button
                      onClick={() => handleDeleteSkill(skill)}
                      className="skills-action-btn skills-action-danger flex items-center gap-1 px-2 py-1.5 rounded-lg text-[11px] transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {activeTab === 'templates' && (
          <SkillTemplates templates={templates} onImport={handleImportTemplate} />
        )}

        {activeTab === 'runs' && (
          <div className="space-y-2">
            {skillRuns.length === 0 ? (
              <div className="text-center py-8">
                <Clock className="w-5 h-5 text-text-muted mx-auto mb-2" />
                <p className="text-[12px] text-text-muted">No skill runs yet</p>
              </div>
            ) : (
              skillRuns.map((run) => (
                <button
                  key={run.id}
                  onClick={() => handleViewRun(run)}
                  className="skills-run-card w-full text-left rounded-xl p-3 transition-all"
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-[12px] font-semibold text-text-primary truncate">
                      {run.skill_title}
                    </span>
                    <span className={`skills-run-status text-[10px] font-bold px-1.5 py-0.5 rounded ${
                      run.status === 'completed' ? 'skills-run-status-ok' :
                      run.status === 'failed' ? 'skills-run-status-fail' :
                      'skills-run-status-pending'
                    }`}>
                      {run.status}
                    </span>
                  </div>
                  <div className="flex items-center gap-2 text-[10px] text-text-muted">
                    <span>{new Date(run.created_at).toLocaleString()}</span>
                    {run.elapsed_time > 0 && <span>·</span>}
                    {run.elapsed_time > 0 && <span>{run.elapsed_time.toFixed(1)}s</span>}
                  </div>
                </button>
              ))
            )}
          </div>
        )}
      </div>
    </div>
  );
}

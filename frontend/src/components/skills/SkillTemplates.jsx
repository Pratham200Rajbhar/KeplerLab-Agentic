'use client';

import { FileText, Download, Search, Globe2, Code2, Zap, Tag } from 'lucide-react';

const TOOL_ICONS = {
  rag: Search,
  web_search: Globe2,
  research: Globe2,
  python_auto: Code2,
  llm: Zap,
};

export default function SkillTemplates({ templates = [], onImport }) {
  if (templates.length === 0) {
    return (
      <div className="text-center py-8">
        <FileText className="w-5 h-5 text-text-muted mx-auto mb-2" />
        <p className="text-[12px] text-text-muted">Loading templates...</p>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-[11px] text-text-muted mb-2 px-1">
        Pre-built skill workflows you can import and customize
      </p>
      {templates.map((template) => (
        <div key={template.slug} className="skills-template-card group rounded-xl p-3.5 transition-all">
          <div className="flex items-start justify-between gap-2 mb-2">
            <div className="min-w-0">
              <h4 className="text-[13px] font-semibold text-text-primary">{template.title}</h4>
              <p className="text-[11px] text-text-muted mt-0.5 leading-relaxed">{template.description}</p>
            </div>
          </div>

          {/* Tags */}
          {template.tags?.length > 0 && (
            <div className="flex items-center gap-1 mb-2.5 flex-wrap">
              {template.tags.map((tag) => (
                <span key={tag} className="skills-tag text-[10px] px-1.5 py-0.5 rounded font-medium">
                  {tag}
                </span>
              ))}
            </div>
          )}

          {/* Meta */}
          <div className="flex items-center gap-2 mb-2.5 text-[10px] text-text-muted">
            <span className="flex items-center gap-1">
              <FileText className="w-3 h-3" />
              {template.steps_count} steps
            </span>
            {template.inputs?.length > 0 && (
              <span className="flex items-center gap-1">
                <Tag className="w-3 h-3" />
                {template.inputs.length} input{template.inputs.length !== 1 ? 's' : ''}
              </span>
            )}
          </div>

          {/* Inputs Preview */}
          {template.inputs?.length > 0 && (
            <div className="flex flex-wrap gap-1 mb-2.5">
              {template.inputs.map((inp) => (
                <span key={inp.name} className="skills-var-badge text-[10px] font-mono px-1.5 py-0.5 rounded">
                  {`{${inp.name}}`}
                </span>
              ))}
            </div>
          )}

          {/* Import Button */}
          <button
            onClick={() => onImport?.(template)}
            className="skills-template-import-btn w-full py-2 px-3 rounded-lg text-[12px] font-semibold flex items-center justify-center gap-1.5 transition-all opacity-0 group-hover:opacity-100"
          >
            <Download className="w-3.5 h-3.5" />
            Import to Editor
          </button>
        </div>
      ))}
    </div>
  );
}

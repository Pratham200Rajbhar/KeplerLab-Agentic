'use client';

import { memo, useState, useMemo } from 'react';
import {
Clock, FileText, Layers, BookOpen, Mic, Presentation, Network,
MoreVertical, Pencil, Trash2
} from 'lucide-react';
import { formatRelativeDate } from '@/lib/utils/helpers';


function contentTypeIcon(type) {
const icons = {
flashcards: <Layers className="w-3.5 h-3.5 text-blue-400" />,
quiz: <BookOpen className="w-3.5 h-3.5 text-green-400" />,
podcast: <Mic className="w-3.5 h-3.5 text-purple-400" />,
presentation: <Presentation className="w-3.5 h-3.5 text-orange-400" />,
explainer: <FileText className="w-3.5 h-3.5 text-cyan-400" />,
mindmap: <Network className="w-3.5 h-3.5 text-pink-400" />,
};
return icons[type] || <FileText className="w-3.5 h-3.5 text-[var(--text-muted)]" />;
}

function contentSubtitle(item) {
switch (item.content_type) {
case 'flashcards': {
const count = item.data?.flashcards?.length || item.data?.cards?.length || 0;
return `${count} card${count !== 1 ? 's' : ''}`;
}
case 'quiz': {
const count = item.data?.questions?.length || 0;
return `${count} question${count !== 1 ? 's' : ''}`;
}
case 'presentation': {
const count = item.data?.slides?.length || item.data?.slide_count || 0;
return `${count} slide${count !== 1 ? 's' : ''}`;
}
case 'mindmap': {
const nodeCount = item.data?.nodes?.length || countNodes(item.data) || 0;
return `${nodeCount} node${nodeCount !== 1 ? 's' : ''}`;
}
default:
return formatRelativeDate(item.created_at);
}
}

function countNodes(node) {
if (!node) return 0;
let count = 1;
if (node.children) {
for (const child of node.children) {
count += countNodes(child);
}
}
return count;
}

const ContentHistory = memo(function ContentHistory({ items = [], activeId, onSelect, onDelete, onRename, filter }) {
  const [menuOpenId, setMenuOpenId] = useState(null);

  const filtered = useMemo(() => {
    if (!filter || filter === 'all') return items;
    return items.filter((i) => i.content_type === filter);
  }, [items, filter]);

  if (!filtered.length) {
    return (
      <div className="px-3 py-6 text-center">
        <Clock className="w-5 h-5 text-[var(--text-muted)] mx-auto mb-2 opacity-40" />
        <p className="text-xs text-[var(--text-muted)]">No generated content yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-1.5">
      {filtered.map((item) => {
        const isActive = activeId === item.id;
        return (
          <div
            key={item.id}
            onClick={() => onSelect?.(item)}
            className={`workspace-studio-history-item group relative flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all ${
              isActive
                ? 'workspace-studio-history-item-active'
                : 'border border-transparent'
            }`}
          >
            <div className="workspace-studio-history-icon-wrap shrink-0">{contentTypeIcon(item.content_type)}</div>

            <div className="flex-1 min-w-0">
              <p className="workspace-studio-history-item-title truncate">
                {item.title || `${item.content_type} ${item.id?.slice(0, 6)}`}
              </p>
              <p className="workspace-studio-history-item-subtitle mt-0.5">
                {contentSubtitle(item)}
              </p>
            </div>

            {/* Menu */}
            <div className="relative shrink-0">
              <button
                onClick={(e) => {
                  e.stopPropagation();
                  setMenuOpenId(menuOpenId === item.id ? null : item.id);
                }}
                className="p-1 rounded hover:bg-[var(--surface)] transition-colors opacity-60 md:opacity-0 md:group-hover:opacity-100"
                aria-label="More options"
              >
                <MoreVertical className="w-3.5 h-3.5 text-[var(--text-muted)]" />
              </button>

              {menuOpenId === item.id && (
                <>
                  <div className="fixed inset-0 z-10" onClick={() => setMenuOpenId(null)} />
                  <div className="absolute right-0 top-full mt-1 z-20 w-32 bg-[var(--surface-raised)] border border-[var(--border)] rounded-lg shadow-lg overflow-hidden">
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(null);
                        onRename?.(item);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors"
                    >
                      <Pencil className="w-3 h-3" /> Rename
                    </button>
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        setMenuOpenId(null);
                        onDelete?.(item);
                      }}
                      className="w-full flex items-center gap-2 px-3 py-2 text-xs text-red-400 hover:bg-red-500/10 transition-colors"
                    >
                      <Trash2 className="w-3 h-3" /> Delete
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>
        );
      })}
    </div>
  );
});

export default ContentHistory;

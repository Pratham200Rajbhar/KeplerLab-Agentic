'use client';

import { useState } from 'react';
import { Download, FileText, FileJson, Loader2, BookOpen } from 'lucide-react';
import usePodcastStore from '@/stores/usePodcastStore';
import { useToast } from '@/stores/useToastStore';
import { getPodcastExportUrl } from '@/lib/api/podcast';

export default function PodcastExportBar() {
  const session = usePodcastStore((s) => s.session);
  const exportSession = usePodcastStore((s) => s.exportSession);
  const generateSummary = usePodcastStore((s) => s.generateSummary);
  const toast = useToast();

  const [exporting, setExporting] = useState(null); // 'pdf' | 'json' | 'summary' | null
  const [showMenu, setShowMenu] = useState(false);

  const handleExport = async (format) => {
    if (!session?.id || exporting) return;
    setExporting(format);
    setShowMenu(false);
    try {
      const result = await exportSession(format);
      if (result?.download_url || result?.filename) {
        const url = result.download_url || getPodcastExportUrl(session.id, result.filename);
        const a = document.createElement('a');
        a.href = url;
        a.download = result.filename || `podcast.${format}`;
        a.click();
        toast.success(`Exported as ${format.toUpperCase()}`);
      }
    } catch (err) {
      toast.error(err.message || 'Export failed');
    } finally {
      setExporting(null);
    }
  };

  const handleSummary = async () => {
    if (!session?.id || exporting) return;
    setExporting('summary');
    setShowMenu(false);
    try {
      await generateSummary();
      toast.success('Summary generated');
    } catch (err) {
      toast.error(err.message || 'Summary failed');
    } finally {
      setExporting(null);
    }
  };

  return (
    <div className="relative">
      <button
        onClick={() => setShowMenu(!showMenu)}
        disabled={!!exporting}
        className="p-1.5 rounded-lg text-[var(--text-muted)] hover:bg-[var(--surface-overlay)] transition-colors"
      >
        {exporting ? (
          <Loader2 className="w-4 h-4 animate-spin" />
        ) : (
          <Download className="w-4 h-4" />
        )}
      </button>

      {showMenu && (
        <>
          <div className="fixed inset-0 z-10" onClick={() => setShowMenu(false)} />
          <div className="absolute right-0 top-full mt-1 z-20 w-40 bg-[var(--surface-raised)] border border-[var(--border)] rounded-xl shadow-lg overflow-hidden animate-fade-in">
            <button
              onClick={() => handleExport('pdf')}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors"
            >
              <FileText className="w-3.5 h-3.5" /> Export PDF
            </button>
            <button
              onClick={() => handleExport('json')}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors"
            >
              <FileJson className="w-3.5 h-3.5" /> Export JSON
            </button>
            <hr className="border-[var(--border)]" />
            <button
              onClick={handleSummary}
              className="w-full flex items-center gap-2 px-3 py-2.5 text-xs text-[var(--text-secondary)] hover:bg-[var(--surface-overlay)] transition-colors"
            >
              <BookOpen className="w-3.5 h-3.5" /> Generate Summary
            </button>
          </div>
        </>
      )}
    </div>
  );
}

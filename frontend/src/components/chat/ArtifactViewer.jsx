'use client';

import { Download, FileText, FileSpreadsheet, FileCode, FileArchive, Image as ImageIcon, ExternalLink } from 'lucide-react';
import { useMemo } from 'react';

const IMAGE_MIMES = new Set(['image/png', 'image/jpeg', 'image/jpg', 'image/gif', 'image/svg+xml', 'image/webp']);
const IMAGE_DISPLAY = new Set(['image', 'chart', 'plot', 'figure', 'heatmap']);

function isImageArtifact(artifact) {
  return IMAGE_MIMES.has(artifact.mime) || IMAGE_DISPLAY.has(artifact.display_type);
}

function formatBytes(bytes) {
  if (!bytes) return '';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileColor(mime, displayType) {
  if (mime?.includes('spread') || mime?.includes('excel') || displayType === 'csv_table') return { icon: 'text-green-400', bg: 'bg-green-400/10' };
  if (mime?.includes('json') || displayType === 'json_tree') return { icon: 'text-blue-400', bg: 'bg-blue-400/10' };
  if (mime?.includes('pdf') || displayType === 'pdf_embed') return { icon: 'text-red-400', bg: 'bg-red-400/10' };
  if (mime?.includes('html') || displayType === 'html_preview') return { icon: 'text-orange-400', bg: 'bg-orange-400/10' };
  if (mime?.includes('zip') || mime?.includes('tar')) return { icon: 'text-yellow-400', bg: 'bg-yellow-400/10' };
  return { icon: 'text-text-muted', bg: 'bg-white/5' };
}

function FileIcon({ mime, displayType }) {
  if (mime?.includes('spread') || mime?.includes('excel') || displayType === 'csv_table') return <FileSpreadsheet size={16} className="text-green-400" />;
  if (mime?.includes('json') || displayType === 'json_tree') return <FileCode size={16} className="text-blue-400" />;
  if (mime?.includes('pdf') || displayType === 'pdf_embed') return <FileText size={16} className="text-red-400" />;
  if (mime?.includes('html') || displayType === 'html_preview') return <FileCode size={16} className="text-orange-400" />;
  if (mime?.includes('zip') || mime?.includes('tar')) return <FileArchive size={16} className="text-yellow-400" />;
  if (mime?.startsWith('image/')) return <ImageIcon size={16} className="text-purple-400" />;
  return <FileText size={16} className="text-text-muted" />;
}

function ArtifactCard({ artifact }) {
  const isImage = isImageArtifact(artifact);
  // Use relative URL so Next.js API proxy handles routing — no hardcoded host needed
  const apiUrl = artifact.url || null;

  if (isImage && apiUrl) {
    return (
      <div className="rounded-xl overflow-hidden border border-white/[0.08] group hover:border-white/[0.14] transition-colors">
        <div className="relative bg-black/20">
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={apiUrl}
            alt={artifact.filename || 'Generated image'}
            className="w-full max-h-[420px] object-contain"
            loading="lazy"
            onError={(e) => {
              e.currentTarget.parentElement.style.display = 'none';
            }}
          />
        </div>
        <div className="flex items-center justify-between px-3 py-2 border-t border-white/[0.06] bg-black/20">
          <div className="flex items-center gap-2 min-w-0">
            <ImageIcon size={12} className="text-purple-400 shrink-0" />
            <span className="text-xs text-text-muted truncate">{artifact.filename}</span>
            {artifact.size > 0 && (
              <span className="text-[10px] text-text-muted/60 shrink-0">{formatBytes(artifact.size)}</span>
            )}
          </div>
          {apiUrl && (
            <a
              href={apiUrl}
              download={artifact.filename}
              className="ml-3 shrink-0 flex items-center gap-1 text-xs text-accent hover:text-accent/80 transition-colors"
            >
              <Download size={11} />
              Save
            </a>
          )}
        </div>
      </div>
    );
  }

  const colors = getFileColor(artifact.mime, artifact.display_type);
  const isPremiumRenderer = artifact.display_type === 'research_report' || artifact.mime?.includes('pdf');

  const cardClasses = isPremiumRenderer 
    ? "relative overflow-hidden flex items-center gap-4 px-4 py-3.5 rounded-xl border transition-all duration-300 group bg-gradient-to-r from-accent/[0.05] to-transparent border-accent/20 hover:border-accent/40 hover:bg-accent/[0.08] shadow-[0_0_15px_-3px_rgba(26,115,232,0.15)]"
    : "flex items-center gap-3 px-3.5 py-3 rounded-xl border border-white/[0.08] hover:border-white/[0.14] transition-colors bg-white/[0.02] group";

  const iconClasses = isPremiumRenderer
    ? "w-10 h-10 rounded-xl flex items-center justify-center shrink-0 bg-accent/20 text-accent shadow-inner shadow-accent/20"
    : `w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${colors.bg}`;

  const titleClasses = isPremiumRenderer
    ? "text-sm font-semibold text-text-primary truncate group-hover:text-accent transition-colors"
    : "text-sm font-medium text-text-primary truncate";

  const buttonClasses = isPremiumRenderer
    ? "shrink-0 flex items-center gap-1.5 text-xs font-semibold px-4 py-2 rounded-lg transition-all bg-accent text-white hover:bg-accent/90 shadow-[0_0_10px_-2px_rgba(26,115,232,0.4)] hover:shadow-[0_0_15px_-2px_rgba(26,115,232,0.6)]"
    : "shrink-0 flex items-center gap-1.5 text-xs font-medium text-accent hover:text-accent/80 transition-colors px-3 py-1.5 rounded-lg border border-accent/25 hover:bg-accent/10";


  return (
    <div className={cardClasses}>
      <div className={iconClasses}>
        <FileIcon mime={artifact.mime} displayType={artifact.display_type} />
      </div>
      <div className="flex-1 min-w-0 z-10">
        <div className={titleClasses}>{artifact.filename}</div>
        <div className="flex items-center gap-2 mt-0.5">
          {artifact.size > 0 && (
            <span className={isPremiumRenderer ? "text-xs text-text-secondary" : "text-xs text-text-muted"}>
              {formatBytes(artifact.size)}
            </span>
          )}
          {artifact.display_type && (
            <span className="text-[10px] text-text-muted/60 uppercase tracking-wider font-semibold">
              {artifact.display_type.replace('_', ' ')}
            </span>
          )}
        </div>
      </div>
      {apiUrl && (
        <a
          href={apiUrl}
          download={artifact.filename}
          className={`${buttonClasses} z-10`}
        >
          <Download size={isPremiumRenderer ? 14 : 12} />
          {isPremiumRenderer ? 'Download Report' : 'Download'}
        </a>
      )}
      {/* Decorative background glow for premium cards */}
      {isPremiumRenderer && (
        <div className="absolute top-0 right-0 w-32 h-full bg-gradient-to-l from-accent/5 to-transparent pointer-events-none rounded-r-xl" />
      )}
    </div>
  );
}


export default function ArtifactViewer({ artifacts }) {
  // De-duplicate artifacts by filename, keeping the last occurrence (most recent)
  const uniqueArtifacts = useMemo(() => {
    if (!artifacts?.length) return [];
    const uniqueMap = new Map();
    artifacts.forEach((art, index) => {
      if (art.filename) {
        uniqueMap.set(art.filename, art);
      } else {
        uniqueMap.set(art.id || `fallback-${index}`, art);
      }
    });
    return Array.from(uniqueMap.values());
  }, [artifacts]);

  if (!artifacts?.length) return null;

  const images = uniqueArtifacts.filter(isImageArtifact);
  const files = uniqueArtifacts.filter(a => !isImageArtifact(a));

  return (
    <div className="space-y-2.5">
      {/* Images in a grid */}
      {images.length > 0 && (
        <div className={images.length === 1 ? '' : 'grid grid-cols-2 gap-2'}>
          {images.map((art, i) => (
            <ArtifactCard key={art.id || i} artifact={art} />
          ))}
        </div>
      )}
      {/* Files in a list */}
      {files.map((art, i) => (
        <ArtifactCard key={art.id || i} artifact={art} />
      ))}
    </div>
  );
}

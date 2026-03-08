'use client';

import { memo, useMemo, useState } from 'react';
import {
  Image as ImageIcon,
  Table2,
  FileBox,
  FileText,
  Files,
  ChevronDown,
  ChevronUp,
} from 'lucide-react';
import ArtifactTablePreview from './ArtifactTablePreview';
import ArtifactDownloadCard from './ArtifactDownloadCard';

/**
 * ArtifactGallery — groups and displays artifacts by category.
 * 
 * Categories:
 * - charts: Images like PNG, JPG, SVG
 * - datasets: CSV, JSON data files
 * - models: Model files (pkl, pt, h5)
 * - reports: Documents (PDF, DOCX, MD)
 * - files: Other files
 *
 * Props:
 *   artifacts: [{ id, filename, mimeType, displayType, category, downloadUrl, size }]
 *   onDownload: (artifact) => void
 */

const CATEGORY_CONFIG = {
  charts: {
    icon: ImageIcon,
    label: 'Charts',
    description: 'Generated visualizations',
    color: 'text-blue-400',
    bgColor: 'bg-blue-500/10',
  },
  datasets: {
    icon: Table2,
    label: 'Datasets',
    description: 'Data files and tables',
    color: 'text-emerald-400',
    bgColor: 'bg-emerald-500/10',
  },
  models: {
    icon: FileBox,
    label: 'Models',
    description: 'Trained ML models',
    color: 'text-purple-400',
    bgColor: 'bg-purple-500/10',
  },
  reports: {
    icon: FileText,
    label: 'Reports',
    description: 'Generated documents',
    color: 'text-amber-400',
    bgColor: 'bg-amber-500/10',
  },
  files: {
    icon: Files,
    label: 'Files',
    description: 'Generated files',
    color: 'text-text-secondary',
    bgColor: 'bg-surface-overlay',
  },
};

// Category display order
const CATEGORY_ORDER = ['charts', 'datasets', 'models', 'reports', 'files'];

function ArtifactGallery({ artifacts = [], onDownload }) {
  // Group artifacts by category.
  // Always use filename-based categorization as the primary source — the backend
  // currently defaults to `category: "file"` for every artifact, so we cannot rely
  // on the backend value.  Fall back to `artifact.category` only when filename-based
  // detection returns the generic "files" bucket AND the backend supplies something
  // more specific.
  const groupedArtifacts = useMemo(() => {
    const groups = {};
    
    for (const artifact of artifacts) {
      const filenameCategory = categorizeByFilename(artifact.filename);
      const backendCategory = artifact.category || artifact.backendCategory || null;
      // Prefer filename-derived category; use backend only when it provides a known
      // non-generic value and filename detection is inconclusive.
      const KNOWN_CATEGORIES = new Set(['charts', 'datasets', 'models', 'reports']);
      const category =
        filenameCategory !== 'files'
          ? filenameCategory
          : KNOWN_CATEGORIES.has(backendCategory)
            ? backendCategory
            : 'files';

      if (!groups[category]) {
        groups[category] = [];
      }
      groups[category].push(artifact);
    }
    
    return groups;
  }, [artifacts]);

  // Get ordered categories that have artifacts
  const activeCategories = useMemo(() => {
    return CATEGORY_ORDER.filter((cat) => groupedArtifacts[cat]?.length > 0);
  }, [groupedArtifacts]);

  if (artifacts.length === 0) {
    return null;
  }

  return (
    <div className="artifact-gallery space-y-4 mt-4">
      {activeCategories.map((category) => (
        <CategorySection
          key={category}
          category={category}
          artifacts={groupedArtifacts[category]}
          onDownload={onDownload}
        />
      ))}
    </div>
  );
}

/**
 * Section for a single category of artifacts.
 */
function CategorySection({ category, artifacts, onDownload }) {
  const [isExpanded, setIsExpanded] = useState(true);
  const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.files;
  const Icon = config.icon;

  return (
    <div className="category-section rounded-lg bg-surface-raised/20 overflow-hidden shadow-sm">
      {/* Header */}
      <button
        onClick={() => setIsExpanded(!isExpanded)}
        className="w-full flex items-center gap-2.5 px-3 py-2.5 bg-surface-raised/50 hover:bg-surface-raised transition-colors"
      >
        <div className={`flex items-center justify-center w-6 h-6 rounded-md ${config.bgColor}`}>
          <Icon className={`w-3.5 h-3.5 ${config.color}`} />
        </div>
        <span className="text-sm font-medium text-text-primary flex-1 text-left">
          {config.label}
        </span>
        <span className="text-xs text-text-muted mr-2">
          {artifacts.length} {artifacts.length === 1 ? 'file' : 'files'}
        </span>
        {isExpanded ? (
          <ChevronUp className="w-4 h-4 text-text-muted" />
        ) : (
          <ChevronDown className="w-4 h-4 text-text-muted" />
        )}
      </button>

      {/* Content */}
      {isExpanded && (
        <div className="p-3 space-y-3">
          {category === 'charts' ? (
            <ChartGrid artifacts={artifacts} onDownload={onDownload} />
          ) : category === 'datasets' ? (
            <DatasetList artifacts={artifacts} onDownload={onDownload} />
          ) : (
            <FileList artifacts={artifacts} onDownload={onDownload} />
          )}
        </div>
      )}
    </div>
  );
}

/**
 * Grid layout for chart images.
 */
function ChartGrid({ artifacts, onDownload }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
      {artifacts.map((artifact) => (
        <ChartPreview key={artifact.id} artifact={artifact} onDownload={onDownload} />
      ))}
    </div>
  );
}

/**
 * Single chart preview with click-to-expand.
 */
function ChartPreview({ artifact, onDownload }) {
  const [fullscreen, setFullscreen] = useState(false);
  const [error, setError] = useState(false);

  if (error) {
    return (
      <ArtifactDownloadCard
        artifact={artifact}
        onDownload={onDownload}
        error="Could not load preview"
      />
    );
  }

  return (
    <>
      <div className="rounded-lg overflow-hidden bg-white/5 group shadow-sm transition-all hover:shadow-md">
        <div
          className="aspect-video relative cursor-pointer"
          onClick={() => setFullscreen(true)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={artifact.downloadUrl}
            alt={artifact.filename}
            className="w-full h-full object-contain"
            onError={() => setError(true)}
            loading="lazy"
          />
          <div className="absolute inset-0 bg-black/0 group-hover:bg-black/20 transition-colors flex items-center justify-center">
            <span className="opacity-0 group-hover:opacity-100 text-xs text-white bg-black/50 px-2 py-1 rounded">
              Click to expand
            </span>
          </div>
        </div>
        <div className="px-3 py-2 bg-black/10 flex items-center justify-between">
          <span className="text-xs text-text-secondary truncate">{artifact.filename}</span>
          {onDownload && (
            <button
              onClick={(e) => { e.stopPropagation(); onDownload(artifact); }}
              className="text-xs text-accent hover:text-accent/80 transition-colors"
            >
              Download
            </button>
          )}
        </div>
      </div>

      {/* Fullscreen overlay */}
      {fullscreen && (
        <div
          className="fixed inset-0 z-50 bg-black/90 flex items-center justify-center cursor-pointer p-4"
          onClick={() => setFullscreen(false)}
        >
          {/* eslint-disable-next-line @next/next/no-img-element */}
          <img
            src={artifact.downloadUrl}
            alt={artifact.filename}
            className="max-w-full max-h-full object-contain"
          />
          <div className="absolute bottom-4 left-1/2 -translate-x-1/2 flex items-center gap-3">
            <span className="text-sm text-white/80">{artifact.filename}</span>
            {onDownload && (
              <button
                onClick={(e) => { e.stopPropagation(); onDownload(artifact); }}
                className="px-3 py-1.5 text-xs bg-white/20 hover:bg-white/30 text-white rounded-md transition-colors"
              >
                Download
              </button>
            )}
          </div>
        </div>
      )}
    </>
  );
}

/**
 * List layout for dataset files with table preview.
 */
function DatasetList({ artifacts, onDownload }) {
  return (
    <div className="space-y-3">
      {artifacts.map((artifact) => {
        const ext = artifact.filename.split('.').pop()?.toLowerCase();
        const isPreviewable = ['csv', 'json'].includes(ext);

        return isPreviewable ? (
          <ArtifactTablePreview
            key={artifact.id}
            artifact={artifact}
            onDownload={onDownload}
          />
        ) : (
          <ArtifactDownloadCard
            key={artifact.id}
            artifact={artifact}
            onDownload={onDownload}
          />
        );
      })}
    </div>
  );
}

/**
 * Simple list for other file types.
 */
function FileList({ artifacts, onDownload }) {
  return (
    <div className="space-y-2">
      {artifacts.map((artifact) => (
        <ArtifactDownloadCard
          key={artifact.id}
          artifact={artifact}
          onDownload={onDownload}
        />
      ))}
    </div>
  );
}

/**
 * Categorize artifact based on filename extension.
 */
function categorizeByFilename(filename) {
  const ext = (filename || '').split('.').pop()?.toLowerCase() || '';

  // Charts
  if (['png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'].includes(ext)) {
    return 'charts';
  }

  // Datasets
  if (['csv', 'tsv', 'json', 'xlsx', 'xls', 'parquet'].includes(ext)) {
    return 'datasets';
  }

  // Models
  if (['pkl', 'pickle', 'joblib', 'h5', 'pt', 'pth', 'onnx', 'pb', 'keras'].includes(ext)) {
    return 'models';
  }

  // Reports
  if (['pdf', 'docx', 'doc', 'md', 'txt', 'html', 'rtf'].includes(ext)) {
    return 'reports';
  }

  return 'files';
}

export default memo(ArtifactGallery);

'use client';

/**
 * FileViewerContent — renders a public file URL in-browser without forcing download.
 *
 * Route: /view?url=<encoded-https-url>
 *
 * Strategy by extension:
 *   .pdf                          → iframe → backend proxy (Content-Disposition: inline)
 *   .docx .doc .xlsx .xls .pptx
 *   .ppt .odt .ods .odp          → MS Office Online Viewer iframe
 *   .txt .csv .md .rtf            → backend proxy (renders as plain text)
 *   other                         → download fallback card
 */

import { useEffect, useState, useCallback } from 'react';
import { useSearchParams, useRouter } from 'next/navigation';
import {
  ChevronLeft,
  Download,
  ExternalLink,
  AlertTriangle,
  FileText,
} from 'lucide-react';

const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE_URL || 'http://localhost:8000';
const FILE_VIEWER_BASE = `${API_BASE}/api/v1`;

const OFFICE_EXTS = new Set([
  '.docx', '.doc', '.xlsx', '.xls', '.pptx', '.ppt', '.odt', '.ods', '.odp',
]);
const PDF_EXTS = new Set(['.pdf']);
const TEXT_EXTS = new Set(['.txt', '.csv', '.md', '.rtf']);

function getExtension(url) {
  try {
    const path = new URL(url).pathname.toLowerCase();
    const dot = path.lastIndexOf('.');
    return dot !== -1 ? path.slice(dot) : '';
  } catch {
    return '';
  }
}

function getFilename(url) {
  try {
    const path = new URL(url).pathname;
    return path.split('/').filter(Boolean).pop() || 'file';
  } catch {
    return 'file';
  }
}

function getDomain(url) {
  try {
    return new URL(url).hostname.replace(/^www\./, '');
  } catch {
    return url;
  }
}

/* ── Sub-components ── */

function TopBar({ filename, domain, fileUrl, onBack }) {
  return (
    <div className="h-12 shrink-0 flex items-center gap-3 px-4 bg-[var(--surface-sunken)] border-b border-[var(--border)] z-10">
      <button
        onClick={onBack}
        className="flex items-center gap-1.5 text-sm text-[var(--text-muted)] hover:text-[var(--text-primary)] transition-colors group"
        title="Back"
      >
        <ChevronLeft className="w-4 h-4 group-hover:-translate-x-0.5 transition-transform" />
        <span className="hidden sm:inline">Back</span>
      </button>

      <div className="w-px h-5 bg-[var(--border)]" />

      {/* Favicon + domain */}
      <img
        src={`https://www.google.com/s2/favicons?sz=32&domain=${domain}`}
        alt=""
        className="w-4 h-4 rounded-sm shrink-0"
        onError={(e) => {
          e.target.style.display = 'none';
        }}
      />
      <span className="text-xs text-[var(--text-muted)] font-medium uppercase tracking-wide hidden sm:block">
        {domain}
      </span>

      <div className="w-px h-5 bg-[var(--border)] hidden sm:block" />

      {/* Filename */}
      <span className="text-sm text-[var(--text-primary)] truncate flex-1 min-w-0">
        {decodeURIComponent(filename)}
      </span>

      {/* Action buttons */}
      <div className="flex items-center gap-1.5 shrink-0">
        <a
          href={fileUrl}
          download
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-overlay)] transition-colors"
          title="Download original"
        >
          <Download className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Download</span>
        </a>
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs text-[var(--text-muted)] hover:text-[var(--text-primary)] hover:bg-[var(--surface-overlay)] transition-colors"
          title="Open original URL"
        >
          <ExternalLink className="w-3.5 h-3.5" />
          <span className="hidden sm:inline">Open Original</span>
        </a>
      </div>
    </div>
  );
}

function LoadingSpinner({ message = 'Loading\u2026' }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 text-[var(--text-muted)]">
      <div className="w-10 h-10 border-2 border-[var(--border)] border-t-(--accent) rounded-full animate-spin" />
      <p className="text-sm">{message}</p>
    </div>
  );
}

function ErrorCard({ message, fileUrl }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-4 p-8">
      <div className="w-16 h-16 rounded-2xl bg-[var(--danger-subtle)] border border-[var(--danger-border)] flex items-center justify-center">
        <AlertTriangle className="w-8 h-8 text-[var(--danger)]" />
      </div>
      <div className="text-center max-w-sm">
        <h3 className="text-[var(--text-primary)] font-semibold mb-1">
          Cannot display file
        </h3>
        <p className="text-sm text-[var(--text-muted)]">{message}</p>
      </div>
      {fileUrl && (
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          download
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--surface-overlay)] hover:bg-[var(--surface-100)] text-[var(--text-primary)] text-sm transition-colors"
        >
          <Download className="w-4 h-4" />
          Download file instead
        </a>
      )}
    </div>
  );
}

function OtherFileCard({ fileUrl, filename, ext }) {
  return (
    <div className="flex-1 flex flex-col items-center justify-center gap-5 p-8">
      <div className="w-20 h-20 rounded-2xl bg-[var(--surface-overlay)] border border-[var(--border-strong)] flex items-center justify-center">
        <FileText className="w-10 h-10 text-[var(--text-muted)]" />
      </div>
      <div className="text-center">
        <h3 className="text-[var(--text-primary)] font-semibold mb-1">
          {decodeURIComponent(filename)}
        </h3>
        <p className="text-sm text-[var(--text-muted)]">
          {ext ? `${ext.slice(1).toUpperCase()} file` : 'File'} — cannot be
          previewed in the browser.
        </p>
      </div>
      <div className="flex gap-2">
        <a
          href={fileUrl}
          download
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--accent)] hover:bg-[var(--accent-light)] text-white text-sm font-medium transition-colors"
        >
          <Download className="w-4 h-4" />
          Download
        </a>
        <a
          href={fileUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[var(--surface-overlay)] hover:bg-[var(--surface-100)] text-[var(--text-primary)] text-sm transition-colors"
        >
          <ExternalLink className="w-4 h-4" />
          Open URL
        </a>
      </div>
    </div>
  );
}

/* ── Main component ── */

export default function FileViewerContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const rawUrl = searchParams.get('url') || '';

  const [state, setState] = useState('loading'); // loading | validating | ready | error
  const [errorMsg, setErrorMsg] = useState('');
  const [viewerInfo, setViewerInfo] = useState(null);
  const [iframeLoaded, setIframeLoaded] = useState(false);

  const handleBack = () => {
    if (typeof window !== 'undefined' && window.history.length > 1) {
      router.back();
    } else {
      router.push('/');
    }
  };

  const validateAndLoad = useCallback(async () => {
    if (!rawUrl) {
      setState('error');
      setErrorMsg(
        'No file URL was provided. Add ?url=<encoded-url> to the address bar.'
      );
      return;
    }

    if (!rawUrl.startsWith('https://')) {
      setState('error');
      setErrorMsg('Only HTTPS file URLs are supported.');
      return;
    }

    setState('validating');
    try {
      const res = await fetch(
        `${FILE_VIEWER_BASE}/file-viewer/info?url=${encodeURIComponent(rawUrl)}`,
        { credentials: 'omit' }
      );
      if (!res.ok) {
        const body = await res.json().catch(() => ({}));
        throw new Error(body.detail || `Server returned ${res.status}`);
      }
      const info = await res.json();
      setViewerInfo(info);
      setState('ready');
    } catch (err) {
      setState('error');
      setErrorMsg(err.message || 'Failed to validate the file URL.');
    }
  }, [rawUrl]);

  useEffect(() => {
    validateAndLoad();
  }, [validateAndLoad]);

  /* ── Derived display values ── */
  const ext = viewerInfo?.ext ?? getExtension(rawUrl);
  const filename = viewerInfo?.filename ?? getFilename(rawUrl);
  const domain = getDomain(rawUrl);

  const proxyUrl = `${FILE_VIEWER_BASE}/file-viewer/proxy?url=${encodeURIComponent(rawUrl)}`;
  const officeUrl = viewerInfo?.office_viewer_url ?? '';

  /* ── Render ── */
  return (
    <div className="h-screen flex flex-col bg-[var(--surface)] text-[var(--text-primary)] overflow-hidden">
      <TopBar
        filename={filename}
        domain={domain}
        fileUrl={rawUrl}
        onBack={handleBack}
      />

      <div className="flex-1 flex overflow-hidden">
        {state === 'loading' || state === 'validating' ? (
          <LoadingSpinner
            message={
              state === 'validating' ? 'Validating URL\u2026' : 'Loading\u2026'
            }
          />
        ) : state === 'error' ? (
          <ErrorCard message={errorMsg} fileUrl={rawUrl} />
        ) : viewerInfo?.kind === 'pdf' ? (
          <div className="flex-1 relative flex flex-col">
            {!iframeLoaded && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--text-muted)] bg-[var(--surface)] z-10">
                <div className="w-10 h-10 border-2 border-[var(--border)] border-t-(--danger) rounded-full animate-spin" />
                <p className="text-sm">Loading PDF\u2026</p>
              </div>
            )}
            <iframe
              src={proxyUrl}
              title={filename}
              className="flex-1 w-full h-full border-0"
              onLoad={() => setIframeLoaded(true)}
              onError={() => {
                setState('error');
                setErrorMsg(
                  'Failed to load PDF. The file may be unavailable or require authentication.'
                );
              }}
              sandbox="allow-scripts allow-same-origin allow-forms allow-popups"
            />
          </div>
        ) : viewerInfo?.kind === 'office' ? (
          <div className="flex-1 relative flex flex-col">
            {!iframeLoaded && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--text-muted)] bg-[var(--surface)] z-10">
                <div className="w-10 h-10 border-2 border-[var(--border)] border-t-(--accent) rounded-full animate-spin" />
                <p className="text-sm">Opening in Office Viewer\u2026</p>
                <p className="text-xs text-[var(--text-muted)]">
                  The file must be publicly accessible on the internet.
                </p>
              </div>
            )}
            <div className="shrink-0 flex items-center gap-2 px-4 py-2 bg-[var(--surface-raised)] border-b border-[var(--border)] text-xs text-[var(--text-muted)]">
              <FileText className="w-4 h-4 text-[var(--accent)]" />
              Powered by Microsoft Office Online Viewer — file must be publicly
              accessible
            </div>
            <iframe
              src={officeUrl}
              title={filename}
              className="flex-1 w-full h-full border-0"
              onLoad={() => setIframeLoaded(true)}
              frameBorder="0"
              allowFullScreen
            />
          </div>
        ) : viewerInfo?.kind === 'text' ? (
          <div className="flex-1 relative flex flex-col">
            {!iframeLoaded && (
              <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 text-[var(--text-muted)] bg-[var(--surface)] z-10">
                <div className="w-10 h-10 border-2 border-[var(--border)] border-t-(--success) rounded-full animate-spin" />
                <p className="text-sm">Loading file\u2026</p>
              </div>
            )}
            <iframe
              src={proxyUrl}
              title={filename}
              className="flex-1 w-full h-full border-0"
              onLoad={() => setIframeLoaded(true)}
              sandbox="allow-scripts allow-same-origin"
            />
          </div>
        ) : (
          <OtherFileCard fileUrl={rawUrl} filename={filename} ext={ext} />
        )}
      </div>
    </div>
  );
}

'use client';

import { memo } from 'react';
import { CheckCircle2, BarChart3, Clock, Cpu } from 'lucide-react';


function ResultSummary({ summary, totalTime }) {
  if (!summary) {
    return null;
  }

  const text = typeof summary === 'string'
    ? summary
    : summary.text || summary.description || summary.title || null;

  
  const keyResults = typeof summary === 'object' ? (summary.key_results || []) : [];
  const metrics = typeof summary === 'object' ? summary.metrics : null;

  if (!text && !metrics && keyResults.length === 0) {
    return null;
  }

  return (
    <div className="result-summary mb-4 rounded-lg bg-surface-overlay/30 overflow-hidden shadow-sm">
      {}
      <div className="flex items-center gap-2 px-3 py-2 bg-emerald-500/10 border-b border-emerald-500/20">
        <CheckCircle2 className="w-4 h-4 text-emerald-400" />
        <span className="text-sm font-medium text-emerald-400">Result Summary</span>
        {totalTime > 0 && (
          <span className="text-xs text-text-muted ml-auto">
            {formatDuration(totalTime)}
          </span>
        )}
      </div>

      {}
      {text && (
        <div className="px-3 py-3">
          <p className="text-sm text-text-secondary leading-relaxed whitespace-pre-wrap">
            {text}
          </p>
        </div>
      )}

      {}
      {keyResults.length > 0 && (
        <div className="px-3 py-2">
          <ul className="space-y-1">
            {keyResults.map((item, idx) => (
              <li key={idx} className="flex items-start gap-2 text-sm text-text-secondary">
                <span className="text-emerald-400 mt-0.5 shrink-0">•</span>
                <span>{typeof item === 'string' ? item : JSON.stringify(item)}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {}
      {metrics && Object.keys(metrics).length > 0 && (
        <div className="px-3 py-2 bg-surface-raised/50">
          <div className="flex flex-wrap gap-4">
            {Object.entries(metrics).map(([key, value]) => (
              <MetricBadge key={key} label={key} value={value} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}


function MetricBadge({ label, value }) {
  const formattedValue = formatMetricValue(label, value);
  const lowerLabel = label.toLowerCase();
  
  
  const isScoreMetric = lowerLabel.includes('accuracy') || lowerLabel.includes('score') || lowerLabel.includes('f1');
  const isTimeMetric = lowerLabel.includes('time') || lowerLabel.includes('duration');
  const isModelMetric = lowerLabel.includes('model') || lowerLabel.includes('algorithm');

  return (
    <div className="flex items-center gap-2">
      {isScoreMetric && <BarChart3 className="w-3.5 h-3.5 text-text-muted" />}
      {isTimeMetric && <Clock className="w-3.5 h-3.5 text-text-muted" />}
      {isModelMetric && <Cpu className="w-3.5 h-3.5 text-text-muted" />}
      {!isScoreMetric && !isTimeMetric && !isModelMetric && <BarChart3 className="w-3.5 h-3.5 text-text-muted" />}
      <span className="text-xs text-text-muted capitalize">
        {formatLabel(label)}:
      </span>
      <span className="text-xs font-medium text-text-secondary">
        {formattedValue}
      </span>
    </div>
  );
}


function formatLabel(label) {
  return label
    .replace(/_/g, ' ')
    .replace(/([A-Z])/g, ' $1')
    .trim();
}


function formatMetricValue(label, value) {
  const lowerLabel = label.toLowerCase();

  
  if (
    lowerLabel.includes('accuracy') ||
    lowerLabel.includes('precision') ||
    lowerLabel.includes('recall') ||
    lowerLabel.includes('f1') ||
    lowerLabel.includes('score')
  ) {
    if (typeof value === 'number') {
      return value > 1 ? `${value.toFixed(1)}%` : `${(value * 100).toFixed(1)}%`;
    }
  }

  
  if (lowerLabel.includes('time') || lowerLabel.includes('duration')) {
    if (typeof value === 'number') {
      return formatDuration(value);
    }
  }

  
  if (typeof value === 'number') {
    if (Number.isInteger(value)) return value.toLocaleString();
    return value.toFixed(4);
  }

  return String(value);
}


function formatDuration(ms) {
  if (ms < 1000) return `${ms}ms`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)}s`;
  const mins = Math.floor(ms / 60000);
  const secs = ((ms % 60000) / 1000).toFixed(0);
  return `${mins}m ${secs}s`;
}


export function ResultSummaryCompact({ summary, totalTime }) {
  const text = typeof summary === 'string' ? summary : summary?.text;

  if (!text) return null;

  return (
    <div className="flex items-start gap-2 text-sm text-text-secondary">
      <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
      <div className="flex-1">
        <p className="line-clamp-2">{text}</p>
        {totalTime > 0 && (
          <span className="text-xs text-text-muted">{formatDuration(totalTime)}</span>
        )}
      </div>
    </div>
  );
}

export default memo(ResultSummary);

'use client';

export default function ResearchProgress({ steps = [], query = '' }) {
  return (
    <div className="research-progress">
      <div className="research-progress-header">
        <span className="research-icon">🔬</span>
        <div>
          <p className="research-title">Deep Research Running...</p>
          {query && <p className="research-query">&ldquo;{query}&rdquo;</p>}
        </div>
      </div>
      <div className="research-steps">
        {steps.map((step, idx) => (
          <div key={idx} className={`research-step research-step--${step.status}`}>
            <span className="research-step-indicator">
              {step.status === 'done' && '✅'}
              {step.status === 'active' && <span className="research-pulse-dot" />}
              {step.status === 'pending' && '⏳'}
            </span>
            <span className="research-step-label">{step.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

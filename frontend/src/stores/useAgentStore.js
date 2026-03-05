import { create } from 'zustand';

/**
 * Zustand store for agent execution state.
 * Tracks progress steps, artifacts, summary, and technical logs.
 */

const initialState = {
  // Execution state
  isExecuting: false,
  executionId: null,
  
  // Progress tracking
  steps: [],           // [{ id, label, status: 'pending'|'running'|'completed'|'error', timestamp }]
  currentStepIndex: -1,
  
  // Results
  artifacts: [],       // [{ id, filename, mimeType, displayType, category, downloadUrl, size }]
  summary: null,       // { text, metrics: { accuracy, duration, etc. } }
  
  // Technical details (hidden by default)
  logs: [],            // [{ timestamp, type, message }]
  generatedCode: null, // { code, language }
  toolOutputs: [],     // [{ tool, output, duration }]
  
  // Intent detection
  detectedIntent: null,
};

const useAgentStore = create((set, get) => ({
  ...initialState,

  // ── Execution lifecycle ──
  
  startExecution: (executionId) => set({
    ...initialState,
    isExecuting: true,
    executionId,
    steps: [],
    artifacts: [],
    logs: [],
    toolOutputs: [],
  }),

  endExecution: () => set({
    isExecuting: false,
  }),

  resetExecution: () => set(initialState),

  // ── Step management ──
  
  addStep: (label) => set((state) => ({
    steps: [...state.steps, {
      id: `step-${Date.now()}`,
      label,
      status: 'pending',
      timestamp: Date.now(),
    }],
  })),

  updateStepStatus: (stepId, status) => set((state) => ({
    steps: state.steps.map((step) =>
      step.id === stepId ? { ...step, status } : step
    ),
  })),

  setCurrentStep: (label) => set((state) => {
    const steps = [...state.steps];
    
    // Mark all previous steps as completed
    const completedSteps = steps.map((s) => ({
      ...s,
      status: s.status === 'running' ? 'completed' : s.status,
    }));
    
    // Add new step as running
    const newStep = {
      id: `step-${Date.now()}`,
      label,
      status: 'running',
      timestamp: Date.now(),
    };
    
    return {
      steps: [...completedSteps, newStep],
      currentStepIndex: completedSteps.length,
    };
  }),

  completeCurrentStep: () => set((state) => {
    if (state.currentStepIndex < 0 || state.currentStepIndex >= state.steps.length) {
      return state;
    }
    
    const steps = [...state.steps];
    steps[state.currentStepIndex] = {
      ...steps[state.currentStepIndex],
      status: 'completed',
    };
    
    return { steps };
  }),

  markStepError: (stepId, error) => set((state) => ({
    steps: state.steps.map((step) =>
      step.id === stepId ? { ...step, status: 'error', error } : step
    ),
  })),

  // ── Artifact management ──
  
  addArtifact: (artifact) => set((state) => ({
    artifacts: [...state.artifacts, {
      id: artifact.artifact_id || artifact.id || `artifact-${Date.now()}`,
      filename: artifact.filename || artifact.name || 'file',
      mimeType: artifact.mime || artifact.mimeType || '',
      displayType: artifact.display_type || artifact.displayType || 'file_card',
      category: artifact.category || categorizeArtifact(artifact),
      downloadUrl: artifact.url || artifact.download_url || artifact.downloadUrl || '',
      size: artifact.size_bytes || artifact.sizeBytes || artifact.size || 0,
    }],
  })),

  clearArtifacts: () => set({ artifacts: [] }),

  // ── Summary ──
  
  setSummary: (summary) => set({
    summary: typeof summary === 'string' ? { text: summary } : summary,
  }),

  // ── Technical details ──
  
  addLog: (message, type = 'info') => set((state) => ({
    logs: [...state.logs, {
      timestamp: Date.now(),
      type,
      message,
    }],
  })),

  setGeneratedCode: (code, language = 'python') => set({
    generatedCode: { code, language },
  }),

  addToolOutput: (tool, output, duration = 0) => set((state) => ({
    toolOutputs: [...state.toolOutputs, { tool, output, duration }],
  })),

  // ── Intent ──
  
  setDetectedIntent: (intent) => set({ detectedIntent: intent }),

  // ── Bulk update from SSE events ──
  
  handleSSEEvent: (eventType, data) => {
    const { setCurrentStep, completeCurrentStep, addArtifact, setSummary, setGeneratedCode, addLog, setDetectedIntent, endExecution } = get();
    
    switch (eventType) {
      case 'step':
        setCurrentStep(data.label || data.step || data);
        break;
      case 'intent':
        setDetectedIntent(data.intent || data);
        break;
      case 'artifact':
        addArtifact(data);
        break;
      case 'summary':
        setSummary(data.summary || data.text || data);
        break;
      case 'code_generated':
        setGeneratedCode(data.code, data.language);
        addLog(`Code generated: ${data.code?.slice(0, 50)}...`, 'code');
        break;
      case 'tool_result':
        set((state) => ({
          toolOutputs: [...state.toolOutputs, {
            tool: data.tool,
            output: data.summary || data.output,
            duration: data.duration_ms || 0,
          }],
        }));
        break;
      case 'done':
        completeCurrentStep();
        endExecution();
        break;
      case 'error':
        addLog(data.error || 'Execution error', 'error');
        endExecution();
        break;
      default:
        // Unknown event, log it
        addLog(`Unknown event: ${eventType}`, 'debug');
    }
  },

  // ── Selectors ──
  
  getArtifactsByCategory: () => {
    const { artifacts } = get();
    const grouped = {};
    
    for (const artifact of artifacts) {
      const category = artifact.category || 'files';
      if (!grouped[category]) {
        grouped[category] = [];
      }
      grouped[category].push(artifact);
    }
    
    return grouped;
  },

  isStepComplete: (stepId) => {
    const { steps } = get();
    const step = steps.find((s) => s.id === stepId);
    return step?.status === 'completed';
  },
}));

/**
 * Categorize artifact based on file extension and mime type.
 */
function categorizeArtifact(artifact) {
  const filename = artifact.filename || '';
  const mime = artifact.mime || artifact.mimeType || '';
  const ext = filename.split('.').pop()?.toLowerCase() || '';

  // Chart/Image
  if (mime.startsWith('image/') || ['png', 'jpg', 'jpeg', 'svg', 'gif', 'webp'].includes(ext)) {
    return 'charts';
  }

  // Tables/Datasets
  if (['csv', 'tsv', 'xlsx', 'xls'].includes(ext) || mime.includes('csv') || mime.includes('spreadsheet')) {
    return 'datasets';
  }

  // Models
  if (['pkl', 'pickle', 'joblib', 'h5', 'pt', 'pth', 'onnx', 'pb'].includes(ext)) {
    return 'models';
  }

  // Reports
  if (['pdf', 'docx', 'doc', 'md', 'txt', 'html'].includes(ext)) {
    return 'reports';
  }

  // JSON data
  if (ext === 'json' || mime.includes('json')) {
    return 'datasets';
  }

  return 'files';
}

export default useAgentStore;

export const SLASH_COMMANDS = [
  {
    command: '/research',
    intent: 'WEB_RESEARCH',
    icon: '🔬',
    label: 'Research',
    description: 'Deep structured research with inline citations',
    placeholder: 'What do you want deeply researched on the web?',
    color: '#3b82f6',
    bgClass: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  },
  {
    command: '/code',
    intent: 'CODE_EXECUTION',
    icon: '💻',
    label: 'Code',
    description: 'Generate Python code — review, edit, then run',
    placeholder: 'Describe what Python to generate...',
    color: '#a855f7',
    bgClass: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  },
  {
    command: '/web',
    intent: 'WEB_SEARCH',
    icon: '🌐',
    label: 'Web',
    description: 'Quick web search for factual answers',
    placeholder: 'Quick web question...',
    color: '#10b981',
    bgClass: 'bg-emerald-500/15 text-emerald-400 border-emerald-500/30',
  },
];

export function getSlashCommand(command) {
  return SLASH_COMMANDS.find(c => c.command === command) || null;
}

export function getSlashCommandByIntent(intent) {
  return SLASH_COMMANDS.find(c => c.intent === intent) || null;
}

export function parseSlashCommand(message) {
  if (!message || !message.startsWith('/')) return null;
  const parts = message.trimStart().split(/\s+/);
  const cmd = parts[0].toLowerCase();
  const match = SLASH_COMMANDS.find(c => c.command === cmd);
  if (!match) return null;
  return { command: match, remainingMessage: parts.slice(1).join(' ').trim() };
}

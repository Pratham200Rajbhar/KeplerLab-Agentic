/**
 * Slash command definitions — shared between input UI and message display.
 *
 * Exactly three commands are active.  Each maps to an intent_override sent to
 * the backend, which bypasses AI intent detection and routes directly.
 *
 * Removed: /data  /quiz  /flash  /summarize  /mindmap
 */

export const SLASH_COMMANDS = [
  {
    command: '/agent',
    label: 'Agent',
    description: 'Autonomous task executor — plan, act, observe, decide',
    intent: 'AGENT_TASK',
    color: '#f97316',
    bgClass: 'bg-orange-500/15 text-orange-400 border-orange-500/30',
  },
  {
    command: '/web',
    label: 'Web',
    description: 'Deep structured research with inline citations',
    intent: 'WEB_RESEARCH',
    color: '#3b82f6',
    bgClass: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  },
  {
    command: '/code',
    label: 'Code',
    description: 'Generate code with explanation — you choose to run or copy',
    intent: 'CODE_GENERATION',
    color: '#a855f7',
    bgClass: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
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

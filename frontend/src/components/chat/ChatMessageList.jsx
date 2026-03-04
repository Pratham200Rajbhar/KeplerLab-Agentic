'use client';

import { useRef, useEffect, useCallback, memo } from 'react';
import { Lightbulb } from 'lucide-react';

import ChatMessage from './ChatMessage';
import MarkdownRenderer, { sanitizeStreamingMarkdown } from './MarkdownRenderer';
import ResearchReport from './ResearchReport';
import CodeReviewBlock from './CodeReviewBlock';

/**
 * LiveStepText — animated step indicator shown during streaming.
 */
function LiveStepText({ steps }) {
  const LIVE_TOOL_LABELS = {
    rag_tool:             'Searching your materials',
    research_tool:        'Researching the web',
    python_tool:          'Running code',
    data_profiler:        'Analyzing data',
    quiz_tool:            'Generating quiz',
    flashcard_tool:       'Creating flashcards',
    ppt_tool:             'Building slides',
    code_repair:          'Fixing error',
    agent_task_tool:      'Executing task…',
    web_research_tool:    'Researching (structured)…',
    code_generation_tool: 'Generating code…',
  };

  const latest = steps[steps.length - 1];
  const raw = latest?.tool || '';
  const key = Object.keys(LIVE_TOOL_LABELS).find((k) => raw.toLowerCase().includes(k));
  const label = key ? LIVE_TOOL_LABELS[key] : raw || 'Processing';

  return (
    <div className="flex items-center gap-1.5 mb-2 animate-fade-in">
      <span className="flex gap-0.5 items-end h-3 shrink-0">
        <span className="w-0.5 h-1.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '0ms' }} />
        <span className="w-0.5 h-2.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '150ms' }} />
        <span className="w-0.5 h-1.5 rounded-full bg-accent/60 animate-[bounce_1s_ease-in-out_infinite]" style={{ animationDelay: '300ms' }} />
      </span>
      <span className="text-xs text-text-muted">{label}…</span>
    </div>
  );
}

/**
 * ChatMessageList — owns the message list with auto-scroll.
 *
 * Props:
 *   messages — array of message objects
 *   notebookId — current notebook id
 *   currentSessionId — current chat session id
 *   onRetry — retry callback  
 *   onEdit — edit callback
 *   onDelete — delete callback
 *   streamingContent — current streaming text
 *   liveStepLog — live step log entries
 *   isThinking — whether agent is thinking
 *   researchMode / researchSteps / researchQuery — research state
 *   codeForReview — pending generated code
 *   agentTaskSteps — /agent ReAct step cards
 *   webResearchPhase — /web research phase progress
 *   agentStepLabel — thinking bar label
 *   isLoading — loading state
 *   hasSource — whether source is selected
 *   isSourceProcessing — sources are indexing
 *   selectedSources — array of selected source IDs
 *   materials — array of all materials
 *   onQuickAction — quick action callback
 */
function ChatMessageList({
  messages,
  notebookId,
  currentSessionId,
  onRetry,
  onEdit,
  onDelete,
  streamingContent,
  liveStepLog,
  isThinking,
  researchMode,
  researchSteps,
  researchQuery,
  codeForReview,
  agentTaskSteps,
  webResearchPhase,
  agentStepLabel,
  isLoading,
}) {
  const messagesEndRef = useRef(null);

  // Auto-scroll on new messages / streaming content
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const showTypingIndicator =
    isLoading && !streamingContent && !researchMode && liveStepLog.length === 0;

  return (
    <div className="max-w-4xl w-full mx-auto px-4 py-8 sm:px-6 md:px-8">
      {messages.map((msg) => (
        <ChatMessage
          key={msg.id}
          message={msg}
          notebookId={notebookId}
          onRetry={msg.role === 'assistant' ? onRetry : undefined}
          onEdit={msg.role === 'user' ? onEdit : undefined}
          onDelete={onDelete}
        />
      ))}

      {/* Research progress */}
      {researchMode && (
        <div className="message flex w-full justify-start message-ai">
          <div className="message-content w-full">
            <ResearchReport steps={researchSteps} query={researchQuery} />
          </div>
        </div>
      )}

      {/* Live streaming bubble */}
      {(streamingContent || codeForReview || (isThinking && liveStepLog.length > 0)) && (
        <div className="chat-msg chat-msg-ai group py-5">
          <div className="flex gap-3 w-full">
            <div className="ai-avatar shrink-0 mt-0.5 streaming-pulse">
              <Lightbulb className="w-4 h-4" />
            </div>
            <div className="flex-1 min-w-0">
              {/* /web phase progress */}
              {webResearchPhase && !streamingContent && (
                <div className="flex items-center gap-2 text-xs text-text-muted mb-2">
                  <span className="text-blue-400">🔬</span>
                  <span>Phase {webResearchPhase.phase}/5 — {webResearchPhase.label}</span>
                </div>
              )}
              {/* /agent ReAct step cards (in-progress) */}
              {agentTaskSteps.length > 0 && !streamingContent && (
                <div className="space-y-1.5 mb-2">
                  {agentTaskSteps.slice(-3).map((step, idx) => (
                    <div
                      key={step.id || idx}
                      className="text-xs text-text-muted bg-surface-overlay/40 rounded-lg px-3 py-1.5"
                    >
                      {step.phase === 'plan' && (
                        <><span className="text-orange-400">📋 Plan</span> {step.action}</>
                      )}
                      {step.phase === 'act' && (
                        <><span className="text-yellow-400">⚡ Act</span> {step.action}</>
                      )}
                      {step.phase === 'observe' && (
                        <><span className="text-green-400">🔎 Observe</span> {step.observation?.slice(0, 120)}…</>
                      )}
                    </div>
                  ))}
                </div>
              )}
              {liveStepLog.length > 0 && !streamingContent && !codeForReview && (
                <LiveStepText steps={liveStepLog} />
              )}
              {/* /code — code review block */}
              {codeForReview && (
                <CodeReviewBlock
                  code={codeForReview.code}
                  language={codeForReview.language}
                  explanation={codeForReview.explanation}
                  dependencies={codeForReview.dependencies}
                  notebookId={notebookId}
                  sessionId={currentSessionId}
                />
              )}
              {streamingContent && (
                <div className="markdown-content">
                  <MarkdownRenderer
                    content={sanitizeStreamingMarkdown(streamingContent)}
                  />
                  <span className="streaming-cursor" />
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Typing indicator */}
      {showTypingIndicator && (
        <div className="chat-msg chat-msg-ai py-5 animate-fade-in">
          <div className="flex gap-3 w-full">
            <div className="ai-avatar shrink-0 mt-0.5 streaming-pulse">
              <Lightbulb className="w-4 h-4" />
            </div>
            <div className="flex items-center gap-2 py-1">
              <div className="typing-indicator">
                <span />
                <span />
                <span />
              </div>
              {agentStepLabel && (
                <span className="text-xs text-text-muted">{agentStepLabel}</span>
              )}
            </div>
          </div>
        </div>
      )}
      <div ref={messagesEndRef} />
    </div>
  );
}

export default memo(ChatMessageList);

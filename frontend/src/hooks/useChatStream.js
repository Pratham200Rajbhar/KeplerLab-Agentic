'use client';

import { useRef, useCallback, useState } from 'react';
import { streamChat, createChatSession, getChatSessions } from '@/lib/api/chat';
import { readSSEStream } from '@/lib/utils/helpers';

/**
 * useChatStream — owns all SSE event processing logic extracted from ChatPanel.
 *
 * Handles event types: token, step, step_done, code_written, code_generating,
 * code_stdout, stdout, agent_step, agent_start, agent_reflection,
 * web_research_phase, code_for_review, repair_attempt, repair_success,
 * file_ready, meta, blocks, artifact, research_phase, research_source,
 * citations, done, error
 */
export default function useChatStream() {
  const abortControllerRef = useRef(null);
  const [isStreaming, setIsStreaming] = useState(false);

  const startStream = useCallback(async ({
    message,
    notebookId,
    materialIds,
    sessionId,
    intentOverride,
    onSessionCreated,
    onToken,
    onStep,
    onStepDone,
    onCodeWritten,
    onCodeGenerating,
    onCodeStdout,
    onStdout,
    onAgentStep,
    onAgentStart,
    onAgentReflection,
    onWebResearchPhase,
    onCodeForReview,
    onRepairAttempt,
    onRepairSuccess,
    onFileReady,
    onMeta,
    onBlocks,
    onArtifact,
    onResearchPhase,
    onResearchSource,
    onCitations,
    onDone,
    onError,
    onStreamEnd,
  }) => {
    const ac = new AbortController();
    abortControllerRef.current = ac;
    setIsStreaming(true);

    let accumulated = '';
    let agentMeta = null;
    let messageBlocks = [];
    let localStepLog = [];
    let localPendingFiles = [];

    try {
      // Create session if needed
      let activeSessionId = sessionId;
      if (!activeSessionId) {
        const title = message.slice(0, 30) + (message.length > 30 ? '...' : '');
        const res = await createChatSession(notebookId, title);
        activeSessionId = res.session_id;
        onSessionCreated?.(activeSessionId);
      }

      const response = await streamChat(
        null,
        message,
        notebookId,
        materialIds,
        activeSessionId,
        ac.signal,
        intentOverride,
      );

      const TOOL_STEP_LABELS = {
        rag_tool:             'Searching materials…',
        research_tool:        'Researching online…',
        python_tool:          'Running Python…',
        data_profiler:        'Profiling dataset…',
        quiz_tool:            'Generating quiz…',
        flashcard_tool:       'Creating flashcards…',
        ppt_tool:             'Building slides…',
        file_generator:       'Generating file…',
        agent_task_tool:      'Executing task…',
        web_research_tool:    'Deep-searching…',
        code_generation_tool: 'Generating code…',
      };

      await readSSEStream(response.body, {
        token: (payload) => {
          accumulated += payload.content || '';
          onToken?.(accumulated, payload.content || '');
        },
        step: (payload) => {
          const raw = payload.tool || payload.label || '';
          const label = TOOL_STEP_LABELS[raw] || payload.label || raw || 'Thinking…';
          onStep?.({ raw, label, payload });
        },
        step_done: (payload) => {
          const stepEntry = payload.step || { tool: payload.tool, status: payload.status };
          localStepLog.push(stepEntry);
          onStepDone?.(stepEntry, localStepLog);
        },
        code_written: (payload) => {
          onCodeWritten?.(payload);
        },
        code_generating: (payload) => {
          onCodeGenerating?.(payload);
        },
        code_stdout: (payload) => {
          onCodeStdout?.(payload);
        },
        stdout: (payload) => {
          onStdout?.(payload);
        },
        agent_step: (payload) => {
          onAgentStep?.(payload);
        },
        agent_start: (payload) => {
          onAgentStart?.(payload);
        },
        agent_reflection: (payload) => {
          onAgentReflection?.(payload);
        },
        web_research_phase: (payload) => {
          onWebResearchPhase?.(payload);
        },
        code_for_review: (payload) => {
          onCodeForReview?.(payload);
        },
        repair_attempt: (payload) => {
          onRepairAttempt?.(payload);
        },
        repair_success: (payload) => {
          onRepairSuccess?.(payload);
        },
        file_ready: (payload) => {
          localPendingFiles.push(payload);
          onFileReady?.(payload, localPendingFiles);
        },
        meta: (payload) => {
          agentMeta = payload;
          onMeta?.(payload);
        },
        blocks: (payload) => {
          messageBlocks = payload.blocks || [];
          onBlocks?.(messageBlocks);
        },
        artifact: (payload) => {
          onArtifact?.(payload);
        },
        research_phase: (payload) => {
          onResearchPhase?.(payload);
        },
        research_source: (payload) => {
          onResearchSource?.(payload);
        },
        citations: (payload) => {
          onCitations?.(payload);
        },
        done: (payload) => {
          onDone?.({
            accumulated,
            agentMeta,
            messageBlocks,
            localStepLog,
            localPendingFiles,
            elapsed: payload.elapsed || 0,
          });
          accumulated = '';
        },
        error: (payload) => {
          onError?.(payload);
          accumulated = '';
        },
      });

      // Fallback if no done event but content accumulated
      if (accumulated) {
        onDone?.({
          accumulated,
          agentMeta,
          messageBlocks,
          localStepLog,
          localPendingFiles,
          elapsed: 0,
        });
      }
    } catch (error) {
      if (error.name === 'AbortError') {
        // Pass accumulated content on abort so it can be saved
        onDone?.({
          accumulated,
          agentMeta,
          messageBlocks,
          localStepLog,
          localPendingFiles,
          elapsed: 0,
          aborted: true,
        });
      } else {
        onError?.({ error: error.message });
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
      onStreamEnd?.();
    }
  }, []);

  const cancelStream = useCallback(() => {
    abortControllerRef.current?.abort();
  }, []);

  return { startStream, cancelStream, isStreaming };
}

'use client';

import { useRef, useCallback, useState } from 'react';
import { streamChat, createChatSession, getChatSessions } from '@/lib/api/chat';
import { readSSEStream } from '@/lib/utils/helpers';

/**
 * useChatStream — owns all SSE event processing logic extracted from ChatPanel.
 *
 * Handles event types: token, step, step_done, code_written, code_generating,
 * code_stdout, stdout, web_research_phase, code_for_review, repair_attempt,
 * repair_success, file_ready, meta, blocks, artifact, research_phase,
 * research_source, citations, installing, installed, install_failed, pivot,
 * step_timing, done, error,
 * agent_start, tool_start, tool_result, code_generated,
 * code_block, done_generation,
 * web_start, web_scraping, web_sources,
 * research_start, execution_start, execution_done, execution_blocked,
 * install_progress, repair_suggestion
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
    // ── Self-healing events ──
    onInstalling,
    onInstalled,
    onInstallFailed,
    onPivot,
    onStepTiming,
    // ── Agentic pipeline events ──
    onAgentStart,
    onToolStart,
    onToolResult,
    onCodeGenerated,
    onCodeBlock,
    onDoneGeneration,
    onWebStart,
    onWebScraping,
    onWebSources,
    onResearchStart,
    onExecutionStart,
    onExecutionDone,
    onExecutionBlocked,
    onInstallProgress,
    onRepairSuggestion,
    // ── Lifecycle ──
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
        // ── New 3-stage self-healing events ──
        installing: (payload) => {
          onInstalling?.(payload);
        },
        installed: (payload) => {
          onInstalled?.(payload);
        },
        install_failed: (payload) => {
          onInstallFailed?.(payload);
        },
        pivot: (payload) => {
          onPivot?.(payload);
        },
        step_timing: (payload) => {
          onStepTiming?.(payload);
        },
        repairattempt: (payload) => {
          onRepairAttempt?.(payload);
        },
        // ── Agentic pipeline events ──
        agent_start: (payload) => {
          onAgentStart?.(payload);
        },
        tool_start: (payload) => {
          onToolStart?.(payload);
        },
        tool_result: (payload) => {
          onToolResult?.(payload);
        },
        code_generated: (payload) => {
          onCodeGenerated?.(payload);
        },
        code_block: (payload) => {
          onCodeBlock?.(payload);
        },
        done_generation: (payload) => {
          onDoneGeneration?.(payload);
        },
        web_start: (payload) => {
          onWebStart?.(payload);
        },
        web_scraping: (payload) => {
          onWebScraping?.(payload);
        },
        web_sources: (payload) => {
          onWebSources?.(payload);
        },
        research_start: (payload) => {
          onResearchStart?.(payload);
        },
        execution_start: (payload) => {
          onExecutionStart?.(payload);
        },
        execution_done: (payload) => {
          onExecutionDone?.(payload);
        },
        execution_blocked: (payload) => {
          onExecutionBlocked?.(payload);
        },
        install_progress: (payload) => {
          onInstallProgress?.(payload);
        },
        repair_suggestion: (payload) => {
          onRepairSuggestion?.(payload);
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

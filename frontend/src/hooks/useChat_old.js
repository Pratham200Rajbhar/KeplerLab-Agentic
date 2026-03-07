/**
 * useChat - Clean React hook for chat operations with unified streaming.
 * 
 * Provides simple interface for sending messages, managing state,
 * and handling streaming responses.
 */

import { useState, useCallback, useRef, useEffect } from 'react';
import { streamChat } from '../api/chat';
import { StreamClient } from '../stream/client';
import { StreamState } from '../stream/state';

/**
 * Chat hook with unified streaming
 * @param {string} notebookId - Current notebook ID
 * @param {string} sessionId - Current chat session ID
 * @param {Array} materialIds - Selected material IDs
 * @returns {Object} Chat interface
 */
export function useChat(notebookId, sessionId, materialIds = []) {
  // Stream state
  const [streamState, setStreamState] = useState(null);
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState(null);
  
  // Client reference
  const clientRef = useRef(null);
  const stateRef = useRef(null);
  
  /**
   * Send a chat message
   * @param {string} message - User message
   * @param {string} intentOverride - Optional intent override
   * @returns {Promise<Object>} Final state
   */
  const sendMessage = useCallback(async (message, intentOverride = null) => {
    if (!notebookId || !message?.trim()) {
      return null;
    }
    
    try {
      // Create new stream state
      const state = new StreamState();
      state.isStreaming = true;
      stateRef.current = state;
      setStreamState(state.snapshot());
      setIsStreaming(true);
      setError(null);
      
      // Create client
      const client = new StreamClient();
      clientRef.current = client;
      
      // Register event handlers that update state
      client.on('token', (data) => {
        state.handleEvent('token', data);
        setStreamState(state.snapshot());
      });
      
      client.on('step', (data) => {
        state.handleEvent('step', data);
        setStreamState(state.snapshot());
      });
      
      client.on('artifact', (data) => {
        state.handleEvent('artifact', data);
        setStreamState(state.snapshot());
      });
      
      client.on('code_block', (data) => {
        state.handleEvent('code_block', data);
        setStreamState(state.snapshot());
      });
      
      client.on('summary', (data) => {
        state.handleEvent('summary', data);
        setStreamState(state.snapshot());
      });
      
      client.on('meta', (data) => {
        state.handleEvent('meta', data);
        setStreamState(state.snapshot());
      });
      
      client.on('blocks', (data) => {
        state.handleEvent('blocks', data);
        setStreamState(state.snapshot());
      });
      
      // Agent events
      client.on('agent_start', (data) => {
        state.handleEvent('agent_start', data);
        setStreamState(state.snapshot());
      });
      
      client.on('tool_start', (data) => {
        state.handleEvent('tool_start', data);
        setStreamState(state.snapshot());
      });
      
      client.on('tool_result', (data) => {
        state.handleEvent('tool_result', data);
        setStreamState(state.snapshot());
      });
      
      // Web search events
      client.on('web_start', (data) => {
        state.handleEvent('web_start', data);
        setStreamState(state.snapshot());
      });
      
      client.on('web_sources', (data) => {
        state.handleEvent('web_sources', data);
        setStreamState(state.snapshot());
      });
      
      // Research events
      client.on('research_start', (data) => {
        state.handleEvent('research_start', data);
        setStreamState(state.snapshot());
      });
      
      client.on('research_phase', (data) => {
        state.handleEvent('research_phase', data);
        setStreamState(state.snapshot());
      });
      
      // Error handling
      client.on('error', (data) => {
        state.handleEvent('error', data);
        setStreamState(state.snapshot());
        setError(data.error);
        setIsStreaming(false);
      });
      
      // Done handling
      client.on('done', (data) => {
        state.handleEvent('done', data);
        const finalState = state.finalize();
        setStreamState(state.snapshot());
        setIsStreaming(false);
        return finalState;
      });
      
      // Start streaming
      const response = await streamChat(
        null,
        message,
        notebookId,
        materialIds,
        sessionId,
        null,
        intentOverride
      );
      
      await client.connect(response);
      
      // Return final state
      return stateRef.current?.finalize();
      
    } catch (err) {
      console.error('Chat error:', err);
      setError(err.message);
      setIsStreaming(false);
      throw err;
    }
  }, [notebookId, sessionId, materialIds]);
  
  /**
   * Abort current streaming
   */
  const abort = useCallback(() => {
    if (clientRef.current) {
      clientRef.current.close();
      clientRef.current = null;
    }
    setIsStreaming(false);
  }, []);
  
  /**
   * Reset/clear state
   */
  const reset = useCallback(() => {
    abort();
    setStreamState(null);
    setError(null);
    stateRef.current = null;
  }, [abort]);
  
  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (clientRef.current) {
        clientRef.current.close();
      }
    };
  }, []);
  
  return {
    streamState,
    isStreaming,
    error,
    sendMessage,
    abort,
    reset,
  };
}

export default useChat;

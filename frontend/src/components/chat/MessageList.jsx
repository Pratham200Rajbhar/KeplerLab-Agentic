'use client';

import MessageItem from './MessageItem';
import TypingIndicator from './TypingIndicator';
import useAutoScroll from '@/hooks/useAutoScroll';


export default function MessageList({ messages, isStreaming, error, onRetry, onEdit, onDelete, notebookId, sessionId }) {
  const lastMessage = messages[messages.length - 1];
  // Avoid duplicate left-side status icons: when an assistant placeholder message
  // is already present, MessageItem handles the streaming UI by itself.
  const showTyping = isStreaming && lastMessage?.role !== 'assistant';

  const { containerRef, scrollToBottom, isAtBottom } = useAutoScroll([
    messages.length,
    lastMessage?.content?.length,
    lastMessage?.codeBlocks?.length,
    isStreaming,
  ]);

  return (
    <div className="workspace-chat-feed-wrap relative flex-1 min-h-0">
      <div ref={containerRef} className="workspace-chat-feed h-full overflow-y-auto scroll-smooth custom-scrollbar">
        <div className="pt-5 pb-28">
          {messages.map((msg, index) => {
            const isLastAssistant =
              index === messages.length - 1 && msg.role === 'assistant';

            return (
              <MessageItem
                key={msg.id}
                message={msg}
                isStreaming={isLastAssistant && isStreaming}
                onRetry={!isStreaming && msg.role === 'assistant' ? onRetry : undefined}
                onEdit={onEdit}
                onDelete={onDelete}
                notebookId={notebookId}
                sessionId={sessionId}
              />
            );
          })}

          {showTyping && <TypingIndicator />}
        </div>
      </div>

      { }
      {!isAtBottom && (
        <button
          onClick={() => scrollToBottom()}
          className="absolute bottom-5 right-5 z-20 w-9 h-9 rounded-full bg-surface-raised/95 border border-border/60 shadow-lg flex items-center justify-center text-text-muted hover:text-text-primary hover:border-accent/40 transition-colors"
          aria-label="Scroll to bottom"
        >
          <svg
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
          >
            <polyline points="6 9 12 15 18 9" />
          </svg>
        </button>
      )}
    </div>
  );
}

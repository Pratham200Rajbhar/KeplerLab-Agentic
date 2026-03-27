'use client';

import MessageItem from './MessageItem';
import TypingIndicator from './TypingIndicator';
import useAutoScroll from '@/hooks/useAutoScroll';


export default function MessageList({ messages, isStreaming, error, onRetry, onEdit, onDelete, notebookId, sessionId }) {
  const lastMessage = messages[messages.length - 1];
  const showTyping =
    isStreaming &&
    lastMessage?.role === 'assistant' &&
    !lastMessage.content &&
    !lastMessage.codeBlocks?.length;

  const { containerRef, scrollToBottom, isAtBottom } = useAutoScroll([
    messages.length,
    lastMessage?.content?.length,
    lastMessage?.codeBlocks?.length,
    isStreaming,
  ]);

  return (
    <div ref={containerRef} className="flex-1 min-h-0 overflow-y-auto scroll-smooth">
      <div className="pt-4 pb-24">
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

      { }
      {!isAtBottom && (
        <button
          onClick={() => scrollToBottom()}
          className="fixed bottom-28 right-8 z-20 w-8 h-8 rounded-full bg-surface-raised border border-white/10 shadow-lg flex items-center justify-center text-text-muted hover:text-text-primary transition-colors"
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

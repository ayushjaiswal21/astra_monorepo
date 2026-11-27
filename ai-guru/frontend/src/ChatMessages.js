import React from 'react';
import Message from './Message';

const ChatMessages = ({ messages, messagesEndRef, submitFeedback, feedbackLoading, processingMessages, showJumpToLatest, scrollToBottom }) => {
  return (
    <div className="p-6" data-testid="chat-messages">
      {messages.map((msg, index) => (
        <Message
          key={msg.id || index}
          msg={msg}
          index={index}
          submitFeedback={submitFeedback}
          feedbackLoading={feedbackLoading}
          processingMessages={processingMessages}
        />
      ))}
      <div ref={messagesEndRef} />
      {showJumpToLatest && (
        <button
          onClick={scrollToBottom}
          className="btn-filled"
          title="Jump to latest message"
          style={{
            position: 'fixed',
            bottom: 'var(--space-12)',
            right: 'var(--space-8)',
            borderRadius: '999px',
            boxShadow: 'var(--shadow-soft)',
            zIndex: 500,
          }}
        >
          ↓ Latest
        </button>
      )}
    </div>
  );
};

export default ChatMessages;
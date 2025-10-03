import React from 'react';
import Message from './Message';

const ChatMessages = ({ messages, messagesEndRef, submitFeedback, feedbackLoading }) => {
  return (
    <div style={{ padding: "20px" }}>
      {messages.map((msg, index) => (
        <Message 
          key={msg.id || index} 
          msg={msg} 
          index={index} 
          submitFeedback={submitFeedback}
          feedbackLoading={feedbackLoading}
        />
      ))}
      <div ref={messagesEndRef} />
    </div>
  );
};

export default ChatMessages;
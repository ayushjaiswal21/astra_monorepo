import React, { useState } from 'react';
import { marked } from 'marked';

const Message = ({ msg, index, submitFeedback, feedbackLoading, processingMessages }) => {
  const isUser = msg.sender === "user";
  const isProcessing = processingMessages.has(msg.id);
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(msg.text || "").then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    }).catch(() => {
      setCopied(false);
    });
  };

  return (
    <div className={`flex items-start gap-4 mb-6`}>
      <div
        className="flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center font-bold text-white"
        style={{ background: isUser ? 'var(--accent)' : '#374151' }}
      >
        {isUser ? "👤" : "🤖"}
      </div>

      <div className="flex-1">
        <div
          className={`px-4 py-3 rounded-lg ${isUser ? '' : 'bg-white border border-gray-200 text-gray-800'}`}
          style={isUser ? { background: 'var(--surface-2)', color: 'var(--text-primary)' } : undefined}
        >
          {msg.image && (
            <div className="mb-3">
              <img
                src={msg.image}
                alt={msg.imageName || "Uploaded image"}
                className="max-w-xs max-h-48 w-full h-auto rounded-md shadow-md cursor-pointer transition-transform hover:scale-105"
                onClick={() => window.open(msg.image, "_blank")}
              />
              <div className="text-xs text-gray-500 mt-1 italic">
                📷 {msg.imageName}
              </div>
            </div>
          )}
          {isProcessing ? (
            <div aria-label="AI is thinking" style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div style={{ height: "10px", width: "70%", borderRadius: "4px", background: "var(--surface-2)", opacity: 0.8 }} />
              <div style={{ height: "10px", width: "45%", borderRadius: "4px", background: "var(--surface-2)", opacity: 0.8 }} />
            </div>
          ) : (
            <>
              <div
                dangerouslySetInnerHTML={{ __html: marked.parse(msg.text || "") }}
                className="prose max-w-none"
              />
              {!isUser && (
                <button
                  onClick={handleCopy}
                  className="copy-btn"
                  style={{ marginTop: "var(--space-3)" }}
                  title="Copy response"
                >
                  {copied ? "Copied!" : "📋 Copy"}
                </button>
              )}

              {!isUser && msg.detectedLanguage && msg.languageName !== "Unknown" && msg.detectedLanguage !== "en" && (
                <div className="mt-3 inline-flex items-center gap-1 px-2 py-1 bg-gray-100 text-gray-600 text-xs rounded-full border border-gray-200">
                  🌐 {msg.languageName} {msg.confidence && `(${Math.round(msg.confidence * 100)}%)`}
                </div>
              )}

              {!isUser && msg.interactionId && !msg.feedbackSubmitted && (
                <div className="mt-4 flex items-center gap-2 flex-wrap">
                  <p className="text-xs text-gray-500 mr-2">Was this helpful?</p>
                  <button
                    onClick={() => submitFeedback(msg.interactionId, msg.sessionId, "thumbs_up")}
                    disabled={feedbackLoading.has(msg.interactionId)}
                    className="px-3 py-1 text-xs bg-white hover:bg-gray-100 border border-gray-300 rounded-full transition-colors disabled:opacity-50"
                  >
                    👍 Yes
                  </button>
                  <button
                    onClick={() => submitFeedback(msg.interactionId, msg.sessionId, "thumbs_down")}
                    disabled={feedbackLoading.has(msg.interactionId)}
                    className="px-3 py-1 text-xs bg-white hover:bg-gray-100 border border-gray-300 rounded-full transition-colors disabled:opacity-50"
                  >
                    👎 No
                  </button>
                </div>
              )}

              {!isUser && msg.feedbackSubmitted && (
                <div className="mt-3 px-3 py-1 text-xs text-green-700 bg-green-100 border border-green-200 rounded-full inline-block">
                  ✓ Thanks for the feedback!
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
};

export default Message;
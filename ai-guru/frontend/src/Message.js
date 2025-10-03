import React from 'react';
import { marked } from 'marked';

const Message = ({ msg, index, submitFeedback, feedbackLoading }) => {
  return (
    <div
      className="message-enter"
      style={{
        marginBottom: "24px",
        display: "flex",
        alignItems: "flex-start",
        gap: "16px",
        animationDelay: `${index * 0.1}s`,
      }}
    >
      <div
        style={{
          width: "40px",
          height: "40px",
          borderRadius: "50%",
          background:
            msg.sender === "user"
              ? "linear-gradient(135deg, #6366f1, #8b5cf6)"
              : "linear-gradient(135deg, #10b981, #06b6d4)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          color: "white",
          fontSize: "16px",
          fontWeight: "700",
          flexShrink: 0,
          boxShadow:
            msg.sender === "user"
              ? "0 4px 12px rgba(99, 102, 241, 0.3)"
              : "0 4px 12px rgba(16, 185, 129, 0.3)",
          border: "2px solid rgba(255, 255, 255, 0.2)",
        }}
      >
        {msg.sender === "user" ? "👤" : "🤖"}
      </div>
      <div
        style={{
          flex: 1,
          padding: "12px 16px",
          backgroundColor:
            msg.sender === "user" ? "#f1f5f9" : "#f0fdf4",
          borderRadius: "12px",
          color: "#374151",
          fontSize: "14px",
          lineHeight: "1.5",
        }}
      >
        {msg.image && (
          <div style={{ marginBottom: "12px" }}>
            <img
              src={msg.image}
              alt={msg.imageName || "Uploaded image"}
              style={{
                maxWidth: "300px",
                maxHeight: "200px",
                width: "100%",
                height: "auto",
                borderRadius: "8px",
                boxShadow: "0 4px 8px rgba(0, 0, 0, 0.1)",
                cursor: "pointer",
                transition: "transform 0.2s ease",
              }}
              onClick={() => {
                window.open(msg.image, "_blank");
              }}
            />
            <div
              style={{
                fontSize: "12px",
                color: "#6b7280",
                marginTop: "4px",
                fontStyle: "italic",
              }}
            >
              📷 {msg.imageName}
            </div>
          </div>
        )}
        {msg.isLoading ? (
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              color: "#697565",
            }}
          >
            <div className="spinner"></div>
            <span>AI is thinking...</span>
            <div className="typing-indicator">
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
              <div className="typing-dot"></div>
            </div>
          </div>
        ) : (
          <>
            <div
              dangerouslySetInnerHTML={{ __html: marked.parse(msg.text || "") }}
              style={{
                lineHeight: "1.6",
              }}
            />
            {msg.sender === "ai" &&
              msg.detectedLanguage &&
              msg.languageName &&
              msg.languageName !== "Unknown" &&
              msg.detectedLanguage !== "en" && (
                <div
                  style={{
                    marginTop: "8px",
                    padding: "6px 10px",
                    backgroundColor: "rgba(16, 185, 129, 0.1)",
                    borderRadius: "16px",
                    fontSize: "12px",
                    color: "#059669",
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "4px",
                    border: "1px solid rgba(16, 185, 129, 0.2)",
                  }}
                >
                  🌐 {msg.languageName}{" "}
                  {msg.confidence &&
                    `(${Math.round(msg.confidence * 100)}%)`}
                </div>
              )}

            {msg.sender === "ai" &&
              msg.interactionId &&
              !msg.feedbackSubmitted && (
                <div
                  style={{
                    marginTop: "12px",
                    display: "flex",
                    gap: "8px",
                    alignItems: "center",
                    flexWrap: "wrap",
                  }}
                >
                  <div
                    style={{
                      fontSize: "12px",
                      color: "#6b7280",
                      marginRight: "4px",
                    }}
                  >
                    Was this helpful?
                  </div>
                  <button
                    onClick={() =>
                      submitFeedback(
                        msg.interactionId,
                        msg.sessionId,
                        "thumbs_up"
                      )
                    }
                    disabled={feedbackLoading.has(
                      msg.interactionId
                    )}
                    style={{
                      background: "none",
                      border: "1px solid #e5e7eb",
                      borderRadius: "16px",
                      padding: "4px 8px",
                      cursor: "pointer",
                      fontSize: "12px",
                      color: "#6b7280",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      transition: "all 0.2s",
                      opacity: feedbackLoading.has(
                        msg.interactionId
                      )
                        ? 0.6
                        : 1,
                    }}
                  >
                    👍 Yes
                  </button>
                  <button
                    onClick={() =>
                      submitFeedback(
                        msg.interactionId,
                        msg.sessionId,
                        "thumbs_down"
                      )
                    }
                    disabled={feedbackLoading.has(
                      msg.interactionId
                    )}
                    style={{
                      background: "none",
                      border: "1px solid #e5e7eb",
                      borderRadius: "16px",
                      padding: "4px 8px",
                      cursor: "pointer",
                      fontSize: "12px",
                      color: "#6b7280",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                      transition: "all 0.2s",
                      opacity: feedbackLoading.has(
                        msg.interactionId
                      )
                        ? 0.6
                        : 1,
                    }}
                  >
                    👎 No
                  </button>
                  <select
                    onChange={(e) => {
                      if (e.target.value) {
                        submitFeedback(
                          msg.interactionId,
                          msg.sessionId,
                          e.target.value
                        );
                        e.target.value = "";
                      }
                    }}
                    disabled={feedbackLoading.has(
                      msg.interactionId
                    )}
                    style={{
                      background: "none",
                      border: "1px solid #e5e7eb",
                      borderRadius: "16px",
                      padding: "4px 8px",
                      cursor: "pointer",
                      fontSize: "12px",
                      color: "#6b7280",
                      opacity: feedbackLoading.has(
                        msg.interactionId
                      )
                        ? 0.6
                        : 1,
                    }}
                  >
                    <option value="">Issues?</option>
                    <option value="format_mismatch">
                      Wrong format
                    </option>
                    <option value="too_long">Too long</option>
                    <option value="too_short">Too short</option>
                    <option value="off_topic">Off topic</option>
                  </select>
                </div>
              )}

            {msg.sender === "ai" && msg.feedbackSubmitted && (
              <div
                style={{
                  marginTop: "8px",
                  padding: "8px 12px",
                  backgroundColor: "#f0f9ff",
                  borderRadius: "16px",
                  fontSize: "12px",
                  color: "#0369a1",
                  display: "flex",
                  alignItems: "center",
                  gap: "6px",
                  border: "1px solid #0ea5e9",
                }}
              >
                <span>✓</span>
                <span>
                  Thanks! The AI learned from your{" "}
                  {msg.feedbackSubmitted.replace("_", " ")}{" "}
                  feedback.
                </span>
              </div>
            )}

            {msg.sender === "ai" && msg.feedbackMessage && (
              <div
                style={{
                  marginTop: "8px",
                  padding: "8px 12px",
                  backgroundColor: "#f0fdf4",
                  borderRadius: "16px",
                  fontSize: "12px",
                  color: "#15803d",
                  border: "1px solid #22c55e",
                }}
              >
                {msg.feedbackMessage}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default Message;
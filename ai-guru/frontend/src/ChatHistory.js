import React from 'react';

const ChatHistory = ({ 
    chatSessions,
    selectedSession,
    sidebarCollapsed,
    deleteAllChatHistory,
    deleteSession,
    setSelectedSession,
    setCurrentSessionId,
    setMessages
}) => {

  const handleSessionClick = (session) => {
    setSelectedSession(session);
    setCurrentSessionId(session.session_id);

    const displayMessages = [];
    session.messages.forEach((msg) => {
      displayMessages.push({
        id: msg.id * 2 - 1,
        text: msg.user_input,
        sender: "user",
      });
      displayMessages.push({
        id: msg.id * 2,
        text: msg.bot_response,
        sender: "ai",
        detectedLanguage: msg.language_code,
        languageName: msg.language_name,
        sessionId: msg.session_id,
        interactionId: msg._id || `${msg.session_id}_${msg.id * 2}`,
      });
    });
    setMessages(displayMessages);
  };

  return (
    <div
      style={{
        flex: 1,
        overflowY: "auto",
        padding: "0 16px",
        scrollbarWidth: "thin",
        scrollbarColor: "#374151 transparent",
      }}
    >
      {!sidebarCollapsed && (
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            marginBottom: "12px",
          }}
        >
          <div
            style={{
              fontSize: "12px",
              color: "#9ca3af",
              fontWeight: "600",
              textTransform: "uppercase",
              letterSpacing: "0.8px",
              opacity: 0.7,
            }}
          >
            Recent Chats
          </div>
          {chatSessions.length > 0 && (
            <button
              onClick={deleteAllChatHistory}
              style={{
                background: "transparent",
                border: "1px solid #4b5563",
                borderRadius: "4px",
                color: "#9ca3af",
                fontSize: "10px",
                padding: "3px 6px",
                cursor: "pointer",
                transition: "all 0.2s ease",
              }}
              onMouseEnter={(e) => {
                e.target.style.backgroundColor = "#dc2626";
                e.target.style.borderColor = "#dc2626";
                e.target.style.color = "white";
              }}
              onMouseLeave={(e) => {
                e.target.style.backgroundColor = "transparent";
                e.target.style.borderColor = "#4b5563";
                e.target.style.color = "#9ca3af";
              }}
              title="Delete all chat history"
            >
              Clear All
            </button>
          )}
        </div>
      )}

      {chatSessions.length === 0 ? (
        <div
          style={{
            color: "#6b7280",
            fontSize: "13px",
            fontStyle: "italic",
            textAlign: sidebarCollapsed ? "center" : "left",
            padding: "8px 0",
          }}
        >
          {sidebarCollapsed ? "📝" : "No conversations yet"}
        </div>
      ) : (
        chatSessions.map((session) => (
          <div
            key={session.session_id}
            className="sidebar-item"
            style={{
              display: "flex",
              alignItems: "center",
              padding: "8px 12px",
              marginBottom: "4px",
              borderRadius: "6px",
              backgroundColor:
                selectedSession &&
                selectedSession.session_id === session.session_id
                  ? "#2d2d2d"
                  : "transparent",
              fontSize: "14px",
              color: "#ccc",
              transition: "background-color 0.2s ease",
              position: "relative",
            }}
            onClick={() => handleSessionClick(session)}
          >
            <div
              style={{
                flex: 1,
                cursor: "pointer",
                whiteSpace: "nowrap",
                overflow: "hidden",
                textOverflow: "ellipsis",
                paddingRight: sidebarCollapsed ? "0" : "8px",
              }}
            >
              <div
                style={{
                  fontSize: "12px",
                  color: "#888",
                  marginBottom: "2px",
                  display: "flex",
                  alignItems: "center",
                  gap: "4px",
                }}
              >
                <span>💬</span>
                <span>{session.message_count} messages</span>
              </div>
              {sidebarCollapsed ? (
                <div style={{ fontSize: "16px", textAlign: "center" }}>
                  💬
                </div>
              ) : (
                session.session_title
              )}
            </div>
            {!sidebarCollapsed && (
              <button
                className="delete-btn"
                onClick={(e) => {
                  e.stopPropagation();
                  deleteSession(session.session_id);
                }}
                style={{
                  background: "transparent",
                  border: "none",
                  color: "#dc2626",
                  fontSize: "14px",
                  cursor: "pointer",
                  padding: "4px",
                  borderRadius: "3px",
                  opacity: "0",
                  transition: "all 0.2s ease",
                  minWidth: "24px",
                  height: "24px",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
                title="Delete this conversation"
              >
                ×
              </button>
            )}
          </div>
        ))
      )}
    </div>
  );
};

export default ChatHistory;
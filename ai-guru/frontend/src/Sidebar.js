import React from 'react';
import ChatHistory from './ChatHistory';

const Sidebar = ({ 
    sidebarCollapsed,
    setSidebarCollapsed,
    startNewChat,
    chatSessions,
    selectedSession,
    setSelectedSession,
    setCurrentSessionId,
    setMessages,
    deleteAllChatHistory,
    deleteSession 
}) => {
  return (
    <div
      style={{
        width: sidebarCollapsed ? "80px" : "260px",
        background: "linear-gradient(180deg, #181C14 0%, #3C3D37 100%)",
        color: "#ECDFCC",
        display: "flex",
        flexDirection: "column",
        borderRight: "1px solid #697565",
        transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
        backdropFilter: "blur(10px)",
        boxShadow: "0 10px 25px rgba(24, 28, 20, 0.3)",
      }}
    >
      {/* Header */}
      <div
        style={{
          padding: "20px 16px",
          borderBottom: "1px solid #697565",
          background: "rgba(236, 223, 204, 0.05)",
          backdropFilter: "blur(10px)",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        {!sidebarCollapsed && (
          <h2
            style={{
              margin: "0",
              fontSize: "20px",
              fontWeight: "700",
              background: "linear-gradient(135deg, #60a5fa, #a78bfa)",
              backgroundClip: "text",
              WebkitBackgroundClip: "text",
              WebkitTextFillColor: "transparent",
              animation: "fadeInUp 0.5s ease-out",
            }}
          >
            AI Guru Multibot
          </h2>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="button-hover"
          style={{
            background: "rgba(255, 255, 255, 0.1)",
            border: "none",
            borderRadius: "8px",
            padding: "8px",
            color: "white",
            cursor: "pointer",
            fontSize: "16px",
            transition: "all 0.2s ease",
          }}
        >
          {sidebarCollapsed ? "→" : "←"}
        </button>
      </div>

      {/* New Chat Button */}
      <div style={{ padding: "16px" }}>
        <button
          onClick={startNewChat}
          className="button-hover"
          style={{
            width: "100%",
            padding: sidebarCollapsed ? "16px 8px" : "14px 16px",
            background: "linear-gradient(135deg, #697565, #3C3D37)",
            color: "#ECDFCC",
            border: "none",
            borderRadius: "12px",
            fontSize: "14px",
            cursor: "pointer",
            display: "flex",
            alignItems: "center",
            justifyContent: sidebarCollapsed ? "center" : "flex-start",
            gap: sidebarCollapsed ? "0" : "10px",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            fontWeight: "600",
            boxShadow: "0 4px 15px rgba(105, 117, 101, 0.3)",
            position: "relative",
            overflow: "hidden",
          }}
        >
          <span
            style={{
              fontSize: "18px",
              filter: "drop-shadow(0 0 2px rgba(255,255,255,0.5))",
            }}
          >
            ✨
          </span>
          {!sidebarCollapsed && "New Chat"}
        </button>
      </div>

      <ChatHistory 
        chatSessions={chatSessions}
        selectedSession={selectedSession}
        sidebarCollapsed={sidebarCollapsed}
        deleteAllChatHistory={deleteAllChatHistory}
        deleteSession={deleteSession}
        setSelectedSession={setSelectedSession}
        setCurrentSessionId={setCurrentSessionId}
        setMessages={setMessages}
      />
    </div>
  );
};

export default Sidebar;
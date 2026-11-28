import React, { useState, useEffect } from 'react';
import ChatHistory from './ChatHistory';

const ASTRA_AUTH_URL = process.env.REACT_APP_ASTRA_AUTH_URL || "http://localhost:5000";

const Sidebar = ({
    sidebarCollapsed,
    setSidebarCollapsed,
    ssoUsername,
    startNewChat,
    chatSessions,
    isHistoryLoading,
    selectedSession,
    setSelectedSession,
    setCurrentSessionId,
    setMessages,
    deleteAllChatHistory,
    deleteSession
}) => {
  const [theme, setTheme] = useState(() => {
    try {
      return localStorage.getItem('aiguru_theme') || 'system';
    } catch {
      return 'system';
    }
  });

  useEffect(() => {
    if (theme === 'dark') {
      document.documentElement.setAttribute('data-theme', 'dark');
    } else if (theme === 'light') {
      document.documentElement.setAttribute('data-theme', 'light');
    } else {
      document.documentElement.removeAttribute('data-theme');
    }
    try {
      localStorage.setItem('aiguru_theme', theme);
    } catch {
      // storage unavailable (private mode etc.) — theme just won't persist
    }
  }, [theme]);

  const toggleTheme = () => {
    // Cycles system -> dark -> light -> system, always explicit after first click.
    setTheme((prev) => (prev === 'dark' ? 'light' : 'dark'));
  };

  return (
    <div className={`app-sidebar transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-20' : 'w-64'} bg-white text-gray-800 flex flex-col border-r border-gray-200`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        {!sidebarCollapsed && (
          <h2 className="text-xl font-bold" style={{ color: 'var(--accent)' }}>AI Guru</h2>
        )}
        <div className="flex items-center gap-2">
          <button
            onClick={toggleTheme}
            className="theme-toggle-btn"
            title={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
            aria-label="Toggle dark mode"
          >
            {theme === 'dark' ? '☀️' : '🌙'}
          </button>
          <button
            onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
            className="p-2 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-600 transition-colors"
            aria-label="Toggle sidebar"
          >
            {sidebarCollapsed ? '→' : '←'}
          </button>
        </div>
      </div>

      {!sidebarCollapsed && ssoUsername && (
        <div
          style={{
            margin: "0 var(--space-4, 1rem)",
            padding: "var(--space-2, 0.5rem) var(--space-3, 0.75rem)",
            fontSize: "13px",
            color: "var(--text-secondary)",
          }}
        >
          Signed in as {ssoUsername}
        </div>
      )}

      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={startNewChat}
          className="btn-filled w-full flex items-center justify-center"
        >
          <span className="text-lg">✨</span>
          {!sidebarCollapsed && <span className="ml-2">New Chat</span>}
        </button>
      </div>

      <ChatHistory
        chatSessions={chatSessions}
        isHistoryLoading={isHistoryLoading}
        selectedSession={selectedSession}
        sidebarCollapsed={sidebarCollapsed}
        deleteAllChatHistory={deleteAllChatHistory}
        deleteSession={deleteSession}
        setSelectedSession={setSelectedSession}
        setCurrentSessionId={setCurrentSessionId}
        setMessages={setMessages}
      />

      <div className="p-4 border-t border-gray-200">
        <a
          href={`${ASTRA_AUTH_URL}/dashboard`}
          className="btn-outline"
          style={{ width: "100%", display: "block", textAlign: "center", textDecoration: "none" }}
        >
          {sidebarCollapsed ? "←" : "Back to Astra Auth"}
        </a>
      </div>
    </div>
  );
};

export default Sidebar;
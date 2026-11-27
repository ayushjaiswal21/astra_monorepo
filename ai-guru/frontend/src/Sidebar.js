import React, { useState, useEffect } from 'react';
import ChatHistory from './ChatHistory';

const Sidebar = ({
    sidebarCollapsed,
    setSidebarCollapsed,
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
          <h2 className="text-xl font-bold text-blue-600">AI Guru</h2>
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

      {/* New Chat Button */}
      <div className="p-4">
        <button
          onClick={startNewChat}
          className="w-full flex items-center justify-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-md transition-colors shadow-sm hover:shadow-md"
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
    </div>
  );
};

export default Sidebar;
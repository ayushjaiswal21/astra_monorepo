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
    <div className={`transition-all duration-300 ease-in-out ${sidebarCollapsed ? 'w-20' : 'w-64'} bg-white text-gray-800 flex flex-col border-r border-gray-200`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200 flex items-center justify-between">
        {!sidebarCollapsed && (
          <h2 className="text-xl font-bold text-blue-600">AI Guru</h2>
        )}
        <button
          onClick={() => setSidebarCollapsed(!sidebarCollapsed)}
          className="p-2 rounded-md bg-gray-100 hover:bg-gray-200 text-gray-600 transition-colors"
        >
          {sidebarCollapsed ? '→' : '←'}
        </button>
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
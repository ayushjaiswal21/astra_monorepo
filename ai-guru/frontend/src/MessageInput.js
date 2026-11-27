import React from 'react';

const MessageInput = ({ 
    handleSubmit,
    currentInput,
    setCurrentInput,
    isConverting,
    isListening,
    speechSupported,
    speechInterimResult,
    isLoading,
    clearTranscription,
    handleVoiceInput,
    fileInputRef,
    handleImageUpload,
    speechError,
    setSpeechError
}) => {
  return (
    <div className="p-4 bg-gray-100 border-t border-gray-200">
      {speechError && (
        <div className="bg-red-100 border border-red-400 text-red-700 px-4 py-3 rounded-md mb-4 flex items-center gap-2">
          <span>⚠️</span>
          <span>{speechError}</span>
          <button type="button" onClick={() => setSpeechError(null)} className="ml-auto bg-transparent border-none text-red-700 hover:text-red-900 cursor-pointer">
            ✕
          </button>
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div className="flex items-center gap-2 bg-white border border-gray-300 rounded-lg px-2 py-2 focus-within:ring-2 focus-within:ring-blue-500">
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            className="p-2 rounded-md text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors"
          >
            📎
          </button>
          <input
            id="message-input-textbox"
            type="text"
            value={speechInterimResult || currentInput}
            onChange={(e) => !isConverting && !isListening && setCurrentInput(e.target.value)}
            placeholder={isListening ? "🎤 Listening..." : "Type your message or use the mic..."}
            className="flex-1 bg-transparent border-none outline-none text-gray-800 placeholder-gray-400 disabled:opacity-50"
            disabled={isLoading || isConverting || isListening}
          />
          {currentInput && !isConverting && (
            <button type="button" onClick={clearTranscription} className="p-2 rounded-md text-gray-500 hover:text-gray-800 hover:bg-gray-100 transition-colors" title="Clear text">
              ✕
            </button>
          )}

          {speechSupported && (
            <button
              type="button"
              onClick={handleVoiceInput}
              disabled={isLoading || isConverting}
              className={`p-2 rounded-md text-white transition-colors ${isListening ? 'bg-red-500 hover:bg-red-600' : 'bg-gray-500 hover:bg-gray-600'}`}
              title={isListening ? "Stop voice input" : "Start voice input"}
            >
              {isListening ? "🛑" : "🎤"}
            </button>
          )}

          <button
            type="submit"
            disabled={!currentInput.trim() || isLoading || isConverting}
            className="btn-filled disabled:bg-gray-400 disabled:cursor-not-allowed"
          >
            {isLoading ? (
              <div className="w-5 h-5 border-2 border-t-transparent border-white rounded-full animate-spin"></div>
            ) : (
              "➤"
            )}
          </button>
        </div>
      </form>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleImageUpload}
        className="hidden"
        accept="image/*"
      />
    </div>
  );
};

export default MessageInput;

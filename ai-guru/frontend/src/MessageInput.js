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
    <div
      style={{
        padding: "24px",
        background:
          "linear-gradient(180deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,1) 100%)",
        backdropFilter: "blur(10px)",
        borderTop: "1px solid rgba(0,0,0,0.05)",
      }}
    >
      {speechError && (
        <div
          style={{
            backgroundColor: "#ffebee",
            border: "1px solid #f44336",
            borderRadius: "8px",
            padding: "12px 16px",
            margin: "0 0 16px 0",
            color: "#c62828",
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <span>⚠️</span>
          <span>{speechError}</span>
          <button
            type="button"
            onClick={() => setSpeechError(null)}
            style={{
              marginLeft: "auto",
              background: "none",
              border: "none",
              color: "#c62828",
              cursor: "pointer",
              fontSize: "16px",
              padding: "4px",
            }}
            title="Dismiss error"
          >
            ✕
          </button>
        </div>
      )}

      {isListening && (
        <div
          style={{
            backgroundColor: "#fff3e0",
            border: "1px solid #ff9800",
            borderRadius: "8px",
            padding: "12px 16px",
            margin: "0 0 16px 0",
            color: "#e65100",
            fontSize: "14px",
            display: "flex",
            alignItems: "center",
            gap: "8px",
            animation: "pulse 2s infinite",
          }}
        >
          <span>🎤</span>
          <span>
            Listening for speech... Speak clearly into your microphone.
          </span>
          <div
            style={{
              marginLeft: "auto",
              width: "12px",
              height: "12px",
              backgroundColor: "#ff4444",
              borderRadius: "50%",
              animation: "pulse 1s infinite",
            }}
          />
        </div>
      )}

      <form onSubmit={handleSubmit}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "8px",
            padding: "12px 16px",
            border: "2px solid #697565",
            borderRadius: "24px",
            backgroundColor: "#ECDFCC",
            transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
            boxShadow:
              "0 4px 20px rgba(105, 117, 101, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.5)",
            animation: currentInput ? "inputFocus 0.3s ease-out" : "none",
            transform: "translateY(0)",
          }}
        >
          <button
            type="button"
            onClick={() => fileInputRef.current?.click()}
            style={{
              padding: "10px",
              backgroundColor: "transparent",
              border: "2px solid transparent",
              borderRadius: "50%",
              cursor: "pointer",
              color: "#697565",
              fontSize: "18px",
              transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              transform: "scale(1)",
              position: "relative",
              overflow: "hidden",
            }}
          >
            📎
          </button>
          <input
            type="text"
            value={speechInterimResult || currentInput}
            onChange={(e) =>
              !isConverting &&
              !isListening &&
              setCurrentInput(e.target.value)
            }
            placeholder={
              isListening
                ? "🎤 Listening... Speak now!"
                : isConverting
                ? "Converting voice to text..."
                : speechSupported
                ? "Type your message or click 🎤 for voice..."
                : "Type your message..."
            }
            style={{
              flex: 1,
              border: "none",
              outline: "none",
              backgroundColor: "transparent",
              fontSize: "16px",
              color: isListening
                ? "#ff4444"
                : isConverting
                ? "#697565"
                : speechInterimResult
                ? "#8B4513"
                : "#181C14",
              fontWeight: isListening ? "600" : "500",
              transition: "all 0.2s ease",
              padding: "4px 0",
              fontStyle:
                isConverting || isListening ? "italic" : "normal",
              opacity: speechInterimResult ? 0.8 : 1,
            }}
            disabled={isLoading || isConverting || isListening}
          />
          {currentInput && !isConverting && (
            <button
              type="button"
              onClick={clearTranscription}
              style={{
                padding: "8px",
                backgroundColor: "transparent",
                border: "2px solid #697565",
                borderRadius: "50%",
                cursor: "pointer",
                color: "#697565",
                fontSize: "14px",
                transition: "all 0.3s ease",
                marginLeft: "8px",
              }}
              title="Clear text"
            >
              ✕
            </button>
          )}

          {speechSupported && (
            <button
              type="button"
              onClick={handleVoiceInput}
              disabled={isLoading || isConverting}
              style={{
                padding: "12px",
                backgroundColor: isListening ? "#ff4444" : "#8B4513",
                border: isListening
                  ? "2px solid #ff6666"
                  : "2px solid #A0522D",
                borderRadius: "50%",
                cursor:
                  isLoading || isConverting ? "not-allowed" : "pointer",
                color: "white",
                fontSize: "18px",
                fontWeight: "bold",
                transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
                transform: "scale(1)",
                boxShadow: isListening
                  ? "0 4px 15px rgba(255, 68, 68, 0.4), 0 0 20px rgba(255, 68, 68, 0.3)"
                  : "0 4px 15px rgba(139, 69, 19, 0.4)",
                background: isListening
                  ? "linear-gradient(135deg, #ff4444 0%, #cc0000 100%)"
                  : "linear-gradient(135deg, #8B4513 0%, #654321 100%)",
                animation: isListening ? "pulse 1.5s infinite" : "none",
                marginRight: "8px",
                opacity: isLoading || isConverting ? 0.6 : 1,
              }}
              title={
                isListening
                  ? "Click to stop voice input"
                  : "Click to start voice input"
              }
            >
              {isListening ? "🛑" : "🎤"}
            </button>
          )}

          <button
            type="submit"
            disabled={!currentInput.trim() || isLoading || isConverting}
            style={{
              padding: "12px",
              backgroundColor:
                currentInput.trim() && !isLoading && !isConverting
                  ? "#697565"
                  : "rgba(209, 213, 219, 0.6)",
              border:
                currentInput.trim() && !isLoading && !isConverting
                  ? "2px solid #3C3D37"
                  : "2px solid transparent",
              borderRadius: "50%",
              cursor:
                currentInput.trim() && !isLoading && !isConverting
                  ? "pointer"
                  : "not-allowed",
              color:
                currentInput.trim() && !isLoading && !isConverting
                  ? "#ECDFCC"
                  : "#9ca3af",
              fontSize: "18px",
              fontWeight: "bold",
              transition: "all 0.3s cubic-bezier(0.4, 0, 0.2, 1)",
              transform: "scale(1)",
              boxShadow:
                currentInput.trim() && !isLoading && !isConverting
                  ? "0 4px 15px rgba(105, 117, 101, 0.4), 0 0 0 0 rgba(105, 117, 101, 0.7)"
                  : "0 2px 8px rgba(0, 0, 0, 0.1)",
              background:
                currentInput.trim() && !isLoading && !isConverting
                  ? "linear-gradient(135deg, #697565 0%, #3C3D37 100%)"
                  : "rgba(209, 213, 219, 0.6)",
              animation:
                currentInput.trim() && !isLoading && !isConverting
                  ? "pulse 2s infinite"
                  : "none",
              position: "relative",
              overflow: "hidden",
            }}
          >
            {isLoading ? (
              <div
                style={{
                  width: "18px",
                  height: "18px",
                  border: "2px solid transparent",
                  borderTop: "2px solid #ECDFCC",
                  borderRadius: "50%",
                  animation: "spin 1s linear infinite",
                }}
              ></div>
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
        style={{ display: "none" }}
        accept="image/*"
      />
    </div>
  );
};

export default MessageInput;
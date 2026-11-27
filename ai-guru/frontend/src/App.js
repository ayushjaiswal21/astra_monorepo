import React, { useState, useRef, useEffect, Suspense } from "react";
import Sidebar from "./Sidebar";
import WelcomeScreen from "./WelcomeScreen";
import MessageInput from "./MessageInput";

// ChatMessages pulls in `marked` (markdown rendering) and is only needed once
// a conversation exists, not on first paint (WelcomeScreen shows first).
const ChatMessages = React.lazy(() => import("./ChatMessages"));

function App() {
  const [chatSessions, setChatSessions] = useState([]);
  const [isHistoryLoading, setIsHistoryLoading] = useState(true);
  const [selectedSession, setSelectedSession] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [ssoUsername, setSsoUsername] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);

  // On narrow screens the sidebar is a fixed-position overlay (see
  // index.css's max-width:640px rule) that sits on top of the chat column,
  // not beside it — left open by default it covers most of the message
  // input, making the chat unusable until the user manually collapses it.
  const [sidebarCollapsed, setSidebarCollapsed] = useState(
    () => typeof window !== "undefined" && window.innerWidth <= 640
  );
  const [isConverting, setIsConverting] = useState(false);
  const [processingMessages, setProcessingMessages] = useState(new Set());

  const [recognition, setRecognition] = useState(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechInterimResult, setSpeechInterimResult] = useState("");
  const [speechError, setSpeechError] = useState(null);
  const [feedbackLoading, setFeedbackLoading] = useState(new Set());
  const [showJumpToLatest, setShowJumpToLatest] = useState(false);
  const [speakingId, setSpeakingId] = useState(null);

  // Text-to-speech: toggles reading an assistant message aloud via the browser's native speechSynthesis.
  const handleToggleSpeak = (id, text) => {
    if (!("speechSynthesis" in window)) return;
    window.speechSynthesis.cancel();
    if (speakingId === id) {
      setSpeakingId(null);
      return;
    }
    const utterance = new SpeechSynthesisUtterance(text);
    utterance.onend = () => setSpeakingId(null);
    utterance.onerror = () => setSpeakingId(null);
    setSpeakingId(id);
    window.speechSynthesis.speak(utterance);
  };
  const [confirmState, setConfirmState] = useState(null);
  const [showConsent, setShowConsent] = useState(() => {
    try {
      return !localStorage.getItem("aiguru_consent_ack");
    } catch {
      return true;
    }
  });

  const mediaRecorderRef = useRef(null);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const activeRequestsRef = useRef(new Map());
  const chatScrollRef = useRef(null);

  const dismissConsent = () => {
    try {
      localStorage.setItem("aiguru_consent_ack", "1");
    } catch {
      // storage unavailable — banner will just reappear next visit
    }
    setShowConsent(false);
  };

  const handleChatScroll = () => {
    const el = chatScrollRef.current;
    if (!el) return;
    const distanceFromBottom = el.scrollHeight - el.scrollTop - el.clientHeight;
    setShowJumpToLatest(distanceFromBottom > 200);
  };

  const requestDeleteSession = (sessionId) => {
    setConfirmState({
      message: "Delete this conversation? This cannot be undone.",
      onConfirm: () => {
        deleteSession(sessionId);
        setConfirmState(null);
      },
    });
  };

  const requestDeleteAllChatHistory = () => {
    setConfirmState({
      message: "Delete all chat history? This action cannot be undone.",
      onConfirm: () => {
        deleteAllChatHistory();
        setConfirmState(null);
      },
    });
  };

  const submitFeedback = async (
    interactionId,
    sessionId,
    feedbackType,
    feedbackText = ""
  ) => {
    try {
      setFeedbackLoading((prev) => new Set([...prev, interactionId]));

      const response = await fetch("http://localhost:8001/feedback", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          interaction_id: interactionId,
          session_id: sessionId,
          feedback_type: feedbackType,
          feedback_text: feedbackText,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        setMessages((prev) =>
          prev.map((msg) =>
            msg.interactionId === interactionId
              ? {
                  ...msg,
                  feedbackSubmitted: feedbackType,
                  feedbackMessage: data.message,
                }
              : msg
          )
        );

        setTimeout(() => {
          setMessages((prev) =>
            prev.map((msg) =>
              msg.interactionId === interactionId
                ? { ...msg, feedbackMessage: null }
                : msg
            )
          );
        }, 3000);
      } else {
        try {
          const errorData = await response.json();
          console.error("Feedback submission failed:", errorData.detail);
        } catch (jsonError) {
          const errorText = await response.text();
          console.error("Feedback submission failed with non-JSON response:", errorText);
        }
      }
    } catch (error) {
      console.error("Error submitting feedback:", error);
    } finally {
      setFeedbackLoading((prev) => {
        const newSet = new Set(prev);
        newSet.delete(interactionId);
        return newSet;
      });
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  useEffect(() => {
    const controller = new AbortController();
    setIsHistoryLoading(true);
    fetch("http://localhost:8001/chat-history", { signal: controller.signal })
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setChatSessions(data.sessions || []);
      })
      .catch((err) => {
        if (err.name !== "AbortError") {
          console.error("Failed to fetch chat sessions:", err);
        }
      })
      .finally(() => setIsHistoryLoading(false));

    return () => controller.abort();
  }, []);

  // SSO handoff from Astra Auth: bind this session to the user's real
  // identity (via a server-derived, email-hashed session_id) instead of a
  // throwaway browser session, so personalization in MongoDB follows the
  // actual person across visits.
  useEffect(() => {
    try {
      const storedSessionId = localStorage.getItem("aiguru_sso_session_id");
      const storedUsername = localStorage.getItem("aiguru_sso_username");
      if (storedSessionId) {
        setCurrentSessionId(storedSessionId);
        setSsoUsername(storedUsername || null);
      }
    } catch {
      // storage unavailable — falls back to a normal anonymous session
    }

    const params = new URLSearchParams(window.location.search);
    const ssoToken = params.get("sso_token");
    if (!ssoToken) return;

    fetch("http://localhost:8001/sso/verify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: ssoToken }),
    })
      .then((res) => res.json())
      .then((data) => {
        if (data.valid) {
          setCurrentSessionId(data.session_id);
          setSsoUsername(data.username || null);
          try {
            localStorage.setItem("aiguru_sso_session_id", data.session_id);
            localStorage.setItem("aiguru_sso_username", data.username || "");
          } catch {
            // storage unavailable — identity won't persist past this visit
          }
        } else {
          console.error("SSO verification failed:", data.error);
        }
      })
      .catch((err) => console.error("SSO verification error:", err))
      .finally(() => {
        // Strip sso_token from the address bar so it never lingers,
        // gets bookmarked, or gets shared.
        params.delete("sso_token");
        const query = params.toString();
        const newUrl =
          window.location.pathname + (query ? `?${query}` : "") + window.location.hash;
        window.history.replaceState({}, "", newUrl);
      });
  }, []);

  useEffect(() => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();

      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = "en-US";
      recognitionInstance.maxAlternatives = 1;

      recognitionInstance.onresult = (event) => {
        let finalTranscript = "";
        let interimTranscript = "";

        for (let i = event.resultIndex; i < event.results.length; i++) {
          const transcript = event.results[i][0].transcript;
          if (event.results[i].isFinal) {
            finalTranscript += transcript;
          } else {
            interimTranscript += transcript;
          }
        }

        if (finalTranscript) {
          setCurrentInput(finalTranscript);
          setSpeechInterimResult("");
        } else if (interimTranscript) {
          setSpeechInterimResult(interimTranscript);
        }
      };

      recognitionInstance.onstart = () => {
        setIsListening(true);
        setSpeechError(null);
        setSpeechInterimResult("");
      };

      recognitionInstance.onend = () => {
        setIsListening(false);
        setSpeechInterimResult("");
      };

      recognitionInstance.onerror = (event) => {
        setIsListening(false);
        setSpeechInterimResult("");

        let errorMessage = "Speech recognition error: ";
        switch (event.error) {
          case "no-speech":
            errorMessage += "No speech detected. Please try again.";
            break;
          case "audio-capture":
            errorMessage +=
              "No microphone found. Please check your microphone.";
            break;
          case "not-allowed":
            errorMessage +=
              "Microphone access denied. Please allow microphone access.";
            break;
          case "network":
            errorMessage += "Network error. Please check your connection.";
            break;
          default:
            errorMessage += event.error;
        }
        setSpeechError(errorMessage);
      };

      setRecognition(recognitionInstance);
      setSpeechSupported(true);

      return () => {
        recognitionInstance.onresult = null;
        recognitionInstance.onstart = null;
        recognitionInstance.onend = null;
        recognitionInstance.onerror = null;
        recognitionInstance.abort();
      };
    } else {
      setSpeechSupported(false);
    }
  }, []);

  const refreshChatSessions = () => {
    fetch("http://localhost:8001/chat-history")
      .then((res) => {
        if (!res.ok) {
          throw new Error(`HTTP error! status: ${res.status}`);
        }
        return res.json();
      })
      .then((data) => {
        setChatSessions(data.sessions || []);
      })
      .catch((err) => {
        console.error("Failed to fetch chat sessions:", err);
      });
  };

  const startSpeechRecognition = () => {
    if (!speechSupported) {
      alert(
        "Speech recognition is not supported in this browser. Please use Chrome or Safari."
      );
      return;
    }

    if (recognition && !isListening) {
      try {
        setSpeechError(null);
        recognition.start();
      } catch (error) {
        setSpeechError("Failed to start speech recognition: " + error.message);
      }
    }
  };

  const stopSpeechRecognition = () => {
    if (recognition && isListening) {
      recognition.stop();
    }
  };

  const handleVoiceInput = () => {
    if (isListening) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  };

  const cancelActiveRequests = () => {
    activeRequestsRef.current.forEach((controller, requestId) => {
      controller.abort();
      setMessages((prev) =>
        prev.filter((msg) => !msg.isLoading || msg.requestId !== requestId)
      );
      setProcessingMessages((prev) => {
        const newSet = new Set(prev);
        newSet.delete(requestId);
        return newSet;
      });
    });
    activeRequestsRef.current.clear();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentInput.trim()) return;

    cancelActiveRequests();

    const userInput = currentInput.trim();
    const messageId = Date.now();
    const userMessage = { text: userInput, sender: "user", id: messageId };

    setMessages((prev) => [...prev, userMessage]);
    setCurrentInput("");
    setProcessingMessages((prev) => new Set([...prev, messageId]));

    const loadingMessageId = messageId + 1;
    const loadingMessage = {
      text: "",
      sender: "ai",
      id: loadingMessageId,
      isLoading: true,
      requestId: messageId,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    const abortController = new AbortController();
    activeRequestsRef.current.set(messageId, abortController);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8001/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: userInput,
          session_id: currentSessionId,
        }),
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();

      if (data.session_id && !currentSessionId) {
        setCurrentSessionId(data.session_id);
      }

      setTimeout(() => {
        const aiMessage = {
          text: data.response,
          sender: "ai",
          id: loadingMessageId,
          detectedLanguage: data.detected_language,
          languageName: data.language_name,
          confidence: data.confidence,
          sessionId: data.session_id || currentSessionId,
          interactionId: data.interaction_id,
        };
        setMessages((prev) =>
          prev.map((msg) => (msg.id === loadingMessageId ? aiMessage : msg))
        );
        setProcessingMessages((prev) => {
          const newSet = new Set(prev);
          newSet.delete(messageId);
          return newSet;
        });
        activeRequestsRef.current.delete(messageId);
        refreshChatSessions();
      }, 800);
    } catch (error) {
      if (error.name === "AbortError") {
        console.log("Request was cancelled");
        return;
      }

      console.error("Error:", error);
      
      let errorMessageText = "Sorry, there was an error processing your request.";
      if (error.response) {
        try {
          const errorData = await error.response.json();
          errorMessageText = errorData.detail || errorMessageText;
        } catch (jsonError) {
          errorMessageText = await error.response.text() || errorMessageText;
        }
      } else if (error.message) {
        errorMessageText = error.message;
      }

      setTimeout(() => {
        const errorMessage = {
          text: errorMessageText,
          sender: "ai",
          id: loadingMessageId,
        };
        setMessages((prev) =>
          prev.map((msg) => (msg.id === loadingMessageId ? errorMessage : msg))
        );
        setProcessingMessages((prev) => {
          const newSet = new Set(prev);
          newSet.delete(messageId);
          return newSet;
        });
        activeRequestsRef.current.delete(messageId);
      }, 500);
    } finally {
      setIsLoading(false);
    }
  };

  const clearTranscription = () => {
    setCurrentInput("");
  };

  const deleteSession = async (sessionId) => {
    try {
      const response = await fetch(
        `http://localhost:8001/session/${sessionId}`,
        {
          method: "DELETE",
        }
      );
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setChatSessions((prev) =>
            prev.filter((session) => session.session_id !== sessionId)
          );
          if (selectedSession && selectedSession.session_id === sessionId) {
            setSelectedSession(null);
            setMessages([]);
          }
          if (currentSessionId === sessionId) {
            setCurrentSessionId(null);
          }
        } else {
          console.error("Failed to delete session:", result.message);
        }
      } else {
        try {
          const errorData = await response.json();
          console.error("Failed to delete session:", errorData.detail);
        } catch (jsonError) {
          const errorText = await response.text();
          console.error("Failed to delete session with non-JSON response:", errorText);
        }
      }
    } catch (error) {
      console.error("Error deleting session:", error);
    }
  };

  const deleteAllChatHistory = async () => {
    // Confirmation now happens via the styled modal (requestDeleteAllChatHistory)
    // before this is ever called.
    try {
      const response = await fetch("http://localhost:8001/chat-history", {
        method: "DELETE",
      });
      if (response.ok) {
        const result = await response.json();
        if (result.success) {
          setChatSessions([]);
          setSelectedSession(null);
          setCurrentSessionId(null);
          setMessages([]);
        } else {
          console.error("Failed to delete all chat history:", result.message);
        }
      } else {
        try {
          const errorData = await response.json();
          console.error("Failed to delete all chat history:", errorData.detail);
        } catch (jsonError) {
          const errorText = await response.text();
          console.error("Failed to delete all chat history with non-JSON response:", errorText);
        }
      }
    } catch (error) {
      console.error("Error deleting all chat history:", error);
    }
  };

  const startNewChat = () => {
    cancelActiveRequests();
    setMessages([]);
    setSelectedSession(null);
    setCurrentSessionId(null);
    setCurrentInput("");
    setIsConverting(false);
    setIsLoading(false);
    setIsRecording(false);
    setProcessingMessages(new Set());
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    cancelActiveRequests();

    const imageUrl = URL.createObjectURL(file);
    const formData = new FormData();
    formData.append("image", file);
    formData.append("text", "Describe this image in detail.");

    const messageId = Date.now();
    const userMessage = {
      text: `[Image uploaded: ${file.name}]`,
      sender: "user",
      image: imageUrl,
      imageName: file.name,
      id: messageId,
    };
    setMessages((prev) => [...prev, userMessage]);

    const loadingMessageId = messageId + 1;
    const loadingMessage = {
      text: "",
      sender: "ai",
      id: loadingMessageId,
      isLoading: true,
      requestId: messageId,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    const abortController = new AbortController();
    activeRequestsRef.current.set(messageId, abortController);
    setIsLoading(true);

    try {
      const response = await fetch("http://localhost:8001/image-chat", {
        method: "POST",
        body: formData,
        signal: abortController.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const data = await response.json();
      const aiMessage = {
        text: data.response,
        sender: "ai",
        id: loadingMessageId,
        detectedLanguage: data.detected_language,
        languageName: data.language_name,
        confidence: data.confidence,
        sessionId: data.session_id || currentSessionId,
        interactionId: data.interaction_id,
      };
      setMessages((prev) =>
        prev.map((msg) => (msg.id === loadingMessageId ? aiMessage : msg))
      );
    } catch (error) {
      if (error.name === "AbortError") {
        console.log("Image request was cancelled");
        return;
      }
      console.error("Error:", error);
      let errorMessageText = "Sorry, there was an error processing your image.";
      if (error.response) {
        try {
          const errorData = await error.response.json();
          errorMessageText = errorData.detail || errorMessageText;
        } catch (jsonError) {
          errorMessageText = await error.response.text() || errorMessageText;
        }
      } else if (error.message) {
        errorMessageText = error.message;
      }
      const errorMessage = {
        text: errorMessageText,
        sender: "ai",
        id: loadingMessageId,
      };
      setMessages((prev) =>
        prev.map((msg) => (msg.id === loadingMessageId ? errorMessage : msg))
      );
    } finally {
      setProcessingMessages((prev) => {
        const newSet = new Set(prev);
        newSet.delete(messageId);
        return newSet;
      });
      activeRequestsRef.current.delete(messageId);
      setIsLoading(false);
    }

    e.target.value = "";
  };

  return (
    <div className="flex h-screen bg-gray-100 text-gray-800 font-sans">
      <a href="#message-input-textbox" className="skip-link">
        Skip to chat input
      </a>

      <Sidebar
        sidebarCollapsed={sidebarCollapsed}
        setSidebarCollapsed={setSidebarCollapsed}
        ssoUsername={ssoUsername}
        startNewChat={startNewChat}
        chatSessions={chatSessions}
        isHistoryLoading={isHistoryLoading}
        selectedSession={selectedSession}
        setSelectedSession={setSelectedSession}
        setCurrentSessionId={setCurrentSessionId}
        setMessages={setMessages}
        deleteAllChatHistory={requestDeleteAllChatHistory}
        deleteSession={requestDeleteSession}
      />

      <div className="flex-1 flex flex-col bg-white">
        <div
          ref={chatScrollRef}
          onScroll={handleChatScroll}
          className="flex-1 overflow-y-auto p-6"
        >
          {!selectedSession && messages.length === 0 ? (
            <WelcomeScreen
              isLoading={isLoading}
              setCurrentInput={setCurrentInput}
              fileInputRef={fileInputRef}
            />
          ) : (
            <Suspense fallback={null}>
              <ChatMessages
                messages={messages}
                messagesEndRef={messagesEndRef}
                submitFeedback={submitFeedback}
                feedbackLoading={feedbackLoading}
                processingMessages={processingMessages}
                showJumpToLatest={showJumpToLatest}
                scrollToBottom={scrollToBottom}
                speakingId={speakingId}
                onToggleSpeak={handleToggleSpeak}
              />
            </Suspense>
          )}
        </div>

        <MessageInput
          handleSubmit={handleSubmit}
          currentInput={currentInput}
          setCurrentInput={setCurrentInput}
          isConverting={isConverting}
          isListening={isListening}
          speechSupported={speechSupported}
          speechInterimResult={speechInterimResult}
          isLoading={isLoading}
          clearTranscription={clearTranscription}
          handleVoiceInput={handleVoiceInput}
          fileInputRef={fileInputRef}
          handleImageUpload={handleImageUpload}
          speechError={speechError}
          setSpeechError={setSpeechError}
        />
      </div>

      {confirmState && (
        <div className="modal-backdrop" onClick={() => setConfirmState(null)}>
          <div className="modal-dialog" onClick={(e) => e.stopPropagation()}>
            <p style={{ margin: "0 0 var(--space-5)", color: "var(--text-primary)" }}>
              {confirmState.message}
            </p>
            <div style={{ display: "flex", gap: "var(--space-3)", justifyContent: "flex-end" }}>
              <button className="btn-outline" onClick={() => setConfirmState(null)}>
                Cancel
              </button>
              <button className="btn-filled" onClick={confirmState.onConfirm}>
                Delete
              </button>
            </div>
          </div>
        </div>
      )}

      {showConsent && (
        <div className="consent-banner">
          <p style={{ margin: 0, fontSize: "14px", color: "var(--text-secondary)" }}>
            AI Guru stores your chat history locally so you can revisit past conversations. Continuing means you're okay with that.
          </p>
          <button className="btn-filled" onClick={dismissConsent}>
            Got it
          </button>
        </div>
      )}
    </div>
  );
}

export default App;
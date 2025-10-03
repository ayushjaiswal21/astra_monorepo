import React, { useState, useRef, useEffect } from "react";
import { marked } from "marked";
import Sidebar from "./Sidebar";
import WelcomeScreen from "./WelcomeScreen";
import ChatMessages from "./ChatMessages";
import MessageInput from "./MessageInput";

function App() {
  const [chatSessions, setChatSessions] = useState([]);
  const [selectedSession, setSelectedSession] = useState(null);
  const [currentSessionId, setCurrentSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isConverting, setIsConverting] = useState(false);
  const [processingMessages, setProcessingMessages] = useState(new Set());

  const [recognition, setRecognition] = useState(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechInterimResult, setSpeechInterimResult] = useState("");
  const [speechError, setSpeechError] = useState(null);
  const [feedbackLoading, setFeedbackLoading] = useState(new Set());

  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const activeRequestsRef = useRef(new Map());

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

      const data = await response.json();

      if (response.ok) {
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
        console.error("Feedback submission failed:", data.detail);
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
    fetch("http://localhost:8001/chat-history")
      .then((res) => res.json())
      .then((data) => {
        setChatSessions(data.sessions || []);
      })
      .catch((err) => {
        console.error("Failed to fetch chat sessions:", err);
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
    } else {
      setSpeechSupported(false);
    }
  }, []);

  const refreshChatSessions = () => {
    fetch("http://localhost:8001/chat-history")
      .then((res) => res.json())
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
      setTimeout(() => {
        const errorMessage = {
          text: "Sorry, there was an error processing your request.",
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
    } catch (error) {
      console.error("Error deleting session:", error);
    }
  };

  const deleteAllChatHistory = async () => {
    if (
      !window.confirm(
        "Are you sure you want to delete all chat history? This action cannot be undone."
      )
    ) {
      return;
    }
    try {
      const response = await fetch("http://localhost:8001/chat-history", {
        method: "DELETE",
      });
      const result = await response.json();
      if (result.success) {
        setChatSessions([]);
        setSelectedSession(null);
        setCurrentSessionId(null);
        setMessages([]);
      } else {
        console.error("Failed to delete all chat history:", result.message);
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
    setSelectedImage(null);
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
    setSelectedImage(file);
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
      const errorMessage = {
        text: "Sorry, there was an error processing your image.",
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
    }
    setSelectedImage(null);
    e.target.value = "";
  };

  return (
    <>
      <div
        style={{
          display: "flex",
          height: "100vh",
          fontFamily:
            "-apple-system, BlinkMacSystemFont, 'Segoe UI', 'Roboto', sans-serif",
          background:
            "linear-gradient(135deg, #ECDFCC 0%, #697565 50%, #3C3D37 100%)",
          overflow: "hidden",
        }}
      >
        <Sidebar
          sidebarCollapsed={sidebarCollapsed}
          setSidebarCollapsed={setSidebarCollapsed}
          startNewChat={startNewChat}
          chatSessions={chatSessions}
          selectedSession={selectedSession}
          setSelectedSession={setSelectedSession}
          setCurrentSessionId={setCurrentSessionId}
          setMessages={setMessages}
          deleteAllChatHistory={deleteAllChatHistory}
          deleteSession={deleteSession}
        />

        <div
          style={{
            flex: 1,
            display: "flex",
            flexDirection: "column",
            background: "linear-gradient(180deg, #ECDFCC 0%, #F5F0E8 100%)",
            borderRadius: "20px 0 0 0",
            boxShadow: "inset 0 1px 0 rgba(105, 117, 101, 0.1)",
            overflow: "hidden",
          }}
        >
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "0",
            }}
          >
            {!selectedSession && messages.length === 0 ? (
              <WelcomeScreen
                isLoading={isLoading}
                setCurrentInput={setCurrentInput}
                fileInputRef={fileInputRef}
              />
            ) : (
              <ChatMessages
                messages={messages}
                messagesEndRef={messagesEndRef}
                submitFeedback={submitFeedback}
                feedbackLoading={feedbackLoading}
              />
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
      </div>
    </>
  );
}

export default App;
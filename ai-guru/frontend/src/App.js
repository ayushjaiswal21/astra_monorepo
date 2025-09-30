import React, { useState, useRef, useEffect } from "react";
import { marked } from "marked";

function App() {
  const [chatSessions, setChatSessions] = useState([]); // Changed from chatHistory to chatSessions
  const [selectedSession, setSelectedSession] = useState(null); // Changed from selectedHistory to selectedSession
  const [currentSessionId, setCurrentSessionId] = useState(null); // Track current conversation session
  const [messages, setMessages] = useState([]);
  const [currentInput, setCurrentInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [selectedImage, setSelectedImage] = useState(null);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [isConverting, setIsConverting] = useState(false); // Track if converting voice to text
  const [recordedAudio, setRecordedAudio] = useState(null); // Store recorded audio blob

  // Web Speech API states
  const [recognition, setRecognition] = useState(null);
  const [speechSupported, setSpeechSupported] = useState(false);
  const [isListening, setIsListening] = useState(false);
  const [speechInterimResult, setSpeechInterimResult] = useState("");
  const [speechError, setSpeechError] = useState(null);
  const [feedbackLoading, setFeedbackLoading] = useState(new Set()); // Track feedback submissions
  const mediaRecorderRef = useRef(null);
  const audioChunksRef = useRef([]);
  const fileInputRef = useRef(null);
  const messagesEndRef = useRef(null);
  const activeRequestsRef = useRef(new Map()); // Track active requests with their AbortControllers

  // Feedback submission function
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
        // Show success message briefly
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

        // Clear feedback message after 3 seconds
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

  // Auto-scroll to bottom when new messages arrive
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Fetch chat sessions on mount
  useEffect(() => {
    fetch("http://localhost:8001/chat-history")
      .then((res) => res.json())
      .then((data) => {
        console.log("Fetched sessions data:", data);
        setChatSessions(data.sessions || []);
      })
      .catch((err) => {
        console.error("Failed to fetch chat sessions:", err);
      });
  }, []);

  // Initialize Web Speech API
  useEffect(() => {
    if ("webkitSpeechRecognition" in window || "SpeechRecognition" in window) {
      const SpeechRecognition =
        window.SpeechRecognition || window.webkitSpeechRecognition;
      const recognitionInstance = new SpeechRecognition();

      // Configure speech recognition for multilingual support
      recognitionInstance.continuous = false;
      recognitionInstance.interimResults = true;
      recognitionInstance.lang = "en-US"; // Default language, can be changed dynamically
      recognitionInstance.maxAlternatives = 1;

      // Handle speech results
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
          console.log("Final speech result:", finalTranscript);
          setCurrentInput(finalTranscript);
          setSpeechInterimResult("");
        } else if (interimTranscript) {
          console.log("Interim speech result:", interimTranscript);
          setSpeechInterimResult(interimTranscript);
        }
      };

      // Handle speech start
      recognitionInstance.onstart = () => {
        console.log("Speech recognition started");
        setIsListening(true);
        setSpeechError(null);
        setSpeechInterimResult("");
      };

      // Handle speech end
      recognitionInstance.onend = () => {
        console.log("Speech recognition ended");
        setIsListening(false);
        setSpeechInterimResult("");
      };

      // Handle speech errors
      recognitionInstance.onerror = (event) => {
        console.error("Speech recognition error:", event.error);
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
      console.log("Speech recognition not supported in this browser");
      setSpeechSupported(false);
    }
  }, []);

  // Function to refresh chat sessions
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

  // Web Speech API functions
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
        console.error("Error starting speech recognition:", error);
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

  // Function to cancel all active requests
  const cancelActiveRequests = () => {
    activeRequestsRef.current.forEach((controller, requestId) => {
      controller.abort();

      // Remove loading messages for cancelled requests
      setMessages((prev) =>
        prev.filter((msg) => !msg.isLoading || msg.requestId !== requestId)
      );

      // Remove from processing messages
      setProcessingMessages((prev) => {
        const newSet = new Set(prev);
        newSet.delete(requestId);
        return newSet;
      });
    });

    // Clear the active requests map
    activeRequestsRef.current.clear();
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!currentInput.trim()) return;

    // Cancel any existing active requests
    cancelActiveRequests();

    const userInput = currentInput.trim();
    const messageId = Date.now();
    const userMessage = { text: userInput, sender: "user", id: messageId };

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage]);
    setCurrentInput("");

    // Track this message as processing
    setProcessingMessages((prev) => new Set([...prev, messageId]));

    // Add a temporary AI message with loading indicator
    const loadingMessageId = messageId + 1;
    const loadingMessage = {
      text: "",
      sender: "ai",
      id: loadingMessageId,
      isLoading: true,
      requestId: messageId,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    // Create AbortController for this request
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

      // Update session ID if this is a new session
      if (data.session_id && !currentSessionId) {
        setCurrentSessionId(data.session_id);
      }

      // Replace loading message with actual response
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

        // Remove from active requests
        activeRequestsRef.current.delete(messageId);

        // Refresh chat sessions to show updated history
        refreshChatSessions();

        // Log language detection info (only for non-English languages)
        if (
          data.detected_language &&
          data.language_name &&
          data.language_name !== "Unknown" &&
          data.detected_language !== "en"
        ) {
          console.log(
            `🌐 Language detected: ${data.language_name} (${data.detected_language})`
          );
        }
      }, 800);
    } catch (error) {
      // Don't show error for cancelled requests
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

        // Remove from active requests
        activeRequestsRef.current.delete(messageId);
      }, 500);
    }
  };

  const clearTranscription = () => {
    setCurrentInput("");
  };

  // Delete individual chat history entry
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
        // Remove from local state
        setChatSessions((prev) =>
          prev.filter((session) => session.session_id !== sessionId)
        );

        // Clear selected session if it was the deleted one
        if (selectedSession && selectedSession.session_id === sessionId) {
          setSelectedSession(null);
          setMessages([]);
        }

        // If the current session was deleted, reset current session
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

  // Delete all chat history
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

  const handleVoiceRecording = async () => {
    if (isRecording) {
      stopRecording();
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaRecorderRef.current = new MediaRecorder(stream);
      audioChunksRef.current = [];

      mediaRecorderRef.current.ondataavailable = (event) => {
        audioChunksRef.current.push(event.data);
      };

      mediaRecorderRef.current.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, {
          type: "audio/wav",
        });

        // Show converting status
        setIsConverting(true);
        setCurrentInput("[🎤 Converting voice to text...]");

        try {
          // Send audio to transcription endpoint
          const formData = new FormData();
          formData.append("audio", audioBlob, "recording.wav");

          const response = await fetch("http://localhost:8001/transcribe", {
            method: "POST",
            body: formData,
          });

          if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
          }

          const data = await response.json();

          // Display transcribed text in input bar
          if (data.transcription && data.transcription.trim()) {
            setCurrentInput(data.transcription.trim());
          } else {
            setCurrentInput(
              "[Could not understand the audio. Please try again.]"
            );
          }
        } catch (error) {
          console.error("Error transcribing audio:", error);
          setCurrentInput("[Error transcribing audio. Please try again.]");
        } finally {
          setIsConverting(false);
          setRecordedAudio(null); // Clear audio since we now have text
        }

        // Stop all tracks to release microphone
        stream.getTracks().forEach((track) => track.stop());
      };

      mediaRecorderRef.current.start();
      setIsRecording(true);
    } catch (error) {
      console.error("Error accessing microphone:", error);
    }
  };

  const stopRecording = () => {
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const startNewChat = () => {
    // Cancel any active requests first
    cancelActiveRequests();

    setMessages([]);
    setSelectedSession(null);
    setCurrentSessionId(null);
    setCurrentInput("");
    setSelectedImage(null);
    setIsConverting(false); // Clear conversion state
    setIsLoading(false);
    setIsRecording(false);
    setProcessingMessages(new Set()); // Clear processing messages
    if (mediaRecorderRef.current && isRecording) {
      mediaRecorderRef.current.stop();
      setIsRecording(false);
    }
  };

  const handleImageUpload = async (e) => {
    const file = e.target.files[0];
    if (!file) return;

    // Cancel any existing active requests
    cancelActiveRequests();

    setSelectedImage(file);

    // Create image preview URL
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

    // Add loading message
    const loadingMessageId = messageId + 1;
    const loadingMessage = {
      text: "",
      sender: "ai",
      id: loadingMessageId,
      isLoading: true,
      requestId: messageId,
    };
    setMessages((prev) => [...prev, loadingMessage]);

    // Create AbortController for this request
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

      // Log language detection info for image chat (only for non-English languages)
      if (
        data.detected_language &&
        data.language_name &&
        data.language_name !== "Unknown" &&
        data.detected_language !== "en"
      ) {
        console.log(
          `🌐 Image chat language detected: ${data.language_name} (${data.detected_language})`
        );
      }
    } catch (error) {
      // Don't show error for cancelled requests
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

      // Remove from active requests
      activeRequestsRef.current.delete(messageId);
    }

    setSelectedImage(null);
    e.target.value = "";
  };

  return (
    <>
      {/* CSS Animations */}
      <style>{`
        @keyframes fadeInUp {
          from {
            opacity: 0;
            transform: translateY(20px);
          }
          to {
            opacity: 1;
            transform: translateY(0);
          }
        }
        
        @keyframes slideIn {
          from {
            opacity: 0;
            transform: translateX(-20px);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
        
        @keyframes pulse {
          0%, 100% {
            transform: scale(1);
          }
          50% {
            transform: scale(1.05);
          }
        }
        
        @keyframes typing {
          0%, 60%, 100% {
            transform: translateY(0);
          }
          30% {
            transform: translateY(-10px);
          }
        }
        
        @keyframes glow {
          0%, 100% {
            box-shadow: 0 0 5px rgba(99, 102, 241, 0.3);
          }
          50% {
            box-shadow: 0 0 20px rgba(99, 102, 241, 0.6);
          }
        }
        
        @keyframes shimmer {
          0% {
            background-position: -200% 0;
          }
          100% {
            background-position: 200% 0;
          }
        }
        
        .message-enter {
          animation: fadeInUp 0.3s ease-out;
        }
        
        .sidebar-item:hover {
          transform: translateX(4px);
          transition: all 0.2s ease;
        }
        
        .typing-indicator {
          display: inline-flex;
          gap: 3px;
        }
        
        .typing-dot {
          width: 6px;
          height: 6px;
          border-radius: 50%;
          background: #6b7280;
          animation: typing 1.4s infinite;
        }
        
        .typing-dot:nth-child(2) {
          animation-delay: 0.2s;
        }
        
        .typing-dot:nth-child(3) {
          animation-delay: 0.4s;
        }
        
        .gradient-bg {
          background: linear-gradient(-45deg, #6366f1, #8b5cf6, #06b6d4, #10b981);
          background-size: 400% 400%;
          animation: gradient 3s ease infinite;
        }
        
        @keyframes gradient {
          0% { background-position: 0% 50%; }
          50% { background-position: 100% 50%; }
          100% { background-position: 0% 50%; }
        }
        
        .button-hover {
          transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        .button-hover:hover {
          transform: translateY(-1px);
          box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
        }
        
        .spinner {
          border: 2px solid #f3f3f3;
          border-top: 2px solid #6366f1;
          border-radius: 50%;
          width: 16px;
          height: 16px;
          animation: spin 1s linear infinite;
        }
        
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
        
        @keyframes sendPulse {
          0% { 
            transform: scale(0.95); 
            box-shadow: 0 0 0 0 rgba(105, 117, 101, 0.7); 
          }
          50% { 
            transform: scale(1.1); 
            box-shadow: 0 0 0 15px rgba(105, 117, 101, 0.2); 
          }
          100% { 
            transform: scale(1); 
            box-shadow: 0 0 0 25px rgba(105, 117, 101, 0); 
          }
        }
        
        @keyframes buttonGlow {
          0% { 
            box-shadow: 0 4px 15px rgba(105, 117, 101, 0.4);
          }
          50% { 
            box-shadow: 0 6px 20px rgba(105, 117, 101, 0.6), 0 0 15px rgba(105, 117, 101, 0.3);
          }
          100% { 
            box-shadow: 0 4px 15px rgba(105, 117, 101, 0.4);
          }
        }
        
        @keyframes inputFocus {
          0% { 
            transform: translateY(0) scale(1);
            box-shadow: 0 4px 20px rgba(105, 117, 101, 0.1);
          }
          50% { 
            transform: translateY(-1px) scale(1.01);
            box-shadow: 0 8px 25px rgba(105, 117, 101, 0.2);
          }
          100% { 
            transform: translateY(0) scale(1);
            box-shadow: 0 6px 22px rgba(105, 117, 101, 0.15);
          }
        }
        
        @keyframes messageSlideIn {
          0% { 
            opacity: 0;
            transform: translateY(20px) scale(0.95);
          }
          100% { 
            opacity: 1;
            transform: translateY(0) scale(1);
          }
        }
      `}</style>

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
        {/* Sidebar */}
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
              onMouseOver={(e) => {
                e.target.style.transform = "translateY(-2px)";
                e.target.style.boxShadow =
                  "0 8px 25px rgba(105, 117, 101, 0.4)";
              }}
              onMouseOut={(e) => {
                e.target.style.transform = "translateY(0)";
                e.target.style.boxShadow =
                  "0 4px 15px rgba(105, 117, 101, 0.3)";
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

          {/* Chat History */}
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
              chatSessions.map((session, index) => (
                <div
                  key={session.session_id}
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
                    group: true,
                  }}
                  onMouseOver={(e) => {
                    if (
                      !(
                        selectedSession &&
                        selectedSession.session_id === session.session_id
                      )
                    ) {
                      e.currentTarget.style.backgroundColor = "#2a2a2a";
                    }
                    const deleteBtn =
                      e.currentTarget.querySelector(".delete-btn");
                    if (deleteBtn && !sidebarCollapsed) {
                      deleteBtn.style.opacity = "1";
                    }
                  }}
                  onMouseOut={(e) => {
                    if (
                      !(
                        selectedSession &&
                        selectedSession.session_id === session.session_id
                      )
                    ) {
                      e.currentTarget.style.backgroundColor = "transparent";
                    }
                    const deleteBtn =
                      e.currentTarget.querySelector(".delete-btn");
                    if (deleteBtn) {
                      deleteBtn.style.opacity = "0";
                    }
                  }}
                >
                  <div
                    onClick={() => {
                      console.log("Selected session:", session);
                      setSelectedSession(session);
                      setCurrentSessionId(session.session_id);

                      // Convert session messages to display format
                      const displayMessages = [];
                      session.messages.forEach((msg, index) => {
                        console.log("Processing message:", msg);
                        // Add user message
                        displayMessages.push({
                          id: msg.id * 2 - 1,
                          text: msg.user_input,
                          sender: "user",
                        });
                        // Add AI response
                        displayMessages.push({
                          id: msg.id * 2,
                          text: msg.bot_response,
                          sender: "ai",
                          detectedLanguage: msg.language_code,
                          languageName: msg.language_name,
                          sessionId: msg.session_id,
                          interactionId:
                            msg._id || `${msg.session_id}_${msg.id * 2}`,
                        });
                      });

                      console.log("Display messages:", displayMessages);
                      setMessages(displayMessages);
                    }}
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
                      onMouseEnter={(e) => {
                        e.target.style.backgroundColor = "#dc2626";
                        e.target.style.color = "white";
                      }}
                      onMouseLeave={(e) => {
                        e.target.style.backgroundColor = "transparent";
                        e.target.style.color = "#dc2626";
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
        </div>

        {/* Main Chat Area */}
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
          {/* Chat Messages */}
          <div
            style={{
              flex: 1,
              overflowY: "auto",
              padding: "0",
            }}
          >
            {/* Welcome Screen */}
            {!selectedSession && messages.length === 0 && (
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  height: "100%",
                  textAlign: "center",
                  padding: "40px 20px",
                  color: "#666",
                }}
              >
                <div
                  style={{
                    width: "100px",
                    height: "100px",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    marginBottom: "32px",
                  }}
                >
                  <svg
                    width="60"
                    height="60"
                    viewBox="0 0 100 100"
                    fill="none"
                    xmlns="http://www.w3.org/2000/svg"
                  >
                    {/* Main circular background with gradient */}
                    <defs>
                      <radialGradient
                        id="botGradient"
                        cx="50%"
                        cy="30%"
                        r="60%"
                      >
                        <stop offset="0%" stopColor="#34d399" />
                        <stop offset="100%" stopColor="#10b981" />
                      </radialGradient>
                      <linearGradient
                        id="faceGradient"
                        cx="50%"
                        cy="50%"
                        r="50%"
                      >
                        <stop offset="0%" stopColor="#ffffff" />
                        <stop offset="100%" stopColor="#f3f4f6" />
                      </linearGradient>
                    </defs>

                    {/* Main bot circle */}
                    <circle cx="50" cy="50" r="45" fill="url(#botGradient)" />

                    {/* Bot face background */}
                    <rect
                      x="25"
                      y="30"
                      width="50"
                      height="40"
                      rx="15"
                      ry="15"
                      fill="url(#faceGradient)"
                    />

                    {/* Eyes */}
                    <circle cx="37" cy="45" r="4" fill="#374151" />
                    <circle cx="63" cy="45" r="4" fill="#374151" />

                    {/* Eye highlights */}
                    <circle cx="38" cy="43" r="1.5" fill="white" />
                    <circle cx="64" cy="43" r="1.5" fill="white" />

                    {/* Simple smile */}
                    <path
                      d="M40 58 Q50 65 60 58"
                      stroke="#374151"
                      strokeWidth="3"
                      strokeLinecap="round"
                      fill="none"
                    />

                    {/* Antenna */}
                    <line
                      x1="50"
                      y1="5"
                      x2="50"
                      y2="15"
                      stroke="#10b981"
                      strokeWidth="3"
                      strokeLinecap="round"
                    />
                    <circle cx="50" cy="5" r="3" fill="#34d399" />

                    {/* Side indicators */}
                    <circle
                      cx="15"
                      cy="50"
                      r="3"
                      fill="#34d399"
                      opacity="0.7"
                    />
                    <circle
                      cx="85"
                      cy="50"
                      r="3"
                      fill="#34d399"
                      opacity="0.7"
                    />
                  </svg>
                </div>
                <h1
                  style={{
                    fontSize: "32px",
                    fontWeight: "700",
                    background:
                      "linear-gradient(135deg, #181C14 0%, #3C3D37 100%)",
                    backgroundClip: "text",
                    WebkitBackgroundClip: "text",
                    WebkitTextFillColor: "transparent",
                    marginBottom: "12px",
                    animation: "fadeInUp 0.8s ease-out 0.2s both",
                  }}
                >
                  Welcome to AI Guru Multibot!
                </h1>
                <p
                  style={{
                    fontSize: "16px",
                    color: "#697565",
                    marginBottom: "32px",
                    maxWidth: "500px",
                    lineHeight: "1.5",
                  }}
                >
                  Start a conversation by typing a message, recording your
                  voice, or uploading an image.
                </p>

                {/* Suggestion buttons */}
                <div
                  style={{
                    display: "flex",
                    gap: "12px",
                    flexWrap: "wrap",
                    justifyContent: "center",
                  }}
                >
                  <button
                    onClick={() =>
                      !isLoading && setCurrentInput("Ask me anything")
                    }
                    disabled={isLoading}
                    style={{
                      padding: "12px 20px",
                      backgroundColor: isLoading ? "#d1d5db" : "#ECDFCC",
                      border: `1px solid ${isLoading ? "#9ca3af" : "#697565"}`,
                      borderRadius: "20px",
                      color: isLoading ? "#6b7280" : "#181C14",
                      fontSize: "14px",
                      cursor: isLoading ? "not-allowed" : "pointer",
                      transition: "all 0.2s ease",
                      opacity: isLoading ? 0.6 : 1,
                    }}
                    onMouseOver={(e) => {
                      e.target.style.backgroundColor = "#697565";
                      e.target.style.borderColor = "#3C3D37";
                      e.target.style.color = "#ECDFCC";
                    }}
                    onMouseOut={(e) => {
                      e.target.style.backgroundColor = "#ECDFCC";
                      e.target.style.borderColor = "#697565";
                      e.target.style.color = "#181C14";
                    }}
                  >
                    Ask me anything
                  </button>
                  <button
                    onClick={() => fileInputRef.current?.click()}
                    style={{
                      padding: "12px 20px",
                      backgroundColor: "#ECDFCC",
                      border: "1px solid #697565",
                      borderRadius: "20px",
                      color: "#181C14",
                      fontSize: "14px",
                      cursor: "pointer",
                      transition: "all 0.2s ease",
                    }}
                    onMouseOver={(e) => {
                      e.target.style.backgroundColor = "#697565";
                      e.target.style.borderColor = "#3C3D37";
                      e.target.style.color = "#ECDFCC";
                    }}
                    onMouseOut={(e) => {
                      e.target.style.backgroundColor = "#ECDFCC";
                      e.target.style.borderColor = "#697565";
                      e.target.style.color = "#181C14";
                    }}
                  >
                    Upload an image
                  </button>
                </div>
              </div>
            )}

            {/* Chat Messages */}
            <div style={{ padding: "20px" }}>
              {messages.map((msg, index) => (
                <div
                  key={msg.id || index}
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
                          onMouseOver={(e) => {
                            e.target.style.transform = "scale(1.02)";
                          }}
                          onMouseOut={(e) => {
                            e.target.style.transform = "scale(1)";
                          }}
                          onClick={() => {
                            // Open image in new tab for full view
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
                          dangerouslySetInnerHTML={{
                            __html: marked.parse(msg.text || "", {
                              breaks: true,
                              gfm: true,
                            }),
                          }}
                          style={{
                            lineHeight: "1.6",
                            "& h1, & h2, & h3, & h4, & h5, & h6": {
                              marginTop: "16px",
                              marginBottom: "8px",
                              fontWeight: "bold",
                            },
                            "& p": {
                              marginBottom: "12px",
                            },
                            "& ul, & ol": {
                              marginLeft: "20px",
                              marginBottom: "12px",
                            },
                            "& li": {
                              marginBottom: "4px",
                            },
                            "& strong": {
                              fontWeight: "bold",
                              color: "#374151",
                            },
                            "& em": {
                              fontStyle: "italic",
                            },
                          }}
                        />
                        {/* Language Detection Indicator for AI messages */}
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

                        {/* Feedback Buttons for AI messages */}
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
                                onMouseOver={(e) => {
                                  e.target.style.backgroundColor = "#f3f4f6";
                                  e.target.style.borderColor = "#10b981";
                                  e.target.style.color = "#10b981";
                                }}
                                onMouseOut={(e) => {
                                  e.target.style.backgroundColor =
                                    "transparent";
                                  e.target.style.borderColor = "#e5e7eb";
                                  e.target.style.color = "#6b7280";
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
                                onMouseOver={(e) => {
                                  e.target.style.backgroundColor = "#fef2f2";
                                  e.target.style.borderColor = "#ef4444";
                                  e.target.style.color = "#ef4444";
                                }}
                                onMouseOut={(e) => {
                                  e.target.style.backgroundColor =
                                    "transparent";
                                  e.target.style.borderColor = "#e5e7eb";
                                  e.target.style.color = "#6b7280";
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

                        {/* Feedback Confirmation Message */}
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

                        {/* Dynamic Feedback Message */}
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
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* Input Area */}
          <div
            style={{
              padding: "24px",
              background:
                "linear-gradient(180deg, rgba(255,255,255,0.8) 0%, rgba(255,255,255,1) 100%)",
              backdropFilter: "blur(10px)",
              borderTop: "1px solid rgba(0,0,0,0.05)",
            }}
          >
            {/* Speech Recognition Error Display */}
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

            {/* Speech Recognition Status */}
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
                onFocus={() => {
                  // This will apply to the container when any child gets focus
                }}
                onMouseEnter={(e) => {
                  e.target.style.borderColor = "#3C3D37";
                  e.target.style.boxShadow =
                    "0 8px 25px rgba(105, 117, 101, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.7)";
                  e.target.style.transform = "translateY(-2px)";
                }}
                onMouseLeave={(e) => {
                  e.target.style.borderColor = "#697565";
                  e.target.style.boxShadow =
                    "0 4px 20px rgba(105, 117, 101, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.5)";
                  e.target.style.transform = "translateY(0)";
                }}
              >
                {/* Attachment Button */}
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
                  onMouseOver={(e) => {
                    e.target.style.backgroundColor = "rgba(105, 117, 101, 0.1)";
                    e.target.style.borderColor = "#697565";
                    e.target.style.transform = "scale(1.1) rotate(10deg)";
                    e.target.style.boxShadow =
                      "0 4px 12px rgba(105, 117, 101, 0.2)";
                  }}
                  onMouseOut={(e) => {
                    e.target.style.backgroundColor = "transparent";
                    e.target.style.borderColor = "transparent";
                    e.target.style.transform = "scale(1) rotate(0deg)";
                    e.target.style.boxShadow = "none";
                  }}
                  onMouseDown={(e) => {
                    e.target.style.transform = "scale(0.95) rotate(5deg)";
                  }}
                  onMouseUp={(e) => {
                    e.target.style.transform = "scale(1.05) rotate(-5deg)";
                    setTimeout(() => {
                      e.target.style.transform = "scale(1) rotate(0deg)";
                    }, 200);
                  }}
                >
                  📎
                </button>
                {/* Text Input */}
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
                  onFocus={(e) => {
                    if (!isConverting) {
                      e.target.style.fontSize = "16px";
                      e.target.style.transform = "translateY(-1px)";
                    }
                  }}
                  onBlur={(e) => {
                    if (!isConverting) {
                      e.target.style.fontSize = "16px";
                      e.target.style.transform = "translateY(0)";
                    }
                  }}
                  disabled={isLoading || isConverting || isListening}
                />
                {/* Clear Transcription Button */}
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
                    onMouseEnter={(e) => {
                      e.target.style.backgroundColor = "#f0f0f0";
                      e.target.style.borderColor = "#3C3D37";
                      e.target.style.color = "#3C3D37";
                    }}
                    onMouseLeave={(e) => {
                      e.target.style.backgroundColor = "transparent";
                      e.target.style.borderColor = "#697565";
                      e.target.style.color = "#697565";
                    }}
                    title="Clear text"
                  >
                    ✕
                  </button>
                )}

                {/* Voice Button */}
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
                    onMouseOver={(e) => {
                      if (!isLoading && !isConverting) {
                        e.target.style.transform = "scale(1.1)";
                        e.target.style.boxShadow = isListening
                          ? "0 8px 25px rgba(255, 68, 68, 0.6), 0 0 30px rgba(255, 68, 68, 0.4)"
                          : "0 8px 25px rgba(139, 69, 19, 0.6), 0 0 20px rgba(139, 69, 19, 0.4)";
                      }
                    }}
                    onMouseOut={(e) => {
                      if (!isLoading && !isConverting) {
                        e.target.style.transform = "scale(1)";
                        e.target.style.boxShadow = isListening
                          ? "0 4px 15px rgba(255, 68, 68, 0.4), 0 0 20px rgba(255, 68, 68, 0.3)"
                          : "0 4px 15px rgba(139, 69, 19, 0.4)";
                      }
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

                {/* Send Button */}
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
                  onMouseOver={(e) => {
                    if (currentInput.trim() && !isLoading && !isConverting) {
                      e.target.style.transform = "scale(1.1)";
                      e.target.style.background =
                        "linear-gradient(135deg, #3C3D37 0%, #181C14 100%)";
                      e.target.style.boxShadow =
                        "0 8px 25px rgba(105, 117, 101, 0.6), 0 0 20px rgba(105, 117, 101, 0.4)";
                      e.target.style.borderColor = "#ECDFCC";
                    }
                  }}
                  onMouseOut={(e) => {
                    if (currentInput.trim() && !isLoading && !isConverting) {
                      e.target.style.transform = "scale(1)";
                      e.target.style.background =
                        "linear-gradient(135deg, #697565 0%, #3C3D37 100%)";
                      e.target.style.boxShadow =
                        "0 4px 15px rgba(105, 117, 101, 0.4), 0 0 0 0 rgba(105, 117, 101, 0.7)";
                      e.target.style.borderColor = "#3C3D37";
                    }
                  }}
                  onMouseDown={(e) => {
                    if (currentInput.trim() && !isLoading && !isConverting) {
                      e.target.style.transform = "scale(0.95)";
                      e.target.style.animation = "none";
                    }
                  }}
                  onMouseUp={(e) => {
                    if (currentInput.trim() && !isLoading && !isConverting) {
                      e.target.style.transform = "scale(1.05)";
                      e.target.style.animation = "sendPulse 0.6s ease-out";
                      setTimeout(() => {
                        e.target.style.transform = "scale(1)";
                        e.target.style.animation = "pulse 2s infinite";
                      }, 600);
                    }
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

            {/* Disclaimer */}
            <div
              style={{
                textAlign: "center",
                padding: "8px 5px",
                fontSize: "11px",
                color: "rgba(105, 117, 101, 0.7)",
                background: "transparent",
                borderTop: "1px solid rgba(105, 117, 101, 0.1)",
                fontWeight: "400",
                letterSpacing: "0.2px",
                lineHeight: "1.0",
              }}
            >
              AI Guru’s got the brains, but it’s still learning the ropes—verify
              important stuff, just in case!
            </div>

            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              onChange={handleImageUpload}
              style={{ display: "none" }}
            />
          </div>
        </div>
      </div>
    </>
  );
}

export default App;

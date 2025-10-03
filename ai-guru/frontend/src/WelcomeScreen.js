import React from 'react';

const WelcomeScreen = ({ isLoading, setCurrentInput, fileInputRef }) => {
  return (
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
          <circle cx="50" cy="50" r="45" fill="url(#botGradient)" />
          <rect
            x="25"
            y="30"
            width="50"
            height="40"
            rx="15"
            ry="15"
            fill="url(#faceGradient)"
          />
          <circle cx="37" cy="45" r="4" fill="#374151" />
          <circle cx="63" cy="45" r="4" fill="#374151" />
          <circle cx="38" cy="43" r="1.5" fill="white" />
          <circle cx="64" cy="43" r="1.5" fill="white" />
          <path
            d="M40 58 Q50 65 60 58"
            stroke="#374151"
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
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
        >
          Upload an image
        </button>
      </div>
    </div>
  );
};

export default WelcomeScreen;
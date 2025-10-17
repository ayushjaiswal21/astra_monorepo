import React from 'react';

const WelcomeScreen = ({ setCurrentInput, fileInputRef }) => {

  const prompts = [
    "Help me draft a professional email",
    "Explain a complex topic in simple terms",
    "Brainstorm ideas for a new project",
    "Summarize a long article for me"
  ];

  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center text-gray-600">
      <div className="max-w-3xl w-full">
        <h1 className="text-4xl font-bold text-gray-800 mb-4">AI Guru at Your Service</h1>
        <p className="text-lg text-gray-500 mb-12">What can I help you with today?</p>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-12">
          {prompts.map((prompt, index) => (
            <div
              key={index}
              onClick={() => setCurrentInput(prompt)}
              className="bg-white p-4 rounded-lg text-left cursor-pointer border border-gray-200 hover:border-gray-300 hover:shadow-lg transition-all duration-200"
            >
              <p className="text-gray-700">{prompt}</p>
            </div>
          ))}
        </div>

        <div 
          onClick={() => fileInputRef.current?.click()}
          className="relative border-2 border-dashed border-gray-300 rounded-lg p-8 flex flex-col items-center justify-center cursor-pointer hover:border-blue-500 hover:bg-gray-50 transition-all duration-200"
        >
          <div className="text-4xl mb-4">🖼️</div>
          <h3 className="text-lg font-semibold text-gray-800">Upload an Image</h3>
          <p className="text-gray-500">Click here to select a file</p>
        </div>
      </div>
    </div>
  );
};

export default WelcomeScreen;

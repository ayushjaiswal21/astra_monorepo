# AI Guru Multibot 🤖

An advanced multimodal AI chat agent with **self-learning capabilities** built on Google Gemini AI:

- **🧠 AI Self-Learning**: Continuously improves from user interactions and feedback
- **🌍 Multilingual Support**: 50+ languages with cultural adaptation (Hinglish, Tenglish, etc.)
- **💬 Natural Conversations**: Context-aware responses like talking to a real friend
- **📸 Image Analysis**: Advanced vision capabilities with Google Gemini Pro Vision
- **📊 Learning Analytics**: Real-time insights into AI improvement and user preferences
- **🔄 Adaptive Responses**: Learns your preferred communication style and formats

## 🚀 Key Features

### 🧠 **AI Learning System**

- **Pattern Recognition**: AI learns from successful interactions to improve future responses
- **User Feedback Integration**: Thumbs up/down feedback trains the AI in real-time
- **Preference Learning**: Remembers your preferred response format (paragraphs vs structured)
- **Style Adaptation**: Matches your communication style (formal, casual, technical)
- **Context Awareness**: Understands conversation flow and responds naturally

### 🌐 **Advanced Multilingual Capabilities**

- **50+ Language Support**: From English to Hindi, Spanish to Japanese
- **Mixed Language Handling**: Perfect for Hinglish, Tenglish, and code-switching
- **Cultural Context**: Adapts responses to cultural nuances and regional preferences
- **Smart Language Detection**: Automatically detects and responds in user's language
- **Translation on Demand**: Provides translations when explicitly requested

### 💡 **Intelligent Conversation Features**

- **Natural Dialogue**: Responds like a knowledgeable friend, not a formal assistant
- **Conversational Memory**: Remembers recent conversation context for coherent responses
- **Format Intelligence**: Provides paragraphs, lists, or casual responses based on your request
- **Emotion & Tone Matching**: Adapts to your mood and communication style
- **Smart Question Understanding**: Handles follow-up questions and contextual queries

### 🛡️ **Professional & Secure**

- **Transparent AI Disclaimer**: Clear indication that you're interacting with AI
- **Secure MongoDB Integration**: All conversations and learning data safely stored
- **Rate Limiting**: Protection against abuse and overuse
- **Production-Ready**: Clean codebase optimized for deployment

## 📋 Prerequisites

- **Python 3.12+**
- **Node.js 18+**
- **Google Gemini API Key** ([Get it here](https://makersuite.google.com/))
- **MongoDB Atlas** (Cloud database for AI learning) - [Get free tier](https://www.mongodb.com/cloud/atlas)
- **Git** for version control

> **Note**: The project now uses MongoDB instead of MySQL for better AI learning data storage and analytics.

## Setup

### Backend (Python/FastAPI)

1. **Navigate to backend/**:

   ```bash
   cd backend
   ```

2. **Create virtual environment**:

   ```bash
   python -m venv venv
   ```

3. **Activate environment**:

   ```bash
   venv\Scripts\activate.bat
   ```

4. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

5. **🔒 Configure environment variables** (SECURITY CRITICAL):

   **Copy the example file and add your credentials:**

   ```bash
   cd backend
   cp .env.example .env
   ```

   **Then edit `.env` file with your actual credentials:**

   ```env
   GEMINI_API_KEY=your_actual_gemini_api_key_here
   MONGODB_URI=mongodb+srv://your_username:your_password@your_cluster.mongodb.net/ai_guru_db
   ENVIRONMENT=development
   ```

   **🔒 SECURITY REQUIREMENTS:**

   - `GEMINI_API_KEY`: Get from [Google AI Studio](https://makersuite.google.com/) - **Keep Secret!**
   - `MONGODB_URI`: Get from [MongoDB Atlas](https://www.mongodb.com/cloud/atlas) - **Never Commit!**
   - `ENVIRONMENT`: Set to `production` for live deployment (hides API docs)

   **⚠️ CRITICAL: Never commit .env files to Git - they contain sensitive credentials!**

### Frontend (React)

1. Navigate to `frontend/`:
   ```
   cd frontend
   ```
2. Install dependencies:
   ```
   npm install
   ```

### 🗄️ Database Setup (MongoDB Atlas)

1. **Create MongoDB Atlas Account**:
   - Visit [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
   - Create a free cluster (M0 Sandbox - perfect for development)
2. **Setup Database Access**:
   - Create database user with read/write permissions
   - Add your IP address to IP Access List (or 0.0.0.0/0 for development)
3. **Database Collections** (Auto-created):

   - `chat_history`: Stores all conversations with learning metadata
   - `learned_patterns`: Stores AI learning patterns and user preferences
   - `user_feedback`: Stores user feedback for continuous improvement

4. **Get Connection String**:
   - Click "Connect" → "Connect your application"
   - Copy MongoDB URI and add to your `.env` file

## Running the App

1. **Start Backend** (Terminal 1):

   ```bash
   cd backend
   venv\Scripts\activate.bat  # Windows
   # source venv/bin/activate  # macOS/Linux
   python main.py
   ```

2. **Start Frontend** (Terminal 2):

   ```bash
   cd frontend
   npm start
   ```

3. **Access Application**:
   - **Frontend**: http://localhost:3000
   - **Backend API**: http://localhost:8001
   - **API Documentation**: http://localhost:8001/docs (development only)
   - **Learning Analytics**: http://localhost:8001/learning-analytics

## 🔌 API Endpoints

### 💬 **Core Chat Features**

- **POST** `/chat` - Intelligent text conversation with learning integration
- **POST** `/image-chat` - Advanced image analysis with Gemini Pro Vision
- **GET** `/chat-history` - Retrieve conversation sessions with learning metadata
- **DELETE** `/session/{session_id}` - Delete specific session and its learned patterns
- **DELETE** `/chat-history` - Clear all conversations and reset learning data

### 🧠 **AI Learning System**

- **POST** `/feedback` - Submit user feedback to train the AI (thumbs up/down)
- **GET** `/learning-analytics` - View AI learning progress and effectiveness metrics
- **GET** `/feedback-test` - Test feedback system functionality

### 🛠️ **System & Diagnostics**

- **GET** `/test-gemini` - Verify Gemini AI API connectivity
- **GET** `/health` - System health check and database status
- **GET** `/docs` - Interactive API documentation (development only)

## 🛠️ Technology Stack

### **Backend Architecture**

- **FastAPI**: High-performance Python web framework with automatic API documentation
- **Google Gemini 2.0 Flash**: Latest AI model for text generation and vision analysis
- **MongoDB Atlas**: Cloud database for scalable AI learning data storage
- **Advanced Learning Engine**: Pattern analysis, preference learning, and feedback integration

### **Frontend Technology**

- **React.js**: Modern component-based UI framework
- **Responsive Design**: Mobile-first approach with clean, professional interface
- **Real-time Feedback**: Interactive thumbs up/down buttons for AI training
- **Voice Support**: Text-to-speech and speech-to-text capabilities (optional)

### **AI & Learning Features**

- **Multilingual AI**: 50+ language support with cultural context awareness
- **Learning Analytics**: Real-time metrics on AI improvement and user satisfaction
- **Adaptive Responses**: Dynamic system prompts based on learned user preferences
- **Conversation Memory**: Context-aware responses using recent conversation history

### **Security & Production**

- **Rate Limiting**: Protection against API abuse and bot traffic
- **Secure Headers**: CORS, security headers, and production-ready configuration
- **Environment-based Config**: Separate development and production environments
- **Error Handling**: Comprehensive error logging and graceful failure recovery

## 📱 Usage Guide

### 💬 **Intelligent Text Chat**

1. **Natural Conversation**: Type your message and press Enter - the AI responds like a knowledgeable friend
2. **Language Flexibility**: Write in any of 50+ supported languages, including mixed languages (Hinglish, Tenglish)
3. **Format Requests**: Ask for "paragraphs," "bullet points," or "detailed explanation" - AI adapts to your preference
4. **Follow-up Questions**: AI remembers context, so ask follow-up questions naturally

### 🧠 **AI Learning & Feedback**

1. **Rate Responses**: Use 👍� buttons to help AI learn your preferences
2. **Style Learning**: AI remembers if you prefer formal or casual responses
3. **Format Learning**: AI learns whether you like structured lists or flowing paragraphs
4. **Conversation Context**: AI uses recent conversation history to provide coherent responses

### 📸 **Advanced Image Analysis**

1. **Upload Images**: Click 📷 to analyze photos with Gemini Pro Vision
2. **Ask Questions**: Add specific questions about your image for targeted analysis
3. **Multiple Formats**: Supports JPEG, PNG, GIF, WebP formats
4. **Contextual Analysis**: Combine image analysis with ongoing conversation

### 📊 **Learning Analytics**

- **View Progress**: Check `/learning-analytics` endpoint to see AI improvement metrics
- **Preference Insights**: Understand how AI adapts to user communication styles
- **Feedback Stats**: Monitor positive vs negative feedback trends
- **Session Learning**: See how AI learns from each conversation session

### 🎨 **Customization Features**

- **Response Style**: AI adapts to match your communication style (formal, casual, technical)
- **Language Preferences**: AI remembers your preferred language and cultural context
- **Topic Interests**: AI learns about your interests and tailors responses accordingly
- **Conversation Flow**: AI maintains natural dialogue without repetitive patterns

## 📁 Project Structure

```
GuruMultibot/
├── 📊 CLEANUP_SUMMARY.md    # Production readiness & optimization report
├── 📖 README.md            # This comprehensive guide
│
├── 🔧 backend/
│   ├── 🤖 main.py          # FastAPI app with AI learning system
│   ├── 📦 requirements.txt # Python dependencies
│   ├── 🔐 .env            # Environment configuration (create this)
│   └── 📂 venv/           # Python virtual environment
│
├── 🎨 frontend/
│   ├── 📂 src/
│   │   ├── 💻 App.js       # Main React app with learning integration
│   │   ├── 🎯 index.js     # React entry point
│   │   └── 📝 index.css    # Global styles
│   ├── 📦 package.json     # Node.js dependencies
│   ├── 🔒 package-lock.json # Dependency lock file
│   └── 📂 public/          # Static assets (favicon, manifest)
│
└── 📚 docs/                # Future documentation
```

### 🎯 **Key Files Explained**

- **`backend/main.py`**: Complete AI system with learning algorithms, multilingual support, and feedback processing
- **`frontend/src/App.js`**: React interface with feedback buttons, disclaimer, and learning integration
- **`CLEANUP_SUMMARY.md`**: Production readiness assessment and deployment recommendations
- **`.env`**: Critical configuration file (you need to create this with your API keys)

## 💰 Cost Estimation

### **Google Gemini API Costs**

- **Gemini 2.0 Flash (Text)**: $0.00015 per 1K input characters, $0.0006 per 1K output characters
- **Gemini Pro Vision (Images)**: $0.0025 per image analysis
- **Estimated Monthly Cost**: $3-10 for moderate usage (100-500 messages/day)

### **MongoDB Atlas Costs**

- **Free Tier (M0)**: 512MB storage, perfect for development and small projects
- **Paid Tiers**: Start at $9/month for production workloads with 2GB+ storage
- **Learning Data**: Minimal storage impact (~1-5MB per 1000 conversations)

### **Total Cost Breakdown**

- **Development**: **$0/month** (Free tiers for MongoDB + Gemini free quota)
- **Small Business**: **$5-15/month** (Gemini API + MongoDB M2 cluster)
- **Production**: **$20-50/month** (Higher API usage + production MongoDB cluster)

> **💡 Pro Tip**: Start with free tiers to test, then scale based on actual usage patterns!

## 🔧 Troubleshooting

### **Common Issues & Solutions**

**🔑 API Key Problems**

```bash
Error: "Gemini API key invalid"
Solution: Check your .env file, ensure GEMINI_API_KEY is correct
Test: Visit http://localhost:8001/test-gemini
```

**🗄️ Database Connection Issues**

```bash
Error: "MongoDB connection failed"
Solution: Verify MONGODB_URI in .env, check Atlas IP whitelist
Test: Look for "MongoDB connected successfully!" in backend logs
```

**🌐 CORS Errors**

```bash
Error: "Access blocked by CORS policy"
Solution: Ensure backend runs on port 8001, frontend on port 3000
Check: Both services should start successfully
```

**📱 Frontend Won't Start**

```bash
Error: "npm start fails"
Solution: Run "npm install" first, then "npm start"
Check: Node.js version 18+ required
```

**🧠 Learning System Not Working**

```bash
Error: Feedback buttons not responding
Solution: Check MongoDB connection, verify feedback endpoint
Test: Visit http://localhost:8001/feedback-test
```

**🌍 Language Detection Issues**

```bash
Error: AI responds in wrong language
Solution: This is normal for short messages, AI will adapt over time
Note: Mixed languages (Hinglish) are fully supported
```

### **Debug Commands**

```bash
# Check all services
curl http://localhost:8001/health
curl http://localhost:3000

# Test API endpoints
curl -X POST http://localhost:8001/chat -H "Content-Type: application/json" -d '{"text":"Hello"}'

# View learning analytics
curl http://localhost:8001/learning-analytics
```

## 🔒 Security Best Practices

### **⚠️ CRITICAL SECURITY MEASURES**

**1. Environment Variables Security:**

```bash
# ✅ ALWAYS use .env files for credentials
cp backend/.env.example backend/.env
# ❌ NEVER commit .env files to Git
# ❌ NEVER hardcode credentials in source code
```

**2. MongoDB Atlas Security:**

- **Enable IP Whitelisting**: Add your server IP to MongoDB Atlas Network Access
- **Strong Passwords**: Use complex passwords with special characters
- **Database User Permissions**: Create specific database users with minimal required permissions
- **Regular Rotation**: Rotate database passwords every 90 days

**3. API Key Protection:**

- **Gemini API Key**: Restrict API key usage to specific IP addresses if possible
- **Rate Limiting**: Monitor API usage to prevent abuse
- **Key Rotation**: Regularly regenerate API keys

**4. Production Security:**

```bash
# Set production environment
ENVIRONMENT=production

# Security features (already configured in main.py):
# - CORS protection
# - Rate limiting
# - Input validation
# - Error handling without sensitive data exposure
```

**5. Deployment Security:**

- **HTTPS Only**: Always use SSL certificates in production
- **Environment Isolation**: Never use development credentials in production
- **Monitoring**: Set up alerts for unusual API usage patterns
- **Backup Security**: Ensure database backups are encrypted

### **🔍 Security Checklist**

- [ ] `.env` file exists and contains real credentials
- [ ] `.env` is listed in `.gitignore`
- [ ] No hardcoded credentials in source code
- [ ] MongoDB Atlas IP whitelisting enabled
- [ ] Strong database passwords used
- [ ] Gemini API key is valid and restricted
- [ ] Production environment variables set
- [ ] SSL certificate configured for production
- [ ] Regular security updates scheduled

## 🤝 Contributing

We welcome contributions to improve the AI learning system! Here's how to get started:

### **Development Setup**

1. **Fork & Clone**: Fork the repository and clone your fork
2. **Setup Environment**: Follow the installation guide above
3. **Create Branch**: `git checkout -b feature/your-feature-name`
4. **Test Changes**: Ensure both backend and frontend work correctly

### **Areas for Contribution**

- 🧠 **AI Learning Algorithms**: Improve pattern recognition and preference learning
- 🌍 **Language Support**: Add new languages or improve cultural adaptations
- 📊 **Analytics Dashboard**: Build frontend for learning analytics visualization
- 🔒 **Security Features**: Enhance authentication and rate limiting
- 🎨 **UI/UX**: Improve user interface and experience design
- 📱 **Mobile Support**: Optimize for mobile devices and PWA features

### **Contribution Guidelines**

- Write clear, descriptive commit messages
- Follow existing code style and patterns
- Test your changes thoroughly with different languages
- Update documentation for new features
- Submit focused PRs (one feature per PR)

### **Testing Your Changes**

```bash
# Backend tests
cd backend
python -m pytest

# Frontend tests
cd frontend
npm test

# Integration testing
# Test feedback system, language detection, learning analytics
```

## 📄 License

This project is open source and available under the **MIT License**.

**What this means:**

- ✅ Commercial use allowed
- ✅ Modification allowed
- ✅ Distribution allowed
- ✅ Private use allowed
- ❌ No warranty provided
- ❌ Authors not liable

## 🌟 Acknowledgments

- **Google Gemini AI**: Powering the intelligent conversations and image analysis
- **MongoDB Atlas**: Providing scalable cloud database for AI learning data
- **FastAPI Community**: For the excellent Python web framework
- **React Team**: For the robust frontend framework
- **Open Source Contributors**: Everyone who helps improve this project

---

**📧 Questions?** Open an issue on GitHub or check the troubleshooting section above.

**🚀 Ready to deploy?** See `CLEANUP_SUMMARY.md` for production deployment guidelines and security recommendations.

# 🌟 Astra — Authentication, AI Learning & Course Platform (Monorepo)

A modern, AI-powered learning and networking ecosystem built with **Flask**, **FastAPI + React**, and **Django**.

Astra combines:

* 🔐 **Authentication & Profile Management**
* 🤖 **AI-Guru – Personal AI Mentor**
* 📚 **AstraLearn – Course Creation & Learning Dashboard**

All inside one monorepo.

---

## 🚀 Project Modules

### 🔐 1. Astra Authentication (Flask – Port 5000)

Handles account creation, user roles, networking, and profile management.

#### ✨ Features

* Email signup & login
* Provider / Seeker role selection
* Profile editing (About, Experience, Education, Skills, Certifications)
* Profile picture & certificate uploads
* Create posts (LinkedIn-style)
* Dynamic dashboard feed
* Clean UI built with TailwindCSS
* View connections & profiles

---

### 🤖 2. AI Guru (FastAPI + React – Ports 8001 & 3000)

Interactive AI-driven chat experience for learning & career support.

#### ✨ Features

* Fully functional React chat UI
* FastAPI backend with mock AI responses
* Sidebar, chat history, message bubbles
* Smooth navigation from Django dashboard
* Extendable to real AI APIs (OpenAI, Gemini, etc.)

---

### 📚 3. AstraLearn Courses (Django – Port 8000)

Complete learning platform with dashboards, courses, and progress tracking.

#### ✨ Features

* Student dashboard
* Course list / My Courses
* Course detail pages
* Enroll system working
* AI-based course creation (prototype-ready)
* Progress tracking UI
* Fully responsive templates
* Admin panel support

---

## 🧪 Testing Summary

Testing included **manual verification**, **service health checks**, and **post-cleanup validation**.

### ✔ Verified Working

* Signup / Login (Flask)
* Role selection
* Full profile editing
* Posting & dynamic feed
* AI Guru chat UI + backend communication
* Django course listing, enrollment, dashboard
* All 3 services start cleanly with no route errors
* Static files, templates, Tailwind styling

### 🗑 Removed Testing Artifacts

* Cypress tests
* Pytest files
* Mock servers
* All debug logs & backups
* Cache folders
* Cleanup scripts

The repo is now clean and stable.

---

## 🏃‍♂️ How to Run the Project

Run each service in a separate terminal.

### 🔐 Flask Authentication

```bash
cd asta_authentication
flask run --port 5000
```

### 🤖 AI Guru Backend (FastAPI)

```bash
cd ai-guru/backend
python main.py
```

### 💬 AI Guru Frontend (React)

```bash
cd ai-guru/frontend
npm install
npm start
```

### 📚 AstraLearn (Django)

```bash
cd astra
python manage.py runserver 8000
```

### Service URLs

| Service             | URL                                            |
| ------------------- | ---------------------------------------------- |
| Flask Auth          | [http://127.0.0.1:5000](http://127.0.0.1:5000) |
| AI Guru Frontend    | [http://127.0.0.1:3000](http://127.0.0.1:3000) |
| AI Guru Backend     | [http://127.0.0.1:8001](http://127.0.0.1:8001) |
| AstraLearn (Django) | [http://127.0.0.1:8000](http://127.0.0.1:8000) |

---

## 📁 Project Structure (Simplified)

```
astra_monorepo/
│
├── asta_authentication/        # Flask Auth & Profiles
├── ai-guru/
│   ├── backend/                # FastAPI AI Guru Backend
│   └── frontend/               # React Chat UI
│
├── astra/                      # Django course system
│   ├── astralearn/
│   └── tutor/
│
├── instance/                   # Local SQLite DBs
├── README.md
├── start_all.bat / start_all.ps1
```

---

## 🛠 Tech Stack

### Backend

* Flask
* FastAPI
* Django
* SQLAlchemy
* SQLite

### Frontend

* React
* TailwindCSS
* Vanilla JS / HTML templates

### Tools & Features

* Celery-ready architecture
* Local file storage
* JWT & login management
* REST APIs
* Async chat responses

---

## 📌 Current Status

✔ All core features working
✔ Clean repo (no test/debug clutter)
✔ Fully stable local development setup
✔ Routes and services functioning end-to-end
✔ Professional UI & UX across modules
✔ Ready for GitHub, submission, or deployment

---

## 🔮 Future Improvements

* Replace mock AI with real LLM APIs
* Add WebSockets for real-time chat
* Add search & filters to posts and courses
* Add quizzes & certificates to courses
* Add full automated testing suite

---

## 🙌 Author

**Ayush Jaiswal**
3rd Year CSE • AI/ML & Full-Stack Developer
Building modern AI-first learning tools 🚀

---
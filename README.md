# Astra Learn Full Monorepo

This repository contains the complete collection of projects for the Astra Learn platform, consolidated into a single monorepo.

## Projects Included

This monorepo contains the following three projects:

1.  **`asta_authentication/`**: A Flask-based web application for user authentication and dashboard.
2.  **`ai-guru/`**: A FastAPI and React-based AI chat application with self-learning capabilities.
3.  **`astra/`**: A Django-based application for learning modules.

## Setup and Installation

To get the entire platform running, follow these steps.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd astra_monorepo
```

### 2. Create a Virtual Environment

It is highly recommended to use a virtual environment to manage the project dependencies.

```bash
# Windows
python -m venv venv
vvenv\Scripts\activate
```

### 3. Install Dependencies

Install all the required Python packages from the root `requirements.txt` file.

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

You will need to set up environment variables for the `ai-guru` and `asta_authentication` applications.

**For `ai-guru`:**

*   Create a file named `.env` inside the `ai-guru/backend/` directory.
*   Add the following content, replacing the placeholder values with your actual credentials:

    ```
    GEMINI_API_KEY=your_gemini_api_key_here
    MONGODB_URI=mongodb+srv://your_username:your_password@your_cluster.mongodb.net/ai_guru_db
    ```

**For `asta_authentication`:**

*   Create a file named `.env` inside the `asta_authentication/` directory.
*   Add the following content, replacing the placeholder values with your Google OAuth credentials:

    ```
    GOOGLE_OAUTH_CLIENT_ID=your_google_client_id.apps.googleusercontent.com
    GOOGLE_OAUTH_CLIENT_SECRET=your_google_client_secret
    ```

## Running the Projects

A convenient batch script is included to start all three servers at once.

1.  Navigate to the root of the `astra_monorepo` directory.
2.  Double-click the `start_all.bat` file.

This will open three separate command prompt windows for each application:

*   **Astra Authentication (Flask):** Running on `http://localhost:5000`
*   **AI Guru (FastAPI):** Running on `http://localhost:8001`
*   **Astra Modules (Django):** Running on `http://localhost:8000`

You can access the main dashboard by navigating to `http://localhost:5000/dashboard` in your web browser.

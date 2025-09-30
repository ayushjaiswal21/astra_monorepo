# Astralearn - AI-Powered Course Generator

Astralearn is a dynamic web application built with Django that leverages AI to automatically generate entire courses, complete with modules, lessons, and quizzes, based on a user-provided topic. It features real-time AI assistance and interactive elements powered by Django Channels.

This project uses a dual-AI strategy:
1.  A local Ollama model (e.g., `phi3:mini`) is used for the high-level course structure (titles, modules, lesson titles).
2.  The Google Generative AI API (Gemini) is used to generate the detailed content for each individual lesson, as well as for interactive features like simplifying content and generating examples.

Asynchronous tasks are managed by Celery with a Redis broker to ensure the user experience is fast and non-blocking while the AI works in the background.

## Key Features

-   **AI-Powered Course Creation**: Enter any topic and get a full course structure in minutes.
-   **Interactive Learning**: Simplify complex topics and generate practical examples on the fly.
-   **Asynchronous Generation**: Uses Celery and Redis to generate course content in the background.
-   **Real-time AI Assistance**: In-lesson chat for asking questions about the content.
-   **Dual-LLM Strategy**: Utilizes both local and cloud-based LLMs.
-   **User-Friendly Interface**: Simple and intuitive UI for creating and viewing courses.

## Technology Stack

-   **Backend**: Django, Django Channels
-   **Frontend**: HTML, JavaScript, Tailwind CSS
-   **Asynchronous Tasks**: Celery
-   **Message Broker & Cache**: Redis
-   **Database**: SQLite (for local development), PostgreSQL (for production)
-   **AI (Structure)**: Ollama
-   **AI (Content & Interactive Features)**: Google Generative AI (Gemini API)

## Local Development Setup

To run this project locally, you will need Python, Redis, and Ollama installed.

1.  **Clone the repository:**
    ```bash
    git clone <your-repo-url>
    cd astralearn
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    pip install -r requirements.txt
    ```

3.  **Set up Environment Variables:**
    -   Create a file named `.env` in the project root.
    -   Add the necessary environment variables (see section below).

4.  **Run Database Migrations:**
    ```bash
    python manage.py migrate
    ```

5.  **Ensure Services are Running:**
    -   **Redis**: Make sure your local Redis server is running on its default port (6379).
    -   **Ollama**: Make sure your local Ollama server is running. You can run it with `ollama serve`. You also need to have a model pulled, for example `ollama pull phi3:mini`.

6.  **Start the Celery Worker:**
    -   In a new terminal, activate the virtual environment and run:
    ```bash
    # On Windows, you may need to use the -P solo flag
    celery -A astralearn worker -l info
    ```

7.  **Start the Django Application:**
    -   Since this project uses Django Channels for WebSockets, you need to run it with an ASGI server like Uvicorn or Daphne.
    -   In another new terminal, activate the virtual environment and run:
    ```bash
    uvicorn astralearn.asgi:application --host 0.0.0.0 --port 8000 --reload
    ```
    You can now access the application at `http://localhost:8000`.

## Environment Variables

Create a `.env` file in the root directory and add the following:

```
# A strong, random string for Django's security features.
SECRET_KEY='your_django_secret_key_goes_here'

# Set to False in production
DEBUG=True

# Your secret API key from Google AI Studio
GEMINI_API_KEY='your_gemini_api_key_goes_here'

# The URL for your local Ollama API endpoint
OLLAMA_URL='http://localhost:11434/api/generate'
```
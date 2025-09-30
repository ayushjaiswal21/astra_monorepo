AstraLearn - Flask Authentication
This project is a Flask-based web application that provides a complete user authentication system, including email/password registration, login, and Google OAuth 2.0 integration.

Features
User Registration (Email and Password)

User Login (Email and Password)

"Continue with Google" Login (OAuth 2.0)

Password Recovery (UI only)

Basic Profile Page

Responsive UI with Tailwind CSS

Project Structure
/
|-- app.py              # Main Flask application file
|-- users.db            # SQLite database for storing user info
|-- templates/
|   |-- index.html      # Home page
|   |-- signin.html     # Main sign-in options page
|   |-- join.html       # User registration page
|   |-- signin_email.html # Sign in with email and password
|   |-- forgot_password.html # Forgot password page
|-- README.md           # This file
|-- requirements.txt    # Python dependencies

Setup and Installation
Clone the repository:

git clone <repository-url>
cd <repository-folder>

Create a virtual environment:

python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`

Install the dependencies:

pip install -r requirements.txt

Set up Google OAuth 2.0 Credentials:

Go to the Google Cloud Console.

Create a new project.

Go to "APIs & Services" -> "Credentials".

Click "Create Credentials" -> "OAuth client ID".

Choose "Web application".

Add an "Authorized JavaScript origins": http://127.0.0.1:5000

Add an "Authorized redirect URIs": http://127.0.0.1:5000/login/google/authorized

Click "Create". You will get a Client ID and Client Secret.

Set Environment Variables:
You need to set the Client ID and Client Secret as environment variables for the application to use.

On macOS/Linux:

export GOOGLE_OAUTH_CLIENT_ID="YOUR_CLIENT_ID"
export GOOGLE_OAUTH_CLIENT_SECRET="YOUR_CLIENT_SECRET"

On Windows (Command Prompt):

set GOOGLE_OAUTH_CLIENT_ID="YOUR_CLIENT_ID"
set GOOGLE_OAUTH_CLIENT_SECRET="YOUR_CLIENT_SECRET"

Note: Replace "YOUR_CLIENT_ID" and "YOUR_CLIENT_SECRET" with the credentials you obtained from Google.

Run the application:

flask run

The application will be running at http://127.0.0.1:5000.

How It Works
Flask: The web framework used for routing and handling requests.

Flask-Dance: Simplifies the process of adding OAuth authentication with providers like Google.

SQLite: A lightweight, serverless database used to store user information.

Werkzeug: Handles password hashing and security.

Tailwind CSS: A utility-first CSS framework for creating the user interface.

The application uses sessions to keep track of logged-in users. When a user logs in with Google, their information is fetched from the Google API and stored in the session. For email/password authentication, passwords are securely hashed before being stored in the database.
# Collaborative Scenario Writer

A Flask web application allowing multiple users to collaborate on writing scenarios for different episodes of an educational mobile app.

## Features

* User login (basic implementation).
* Dashboard displaying assigned episodes and other collaborators.
* Episode page with separate sections for 'Plan' and 'Scenario'.
* Ability to edit and save Plan and Scenario content.
* Clickable scenario lines to add and view comments.
* Modern, responsive frontend using Tailwind CSS.

## Project Structure

```
collaborative-scenario-writer/
├── app.py                 # Main Flask application file
├── models.py              # Database models (SQLAlchemy)
├── requirements.txt       # Python dependencies
├── README.md              # This file
├── .env                   # Optional: For environment variables (e.g., SECRET_KEY) - *Create this file*
├── instance/              # Folder created automatically by Flask/SQLAlchemy for the database
│   └── app.db             # SQLite database file (created automatically)
├── static/
│   └── css/
│       └── style.css      # Optional: Custom CSS
│   └── js/
│       └── script.js      # Frontend JavaScript
└── templates/
    ├── base.html          # Base HTML template
    ├── login.html         # Login page
    ├── dashboard.html     # User dashboard
    └── episode.html       # Episode editing page
```

## Setup and Installation

1.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url> # Or download the files
    cd collaborative-scenario-writer
    ```

2.  **Create a Virtual Environment:**
    It's highly recommended to use a virtual environment to manage dependencies.
    ```bash
    python -m venv venv
    ```
    Activate the environment:
    * Windows: `.\venv\Scripts\activate`
    * macOS/Linux: `source venv/bin/activate`

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Create a `.env` file:** (Optional but recommended for `SECRET_KEY`)
    Create a file named `.env` in the project root directory and add a secret key:
    ```
    SECRET_KEY='a_very_strong_and_random_secret_key_please_change_me'
    # Replace with a real random key (e.g., generated using os.urandom(24).hex())
    ```

5.  **Initialize the Database:**
    Run the following command in your terminal (make sure your virtual environment is active):
    ```bash
    flask create-db
    ```
    This will create the `instance/app.db` SQLite database file, create the necessary tables, and seed some initial user and episode data for demonstration purposes (users: alice/password1, bob/password2, charlie/password3).

## Running the Application

1.  **Make sure your virtual environment is activated.**

2.  **Run the Flask development server:**
    ```bash
    flask run
    ```
    Or, you can run the `app.py` script directly (which also calls `flask run` with debug mode):
    ```bash
    python app.py
    ```

3.  **Access the Application:**
    Open your web browser and navigate to `http://127.0.0.1:5000` (or the address provided in the terminal output).

4.  **Login:**
    Use one of the seeded usernames and passwords (e.g., `alice` / `password1`).

## Development Notes

* **Authentication:** The current implementation uses plain text passwords for demonstration ONLY. **Never use this in production.** Implement proper password hashing (e.g., using `werkzeug.security.generate_password_hash` and `check_password_hash`) and a more robust user management system.
* **Real-time Collaboration:** For true real-time updates (seeing changes and comments instantly without refreshing), consider integrating Flask-SocketIO.
* **Commenting:** The current comment system links comments to line numbers. If the scenario text is heavily edited, the line numbers might shift, potentially misaligning comments. More robust solutions might involve anchoring comments to specific text content or using differential synchronization libraries.
* **Error Handling:** Basic error handling is included, but more comprehensive logging and user feedback can be added.
* **Styling:** Tailwind CSS is used via CDN. For production, consider setting up a build process to bundle and purge unused styles. Custom CSS can be added in `static/css/style.css`.
* **Database:** SQLite is used for simplicity. For production, switch to a more robust database like PostgreSQL or MySQL and update the `SQLALCHEMY_DATABASE_URI` configuration.

## Future Enhancements

* Implement real-time updates using WebSockets (Flask-SocketIO).
* Add user roles and permissions.
* Improve comment anchoring to handle text edits more robustly.
* Add features for episode creation, deletion, and user assignment via the UI.
* Implement proper password hashing and user registration.
* Add notifications for new comments or updates.
* Enhance microanimations and UI polish.

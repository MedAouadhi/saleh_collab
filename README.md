# صالح - الكراسة الحمراء 📕

A Flask web application allowing multiple users to collaborate on writing scenarios for different episodes of an educational mobile app. Fully localized in Arabic with RTL support.

## Features

* User login (with hashed passwords).
* Admin panel (`/admin`) for managing Users and Episodes (requires login as 'admin' user).
* Dashboard displaying all episodes, highlighting assigned ones.
* Episode page with separate, toggleable View/Edit sections for 'Plan' and 'Scenario'.
* Markdown support for Plan and Scenario content.
* Block-based commenting on the Scenario section.
* Ability for users/admins to assign users to episodes.
* Ability for users to unassign themselves.
* Ability for comment authors and admins to delete comments.
* Ability for assigned users and admins to delete episodes (from dashboard or admin panel).
* Server-side PDF export for Plan and Scenario content.
* Arabic interface with RTL layout.

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

1.  **Prerequisites (for PDF Export):**
    * Install WeasyPrint system dependencies. This varies by OS:
        * **Debian/Ubuntu:** `sudo apt-get update && sudo apt-get install libpango-1.0-0 libcairo2 libpangoft2-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info`
        * **macOS (Homebrew):** `brew install pango cairo libffi gdk-pixbuf`
        * **Windows:** See WeasyPrint documentation for installing GTK+ dependencies.

2.  **Clone the Repository:**
    ```bash
    git clone <your-repository-url> # Or download the files
    cd collaborative-scenario-writer
    ```

3.  **Create a Virtual Environment:**
    ```bash
    python -m venv venv
    # Activate:
    # Windows: .\venv\Scripts\activate
    # macOS/Linux: source venv/bin/activate
    ```

4.  **Install Python Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

5.  **Create a `.env` file:** (Optional but recommended for `SECRET_KEY`)
    Create a file named `.env` in the project root directory and add a secret key:
    ```
    SECRET_KEY='a_very_strong_and_random_secret_key_please_change_me'
    ```

6.  **Initialize/Recreate the Database:**
    **(Important: If you previously had an `instance/app.db` file, delete it first to apply new seeding/model changes).**
    Run the following command in your terminal (make sure your virtual environment is active):
    ```bash
    flask create-db
    ```
    This will create the `instance/app.db` SQLite database file, create the necessary tables, and seed the initial users (`admin`, `ahmed_a`, `ahmed_s`, `hakim`, `jawhar`) with hashed passwords.

## Running the Application

1.  Make sure your virtual environment is activated.
2.  Run the Flask development server:
    ```bash
    flask run
    # Or: python app.py
    ```
3.  Access the Application: Open `http://127.0.0.1:5000`.
4.  **Login:**
    * Admin: `admin` / `adminpassword`
    * Normal Users: e.g., `ahmed_a` / `ahmed_a2023`
5.  **Access Admin Panel:** Log in as `admin` and go to `http://127.0.0.1:5000/admin`.

## Development Notes

* **Authentication:** Uses Flask-Login with password hashing (pbkdf2:sha256).
* **Authorization:** Basic admin check via `is_admin` flag on User model. Episode/comment actions check assignment or ownership.
* **Admin:** Uses Flask-Admin with basic customization and access control.
* **PDF Export:** Uses WeasyPrint server-side. Requires system dependencies. PDF styling is basic and defined in `app.py`.
* **Frontend:** Uses Tailwind CSS (via CDN), Alpine.js (via CDN), Marked.js (via CDN), custom JavaScript (`static/js/script.js`).
* **Language/Direction:** Set to Arabic / RTL. Styling uses Tailwind's RTL modifiers where possible, with some CSS overrides.


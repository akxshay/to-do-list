# My.Tasks — Flask Web App

A to-do list web app built with Flask and SQLite.

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run the app
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Project Structure

```
mytasks/
├── app.py              # Flask backend
├── requirements.txt
├── tasks.db            # SQLite database (auto-created on first run)
├── templates/
│   ├── auth.html       # Sign in / Sign up page
│   └── tasks.html      # Main tasks page
└── static/
    └── style.css       # Styles
```

## Features
- Sign up & sign in (passwords hashed with SHA-256)
- Per-user task lists stored in SQLite
- Add tasks with optional due dates
- Mark tasks complete / incomplete
- Delete tasks
- Filter by All / Active / Done
- Due date highlights (overdue in red, due today in amber)

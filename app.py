from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import sqlite3, hashlib, os
from datetime import date

app = Flask(__name__)
app.secret_key = os.urandom(24)   # change to a fixed string in production
DB = os.path.join(os.path.dirname(__file__), "tasks.db")

# ── DATABASE ─────────────────────────────────────────────────────────────────
def get_db():
    db = sqlite3.connect(DB)
    db.row_factory = sqlite3.Row
    return db

def init_db():
    with get_db() as db:
        db.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS tasks (
                id       INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id  INTEGER NOT NULL REFERENCES users(id),
                text     TEXT NOT NULL,
                due      TEXT DEFAULT '',
                done     INTEGER DEFAULT 0,
                created  TEXT DEFAULT (date('now'))
            );
        """)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

# ── HELPERS ───────────────────────────────────────────────────────────────────
def current_user():
    return session.get("user_id"), session.get("username")

def require_login():
    uid, _ = current_user()
    return uid is None

# ── AUTH ROUTES ───────────────────────────────────────────────────────────────
@app.route("/")
def index():
    uid, _ = current_user()
    return redirect(url_for("tasks_page") if uid else url_for("signin"))

@app.route("/signin", methods=["GET", "POST"])
def signin():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute(
                "SELECT * FROM users WHERE username = ?", (username,)
            ).fetchone()
        if not user:
            error = "No account found with that username."
        elif user["password"] != hash_pw(password):
            error = "Incorrect password."
        else:
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            return redirect(url_for("tasks_page"))
    return render_template("auth.html", mode="signin", error=error)

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        confirm  = request.form.get("confirm", "")
        if len(username) < 2:
            error = "Username must be at least 2 characters."
        elif len(password) < 4:
            error = "Password must be at least 4 characters."
        elif password != confirm:
            error = "Passwords do not match."
        else:
            try:
                with get_db() as db:
                    db.execute(
                        "INSERT INTO users (username, password) VALUES (?, ?)",
                        (username, hash_pw(password))
                    )
                    user = db.execute(
                        "SELECT * FROM users WHERE username = ?", (username,)
                    ).fetchone()
                session["user_id"] = user["id"]
                session["username"] = user["username"]
                return redirect(url_for("tasks_page"))
            except sqlite3.IntegrityError:
                error = "That username is already taken."
    return render_template("auth.html", mode="signup", error=error)

@app.route("/signout")
def signout():
    session.clear()
    return redirect(url_for("signin"))

# ── TASK ROUTES ───────────────────────────────────────────────────────────────
@app.route("/tasks")
def tasks_page():
    if require_login():
        return redirect(url_for("signin"))
    uid, username = current_user()
    filter_mode = request.args.get("filter", "all")
    today = date.today().isoformat()
    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM tasks WHERE user_id = ? ORDER BY created DESC, id DESC",
            (uid,)
        ).fetchall()
    tasks = [dict(r) for r in rows]
    # Annotate due status
    for t in tasks:
        d = t.get("due", "")
        if d == today:   t["due_status"] = "today"
        elif d and d < today: t["due_status"] = "overdue"
        else:            t["due_status"] = ""
    if filter_mode == "active":
        tasks = [t for t in tasks if not t["done"]]
    elif filter_mode == "done":
        tasks = [t for t in tasks if t["done"]]
    total     = len([t for t in [dict(r) for r in rows]])
    done_cnt  = sum(1 for r in rows if r["done"])
    return render_template("tasks.html",
        tasks=tasks, username=username,
        filter=filter_mode, today=today,
        total=len(rows), done=done_cnt
    )

@app.route("/tasks/add", methods=["POST"])
def add_task():
    if require_login():
        return redirect(url_for("signin"))
    uid, _ = current_user()
    text = request.form.get("text", "").strip()
    due  = request.form.get("due", "").strip()
    if text:
        with get_db() as db:
            db.execute(
                "INSERT INTO tasks (user_id, text, due) VALUES (?, ?, ?)",
                (uid, text, due)
            )
    return redirect(url_for("tasks_page", filter=request.form.get("filter","all")))

@app.route("/tasks/<int:task_id>/toggle", methods=["POST"])
def toggle_task(task_id):
    if require_login():
        return redirect(url_for("signin"))
    uid, _ = current_user()
    with get_db() as db:
        task = db.execute(
            "SELECT * FROM tasks WHERE id = ? AND user_id = ?", (task_id, uid)
        ).fetchone()
        if task:
            db.execute(
                "UPDATE tasks SET done = ? WHERE id = ?",
                (0 if task["done"] else 1, task_id)
            )
    return redirect(url_for("tasks_page", filter=request.form.get("filter","all")))

@app.route("/tasks/<int:task_id>/delete", methods=["POST"])
def delete_task(task_id):
    if require_login():
        return redirect(url_for("signin"))
    uid, _ = current_user()
    with get_db() as db:
        db.execute(
            "DELETE FROM tasks WHERE id = ? AND user_id = ?", (task_id, uid)
        )
    return redirect(url_for("tasks_page", filter=request.form.get("filter","all")))

# ── MAIN ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True)

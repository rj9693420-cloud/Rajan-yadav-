import os, sqlite3, secrets
from datetime import datetime
from functools import wraps
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, session, flash, abort, send_from_directory
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

ROOT = Path(__file__).resolve().parent
DB_PATH = ROOT / "rajan_site.db"
UPLOAD_DIR = ROOT / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
ALLOWED = {"png", "jpg", "jpeg", "gif", "webp", "mp4", "webm", "mov"}

app = Flask(__name__)
app.config["SECRET_KEY"] = os.environ.get("SECRET_KEY") or "change-this-secret-key-before-public-launch"
app.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with db() as con:
        con.execute("""CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT UNIQUE NOT NULL, password_hash TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS posts (
            id INTEGER PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
            category TEXT NOT NULL DEFAULT 'Update', media TEXT, media_type TEXT,
            created_at TEXT NOT NULL)""")
        con.execute("""CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY, post_id INTEGER NOT NULL, name TEXT NOT NULL,
            body TEXT NOT NULL, created_at TEXT NOT NULL,
            FOREIGN KEY(post_id) REFERENCES posts(id) ON DELETE CASCADE)""")

init_db()

def csrf_token():
    if "_csrf" not in session:
        session["_csrf"] = secrets.token_urlsafe(24)
    return session["_csrf"]
app.jinja_env.globals["csrf_token"] = csrf_token

@app.before_request
def protect_posts():
    if request.method == "POST":
        token = request.form.get("_csrf", "")
        if not token or not secrets.compare_digest(token, session.get("_csrf", "")):
            abort(400, "Invalid form token. Please refresh and try again.")

def logged_in():
    return bool(session.get("admin_id"))

def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if not logged_in():
            return redirect(url_for("login"))
        return fn(*args, **kwargs)
    return wrapper

def allowed_file(name):
    return "." in name and name.rsplit(".", 1)[1].lower() in ALLOWED

@app.route("/")
def home():
    with db() as con:
        posts = con.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return render_template("home.html", posts=posts)

@app.route("/post/<int:post_id>", methods=["GET", "POST"])
def post_detail(post_id):
    with db() as con:
        post = con.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            abort(404)
        if request.method == "POST":
            name = request.form.get("name", "").strip()[:50]
            body = request.form.get("body", "").strip()[:1000]
            if name and body:
                con.execute("INSERT INTO comments(post_id,name,body,created_at) VALUES(?,?,?,?)",
                            (post_id, name, body, datetime.now().strftime("%d %b %Y, %I:%M %p")))
                flash("Comment submitted.", "success")
                return redirect(url_for("post_detail", post_id=post_id))
            flash("Please enter your name and comment.", "error")
        comments = con.execute("SELECT * FROM comments WHERE post_id=? ORDER BY id DESC", (post_id,)).fetchall()
    return render_template("post.html", post=post, comments=comments)

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/admin")
@admin_required
def admin():
    with db() as con:
        posts = con.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
        count = con.execute("SELECT COUNT(*) FROM comments").fetchone()[0]
    return render_template("admin.html", posts=posts, comment_count=count)

@app.route("/setup", methods=["GET", "POST"])
def setup():
    with db() as con:
        exists = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    if exists:
        return redirect(url_for("login"))
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        if len(username) < 3 or len(password) < 10:
            flash("Username must be 3+ characters and password at least 10 characters.", "error")
        else:
            with db() as con:
                con.execute("INSERT INTO users(username,password_hash) VALUES(?,?)",
                            (username, generate_password_hash(password)))
            flash("Admin account created. Please log in.", "success")
            return redirect(url_for("login"))
    return render_template("setup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        with db() as con:
            user = con.execute("SELECT * FROM users WHERE username=?", (username,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["admin_id"] = user["id"]
            session["admin_name"] = user["username"]
            flash("Welcome to your dashboard.", "success")
            return redirect(url_for("admin"))
        flash("Incorrect username or password.", "error")
    return render_template("login.html")

@app.route("/logout", methods=["POST"])
@admin_required
def logout():
    session.clear()
    return redirect(url_for("home"))

@app.route("/admin/new", methods=["GET", "POST"])
@admin_required
def new_post():
    if request.method == "POST":
        title = request.form.get("title", "").strip()[:120]
        body = request.form.get("body", "").strip()[:10000]
        category = request.form.get("category", "Update").strip()[:30]
        media = request.files.get("media")
        filename = media_type = None
        if not title or not body:
            flash("Title and content are required.", "error")
        else:
            if media and media.filename:
                if not allowed_file(media.filename):
                    flash("Allowed files: images, MP4, WebM, MOV.", "error")
                    return render_template("edit_post.html", post=None)
                ext = media.filename.rsplit(".", 1)[1].lower()
                filename = secrets.token_hex(12) + "." + ext
                media.save(UPLOAD_DIR / filename)
                media_type = "video" if ext in {"mp4", "webm", "mov"} else "image"
            with db() as con:
                con.execute("INSERT INTO posts(title,body,category,media,media_type,created_at) VALUES(?,?,?,?,?,?)",
                            (title, body, category, filename, media_type, datetime.now().strftime("%d %b %Y, %I:%M %p")))
            flash("Your post is published.", "success")
            return redirect(url_for("admin"))
    return render_template("edit_post.html", post=None)

@app.route("/admin/edit/<int:post_id>", methods=["GET", "POST"])
@admin_required
def edit_post(post_id):
    with db() as con:
        post = con.execute("SELECT * FROM posts WHERE id=?", (post_id,)).fetchone()
        if not post:
            abort(404)
        if request.method == "POST":
            title = request.form.get("title", "").strip()[:120]
            body = request.form.get("body", "").strip()[:10000]
            category = request.form.get("category", "Update").strip()[:30]
            media = request.files.get("media")
            filename, media_type = post["media"], post["media_type"]
            if media and media.filename:
                if not allowed_file(media.filename):
                    flash("Unsupported file type.", "error")
                    return render_template("edit_post.html", post=post)
                ext = media.filename.rsplit(".", 1)[1].lower()
                newname = secrets.token_hex(12) + "." + ext
                media.save(UPLOAD_DIR / newname)
                if filename:
                    try: (UPLOAD_DIR / filename).unlink()
                    except OSError: pass
                filename = newname
                media_type = "video" if ext in {"mp4", "webm", "mov"} else "image"
            if title and body:
                con.execute("UPDATE posts SET title=?,body=?,category=?,media=?,media_type=? WHERE id=?",
                            (title, body, category, filename, media_type, post_id))
                flash("Post updated.", "success")
                return redirect(url_for("admin"))
            flash("Title and content are required.", "error")
    return render_template("edit_post.html", post=post)

@app.route("/admin/delete/<int:post_id>", methods=["POST"])
@admin_required
def delete_post(post_id):
    with db() as con:
        post = con.execute("SELECT media FROM posts WHERE id=?", (post_id,)).fetchone()
        con.execute("DELETE FROM comments WHERE post_id=?", (post_id,))
        con.execute("DELETE FROM posts WHERE id=?", (post_id,))
    if post and post["media"]:
        try: (UPLOAD_DIR / post["media"]).unlink()
        except OSError: pass
    flash("Post deleted.", "success")
    return redirect(url_for("admin"))

@app.route("/uploads/<path:filename>")
def uploaded_file(filename):
    return send_from_directory(UPLOAD_DIR, filename)

@app.errorhandler(413)
def too_large(_):
    return "File too large. Maximum upload size is 100 MB.", 413

if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)

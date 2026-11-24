# Rajan Yadav — Personal Website

A working Flask + SQLite website with a public homepage, About page, post pages, comments, private admin login, post editing/deleting, and photo/video uploads.

## Run on a computer

1. Install Python 3.10 or newer.
2. Open a terminal in this folder.
3. Create and activate a virtual environment (optional but recommended):
   - Windows: `py -m venv .venv` then `.venv\\Scripts\\activate`
   - macOS/Linux: `python3 -m venv .venv` then `source .venv/bin/activate`
4. Install packages: `pip install -r requirements.txt`
5. Set a private secret key before public deployment:
   - Windows PowerShell: `$env:SECRET_KEY="put-a-long-random-secret-here"`
   - macOS/Linux: `export SECRET_KEY="put-a-long-random-secret-here"`
6. Start: `python app.py`
7. Open `http://127.0.0.1:5000/setup` and create your admin username/password (password must be at least 10 characters).
8. Use `/login` to manage the site. Public visitors can see posts and leave comments.

## Features

- Responsive dark editorial design
- Admin setup (available only before the first admin exists)
- Password hashing and session-based login
- Create, edit and delete posts
- Categories for shayari, love, sad, motivation, photos, videos and updates
- Upload images and videos (up to 100 MB)
- Public comments on each post
- SQLite database stored locally as `rajan_site.db`

## Before putting it on the public internet

This is a complete starter application, not a hosted live website. Deploy it to a trusted Python hosting provider with HTTPS, set a strong random `SECRET_KEY`, use the provider's persistent disk for `rajan_site.db` and `uploads/`, and run it with a production WSGI server (for example Gunicorn). Do not share your admin password. Add backups and moderation before inviting public comments. For a public production launch, configure rate limiting and stronger spam protection.

## Important

The first run creates the database automatically. Keep `rajan_site.db` and `uploads/` together with the app. Deleting the database removes the admin account, posts and comments.

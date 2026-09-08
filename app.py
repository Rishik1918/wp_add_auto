import os
import json
import sqlite3
import secrets
from functools import wraps
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, flash, Response, session
import io
import csv
import re
def extract_invite_code(url):
    match = re.search(r"chat\.whatsapp\.com/([a-zA-Z0-9_-]+)", url)
    return match.group(1) if match else ""


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
IS_VERCEL = bool(os.environ.get("VERCEL"))

if IS_VERCEL:
    import shutil
    CONFIG_FILE = "/tmp/config.json"
    DB_FILE = "/tmp/invites.db"
    orig_cfg = os.path.join(BASE_DIR, "config.json")
    if not os.path.exists(CONFIG_FILE) and os.path.exists(orig_cfg):
        shutil.copyfile(orig_cfg, CONFIG_FILE)
else:
    CONFIG_FILE = os.path.join(BASE_DIR, "config.json")
    DB_FILE = os.path.join(BASE_DIR, "invites.db")

app = Flask(__name__)
app.secret_key = secrets.token_hex(24)

def load_config():
    if not os.path.exists(CONFIG_FILE):
        default_cfg = {
            "whatsapp_group_link": "https://chat.whatsapp.com/YOUR_INVITE_CODE",
            "base_url": "http://localhost:5000",
            "admin_password": "admin"
        }
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(default_cfg, f, indent=2)
        return default_cfg
    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_config(cfg):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS invites (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT UNIQUE NOT NULL,
                assigned_to TEXT,
                is_used INTEGER DEFAULT 0,
                used_at TEXT,
                ip_address TEXT,
                created_at TEXT
            )
        """)
        conn.commit()

init_db()

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("admin_authenticated"):
            return redirect(url_for("admin_login"))
        return f(*args, **kwargs)
    return decorated_function

# PUBLIC HOME ROUTE - Shows simple safe page, NEVER the links!
@app.route("/")
def index():
    return render_template("index.html")

# PUBLIC ONE-TIME JOIN ROUTE - Users only access their own token
@app.route("/join/<token>")
def join_group(token):
    cfg = load_config()
    group_link = cfg.get("whatsapp_group_link", "").strip()
    client_ip = request.headers.get("CF-Connecting-IP") or request.headers.get("X-Forwarded-For", request.remote_addr)

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invites WHERE token = ?", (token,))
        invite = cursor.fetchone()

        if not invite:
            return render_template("invalid.html"), 404

        if invite["is_used"]:
            return render_template("expired.html", used_at=invite["used_at"]), 410

        # Mark as used atomically
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor.execute("""
            UPDATE invites 
            SET is_used = 1, used_at = ?, ip_address = ? 
            WHERE token = ? AND is_used = 0
        """, (now_str, client_ip, token))
        conn.commit()

        if cursor.rowcount == 0:
            return render_template("expired.html", used_at=now_str), 410

    code = extract_invite_code(group_link)
    deep_link = f"whatsapp://chat?code={code}" if code else group_link
    return render_template("redirect.html", group_url=group_link, deep_link=deep_link, code=code)

# ADMIN LOGIN
@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    cfg = load_config()
    actual_pw = cfg.get("admin_password", "admin")

    if request.method == "POST":
        entered_pw = request.form.get("password", "")
        if entered_pw == actual_pw:
            session["admin_authenticated"] = True
            flash("Welcome to the Admin Dashboard!")
            return redirect(url_for("admin_dashboard"))
        else:
            flash("Incorrect admin password. Please try again.")

    return render_template("login.html")

# ADMIN LOGOUT
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin_authenticated", None)
    return redirect(url_for("admin_login"))

# PROTECTED ADMIN DASHBOARD
@app.route("/admin")
@admin_required
def admin_dashboard():
    cfg = load_config()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invites ORDER BY id DESC")
        invites = cursor.fetchall()

        total = len(invites)
        used = sum(1 for inv in invites if inv["is_used"])
        active = total - used

        stats = {"total": total, "used": used, "active": active}

    return render_template("admin.html", invites=invites, stats=stats, config=cfg)

# PROTECTED CONFIG UPDATE
@app.route("/admin/config", methods=["POST"])
@admin_required
def update_config():
    cfg = load_config()
    new_group_link = request.form.get("whatsapp_group_link", "").strip()
    new_base_url = request.form.get("base_url", "").strip().rstrip("/")
    new_password = request.form.get("admin_password", "").strip()

    if new_group_link:
        cfg["whatsapp_group_link"] = new_group_link
    if new_base_url:
        cfg["base_url"] = new_base_url
    if new_password:
        cfg["admin_password"] = new_password

    save_config(cfg)
    flash("Configuration successfully saved!")
    return redirect(url_for("admin_dashboard"))

# PROTECTED LINK GENERATION
@app.route("/admin/generate", methods=["POST"])
@admin_required
def generate_links():
    names_raw = request.form.get("names_list", "").strip()
    count_raw = request.form.get("count", "").strip()

    names = [n.strip() for n in names_raw.splitlines() if n.strip()]
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    items_to_insert = []

    if names:
        for name in names:
            token = secrets.token_urlsafe(12)
            items_to_insert.append((token, name, 0, None, None, now_str))
    else:
        try:
            count = int(count_raw) if count_raw else 350
        except ValueError:
            count = 350
        count = min(max(1, count), 1000)

        for i in range(count):
            token = secrets.token_urlsafe(12)
            items_to_insert.append((token, f"Member #{i+1}", 0, None, None, now_str))

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.executemany("""
            INSERT INTO invites (token, assigned_to, is_used, used_at, ip_address, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, items_to_insert)
        conn.commit()

    flash(f"Successfully generated {len(items_to_insert)} one-time invite links!")
    return redirect(url_for("admin_dashboard"))

# PROTECTED CSV EXPORT
@app.route("/admin/export")
@admin_required
def export_csv():
    cfg = load_config()
    base_url = cfg.get("base_url", "http://localhost:5000").rstrip("/")

    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM invites ORDER BY id ASC")
        invites = cursor.fetchall()

    output = io.StringIO()
    output.write("\ufeff")
    writer = csv.writer(output)
    writer.writerow(["ID", "Assigned To", "One-Time Link", "Status", "Redeemed At", "IP Address", "Created At"])

    for inv in invites:
        full_link = f"{base_url}/join/{inv['token']}"
        status = "Used" if inv["is_used"] else "Active"
        writer.writerow([
            inv["id"],
            inv["assigned_to"] or "",
            full_link,
            status,
            inv["used_at"] or "",
            inv["ip_address"] or "",
            inv["created_at"] or ""
        ])

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=whatsapp_onetime_links.csv"}
    )

# PROTECTED DELETE LINK
@app.route("/admin/delete/<token>", methods=["POST"])
@admin_required
def delete_link(token):
    with get_db() as conn:
        conn.execute("DELETE FROM invites WHERE token = ?", (token,))
        conn.commit()
    flash("Link deleted.")
    return redirect(url_for("admin_dashboard"))

# PROTECTED CLEAR USED
@app.route("/admin/clear-used", methods=["POST"])
@admin_required
def clear_used():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM invites WHERE is_used = 1")
        deleted = cursor.rowcount
        conn.commit()
    flash(f"Cleared {deleted} used links from database.")
    return redirect(url_for("admin_dashboard"))

if __name__ == "__main__":
    print("\n=======================================================")
    print(" WhatsApp One-Time Link Gateway is starting...")
    print(" Access the Admin Dashboard at: http://localhost:5000/admin")
    print(" Default Password: admin (change in config or dashboard)")
    print("=======================================================\n")
    app.run(host="0.0.0.0", port=5000, debug=False)

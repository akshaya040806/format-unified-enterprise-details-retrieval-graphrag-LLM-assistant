"""
Veltrix Systems — SQLite User Database
Handles users, roles, sessions, registration requests, and audit logging.

Tables:
  users              — all user accounts with hashed passwords
  registration_queue — pending new employee registration requests
  audit_log          — every login/logout/action for compliance
  documents_added    — track documents added by admins to the dataset
"""

import sqlite3
import hashlib
import secrets
import os
from datetime import datetime

DB_PATH = "./veltrix.db"

# ── Password hashing ──────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    salt = "veltrix_2026_salt"
    return hashlib.sha256(f"{salt}{password}".encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def generate_secure_password(length: int = 12) -> str:
    import string
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    while True:
        pwd = "".join(secrets.choice(chars) for _ in range(length))
        if (any(c.isupper() for c in pwd) and any(c.islower() for c in pwd)
                and any(c.isdigit() for c in pwd) and any(c in "!@#$%^&*" for c in pwd)):
            return pwd

# ── Connection ────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ── Schema ────────────────────────────────────────────────────────────────────
def init_db():
    conn = get_conn()
    c = conn.cursor()

    c.executescript("""
    CREATE TABLE IF NOT EXISTS users (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        username     TEXT    UNIQUE NOT NULL,
        password     TEXT    NOT NULL,
        display_name TEXT    NOT NULL,
        title        TEXT    NOT NULL DEFAULT '',
        role         TEXT    NOT NULL,
        department   TEXT    NOT NULL,
        project      TEXT    NOT NULL DEFAULT 'All Projects',
        is_active    INTEGER DEFAULT 1,
        created_at   TEXT    DEFAULT (datetime('now')),
        last_login   TEXT
    );

    CREATE TABLE IF NOT EXISTS registration_queue (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        full_name    TEXT NOT NULL,
        email        TEXT UNIQUE NOT NULL,
        department   TEXT NOT NULL,
        project      TEXT NOT NULL,
        title        TEXT NOT NULL,
        reason       TEXT NOT NULL,
        status       TEXT DEFAULT 'pending',
        reviewed_by  TEXT,
        reviewed_at  TEXT,
        notes        TEXT,
        submitted_at TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id        INTEGER PRIMARY KEY AUTOINCREMENT,
        username  TEXT NOT NULL,
        action    TEXT NOT NULL,
        status    TEXT NOT NULL,
        details   TEXT,
        timestamp TEXT DEFAULT (datetime('now'))
    );

    CREATE TABLE IF NOT EXISTS documents_added (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        added_by     TEXT NOT NULL,
        filename     TEXT NOT NULL,
        format       TEXT NOT NULL,
        project      TEXT NOT NULL,
        description  TEXT,
        status       TEXT DEFAULT 'pending_index',
        added_at     TEXT DEFAULT (datetime('now'))
    );
    """)

    conn.commit()

    c.execute("SELECT COUNT(*) FROM users")
    if c.fetchone()[0] == 0:
        _seed_users(c)
        conn.commit()
        print(f"Database created at {DB_PATH} with default users.")

    conn.close()


def _seed_users(c):
    # Role definitions:
    # admin        — VPs and leads, full access + can add docs
    # engineering  — developers and QA, read-only LLM access
    # hr           — HR team, read-only LLM access
    # product      — PMs and designers, read-only LLM access
    # security     — security team, read-only LLM access
    # analytics    — data team, read-only LLM access
    # client       — client success, read-only LLM access
    # new_employee — just joined, onboarding access only

    users = [
        # ── Leadership / Admin (can add docs, manage users) ──
        ("robert.vp",    "Vqn1!qJxpTMg", "Robert",  "CTO",                    "admin",       "Leadership",     "All Projects"),
        ("susan.vp",     "3vE6Wu#hBdwe", "Susan",   "VP Engineering",          "admin",       "Leadership",     "All Projects"),
        ("ananya.vp",    "@wpIfA8bn!ri", "Ananya",  "VP Product",              "admin",       "Leadership",     "All Projects"),
        ("marcus.vp",    "R@hMuz^$5!nO", "Marcus",  "CFO",                     "admin",       "Leadership",     "All Projects"),
        ("priya.sharma", "d!Iq1eBnIxd%", "Priya",   "Engineering Manager",     "admin",       "Engineering",    "Project Orion"),
        ("naomi.brooks", "vIig!7&CON4!", "Naomi",   "Engineering Manager",     "admin",       "Engineering",    "Project Atlas"),
        ("sanjay.gupta", "!bL8wu&M9@!*", "Sanjay",  "Engineering Manager",     "admin",       "Engineering",    "Project Nova"),
        ("willie.scott", "V1H0@dHc7ZyC", "Willie",  "Engineering Manager",     "admin",       "Engineering",    "Project Sentinel"),
        # ── HR Team ──
        ("janice.hr",    "SrZw2iqsW7s#", "Janice",  "HR Manager",              "hr",          "Human Resources","All Projects"),
        ("lindsey.hr",   "sGUsSLQ3N4!B", "Lindsey", "Talent Acquisition Lead", "hr",          "Human Resources","All Projects"),
        # ── Client Success ──
        ("cheryl.cs",    "RUUnQ0sv&KTc", "Cheryl",  "Customer Success Lead",   "client",      "Client Success", "All Projects"),
        # ── Engineering — Project Orion ──
        ("arjun.kumar",  "FZ0hsYHNDH#t", "Arjun",   "Backend Developer",       "engineering", "Engineering",    "Project Orion"),
        ("karan.mehta",  "@RTdF@40f$VF", "Karan",   "QA Lead",                 "engineering", "Engineering",    "Project Orion"),
        ("meera.iyer",   "B4Y!*00bRsdS", "Meera",   "Frontend Developer",      "engineering", "Engineering",    "Project Orion"),
        ("rahul.das",    "Fb!G8txwrHYq", "Rahul",   "DevOps Engineer",         "engineering", "Engineering",    "Project Orion"),
        # ── Product — Project Orion ──
        ("sarah.chen",   "33Uyo3y3*1be", "Sarah",   "Product Manager",         "product",     "Product",        "Project Orion"),
        ("daniel.ko",    "x72DTx6*VrEL", "Daniel",  "Product Designer",        "product",     "Product",        "Project Orion"),
        # ── Engineering — Project Atlas ──
        ("vikram.nair",  "p**xu7cMwnqz", "Vikram",  "Backend Developer",       "engineering", "Engineering",    "Project Atlas"),
        ("felix.wagner", "8GDw&uluvgwO", "Felix",   "QA Lead",                 "engineering", "Engineering",    "Project Atlas"),
        ("olga.petrov",  "4*L!1LsKDxRa", "Olga",   "Frontend Developer",      "engineering", "Engineering",    "Project Atlas"),
        # ── Engineering/Analytics — Project Nova ──
        ("deepa.rao",    "73T!X#e%O6VV", "Deepa",   "Data Engineer",           "engineering", "Engineering",    "Project Nova"),
        ("pooja.singh",  "%ARSmwW^3swD", "Pooja",   "Frontend Developer",      "engineering", "Engineering",    "Project Nova"),
        ("ravi.kumar",   "4soP4Ax$JCND", "Ravi",    "QA Lead",                 "engineering", "Engineering",    "Project Nova"),
        ("sneha.pillai", "kKZzN2h%rKhH", "Sneha",   "Product Manager",         "product",     "Product",        "Project Nova"),
        # ── Security — Project Sentinel ──
        ("donna.james",  "v5Zn99Syu^GH", "Donna",   "Security Lead",           "security",    "Security",       "Project Sentinel"),
        ("sasha.miller", "Rjf14@hpBYWL", "Sasha",   "Compliance Officer",      "security",    "Compliance",     "Project Sentinel"),
        ("patrick.owen", "mFG7HGgbZ&VN", "Patrick", "DevOps Engineer",         "engineering", "Engineering",    "Project Sentinel"),
        # ── New Employees ──
        ("maya.thompson","gXnt6Q9!5yYP", "Maya",    "Backend Developer",       "new_employee","Engineering",    "Project Orion"),
        ("tariq.hassan", "J%vGbHYNoW3E", "Tariq",   "Frontend Developer",      "new_employee","Engineering",    "Project Atlas"),
        ("carlos.mendez","Z@m5NEt$g$bI", "Carlos",  "Data Analyst",            "new_employee","Analytics",      "Project Nova"),
        ("yuki.tanaka",  "i1i8Rxx73@XM", "Yuki",    "Security Analyst",        "new_employee","Security",       "Project Sentinel"),
        ("lior.cohen",   generate_secure_password(), "Lior", "Cloud Engineer",  "new_employee","Engineering",    "Project Phoenix"),
    ]
    c.executemany(
        "INSERT INTO users (username,password,display_name,title,role,department,project) VALUES (?,?,?,?,?,?,?)",
        [(u[0], hash_password(u[1]), u[2], u[3], u[4], u[5], u[6]) for u in users]
    )

# ── Auth ──────────────────────────────────────────────────────────────────────
def authenticate(username: str, password: str):
    conn = get_conn()
    user = conn.execute(
        "SELECT * FROM users WHERE username=? AND is_active=1",
        (username.lower().strip(),)
    ).fetchone()
    if user and verify_password(password, user["password"]):
        conn.execute(
            "UPDATE users SET last_login=? WHERE username=?",
            (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), username)
        )
        conn.execute(
            "INSERT INTO audit_log (username,action,status) VALUES (?,'LOGIN','SUCCESS')",
            (username,)
        )
        conn.commit()
        conn.close()
        return dict(user)
    conn.execute(
        "INSERT INTO audit_log (username,action,status,details) VALUES (?,'LOGIN','FAILED','Invalid credentials')",
        (username,)
    )
    conn.commit()
    conn.close()
    return None

def log_action(username: str, action: str, status: str = "SUCCESS", details: str = ""):
    conn = get_conn()
    conn.execute(
        "INSERT INTO audit_log (username,action,status,details) VALUES (?,?,?,?)",
        (username, action, status, details)
    )
    conn.commit()
    conn.close()

# ── User management ───────────────────────────────────────────────────────────
def get_all_users():
    conn  = get_conn()
    rows  = conn.execute("SELECT * FROM users ORDER BY role,username").fetchall()
    conn.close()
    return [dict(r) for r in rows]

def add_user(username, password, display_name, title, role, department, project):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO users (username,password,display_name,title,role,department,project) VALUES (?,?,?,?,?,?,?)",
            (username.lower().strip(), hash_password(password), display_name, title, role, department, project)
        )
        conn.commit()
        conn.close()
        return True, f"User '{username}' created."
    except sqlite3.IntegrityError:
        return False, f"Username '{username}' already exists."
    except Exception as e:
        return False, str(e)

def update_user(username, field, value):
    allowed = {"role", "department", "project", "title", "is_active", "display_name"}
    if field not in allowed:
        return False, "Invalid field."
    try:
        conn = get_conn()
        conn.execute(f"UPDATE users SET {field}=? WHERE username=?", (value, username))
        conn.commit()
        conn.close()
        return True, "Updated."
    except Exception as e:
        return False, str(e)

def change_password(username, new_password):
    if len(new_password) < 8:
        return False, "Password must be at least 8 characters."
    try:
        conn = get_conn()
        conn.execute("UPDATE users SET password=? WHERE username=?",
                     (hash_password(new_password), username))
        conn.commit()
        conn.close()
        return True, "Password changed."
    except Exception as e:
        return False, str(e)

# ── Registration queue ────────────────────────────────────────────────────────
def submit_registration(full_name, email, department, project, title, reason):
    try:
        conn = get_conn()
        conn.execute(
            "INSERT INTO registration_queue (full_name,email,department,project,title,reason) VALUES (?,?,?,?,?,?)",
            (full_name, email, department, project, title, reason)
        )
        conn.commit()
        conn.close()
        return True, "Registration submitted. An admin will review your request."
    except sqlite3.IntegrityError:
        return False, "This email is already registered or has a pending request."
    except Exception as e:
        return False, str(e)

def get_pending_registrations():
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM registration_queue WHERE status='pending' ORDER BY submitted_at DESC"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def approve_registration(reg_id, reviewed_by, auto_password=None):
    conn = get_conn()
    reg  = conn.execute("SELECT * FROM registration_queue WHERE id=?", (reg_id,)).fetchone()
    if not reg:
        conn.close()
        return False, "Registration not found."
    password = auto_password or generate_secure_password()
    username = reg["email"].split("@")[0].lower().replace(".", ".")
    ok, msg = add_user(username, password, reg["full_name"], reg["title"],
                       "new_employee", reg["department"], reg["project"])
    if ok:
        conn.execute(
            "UPDATE registration_queue SET status='approved',reviewed_by=?,reviewed_at=? WHERE id=?",
            (reviewed_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), reg_id)
        )
        conn.commit()
        conn.close()
        return True, {"username": username, "password": password, "message": msg}
    conn.close()
    return False, msg

def reject_registration(reg_id, reviewed_by, notes=""):
    conn = get_conn()
    conn.execute(
        "UPDATE registration_queue SET status='rejected',reviewed_by=?,reviewed_at=?,notes=? WHERE id=?",
        (reviewed_by, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), notes, reg_id)
    )
    conn.commit()
    conn.close()
    return True, "Registration rejected."

# ── Document tracking ─────────────────────────────────────────────────────────
def log_document_added(added_by, filename, fmt, project, description):
    conn = get_conn()
    conn.execute(
        "INSERT INTO documents_added (added_by,filename,format,project,description) VALUES (?,?,?,?,?)",
        (added_by, filename, fmt, project, description)
    )
    conn.commit()
    conn.close()

def get_documents_added():
    conn = get_conn()
    rows = conn.execute("SELECT * FROM documents_added ORDER BY added_at DESC").fetchall()
    conn.close()
    return [dict(r) for r in rows]

# ── Audit log ─────────────────────────────────────────────────────────────────
def get_audit_log(limit=100):
    conn = get_conn()
    rows = conn.execute(
        "SELECT * FROM audit_log ORDER BY timestamp DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_db_stats():
    conn = get_conn()
    return {
        "total_users":    conn.execute("SELECT COUNT(*) FROM users").fetchone()[0],
        "active_users":   conn.execute("SELECT COUNT(*) FROM users WHERE is_active=1").fetchone()[0],
        "pending_regs":   conn.execute("SELECT COUNT(*) FROM registration_queue WHERE status='pending'").fetchone()[0],
        "total_logins":   conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='LOGIN' AND status='SUCCESS'").fetchone()[0],
        "failed_logins":  conn.execute("SELECT COUNT(*) FROM audit_log WHERE action='LOGIN' AND status='FAILED'").fetchone()[0],
        "docs_added":     conn.execute("SELECT COUNT(*) FROM documents_added").fetchone()[0],
    }

# ── Init on import ────────────────────────────────────────────────────────────
init_db()

if __name__ == "__main__":
    stats = get_db_stats()
    print("Veltrix Database Stats:")
    for k, v in stats.items():
        print(f"  {k}: {v}")
    print("\nAll users:")
    for u in get_all_users():
        print(f"  {u['username']:20s} | {u['role']:15s} | {u['title']:30s} | {u['project']}")
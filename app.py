"""
Veltrix Systems — Internal Knowledge Assistant
Full enterprise app with:
- SQLite-backed user authentication
- Role-based access control (admin / engineering / hr / product / security / analytics / client / new_employee)
- New employee self-registration portal
- Admin document upload + dataset ingestion
- Audit logging
- GraphRAG chat interface
"""

import streamlit as st
import sys, os
from datetime import datetime

sys.path.insert(0, os.path.dirname(__file__))
from rag_engine    import index_dataset, ask, knowledge_graph
from database      import (authenticate, log_action, get_all_users, add_user,
                            update_user, change_password, get_pending_registrations,
                            approve_registration, reject_registration, submit_registration,
                            get_audit_log, get_db_stats, get_documents_added,
                            log_document_added, generate_secure_password)
from doc_ingestion import process_uploaded_file

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Veltrix · Knowledge Assistant",
    page_icon="⬡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Role definitions ──────────────────────────────────────────────────────────
ROLES = {
    "admin": {
        "label": "Administrator", "icon": "🔐", "color": "#F59E0B",
        "desc": "Full access — query LLM, upload documents, manage users",
        "can_query": True, "can_upload_docs": True, "can_manage_users": True,
        "projects": ["Project Orion","Project Atlas","Project Nova","Project Sentinel","Project Phoenix"],
        "suggested": [
            "Give me a complete status report across all active projects",
            "Which project has the highest completion percentage?",
            "Who are all the new employees across all projects?",
            "What are the critical blockers right now?",
            "List all vendors being used across projects",
            "What was the total budget approved for Project Sentinel?",
        ],
    },
    "engineering": {
        "label": "Engineering", "icon": "⚙️", "color": "#14B8A6",
        "desc": "Query LLM only — read access to engineering projects",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Orion","Project Atlas","Project Phoenix"],
        "suggested": [
            "What is the production status of Project Orion?",
            "Who is the QA lead on Project Orion?",
            "What critical bugs were found and who fixed them?",
            "Why was OmniPay chosen over SecurePay?",
            "What is the current test coverage percentage?",
            "What happened after the sandbox credentials issue was resolved?",
        ],
    },
    "hr": {
        "label": "Human Resources", "icon": "👥", "color": "#EC4899",
        "desc": "Query LLM only — people, onboarding, and team communications",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Orion","Project Atlas","Project Nova","Project Sentinel"],
        "suggested": [
            "Who are the new employees who recently joined?",
            "Who joined partway through the project and who mentored them?",
            "What was Maya Thompson's onboarding experience like?",
            "Who is Tariq Hassan's mentor on Project Atlas?",
            "Which team members are working across multiple projects?",
            "What is the team structure for Project Orion?",
        ],
    },
    "product": {
        "label": "Product", "icon": "📊", "color": "#8B5CF6",
        "desc": "Query LLM only — product and analytics projects",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Nova","Project Orion"],
        "suggested": [
            "What is Project Nova trying to achieve?",
            "How many KPIs does Project Nova track?",
            "What feedback did the Finance team give on the dashboard?",
            "What did Ananya request to be added to Project Nova?",
            "What is the data accuracy percentage for Project Nova?",
            "When is Project Nova's production rollout scheduled?",
        ],
    },
    "security": {
        "label": "Security", "icon": "🔒", "color": "#EF4444",
        "desc": "Query LLM only — security and compliance communications",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Sentinel"],
        "suggested": [
            "What critical security gaps were found in the audit?",
            "How many over-privileged accounts did Yuki reduce?",
            "What is the status of the MFA rollout?",
            "Which legacy systems were incompatible with Okta?",
            "Has the external auditor confirmed the gaps are resolved?",
            "What vendor was selected for IAM and why?",
        ],
    },
    "analytics": {
        "label": "Analytics", "icon": "📈", "color": "#06B6D4",
        "desc": "Query LLM only — data and analytics projects",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Nova"],
        "suggested": [
            "What data sources feed into Project Nova?",
            "How often does the dashboard refresh data?",
            "What was the headcount bug found in Project Nova?",
            "Who fixed the headcount connector issue?",
            "What KPIs does the executive email digest include?",
            "What is the data accuracy level for Project Nova?",
        ],
    },
    "client": {
        "label": "Client Success", "icon": "🤝", "color": "#10B981",
        "desc": "Query LLM only — client-facing communications",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Orion","Project Atlas"],
        "suggested": [
            "What did Sarah tell the client success team about Project Orion?",
            "Is the new payment system on track for the client?",
            "What is the current status of Project Atlas from a client perspective?",
            "When is the go-live date for Project Atlas?",
            "What should we tell the client about the timeline slip?",
            "What was the client's key concern about Project Orion?",
        ],
    },
    "new_employee": {
        "label": "New Employee", "icon": "👋", "color": "#22C55E",
        "desc": "Query LLM only — onboarding access to project overviews",
        "can_query": True, "can_upload_docs": False, "can_manage_users": False,
        "projects": ["Project Orion","Project Atlas","Project Nova"],
        "suggested": [
            "Give me an overview of all current projects",
            "What is my team working on right now?",
            "What tools and vendors are we using?",
            "Who should I contact for technical questions?",
            "What stage is the project at and what is my role?",
            "What are the key decisions made so far on this project?",
        ],
    },
}

PROJECTS = ["Project Orion","Project Atlas","Project Nova","Project Sentinel","Project Phoenix","All Projects"]
DEPARTMENTS = ["Engineering","Human Resources","Product","Security","Analytics","Client Success","Leadership","Compliance"]

# ── Styling ───────────────────────────────────────────────────────────────────
st.markdown("""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap');
  html,body,[class*="css"]{font-family:'Inter',sans-serif;}
  .stApp{background:#0A0F1E;}
  .block-container{padding:1rem!important;max-width:100%!important;}
  [data-testid="stSidebar"]{background:#0F172A!important;border-right:1px solid #1E293B;}

  .login-card{max-width:440px;margin:60px auto;background:#0F172A;border:1px solid #1E293B;border-radius:16px;padding:40px;}
  .login-logo{text-align:center;font-size:44px;margin-bottom:8px;}
  .login-title{text-align:center;font-size:20px;font-weight:700;color:#F1F5F9;margin-bottom:4px;}
  .login-sub{text-align:center;font-size:13px;color:#64748B;margin-bottom:28px;}

  .role-pill{display:inline-block;padding:2px 10px;border-radius:12px;font-size:11px;font-weight:600;font-family:monospace;margin:2px;}
  .proj-pill{display:inline-block;background:#1E293B;border:1px solid #334155;border-radius:10px;padding:2px 8px;font-size:11px;color:#94A3B8;margin:2px;}
  .perm-yes{color:#22C55E;font-weight:600;}
  .perm-no{color:#EF4444;}

  .main-header{background:#0F172A;border:1px solid #1E293B;border-radius:8px;padding:14px 20px;margin-bottom:16px;}
  .hdr-title{font-size:15px;font-weight:700;color:#F1F5F9;}
  .hdr-sub{font-size:11px;color:#64748B;margin-top:2px;}

  .source-card{background:#0A0F1E;border:1px solid #1E293B;border-left:3px solid #14B8A6;border-radius:6px;padding:10px 12px;margin-bottom:8px;}
  .badge{font-size:10px;font-weight:500;padding:2px 7px;border-radius:4px;font-family:monospace;display:inline-block;margin-right:4px;margin-bottom:4px;}
  .badge-platform{background:#164E63;color:#67E8F9;}
  .badge-project{background:#1E1B4B;color:#A5B4FC;}
  .badge-stage{background:#14532D;color:#86EFAC;}
  .badge-pct{background:#27272A;color:#A1A1AA;}
  .source-preview{font-size:12px;color:#64748B;line-height:1.5;font-style:italic;margin-top:6px;}

  .reg-card{background:#0F172A;border:1px solid #1E293B;border-radius:8px;padding:16px;margin-bottom:12px;}
  .audit-row{font-size:12px;font-family:monospace;padding:4px 0;border-bottom:1px solid #1E293B;color:#94A3B8;}

  .stChatMessage{background:#0F172A!important;border:1px solid #1E293B!important;border-radius:12px!important;}
  #MainMenu, footer { visibility: hidden; }
  [data-testid="collapsedControl"] { display: block !important; visibility: visible !important; } 
  .stDeployButton{display:none;}
</style>
""", unsafe_allow_html=True)

# ── Session state ─────────────────────────────────────────────────────────────
defaults = {
    "logged_in": False, "user": None, "messages": [],
    "indexed": False, "data_path": "./data/_all_conversations.json",
    "page": "chat", "show_admin": False,
}
for k, v in defaults.items():
    if k not in st.session_state:
        st.session_state[k] = v

def get_role(): return ROLES.get(st.session_state.user["role"], ROLES["new_employee"]) if st.session_state.user else {}
def logout():
    if st.session_state.user:
        log_action(st.session_state.user["username"], "LOGOUT")
    for k in defaults:
        st.session_state[k] = defaults[k]
    st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# LOGIN PAGE
# ─────────────────────────────────────────────────────────────────────────────
def page_login():
    tab_login, tab_register = st.tabs(["🔑 Sign In", "📝 Register (New Employee)"])

    with tab_login:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("""
            <div class="login-card">
              <div class="login-logo">⬡</div>
              <div class="login-title">Veltrix Knowledge Assistant</div>
              <div class="login-sub">Sign in with your company credentials</div>
            </div>""", unsafe_allow_html=True)

            with st.form("login"):
                username = st.text_input("Username", placeholder="firstname.lastname")
                password = st.text_input("Password", type="password", placeholder="Your 12-character password")
                submitted = st.form_submit_button("Sign In →", use_container_width=True)
                if submitted:
                    user = authenticate(username, password)
                    if user:
                        st.session_state.logged_in = True
                        st.session_state.user      = user
                        st.session_state.messages  = []
                        st.rerun()
                    else:
                        st.error("Invalid username or password.")

            st.markdown("---")
            st.markdown("**Role Overview**")
            for role_key, role_cfg in ROLES.items():
                c = role_cfg["color"]
                st.markdown(
                    f"<span class='role-pill' style='background:{c}22;color:{c};border:1px solid {c}44'>"
                    f"{role_cfg['icon']} {role_cfg['label']}</span> {role_cfg['desc']}",
                    unsafe_allow_html=True
                )

    with tab_register:
        c1, c2, c3 = st.columns([1,2,1])
        with c2:
            st.markdown("### 📝 New Employee Registration")
            st.info("Fill in your details below. An admin will review and approve your access within 24 hours. You will receive your login credentials by email.")

            st.markdown("**Your Access Will Be:**")
            r = ROLES["new_employee"]
            st.markdown(f"- Role: **{r['icon']} {r['label']}**")
            st.markdown(f"- Access: **{r['desc']}**")
            st.markdown(f"- Projects visible: {', '.join(r['projects'])}")
            st.markdown(f"- <span class='perm-no'>✗ Cannot upload or modify documents</span>", unsafe_allow_html=True)
            st.markdown(f"- <span class='perm-no'>✗ Cannot manage users</span>", unsafe_allow_html=True)
            st.markdown(f"- <span class='perm-yes'>✓ Can query the knowledge assistant</span>", unsafe_allow_html=True)
            st.markdown("---")

            with st.form("register"):
                full_name  = st.text_input("Full Name *", placeholder="Maya Thompson")
                email      = st.text_input("Work Email *", placeholder="maya.thompson@veltrix.com")
                title      = st.text_input("Job Title *", placeholder="Backend Developer")
                department = st.selectbox("Department *", DEPARTMENTS)
                project    = st.selectbox("Primary Project *", PROJECTS)
                reason     = st.text_area("Why do you need access? *",
                             placeholder="I joined as a Backend Developer on Project Orion on Jan 30, 2026 and need access to understand the project status, team structure, and technical decisions.")
                submitted  = st.form_submit_button("Submit Registration Request", use_container_width=True)
                if submitted:
                    if not all([full_name, email, title, reason]):
                        st.error("Please fill in all required fields.")
                    elif "@" not in email:
                        st.error("Please enter a valid email address.")
                    else:
                        ok, msg = submit_registration(full_name, email, department, project, title, reason)
                        if ok:
                            st.success(msg)
                            st.balloons()
                        else:
                            st.error(msg)

# ─────────────────────────────────────────────────────────────────────────────
# ADMIN PANEL
# ─────────────────────────────────────────────────────────────────────────────
def page_admin():
    user = st.session_state.user
    st.markdown("## 🔐 Admin Panel")

    tabs = st.tabs(["👥 Users", "📝 Registrations", "📄 Add Document", "📋 Documents Added", "📊 Stats", "🔍 Audit Log"])

    # ── Tab 1: User management ────────────────────────────────────────────────
    with tabs[0]:
        st.markdown("### All Users")
        users = get_all_users()

        search = st.text_input("Search users", placeholder="Search by name, role, or department")
        if search:
            s = search.lower()
            users = [u for u in users if s in u["username"].lower() or s in u["role"].lower()
                     or s in u["department"].lower() or s in u["display_name"].lower()]

        for u in users:
            rc = ROLES.get(u["role"], {})
            c  = rc.get("color", "#64748B")
            with st.expander(f"{rc.get('icon','👤')} {u['display_name']} — {u['username']} | {u['title']}"):
                col1, col2, col3 = st.columns(3)
                col1.markdown(f"**Role:** <span class='role-pill' style='background:{c}22;color:{c};border:1px solid {c}44'>{u['role']}</span>", unsafe_allow_html=True)
                col2.markdown(f"**Department:** {u['department']}")
                col3.markdown(f"**Project:** {u['project']}")
                col1.markdown(f"**Status:** {'🟢 Active' if u['is_active'] else '🔴 Inactive'}")
                col2.markdown(f"**Last login:** {u['last_login'] or 'Never'}")
                col3.markdown(f"**Created:** {u['created_at'][:10] if u['created_at'] else '-'}")

                st.markdown("**Permissions:**")
                perms = ROLES.get(u["role"], {})
                pc1, pc2, pc3 = st.columns(3)
                pc1.markdown(f"<span class='{'perm-yes' if perms.get('can_query') else 'perm-no'}'>{'✓' if perms.get('can_query') else '✗'} Query LLM</span>", unsafe_allow_html=True)
                pc2.markdown(f"<span class='{'perm-yes' if perms.get('can_upload_docs') else 'perm-no'}'>{'✓' if perms.get('can_upload_docs') else '✗'} Upload Docs</span>", unsafe_allow_html=True)
                pc3.markdown(f"<span class='{'perm-yes' if perms.get('can_manage_users') else 'perm-no'}'>{'✓' if perms.get('can_manage_users') else '✗'} Manage Users</span>", unsafe_allow_html=True)

                st.markdown("---")
                ac1, ac2, ac3, ac4 = st.columns(4)
                new_role = ac1.selectbox("Change role", list(ROLES.keys()),
                            index=list(ROLES.keys()).index(u["role"]) if u["role"] in ROLES else 0,
                            key=f"role_{u['username']}")
                if ac2.button("Update Role", key=f"updrole_{u['username']}"):
                    ok, msg = update_user(u["username"], "role", new_role)
                    log_action(user["username"], f"ROLE_CHANGE:{u['username']}", details=f"→{new_role}")
                    st.success(msg) if ok else st.error(msg)
                    st.rerun()

                new_pwd = ac3.text_input("New password", type="password", key=f"pwd_{u['username']}")
                if ac4.button("Reset Password", key=f"resetpwd_{u['username']}"):
                    if new_pwd:
                        ok, msg = change_password(u["username"], new_pwd)
                        log_action(user["username"], f"PASSWORD_RESET:{u['username']}")
                        st.success(msg) if ok else st.error(msg)
                    else:
                        st.warning("Enter a new password first.")

                da1, da2 = st.columns(2)
                if u["is_active"] and u["username"] != "admin":
                    if da1.button("🔴 Deactivate", key=f"deact_{u['username']}"):
                        update_user(u["username"], "is_active", 0)
                        log_action(user["username"], f"DEACTIVATE:{u['username']}")
                        st.rerun()
                elif not u["is_active"]:
                    if da2.button("🟢 Reactivate", key=f"react_{u['username']}"):
                        update_user(u["username"], "is_active", 1)
                        log_action(user["username"], f"REACTIVATE:{u['username']}")
                        st.rerun()

        st.markdown("---")
        st.markdown("### ➕ Add New User Manually")
        with st.form("add_user"):
            fc1, fc2 = st.columns(2)
            new_username = fc1.text_input("Username *", placeholder="firstname.lastname")
            new_name     = fc2.text_input("Display Name *", placeholder="First Last")
            new_title    = fc1.text_input("Job Title *", placeholder="Software Engineer")
            new_role     = fc2.selectbox("Role *", list(ROLES.keys()))
            new_dept     = fc1.selectbox("Department *", DEPARTMENTS)
            new_proj     = fc2.selectbox("Project *", PROJECTS)
            auto_pwd     = generate_secure_password()
            st.markdown(f"**Auto-generated password:** `{auto_pwd}`")
            custom_pwd   = st.text_input("Or enter custom password (min 8 chars)", type="password")
            if st.form_submit_button("Create User", use_container_width=True):
                pwd_to_use = custom_pwd if custom_pwd else auto_pwd
                ok, msg    = add_user(new_username, pwd_to_use, new_name, new_title, new_role, new_dept, new_proj)
                if ok:
                    log_action(user["username"], f"CREATE_USER:{new_username}")
                    st.success(f"{msg} | Password: `{pwd_to_use}`")
                else:
                    st.error(msg)

    # ── Tab 2: Registration requests ──────────────────────────────────────────
    with tabs[1]:
        st.markdown("### Pending Registration Requests")
        pending = get_pending_registrations()

        if not pending:
            st.info("No pending registration requests.")
        else:
            st.markdown(f"**{len(pending)} request(s) awaiting review**")
            for req in pending:
                with st.expander(f"📝 {req['full_name']} — {req['title']} | {req['department']} | {req['submitted_at'][:10]}"):
                    rc1, rc2 = st.columns(2)
                    rc1.markdown(f"**Name:** {req['full_name']}")
                    rc2.markdown(f"**Email:** {req['email']}")
                    rc1.markdown(f"**Title:** {req['title']}")
                    rc2.markdown(f"**Department:** {req['department']}")
                    rc1.markdown(f"**Project:** {req['project']}")
                    rc2.markdown(f"**Submitted:** {req['submitted_at'][:16]}")
                    st.markdown(f"**Reason for access:**\n> {req['reason']}")
                    st.markdown("---")
                    ac1, ac2, ac3 = st.columns(3)
                    if ac1.button("✅ Approve", key=f"approve_{req['id']}"):
                        ok, result = approve_registration(req["id"], user["username"])
                        if ok:
                            log_action(user["username"], f"APPROVE_REG:{req['email']}")
                            # ── Digital Access Pass ───────────────────────
                            st.markdown(f"""
<div style="
  background: linear-gradient(135deg, #0F2027, #203A43, #2C5364);
  border: 2px solid #14B8A6;
  border-radius: 16px;
  padding: 28px 32px;
  margin: 16px 0;
  font-family: 'Inter', sans-serif;
  position: relative;
  overflow: hidden;
">
  <!-- watermark -->
  <div style="position:absolute;top:10px;right:20px;font-size:64px;opacity:0.05;font-weight:900;color:white">⬡</div>

  <!-- header -->
  <div style="display:flex;align-items:center;gap:12px;margin-bottom:20px;border-bottom:1px solid #1E3A4A;padding-bottom:14px">
    <div style="background:linear-gradient(135deg,#14B8A6,#0EA5E9);border-radius:8px;width:40px;height:40px;display:flex;align-items:center;justify-content:center;font-size:20px">⬡</div>
    <div>
      <div style="font-size:13px;font-weight:700;color:#F1F5F9;letter-spacing:0.05em">VELTRIX SYSTEMS</div>
      <div style="font-size:10px;color:#64748B;letter-spacing:0.12em;text-transform:uppercase">Knowledge Assistant — Access Pass</div>
    </div>
    <div style="margin-left:auto;background:#22C55E22;border:1px solid #22C55E44;border-radius:8px;padding:4px 12px">
      <span style="color:#22C55E;font-size:11px;font-weight:600">✓ APPROVED</span>
    </div>
  </div>

  <!-- employee details -->
  <div style="margin-bottom:20px">
    <div style="font-size:18px;font-weight:700;color:#F1F5F9;margin-bottom:2px">{req['full_name']}</div>
    <div style="font-size:13px;color:#94A3B8">{req['title']} &nbsp;·&nbsp; {req['department']} &nbsp;·&nbsp; {req['project']}</div>
  </div>

  <!-- credential grid -->
  <div style="display:grid;grid-template-columns:1fr 1fr;gap:12px;margin-bottom:20px">
    <div style="background:#0A0F1E99;border:1px solid #1E293B;border-radius:8px;padding:12px 16px">
      <div style="font-size:10px;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Username</div>
      <div style="font-size:14px;font-weight:600;color:#14B8A6;font-family:monospace">{result['username']}</div>
    </div>
    <div style="background:#0A0F1E99;border:1px solid #1E293B;border-radius:8px;padding:12px 16px">
      <div style="font-size:10px;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Password (change on first login)</div>
      <div style="font-size:14px;font-weight:600;color:#F59E0B;font-family:monospace;letter-spacing:0.05em">{result['password']}</div>
    </div>
    <div style="background:#0A0F1E99;border:1px solid #1E293B;border-radius:8px;padding:12px 16px">
      <div style="font-size:10px;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Role</div>
      <div style="font-size:13px;font-weight:600;color:#22C55E">👋 New Employee</div>
    </div>
    <div style="background:#0A0F1E99;border:1px solid #1E293B;border-radius:8px;padding:12px 16px">
      <div style="font-size:10px;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:4px">Access URL</div>
      <div style="font-size:13px;font-weight:600;color:#94A3B8;font-family:monospace">localhost:8501</div>
    </div>
  </div>

  <!-- permissions -->
  <div style="background:#0A0F1E99;border:1px solid #1E293B;border-radius:8px;padding:12px 16px;margin-bottom:16px">
    <div style="font-size:10px;color:#64748B;letter-spacing:0.08em;text-transform:uppercase;margin-bottom:8px">Access Permissions</div>
    <div style="display:flex;gap:20px;flex-wrap:wrap">
      <span style="font-size:12px;color:#22C55E">✓ Query Knowledge Base</span>
      <span style="font-size:12px;color:#EF4444">✗ Upload Documents</span>
      <span style="font-size:12px;color:#EF4444">✗ Modify Dataset</span>
      <span style="font-size:12px;color:#EF4444">✗ Manage Users</span>
    </div>
  </div>

  <!-- footer -->
  <div style="display:flex;justify-content:space-between;align-items:center">
    <div style="font-size:10px;color:#475569">Approved by: <strong style="color:#94A3B8">{user['display_name']}</strong> &nbsp;·&nbsp; {datetime.now().strftime('%b %d, %Y %H:%M')}</div>
    <div style="font-size:10px;color:#475569;font-family:monospace">ID: {result['username'].upper()[:8]}</div>
  </div>
</div>
""", unsafe_allow_html=True)
                            st.caption("📋 Take a screenshot of this pass and share it securely with the new employee.")
                        else:
                            st.error(result)

                    reject_note = ac2.text_input("Rejection reason", key=f"rej_note_{req['id']}")
                    if ac3.button("❌ Reject", key=f"reject_{req['id']}"):
                        reject_registration(req["id"], user["username"], reject_note)
                        log_action(user["username"], f"REJECT_REG:{req['email']}", details=reject_note)
                        st.warning("Registration rejected.")
                        st.rerun()

    # ── Tab 3: Add document ───────────────────────────────────────────────────
    with tabs[2]:
        st.markdown("### 📄 Add Document to Knowledge Base")
        st.info("Upload a document and it will be converted to JSON and added to the RAG dataset. The system will need to re-index after adding documents.")

        st.markdown("**Supported formats:** PDF, DOCX, TXT, CSV, XLSX, MP3, WAV, MP4")
        st.markdown("**Security:** Only admins can add documents. All uploads are logged. New employees cannot modify the knowledge base.")

        with st.form("upload_doc"):
            uploaded = st.file_uploader(
                "Choose a file",
                type=["pdf","docx","txt","csv","xlsx","mp3","wav","mp4","mov"],
            )
            doc_project = st.selectbox("Which project is this document for?", PROJECTS)
            doc_desc    = st.text_area("Document description *",
                          placeholder="E.g.: Weekly status report for Project Orion, week of Feb 17 2026")
            submitted   = st.form_submit_button("Upload and Add to Dataset", use_container_width=True)

            if submitted and uploaded:
                if not doc_desc.strip():
                    st.error("Please provide a description.")
                else:
                    with st.spinner(f"Processing {uploaded.name}…"):
                        result = process_uploaded_file(
                            file_bytes  = uploaded.getvalue(),
                            filename    = uploaded.name,
                            project     = doc_project,
                            description = doc_desc,
                            added_by    = user["username"],
                        )

                    if result["success"]:
                        log_document_added(user["username"], uploaded.name,
                                           result["format"], doc_project, doc_desc)
                        log_action(user["username"], f"UPLOAD_DOC:{uploaded.name}", details=doc_project)
                        st.success(f"✅ {result['message']}")
                        st.markdown(f"""
                        - **File:** {result['filename']}
                        - **Format:** {result['format'].upper()}
                        - **Words extracted:** {result['word_count']:,}
                        - **Message chunks created:** {result['chunks_added']}
                        - **Document ID:** `{result['doc_id']}`
                        """)
                        if result.get("needs_reindex"):
                            st.warning("⚠️ The RAG index needs to be refreshed to include this document. Go to Settings and click Re-index.")
                    else:
                        st.error(f"❌ {result['message']}")

    # ── Tab 4: Documents added ────────────────────────────────────────────────
    with tabs[3]:
        st.markdown("### Documents Added to Knowledge Base")
        docs = get_documents_added()
        if not docs:
            st.info("No documents have been added yet.")
        else:
            for doc in docs:
                st.markdown(f"""
                <div class="reg-card">
                  <strong>{doc['filename']}</strong>
                  <span class="badge badge-platform">{doc['format'].upper()}</span>
                  <span class="badge badge-project">{doc['project']}</span><br>
                  <small style="color:#64748B">Added by <strong>{doc['added_by']}</strong> on {doc['added_at'][:16]}</small><br>
                  <small style="color:#94A3B8">{doc['description']}</small>
                </div>
                """, unsafe_allow_html=True)

    # ── Tab 5: Stats ──────────────────────────────────────────────────────────
    with tabs[4]:
        st.markdown("### System Statistics")
        stats = get_db_stats()
        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("Total Users",    stats["total_users"])
        c2.metric("Active Users",   stats["active_users"])
        c3.metric("Pending Regs",   stats["pending_regs"])
        c4.metric("Total Logins",   stats["total_logins"])
        c5.metric("Failed Logins",  stats["failed_logins"])
        c6.metric("Docs Added",     stats["docs_added"])

        st.markdown("### RAG Index")
        try:
            from rag_engine import child_col, parent_col
            ic1,ic2,ic3,ic4 = st.columns(4)
            ic1.metric("Child Chunks",  child_col.count())
            ic2.metric("Parent Chunks", parent_col.count())
            ic3.metric("Graph Nodes",   knowledge_graph.number_of_nodes())
            ic4.metric("Graph Edges",   knowledge_graph.number_of_edges())
        except Exception as e:
            st.warning(f"Index stats unavailable: {e}")

        st.markdown("### Users by Role")
        all_users = get_all_users()
        from collections import Counter
        role_counts = Counter(u["role"] for u in all_users if u["is_active"])
        for role_key, count in sorted(role_counts.items()):
            rc = ROLES.get(role_key, {})
            st.markdown(f"{rc.get('icon','👤')} **{rc.get('label', role_key)}**: {count}")

        st.markdown("---")
        st.markdown("### Settings")
        data_path_input = st.text_input("Dataset path", value=st.session_state.data_path)
        if data_path_input != st.session_state.data_path:
            st.session_state.data_path = data_path_input
            st.session_state.indexed   = False

        if st.button("🔄 Re-index Dataset (picks up new documents)", use_container_width=True):
            log_action(user["username"], "REINDEX_DATASET")
            try:
                # Live re-index via the ChromaDB server (no restart needed)
                from rag_engine import reindex_live
                with st.spinner("Re-indexing live — this takes 1-2 minutes..."):
                    reindex_live(st.session_state.data_path)
                st.success("Live re-index complete! New documents are now searchable.")
                st.rerun()
            except Exception as e:
                # Fallback: server not running, show restart instructions
                st.warning(
                    "Live re-index unavailable (ChromaDB server not running). To re-index:\n\n"
                    "1. Stop the app (Ctrl+C)\n"
                    "2. Run: Remove-Item -Recurse -Force chroma_store\n"
                    "3. Restart: streamlit run app.py\n\n"
                    f"(Details: {e})"
                )

    # ── Tab 6: Audit log ──────────────────────────────────────────────────────
    with tabs[5]:
        st.markdown("### Audit Log (Last 100 actions)")
        logs = get_audit_log(100)
        for entry in logs:
            color = "#22C55E" if entry["status"] == "SUCCESS" else "#EF4444"
            st.markdown(
                f"<div class='audit-row'>"
                f"<span style='color:{color}'>[{entry['status']}]</span> "
                f"<strong>{entry['username']}</strong> — {entry['action']} "
                f"<span style='color:#475569'>{entry['timestamp']}</span>"
                f"{'  |  ' + entry['details'] if entry.get('details') else ''}"
                f"</div>",
                unsafe_allow_html=True
            )

# Force sidebar to always be expanded on load
st.session_state["sidebar_state"] = "expanded"

# ─────────────────────────────────────────────────────────────────────────────
# MAIN CHAT PAGE
# ─────────────────────────────────────────────────────────────────────────────
def page_chat():
    user     = st.session_state.user
    role_cfg = get_role()
    color    = role_cfg["color"]

    # Index dataset
    if not st.session_state.indexed:
        with st.spinner("Loading project communications…"):
            index_dataset(st.session_state.data_path)
            st.session_state.indexed = True

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown(f"""
        <div style="padding:12px;background:#1E293B;border-radius:8px;margin-bottom:12px">
          <div style="font-size:13px;font-weight:700;color:#F1F5F9">{user['display_name']}</div>
          <div style="font-size:11px;color:#94A3B8;margin-top:2px">{user['title']}</div>
          <div style="margin-top:6px">
            <span class="role-pill" style="background:{color}22;color:{color};border:1px solid {color}44">
              {role_cfg['icon']} {role_cfg['label']}
            </span>
          </div>
        </div>""", unsafe_allow_html=True)

        st.markdown("**Project access:**")
        st.markdown(" ".join([f"<span class='proj-pill'>{p}</span>" for p in role_cfg["projects"]]),
                    unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("**Permissions**")
        perms = [
            ("Query Knowledge Base",   role_cfg.get("can_query",        False)),
            ("Upload Documents",       role_cfg.get("can_upload_docs",  False)),
            ("Manage Users",           role_cfg.get("can_manage_users", False)),
        ]
        for perm, allowed in perms:
            icon = "✓" if allowed else "✗"
            cls  = "perm-yes" if allowed else "perm-no"
            st.markdown(f"<span class='{cls}'>{icon} {perm}</span>", unsafe_allow_html=True)

        st.markdown("---")
        if user["role"] == "admin":
            if st.button("🔐 Admin Panel", use_container_width=True):
                st.session_state.page = "admin"
                st.rerun()
        if st.button("🗑 Clear conversation", use_container_width=True):
            st.session_state.messages = []
            st.rerun()
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="main-header" style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <div class="hdr-title">⬡ Project Knowledge Assistant</div>
        <div class="hdr-sub">Ask anything about ongoing projects, team members, decisions, and timelines</div>
      </div>
      <div style="text-align:right">
        <span class="role-pill" style="background:{color}22;color:{color};border:1px solid {color}44">
          {role_cfg['icon']} {role_cfg['label']}
        </span>
        <div style="font-size:11px;color:#475569;margin-top:4px">{datetime.now().strftime('%b %d, %Y')}</div>
      </div>
    </div>""", unsafe_allow_html=True)

    # ── Layout ────────────────────────────────────────────────────────────────
    chat_col, src_col = st.columns([3, 2], gap="medium")

    with chat_col:
        if not st.session_state.messages:
            if user["role"] == "new_employee":
                st.markdown(f"### 👋 Welcome to Veltrix Systems, {user['display_name'].split()[0]}!")
                st.markdown("I'm your onboarding assistant. Ask me anything about the projects, your team, tools used, or key decisions made. I'll help you get up to speed without taking up your team lead's time.")
            else:
                st.markdown(f"### {role_cfg['icon']} {role_cfg['label']} Knowledge Base")
                st.markdown(f"Welcome back, **{user['display_name']}**.")

            st.markdown("**Suggested questions for your role:**")
            cols = st.columns(2)
            for i, q in enumerate(role_cfg["suggested"][:6]):
                with cols[i % 2]:
                    if st.button(q, key=f"sug_{i}", use_container_width=True):
                        st.session_state.messages.append({"role": "user", "content": q})
                        st.rerun()

        for msg in st.session_state.messages:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    answer = msg.get("content", "")
                    if answer:
                        st.markdown(answer)
                    else:
                        st.warning("No answer generated.")
                    conf = msg.get("confidence", 0)
                    icon = "🟢" if conf > 0.7 else "🟡" if conf > 0.4 else "🔴"
                    st.progress(conf, text=f"{icon} Confidence: {int(conf*100)}%")

        user_input = st.chat_input(f"Ask about {', '.join(role_cfg['projects'][:2])}…")

        # Process the question immediately so the answer shows on rerun
        if user_input and user_input.strip():
            _q = user_input.strip()
            st.session_state.messages.append({"role": "user", "content": _q})
            _ctx = " OR ".join(role_cfg["projects"])
            _aug = f"{_q} [context: {_ctx}]" if user["role"] != "admin" else _q
            with st.spinner("Searching project communications..."):
                _result = ask(_aug)
            log_action(user["username"], "QUERY", details=_q[:100])
            st.session_state.messages.append({
                "role": "assistant", "content": _result["answer"],
                "sources": _result["sources"], "confidence": _result["confidence"],
                "graph_entities": _result["graph_entities"],
            })
            st.rerun()

    with src_col:
        st.markdown("#### 📎 Source Attribution")
        st.caption("Every answer is traceable to real team communications")

        last_bot = next(
            (m for m in reversed(st.session_state.messages) if m["role"] == "assistant" and "sources" in m),
            None
        )
        if last_bot and last_bot.get("sources"):
            entities = last_bot.get("graph_entities", [])
            if entities:
                st.markdown("**Detected entities**")
                st.markdown(" ".join([f"`{e['entity']}`" for e in entities[:10]]))
            st.markdown("**Retrieved sources**")
            for src in last_bot["sources"]:
                platform = src.get("platform","").upper()
                project  = src.get("project","")
                stage    = src.get("stage","")[:35]
                pct      = src.get("completion","")
                score    = src.get("score",0)
                preview  = src.get("text_preview","")[:180]
                st.markdown(f"""
<div class="source-card">
  <div>
    <span class="badge badge-platform">{platform}</span>
    <span class="badge badge-project">{project}</span>
    <span class="badge badge-stage">{stage}{'…' if len(src.get('stage',''))>35 else ''}</span>
    <span class="badge badge-pct">{pct}%</span>
    <span style="font-size:10px;color:#475569;font-family:monospace">RRF {score:.3f}</span>
  </div>
  <div class="source-preview">"{preview}{'...' if len(src.get('text_preview',''))>180 else ''}"</div>
</div>""", unsafe_allow_html=True)
        else:
            st.markdown("""
            <div style="text-align:center;padding:40px 16px">
              <div style="font-size:32px;margin-bottom:12px">🕸</div>
              <div style="font-size:13px;color:#64748B;line-height:1.6">
                Ask a question and every answer will show exactly which
                conversation, document, or meeting it came from.
              </div>
            </div>""", unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────────────────────────
# ROUTER
# ─────────────────────────────────────────────────────────────────────────────
if not st.session_state.logged_in:
    page_login()
elif st.session_state.page == "admin":
    # Back button in sidebar
    with st.sidebar:
        st.markdown(f"### ⬡ Veltrix Systems")
        if st.button("← Back to Chat", use_container_width=True):
            st.session_state.page = "chat"
            st.rerun()
        if st.button("🚪 Sign Out", use_container_width=True):
            logout()
    page_admin()
else:
    page_chat()

 
from flask import Flask, render_template, request, jsonify, send_from_directory, session
from flask import request, redirect, url_for
from flask import make_response
from datetime import datetime
import os
import sys
import sqlite3

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUB_APP_DIR = os.path.join(BASE_DIR, 'ld-metrics-translator')
TEMPLATES_DIR = os.path.join(SUB_APP_DIR, 'templates')
STATIC_DIR = os.path.join(SUB_APP_DIR, 'static')

# Point Flask to the sub-app's templates and static assets to ensure we serve the latest UI
app = Flask(__name__, static_folder=str(STATIC_DIR), template_folder=str(TEMPLATES_DIR))
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret-key")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # disable static caching in dev
# Allow both '/path' and '/path/' variants everywhere in this dev server
try:
    app.url_map.strict_slashes = False
except Exception:
    pass
try:
    app.jinja_env.auto_reload = True
except Exception:
    pass

# In dev/debug, force no-cache headers so the browser always fetches fresh assets
@app.after_request
def add_no_cache_headers(resp):
    try:
        if app.debug:
            ct = resp.headers.get('Content-Type', '')
            if any(t in ct for t in ('text/html', 'application/javascript', 'text/javascript', 'text/css')):
                resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
                resp.headers['Pragma'] = 'no-cache'
                resp.headers['Expires'] = '0'
    except Exception:
        pass
    return resp
MOCKS_ENABLED = os.environ.get("USE_MOCKS", "true").lower() == "true"
CONTEXT_STATE_UPSTREAM = os.environ.get("CONTEXT_STATE_UPSTREAM", "").strip()
CONTEXT_SYSTEM_UPSTREAM = os.environ.get("CONTEXT_SYSTEM_UPSTREAM", "").strip()
CONTEXT_METRICS_SELECT_UPSTREAM = os.environ.get("CONTEXT_METRICS_SELECT_UPSTREAM", "").strip()
CONTEXT_METRICS_DESELECT_UPSTREAM = os.environ.get("CONTEXT_METRICS_DESELECT_UPSTREAM", "").strip()
CONTEXT_FRAMEWORK_COMPETENCIES_UPSTREAM = os.environ.get("CONTEXT_FRAMEWORK_COMPETENCIES_UPSTREAM", "").strip()
FRAMEWORKS_TREE_UPSTREAM = os.environ.get("FRAMEWORKS_TREE_UPSTREAM", "").strip()
FRAMEWORKS_LIST_UPSTREAM = os.environ.get("FRAMEWORKS_LIST_UPSTREAM", "").strip()
SMART_RECS_GENERATE_UPSTREAM = os.environ.get("SMART_RECS_GENERATE_UPSTREAM", "").strip()
SMART_RECS_INTERACT_UPSTREAM = os.environ.get("SMART_RECS_INTERACT_UPSTREAM", "").strip()
DYNAMIC_REPORTS_START_UPSTREAM = os.environ.get("DYNAMIC_REPORTS_START_UPSTREAM", "").strip()
DYNAMIC_REPORTS_STATUS_UPSTREAM = os.environ.get("DYNAMIC_REPORTS_STATUS_UPSTREAM", "").strip()

# Try to import the real backend app (database-backed) from the sub-app folder
BACKEND_AVAILABLE = False
backend_app = None
backend_db = None
backend_models = None
try:
    # Ensure the sub-app directory is importable as a package root
    if SUB_APP_DIR not in sys.path:
        sys.path.insert(0, SUB_APP_DIR)
    from app import create_app as create_backend_app  # type: ignore
    from app import db as _backend_db  # type: ignore
    from app import models as _backend_models  # type: ignore
    backend_app = create_backend_app('default')
    backend_db = _backend_db
    backend_models = _backend_models
    BACKEND_AVAILABLE = True
except Exception as _e:
    # Stay in mock mode only; expose a debug endpoint to confirm
    BACKEND_AVAILABLE = False

def _require_mocks():
    if not MOCKS_ENABLED:
        return jsonify({"error": "mocks disabled"}), 404
    return None

@app.context_processor
def inject_flags():
    try:
        is_debug = app.debug
    except Exception:
        is_debug = False
    prod_parity = (not MOCKS_ENABLED) and (not is_debug)
    # Derive auth flags (best-effort in dev)
    is_authenticated = False
    is_admin = False
    try:
        uid = session.get('user_id') or session.get('admin_user_id')
        if uid and BACKEND_AVAILABLE and backend_models is not None and backend_app is not None:
            with backend_app.app_context():
                AdminUser = getattr(backend_models, 'AdminUser', None)
                if AdminUser is not None:
                    u = AdminUser.query.get(int(uid))
                    if u and getattr(u, 'is_active', True):
                        is_authenticated = True
                        is_admin = bool(getattr(u, 'is_admin', False)) or (str(getattr(u, 'role', '')).lower() == 'admin') or (str(getattr(u, 'username', '')).lower() == 'admin')
        else:
            # Dev/session-only heuristic: allow toggling via session keys
            is_authenticated = bool(uid)
            is_admin = bool(session.get('is_admin'))
    except Exception:
        pass
    # Expose feature and auth flags for UI
    return {
        "mocks_enabled": MOCKS_ENABLED,
        "prod_parity": prod_parity,
        "DRIVER_CARDS_V1": True,
        "UI_TABS_V2": True,
        "WORKFLOW_STRIP": False,
        "is_authenticated": is_authenticated,
        "is_admin": is_admin,
    }

# In debug/dev, disable HTTP caching so latest JS/CSS is always served
@app.after_request
def add_no_cache_headers(response):
    try:
        if app.debug:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
    except Exception:
        pass
    return response


# Ensure csrf_token is defined for templates used by the dev server
@app.context_processor
def inject_csrf_token():
    try:
        # Prefer a real token if Flask-WTF is installed
        from flask_wtf.csrf import generate_csrf  # type: ignore
        def _csrf_token():
            try:
                return generate_csrf()
            except Exception:
                return ""
        return {"csrf_token": _csrf_token}
    except Exception:
        # Fallback: provide an empty callable to avoid Jinja errors in dev/demo
        return {"csrf_token": (lambda: "")}


# --------- Page Routes ---------
@app.route("/")
def dashboard():
    return render_template("index.html")


@app.route("/diagnostics")
def diagnostics():
    return render_template("diagnostics.html")


@app.route("/plan-builder")
def plan_builder():
    return render_template("plan_builder.html")


@app.route("/playbook")
def playbook():
    return render_template("playbook.html")

# Role Architect and Reports (dev server routes)
@app.route("/roles")
def roles():
    return render_template("roles_list.html")


@app.route("/roles/new")
def role_new():
    return render_template("role_wizard.html")


@app.route("/reports")
def reports():
    # Use the v2 template that includes the external reports-list.js loader
    return render_template("reports_v2.html")


@app.route("/reports/compare")
def reports_compare():
    return render_template("reports_compare.html")


# ---------------- Dev Admin fallbacks (login/logout) ----------------
@app.route('/admin/login', methods=['GET', 'POST'])
def dev_admin_login():
    """Provide a simple admin login fallback in the dev server.

    - GET renders a minimal HTML login form (not Flask-WTF) to avoid template/form dependencies.
    - POST sets session flags and redirects to Role Architect.
    """
    # Always provide a simple, dependency-free login page in the dev server
    # to avoid redirect loops regardless of BACKEND_AVAILABLE.
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip() or 'admin'
        # Mark session as admin
        session['admin_user_id'] = 1
        session['admin_username'] = username
        session['is_admin'] = True
        # After login, take admins directly to Role Architect under admin path
        return redirect('/admin/roles')
    return """
        <!doctype html>
        <html><head><meta charset='utf-8'><title>Admin Login</title>
        <style>body{font-family:system-ui,Arial;margin:2rem}label{display:block;margin:.5rem 0}</style>
        </head><body>
        <h1>Admin Login (Dev)</h1>
        <form method="post">
          <label>Username <input name="username" placeholder="admin" /></label>
          <label>Password <input name="password" type="password" placeholder="••••••" /></label>
          <button type="submit">Login</button>
        </form>
        <p style="margin-top:1rem;color:#555">This is a lightweight dev-only login. In production, use the Admin login page.</p>
        </body></html>
        """


@app.route('/login')
def dev_login_alias():
    """Convenience alias to the admin login in dev server."""
    return redirect('/admin/login')


@app.route('/admin/')
def dev_admin_root():
    """Provide a landing route for /admin/ in the dev server.

    Redirect signed-in admins to the admin roles list; otherwise send users to the
    lightweight dev login form. This avoids a 404 when hitting /admin/ directly.
    """
    if session.get('admin_user_id') or session.get('is_admin'):
        return redirect('/admin/roles')
    return redirect('/admin/login')


@app.route('/admin/logout')
def dev_admin_logout():
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    session.pop('is_admin', None)
    return redirect('/')


# ---------------- Dev Auth status fallback ----------------
@app.route('/api/auth_status', methods=['GET'])
def dev_auth_status():
    """Return auth status based on session (dev fallback)."""
    try:
        is_authenticated = session.get('admin_user_id') is not None
        username = session.get('admin_username')
        return jsonify({'success': True, 'authenticated': is_authenticated, 'username': username})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


# ---------------- Dev Admin Role Architect routes ----------------
@app.route('/admin/roles')
def dev_admin_roles_list():
    # Render the same template as public roles, but under the admin path
    return render_template('roles_list.html', is_admin=True)


@app.route('/admin/roles/new')
def dev_admin_roles_new():
    return render_template('role_wizard.html', is_admin=True)

# Trailing-slash variants to avoid 404 when a slash is present
@app.route('/admin/roles/', methods=['GET'])
def dev_admin_roles_list_slash():
    return dev_admin_roles_list()

@app.route('/admin/roles/new/', methods=['GET'])
def dev_admin_roles_new_slash():
    return dev_admin_roles_new()


# ---------------- Public Role Architect (dev) with admin auto-redirect ----------------
@app.route('/roles')
def dev_public_roles():
    # If logged in as admin in this dev server, redirect to admin list
    if session.get('is_admin') or session.get('admin_user_id'):
        saved = request.args.get('saved')
        target = '/admin/roles'
        if saved:
            target += f'?saved={saved}'
        return redirect(target)
    return render_template('roles_list.html', is_admin=False)


@app.route('/roles/new')
def dev_public_roles_new():
    if session.get('is_admin') or session.get('admin_user_id'):
        return redirect('/admin/roles/new')
    return render_template('role_wizard.html', is_admin=False)


# ---------------- Public debug: list key routes ----------------
@app.route('/api/routes_summary', methods=['GET'])
def dev_routes_summary():
    try:
        subset_prefixes = ('/api/roles', '/api/auth_status', '/api/health', '/admin')
        routes = []
        for rule in app.url_map.iter_rules():
            rule_str = str(rule)
            if any(rule_str.startswith(p) for p in subset_prefixes):
                methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
                routes.append({'rule': rule_str, 'endpoint': rule.endpoint, 'methods': methods})
        routes = sorted(routes, key=lambda r: r['rule'])
        return jsonify({'routes': routes, 'count': len(routes)})
    except Exception as e:
        return jsonify({'error': 'Failed to summarize routes', 'details': str(e)}), 500

# Dev alias to hard-bust any cached HTML under a fresh URL
@app.route("/reports2")
def reports2():
    return render_template("reports_v2.html")

@app.route("/report/<int:report_id>")
def report_view(report_id: int):
    """Single report view page (dev)."""
    return render_template("report_view.html", report_id=report_id)

# Alias endpoints to match blueprint-style names used in templates (main.*)
app.add_url_rule('/', endpoint='main.index', view_func=dashboard)
app.add_url_rule('/', endpoint='main.dashboard', view_func=dashboard)
app.add_url_rule('/diagnostics', endpoint='main.diagnostics', view_func=diagnostics)
app.add_url_rule('/plan-builder', endpoint='main.plan_builder', view_func=plan_builder)
app.add_url_rule('/playbook', endpoint='main.playbook', view_func=playbook)
app.add_url_rule('/roles', endpoint='main.roles', view_func=roles)
app.add_url_rule('/roles/new', endpoint='main.role_new', view_func=role_new)
app.add_url_rule('/reports', endpoint='main.reports', view_func=reports)
app.add_url_rule('/reports/compare', endpoint='main.reports_compare', view_func=reports_compare)
app.add_url_rule('/reports2', endpoint='main.reports2', view_func=reports2)
app.add_url_rule('/report/<int:report_id>', endpoint='main.report_view', view_func=report_view)


@app.route("/plan/report")
def plan_report():
    """Simple report page that can start and monitor a dynamic report job."""
    return render_template("plan_report.html")

# ---------------- Minimal Role APIs for dev server ----------------
import sqlite3

DB_PATH = os.path.join(SUB_APP_DIR, 'app.db')

def _db_conn():
    try:
        return sqlite3.connect(DB_PATH)
    except Exception:
        return None

def _ensure_role_tables(conn):
    try:
        cur = conn.cursor()
        # Minimal role_profiles table for dev/demo use
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS role_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                department TEXT,
                description TEXT,
                is_active INTEGER DEFAULT 1,
                created_date TEXT
            )
            """
        )
        # Minimal role_competency_targets table
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS role_competency_targets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                role_profile_id INTEGER NOT NULL,
                competency_id INTEGER NOT NULL,
                target_level INTEGER NOT NULL,
                weight REAL DEFAULT 1.0
            )
            """
        )
        conn.commit()
    except Exception:
        pass

def _rows_to_dicts(cur):
    cols = [c[0] for c in cur.description] if cur.description else []
    return [dict(zip(cols, r)) for r in cur.fetchall()]

@app.route('/api/roles', methods=['GET','POST'])
def dev_list_roles():
    """List or create Role Profiles (dev/demo).
    GET: returns list. POST: creates a role.
    """
    try:
        con = _db_conn()
        if not con:
            if request.method == 'POST':
                return jsonify({'error': 'storage unavailable'}), 500
            return jsonify({'roles': [], 'count': 0})
        _ensure_role_tables(con)
        if request.method == 'POST':
            data = request.get_json(force=True) or {}
            name = (data.get('name') or '').strip()
            department = (data.get('department') or '').strip()
            description = (data.get('description') or '').strip()
            if not name:
                return jsonify({'error': 'name is required'}), 400
            cur = con.cursor()
            cur.execute(
                "INSERT INTO role_profiles (name, department, description, is_active, created_date) VALUES (?,?,?,?,?)",
                (name, department or None, description or None, 1, datetime.utcnow().isoformat(' '))
            )
            rid = cur.lastrowid
            con.commit()
            return jsonify({'role': {'id': int(rid), 'name': name, 'department': department, 'description': description}})
        # GET branch
        q = (request.args.get('q') or '').strip().lower()
        cur = con.cursor()
        sql = "SELECT id, name, department, is_active, created_date FROM role_profiles ORDER BY name"
        cur.execute(sql)
        rows = _rows_to_dicts(cur)
        if q:
            rows = [r for r in rows if q in (r.get('name') or '').lower()]
        return jsonify({'roles': rows, 'count': len(rows)})
    except Exception as e:
        if request.method == 'POST':
            try:
                con.rollback()
            except Exception:
                pass
            return jsonify({'error': 'failed_to_create', 'detail': str(e)}), 500
        return jsonify({'roles': [], 'count': 0})



# Get a role with optional includes (ksaos,targets)
@app.route('/api/roles/<int:role_id>', methods=['GET','PATCH'])
def dev_get_role(role_id: int):
    try:
        # PATCH: update
        if request.method == 'PATCH':
            data = request.get_json(force=True) or {}
            name = data.get('name')
            department = data.get('department')
            description = data.get('description')
            con = _db_conn()
            if not con:
                return jsonify({'error': 'storage unavailable'}), 500
            _ensure_role_tables(con)
            cur = con.cursor()
            fields = []
            vals = []
            if name is not None:
                fields.append('name = ?'); vals.append(name)
            if department is not None:
                fields.append('department = ?'); vals.append(department)
            if description is not None:
                fields.append('description = ?'); vals.append(description)
            if fields:
                vals.append(role_id)
                cur.execute(f"UPDATE role_profiles SET {', '.join(fields)} WHERE id = ?", vals)
                con.commit()
            return jsonify({'ok': True})
        # GET: fetch
        include = (request.args.get('include') or '').lower()
        con = _db_conn()
        if not con:
            return jsonify({'error': 'not found'}), 404
        _ensure_role_tables(con)
        cur = con.cursor()
        cur.execute("SELECT id, name, department, description, is_active, created_date FROM role_profiles WHERE id = ?", (role_id,))
        row = cur.fetchone()
        if not row:
            return jsonify({'error': 'not found'}), 404
        cols = [c[0] for c in cur.description]
        rec = dict(zip(cols, row))
        # include KSAOs from session
        if 'ksaos' in include:
            allk = session.get('role_ksaos') or {}
            rec.update(allk.get(str(role_id)) or {})
        # include targets from DB
        if 'targets' in include:
            try:
                cur.execute("SELECT id, role_profile_id, competency_id, target_level, weight FROM role_competency_targets WHERE role_profile_id = ? ORDER BY id", (role_id,))
                tcols = [c[0] for c in cur.description]
                rec['competency_targets'] = [dict(zip(tcols, r)) for r in cur.fetchall()]
            except Exception:
                rec['competency_targets'] = []
        return jsonify({'role': rec})
    except Exception:
        return jsonify({'error': 'not found'}), 404


# Upsert KSAOs for a role (session-backed in dev)
@app.route('/api/roles/<int:role_id>/ksaos', methods=['POST'])
def dev_set_role_ksaos(role_id: int):
    try:
        data = request.get_json(force=True) or {}
        allowed = ['knowledge','skills','abilities','others']
        store = session.setdefault('role_ksaos', {})
        curv = store.get(str(role_id)) or {}
        for k in allowed:
            v = data.get(k)
            if isinstance(v, list):
                # normalize items as {name: str}
                curv[k] = [ {'name': (x.get('name') or '').strip()} for x in v if isinstance(x, dict) and (x.get('name') or '').strip() ]
        store[str(role_id)] = curv
        session['role_ksaos'] = store
        session.modified = True
        return jsonify({'ok': True})
    except Exception as e:
        return jsonify({'error': 'failed_to_set_ksaos', 'detail': str(e)}), 500



@app.route('/api/roles/<int:role_id>/targets', methods=['GET','POST'])
def dev_get_role_targets(role_id: int):
    """Return role competency targets, including competency name when present."""
    try:
        # POST: replace targets
        if request.method == 'POST':
            data = request.get_json(force=True) or {}
            targets = data.get('targets') or []
            con = _db_conn()
            if not con:
                return jsonify({'error': 'storage unavailable'}), 500
            _ensure_role_tables(con)
            cur = con.cursor()
            cur.execute("DELETE FROM role_competency_targets WHERE role_profile_id = ?", (role_id,))
            for t in targets:
                try:
                    cid = int(t.get('competency_id'))
                    lvl = int(t.get('target_level'))
                    wt = float(t.get('weight') or 1.0)
                except Exception:
                    continue
                cur.execute(
                    "INSERT INTO role_competency_targets (role_profile_id, competency_id, target_level, weight) VALUES (?,?,?,?)",
                    (role_id, cid, lvl, wt)
                )
            con.commit()
            return jsonify({'ok': True})
        # GET branch
        con = _db_conn()
        if not con:
            return jsonify({'targets': [], 'count': 0})
        cur = con.cursor()
        cur.execute(
            """
            SELECT t.id, t.role_profile_id, t.competency_id, t.target_level, t.weight,
                   c.name AS competency_name
            FROM role_competency_targets t
            LEFT JOIN competencies c ON c.id = t.competency_id
            WHERE t.role_profile_id = ?
            ORDER BY t.id
            """,
            (role_id,)
        )
        items = _rows_to_dicts(cur)
        return jsonify({'targets': items, 'count': len(items)})
    except Exception:
        return jsonify({'targets': [], 'count': 0})


@app.route('/api/proficiency', methods=['GET', 'POST'])
def dev_proficiency():
    """Session-scoped competency proficiency mapping used for gap calculations."""
    try:
        if request.method == 'GET':
            return jsonify({'competency_proficiency': session.get('competency_proficiency') or {}})
        data = request.get_json(silent=True) or {}
        mapping = data.get('competency_proficiency') or {}
        clean = {}
        for k, v in (mapping.items() if isinstance(mapping, dict) else []):
            try:
                key = int(k)
                val = int(v)
            except Exception:
                continue
            clean[str(key)] = max(0, min(5, val))
        session['competency_proficiency'] = clean
        session.modified = True
        return jsonify({'ok': True, 'competency_proficiency': clean})
    except Exception as e:
        return jsonify({'error': 'Failed to update proficiency', 'details': str(e)}), 500


@app.route('/api/roles/select', methods=['GET', 'POST'])
def dev_role_select():
    try:
        if request.method == 'GET':
            rid = session.get('selected_role_profile_id')
            return jsonify({'selected_role_profile_id': rid})
        data = request.get_json(silent=True) or {}
        rid = data.get('role_profile_id') or data.get('id') or data.get('role_id')
        if rid in (None, '', 0, '0'):
            session.pop('selected_role_profile_id', None)
        else:
            session['selected_role_profile_id'] = int(rid)
        session.modified = True
        return jsonify({'ok': True, 'selected_role_profile_id': session.get('selected_role_profile_id')})
    except Exception as e:
        return jsonify({'error': 'Failed to set selected role', 'details': str(e)}), 500


@app.route('/api/roles/<int:role_id>/gaps', methods=['GET'])
def dev_role_gaps(role_id: int):
    """Compute gaps vs targets using session proficiency with basic weighting."""
    try:
        con = _db_conn()
        if not con:
            return jsonify({'gaps': [], 'weighted_gap': 0.0})
        # Load targets
        cur = con.cursor()
        cur.execute(
            """
            SELECT t.competency_id, t.target_level, t.weight, c.name AS competency_name
            FROM role_competency_targets t
            LEFT JOIN competencies c ON c.id = t.competency_id
            WHERE t.role_profile_id = ?
            """,
            (role_id,)
        )
        targets = _rows_to_dicts(cur)
        prof = session.get('competency_proficiency') or {}
        gaps = []
        total_w = 0.0
        total_g = 0.0
        for t in targets:
            cid = t.get('competency_id')
            tgt = int(t.get('target_level') or 0)
            wt = float(t.get('weight') or 1.0)
            curr = int(prof.get(str(cid)) or prof.get(cid) or 0)
            gap = max(0, tgt - curr)
            gaps.append({
                'competency_id': cid,
                'competency_name': t.get('competency_name'),
                'target_level': tgt,
                'current_level': curr,
                'gap': gap,
                'weight': wt,
            })
            total_w += wt
            total_g += gap * wt
        weighted = (total_g / total_w) if total_w > 0 else 0.0
        return jsonify({'gaps': gaps, 'count': len(gaps), 'weighted_gap': round(weighted, 4)})
    except Exception:
        return jsonify({'gaps': [], 'weighted_gap': 0.0})

# ---------------- Minimal Reports APIs for dev server ----------------
@app.route('/api/reports', methods=['GET'])
def dev_reports_list():
    """Return an empty list or a lightweight list if a table exists. Safe fallback to empty."""
    try:
        con = _db_conn()
        if not con:
            return jsonify({'reports': [], 'count': 0})
        cur = con.cursor()
        # Try to select if table exists
        try:
            cur.execute("SELECT id, title, created_date, generation_status FROM dynamic_reports ORDER BY created_date DESC LIMIT 50")
            rows = _rows_to_dicts(cur)
            return jsonify({'reports': rows, 'count': len(rows)})
        except Exception:
            return jsonify({'reports': [], 'count': 0})
    except Exception:
        return jsonify({'reports': [], 'count': 0})


@app.route('/api/reports/<int:report_id>', methods=['GET'])
def dev_reports_get(report_id: int):
    try:
        con = _db_conn()
        if not con:
            return jsonify({'error': 'not found'}), 404
        cur = con.cursor()
        try:
            cur.execute("SELECT id, title, created_date, generation_status, content FROM dynamic_reports WHERE id = ?", (report_id,))
            row = cur.fetchone()
            if not row:
                return jsonify({'error': 'not found'}), 404
            cols = [c[0] for c in cur.description]
            rec = dict(zip(cols, row))
            include = (request.args.get('include') or '').lower()
            if 'content' not in include:
                rec.pop('content', None)
            return jsonify({'report': rec})
        except Exception:
            return jsonify({'error': 'not found'}), 404
    except Exception:
        return jsonify({'error': 'not found'}), 404

# Provide simple status/health pages for dev to satisfy base.html links
@app.route('/status')
def detailed_status():
    # Reuse a generic template if available
    try:
        return render_template('status.html')
    except Exception:
        return render_template('index.html')

@app.route('/health')
def health_check():
    # For dev, show a minimal status page
    try:
        return render_template('status.html')
    except Exception:
        from flask import jsonify
        return jsonify({
            'status': 'ok',
            'message': 'Dev health endpoint',
        })

app.add_url_rule('/status', endpoint='main.detailed_status', view_func=detailed_status)
app.add_url_rule('/health', endpoint='main.health_check', view_func=health_check)


# ---------------- Reports utilities (cleanup and debug) ----------------
def _cleanup_stale_report_jobs(max_age_seconds: int = 3600):
    """Remove jobs older than max_age_seconds or with broken download_url from session.

    Keeps this lightweight and best-effort; it only mutates the session dict.
    """
    try:
        jobs = session.get('report_jobs') or {}
        if not isinstance(jobs, dict):
            session['report_jobs'] = {}
            session.modified = True
            return
        now_ts = datetime.utcnow().timestamp()
        reports_dir = os.path.join(STATIC_DIR, 'reports')
        changed = False
        to_del = []
        for jid, job in jobs.items():
            try:
                created_iso = job.get('created')
                created_ts = 0
                if created_iso:
                    try:
                        # Accept both with/without 'Z'
                        created_ts = datetime.fromisoformat(created_iso.replace('Z','')).timestamp()
                    except Exception:
                        created_ts = 0
                is_old = (now_ts - created_ts) > max_age_seconds if created_ts else False
                # If completed with download_url, verify existence
                has_url = bool(job.get('download_url'))
                missing_file = False
                if has_url:
                    try:
                        # Expect /static/reports/<name>.pdf
                        url = str(job.get('download_url')).replace('\\','/')
                        if '/static/reports/' in url:
                            fname = url.split('/static/reports/', 1)[1]
                            fpath = os.path.join(reports_dir, fname)
                            if not os.path.isfile(fpath):
                                missing_file = True
                    except Exception:
                        missing_file = True
                if is_old or (has_url and missing_file):
                    to_del.append(jid)
            except Exception:
                to_del.append(jid)
        for jid in to_del:
            jobs.pop(jid, None)
            changed = True
        if changed:
            session['report_jobs'] = jobs
            session.modified = True
    except Exception:
        # Never raise cleanup errors to caller
        pass


@app.route('/api/debug/static-reports', methods=['GET'])
def api_debug_static_reports():
    """List files under the served static reports directory for quick verification."""
    try:
        reports_dir = os.path.join(STATIC_DIR, 'reports')
        os.makedirs(reports_dir, exist_ok=True)
        items = []
        for name in sorted(os.listdir(reports_dir)):
            path = os.path.join(reports_dir, name)
            if not os.path.isfile(path):
                continue
            try:
                st = os.stat(path)
                items.append({
                    'name': name,
                    'size': st.st_size,
                    'mtime': datetime.utcfromtimestamp(st.st_mtime).isoformat() + 'Z',
                    'url': f"/static/reports/{name}",
                })
            except Exception:
                items.append({'name': name, 'url': f"/static/reports/{name}"})
        return jsonify({'count': len(items), 'items': items})
    except Exception as e:
        return jsonify({'error': 'failed_to_list', 'detail': str(e)}), 500


# --------- Minimal API stubs to support Resume Card and context badge ---------
# In your full app, these should be served by your existing context manager APIs.
@app.route("/api/context/framework/state", methods=["GET"])
def get_framework_state():
    # If mocks are disabled and an upstream is configured, proxy to it
    if not MOCKS_ENABLED and CONTEXT_STATE_UPSTREAM:
        try:
            import urllib.request, json as _json
            with urllib.request.urlopen(CONTEXT_STATE_UPSTREAM) as resp:
                data = _json.loads(resp.read().decode("utf-8"))
                return jsonify(data)
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Fallback to session-backed state
    state = session.get("framework_state", {
        "framework_id": None,
        "framework_name": None,
        "active_competencies": [],
        "selected_metrics_count": 0,
        "last_activity": None,
        "has_plan_config": False,
        "has_ai_summary": False,
    })
    return jsonify(state)


@app.route("/api/context/framework/state", methods=["POST"])  # helper for demo
def set_framework_state():
    payload = request.get_json(force=True)
    state = session.get("framework_state", {})
    state.update(payload or {})
    state["last_activity"] = datetime.utcnow().isoformat() + "Z"
    session["framework_state"] = state
    return jsonify({"ok": True, "state": state})


# Optional landing to quickly set some demo context
@app.route("/demo/seed-context")
def demo_seed():
    # Only allow seeding when mocks are enabled (dev/demo mode)
    if not MOCKS_ENABLED:
        return jsonify({"error": "not_available"}), 404
    session["framework_state"] = {
        "framework_id": "fwk-001",
        "framework_name": "L&D Core Competencies",
        "active_competencies": ["communication", "coaching"],
        "selected_metrics_count": 3,
        "last_activity": datetime.utcnow().isoformat() + "Z",
        "has_plan_config": True,
        "has_ai_summary": True,
    }
    return redirect(url_for("dashboard"))

@app.route("/api/demo/reset", methods=["POST"])
def api_demo_reset():
    # Only available in mock mode to avoid accidental data loss in production
    if not MOCKS_ENABLED:
        return jsonify({"error": "not_available"}), 404
    for key in [
        "framework_state",
        "selected_metrics",
        "kv",
        "rec_interactions",
        "report_jobs",
    ]:
        if key in session:
            session.pop(key)
    session.modified = True
    return jsonify({"ok": True})

# --------- Safe session-based mock APIs (for local demo only) ---------
# These are provided to exercise the UI end-to-end without external services.
# Replace these with your real backend endpoints when available.

def _get_kv():
    if "kv" not in session:
        session["kv"] = {}
    return session["kv"]


@app.route("/api/context/system", methods=["GET"])
def api_get_kv():
    # Live path: proxy to upstream when mocks are off and upstream configured
    if not MOCKS_ENABLED and CONTEXT_SYSTEM_UPSTREAM:
        try:
            import urllib.parse, urllib.request
            url = CONTEXT_SYSTEM_UPSTREAM
            key = request.args.get("key")
            if key:
                sep = '&' if ('?' in url) else '?'
                url = f"{url}{sep}key={urllib.parse.quote(key)}"
            with urllib.request.urlopen(url) as resp:
                return jsonify(__import__('json').loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock/session path
    key = request.args.get("key")
    kv = _get_kv()
    if key:
        return jsonify({"key": key, "value": kv.get(key)})
    return jsonify(kv)


@app.route("/api/context/system", methods=["POST"])
def api_set_kv():
    # Live path: proxy to upstream when mocks are off and upstream configured
    if not MOCKS_ENABLED and CONTEXT_SYSTEM_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                CONTEXT_SYSTEM_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock/session path
    data = request.get_json(force=True) or {}
    key = data.get("key")
    value = data.get("value")
    if not key:
        return jsonify({"error": "key required"}), 400
    kv = _get_kv()
    kv[key] = value
    session.modified = True
    return jsonify({"ok": True})


@app.route("/api/analyze-event", methods=["POST", "OPTIONS"])
def api_analyze_event():
    # Preflight support (some browsers/frameworks issue OPTIONS before POST)
    if request.method == 'OPTIONS':
        try:
            from flask import make_response
            resp = make_response(('', 204))
            resp.headers['Access-Control-Allow-Methods'] = 'POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
            return resp
        except Exception:
            return ('', 204)
    maybe = _require_mocks()
    if maybe: return maybe
    # The front-end in ld-metrics-translator/static/js/event-analysis.js expects:
    # { success: bool, analysis: { learning_needs, recommended_metrics, interventions, success_measures }, generated_by }
    payload = request.get_json(force=True) or {}
    # Accept either 'event_description' (sub-app) or 'description' (legacy)
    desc = (payload.get("event_description") or payload.get("description") or "").strip()
    # Simple heuristic mapping based on keywords to vary content slightly
    dn = desc.lower()
    learning_needs = []
    if any(k in dn for k in ("conflict", "dispute", "feedback")):
        learning_needs = [
            "Giving constructive feedback",
            "Conflict resolution techniques",
            "Clarify scope and roles",
        ]
    elif any(k in dn for k in ("decision", "pressure", "deadline")):
        learning_needs = [
            "Decision hygiene under pressure",
            "Clarify decision rights",
            "Stakeholder alignment",
        ]
    else:
        learning_needs = [
            "Clarify scope and roles",
            "Improve cross-team communication",
            "Establish feedback loops",
        ]

    recommended_metrics = [
        "Cycle time",
        "Rework rate",
        "Decision quality reviews",
    ]
    interventions = [
        "Pre-mortem session",
        "Decision checklist",
        "Short feedback loops",
    ]
    success_measures = [
        "Fewer last-minute changes",
        "Higher team confidence",
        "On-time delivery",
    ]

    analysis = {
        "learning_needs": learning_needs,
        "recommended_metrics": recommended_metrics,
        "interventions": interventions,
        "success_measures": success_measures,
    }
    return jsonify({
        "success": True,
        "analysis": analysis,
        "generated_by": "AI-assisted analysis",
    })


@app.route("/api/context/metrics/select", methods=["POST"])
def api_select_metric():
    # Live path: proxy to upstream when mocks are off and upstream configured
    if not MOCKS_ENABLED and CONTEXT_METRICS_SELECT_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                CONTEXT_METRICS_SELECT_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock/session path
    data = request.get_json(force=True) or {}
    metric_id = data.get("metric_id")
    if not metric_id:
        return jsonify({"error": "metric_id required"}), 400
    # update count + list in framework_state
    state = session.get("framework_state", {
        "framework_id": None,
        "framework_name": None,
        "active_competencies": [],
        "selected_metrics_count": 0,
        "last_activity": None,
        "has_plan_config": False,
        "has_ai_summary": False,
    })
    state["selected_metrics_count"] = int(state.get("selected_metrics_count") or 0) + 1
    session.setdefault("selected_metrics", [])
    if metric_id not in session["selected_metrics"]:
        session["selected_metrics"].append(metric_id)
    state["last_activity"] = datetime.utcnow().isoformat() + "Z"
    session["framework_state"] = state
    session.modified = True
    return jsonify({"ok": True, "selected_metrics_count": state["selected_metrics_count"]})


@app.route("/api/context/metrics/deselect", methods=["POST"])
def api_deselect_metric():
    # Live path: proxy to upstream when configured
    if not MOCKS_ENABLED and CONTEXT_METRICS_DESELECT_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                CONTEXT_METRICS_DESELECT_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock/session path
    data = request.get_json(force=True) or {}
    metric_id = data.get("metric_id")
    if not metric_id:
        return jsonify({"error": "metric_id required"}), 400
    state = session.get("framework_state", {
        "framework_id": None,
        "framework_name": None,
        "active_competencies": [],
        "selected_metrics_count": 0,
        "last_activity": None,
        "has_plan_config": False,
        "has_ai_summary": False,
    })
    # Remove from list if present
    selected = session.setdefault("selected_metrics", [])
    if metric_id in selected:
        selected.remove(metric_id)
        state["selected_metrics_count"] = max(0, int(state.get("selected_metrics_count") or 0) - 1)
    state["last_activity"] = datetime.utcnow().isoformat() + "Z"
    session["framework_state"] = state
    session.modified = True
    return jsonify({"ok": True, "selected_metrics_count": state["selected_metrics_count"]})


@app.route("/api/context/metrics/list", methods=["GET"])
def api_list_metrics():
    maybe = _require_mocks()
    if maybe: return maybe
    ids = session.get("selected_metrics", [])
    name_map = {
        "m-comm-01": "Communication Clarity Score",
        "m-comm-02": "Feedback Loop Completion",
        "m-coach-01": "Coaching Quality Index",
        "m-coach-02": "Coaching Session Adoption",
        "m-eng-03": "Learner Engagement Index",
    }
    items = [{"id": i, "name": name_map.get(i, i)} for i in ids]
    return jsonify({"items": items})


# --- Driver/Bias/Heuristic Cards API (CSV-backed for local dev) ---
from typing import List, Dict, Any
import csv

def _static_data_path(filename: str) -> str:
    return os.path.join(STATIC_DIR, 'data', filename)

def _parse_driver_chain(s: str) -> Dict[str, List[str]]:
    result = {}
    if not s:
        return result
    # Example: Drives: A, B; Measured by: X; Leads to: Y, Z
    try:
        parts = [p.strip() for p in s.split(';') if p.strip()]
        for p in parts:
            if ':' in p:
                k, v = p.split(':', 1)
                key = k.strip()
                vals = [x.strip() for x in v.split(',') if x.strip()]
                result[key] = vals
    except Exception:
        pass
    return result

def _load_driver_cards_from_csv() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    path = _static_data_path('driver_cards.csv')
    if not os.path.isfile(path):
        return cards
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        i = 1
        for row in reader:
            name = (row.get('Driver Card Title') or '').strip()
            ident = (row.get('Type Identifier') or '').strip().lower()
            raw_chain = _parse_driver_chain(row.get('Driver Chain') or '')
            outcome = (row.get("L&D Outcome") or '').strip()
            mtype = (row.get('Metric Type') or '').strip()
            data_collection = (row.get('Data Collection') or '').strip()
            frequency = (row.get('Frequency') or '').strip()
            frameworks = (row.get('Associated Framework(s)') or '').strip()
            nudges = (row.get('Recommended Nudges') or '').strip()
            # Map identifier to overall kind for UI labels (drivers by default)
            kind = 'driver'
            # Derive id deterministically
            cid = 1000 + i
            i += 1
            # Synthesize a helpful brief description when not provided
            brief = (row.get('Brief Description') or '').strip()
            if not brief:
                title_l = (name or '').strip().lower()
                # Hand-authored blurbs for common drivers
                templates = {
                    'growth mindset': 'Improve early learner experience. Growth Mindset belief that abilities can improve with effort.',
                    'giving recognition': 'Reinforce desired behaviors through timely, specific recognition and positive feedback.',
                    'time to productivity': 'Reduce ramp-up time for new hires and transitions by streamlining onboarding and coaching.',
                    'improved employee retention': 'Increase tenure by improving employee experience, development, and manager support.',
                    'psychological safety': 'Create a climate where people feel safe to speak up, admit mistakes, and challenge ideas.',
                }
                brief = templates.get(title_l) or (f"{name} supports {outcome.lower()} through the practices in this card." if (name and outcome) else f"{name}")

            # Normalize driver chain to an ordered array of stages (title, items)
            def _chain_array(identifier: str, chain_map: Dict[str, Any]) -> list:
                idl = (identifier or '').lower()
                # CSV keys may vary slightly; support common variants
                def g(*names: str):
                    for n in names:
                        if n in chain_map:
                            return chain_map.get(n) or []
                    return []
                if idl == 'concept':
                    return [
                        {'key': 'drives_behaviors', 'title': 'Drives Behavior', 'items': g('Drives', 'Drives Behavior')},
                        {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': g('Measured by', 'Measured')},
                        {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': g('Leads to')},
                    ]
                if idl == 'behavior' or idl == 'behaviour':
                    return [
                        {'key': 'driven_by_concepts', 'title': 'Driven by Concept', 'items': g('Driven by')},
                        {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': g('Measured by', 'Measured')},
                        {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': g('Leads to')},
                    ]
                if idl == 'kpi':
                    return [
                        {'key': 'measures_behaviors', 'title': 'Measures Behavior', 'items': g('Measures')},
                        {'key': 'indicates_concepts', 'title': 'Indicates Concept', 'items': g('Indicates')},
                        {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': g('Leads to')},
                    ]
                if idl == 'outcome':
                    return [
                        {'key': 'driven_by_behaviors', 'title': 'Driven by Behavior', 'items': g('Driven by')},
                        {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': g('Measured by', 'Measured')},
                    ]
                # default
                return [
                    {'key': 'drives_behaviors', 'title': 'Drives Behavior', 'items': g('Drives')},
                    {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': g('Measured by')},
                    {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': g('Leads to')},
                ]

            chain_arr = _chain_array(ident, raw_chain)

            cards.append({
                'id': cid,
                'name': name,
                'description': brief,
                'outcome': {'name': outcome} if outcome else None,
                'metric_type': {'name': mtype} if mtype else None,
                'identifier_type': ident.upper() if ident else None,
                'kind': kind,
                'tags': [t.strip() for t in frameworks.split(',') if t.strip()],
                'related_nudges': [t.strip() for t in (nudges.replace(';', ',')).split(',') if t.strip()],
                'driver_chain': chain_arr,
                'classification': {
                    'ld_outcome': outcome or None,
                    'metric_type': mtype or None,
                    'data_collection': data_collection or None,
                    'frequency': frequency or None,
                },
            })
    return cards

def _load_bias_cards_from_csv() -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    path = _static_data_path('biases_heuristics.csv')
    if not os.path.isfile(path):
        return cards
    with open(path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        i = 1
        for row in reader:
            name = (row.get('Bias/Heuristic Name') or '').strip()
            btype = (row.get('Type') or '').strip()
            desc = (row.get('Brief Description') or '').strip()
            relevance = (row.get("Relevance to L&D/Leadership") or '').strip()
            nudges = (row.get('Recommended Nudges') or '').strip()
            kind = 'bias' if btype.lower() != 'heuristic' else 'heuristic'
            cid = 2000 + i
            i += 1
            cards.append({
                'id': cid,
                'name': name,
                'description': f"{desc} {('Relevance: ' + relevance) if relevance else ''}",
                'outcome': None,
                'metric_type': {'name': btype} if btype else None,
                'identifier_type': btype.upper() if btype else None,
                'kind': kind,
                'tags': [],
                'related_nudges': [t.strip() for t in (nudges.replace(';', ',')).split(',') if t.strip()],
            })
    return cards

def _all_cards_from_csv() -> List[Dict[str, Any]]:
    drivers = _load_driver_cards_from_csv()
    biases = _load_bias_cards_from_csv()
    return drivers + biases

# --- Mock Outcomes (for Plan Builder initial choice) ---
MOCK_OUTCOMES = [
    {"id": 1, "name": "Improve Employee Retention"},
    {"id": 2, "name": "Increase Productivity"},
    {"id": 3, "name": "Enhance Manager Capability"},
    {"id": 4, "name": "Boost Learner Engagement"},
]

@app.route('/api/outcomes', methods=['GET'])
def api_outcomes_list():
    # If backend is available, serve real outcomes from DB
    try:
        if BACKEND_AVAILABLE and backend_models is not None:
            LDOutcome = getattr(backend_models, 'LDOutcome', None)
            if LDOutcome is not None:
                rows = LDOutcome.query.order_by(LDOutcome.name).all()
                items = [{"id": r.id, "name": r.name} for r in rows]
                return jsonify({"items": items})
    except Exception:
        # fall through to mock
        pass
    # Dev fallback
    return jsonify({"items": MOCK_OUTCOMES})


@app.route('/api/driver-cards', methods=['GET'])
def api_driver_cards_list():
    from flask import request
    kind = (request.args.get('kind') or '').strip().lower()
    q = (request.args.get('q') or '').strip().lower()
    outcome_id = request.args.get('outcome_id', type=int)
    cards = _all_cards_from_csv()
    if kind in ('driver','bias','heuristic'):
        cards = [c for c in cards if (c.get('kind') or '').lower() == kind]
    if q:
        cards = [c for c in cards if q in (c.get('name') or '').lower() or q in (c.get('description') or '').lower()]
    # Filter by outcome_id by matching the outcome name on the card
    if outcome_id:
        sel = next((o for o in MOCK_OUTCOMES if o.get('id') == outcome_id), None)
        if sel:
            oname = (sel.get('name') or '').strip().lower()
            def _matches_outcome(card: Dict[str, Any]) -> bool:
                # Cards may have outcome.name or classification.ld_outcome
                try:
                    cname = ((card.get('outcome') or {}).get('name') or card.get('classification', {}).get('ld_outcome') or '').strip().lower()
                except Exception:
                    cname = ''
                return cname == oname or (oname and oname in cname)
            cards = [c for c in cards if _matches_outcome(c)]
    return jsonify({
        'items': cards,
        'pagination': {'page': 1, 'page_size': len(cards), 'total': len(cards), 'pages': 1, 'has_next': False, 'has_prev': False}
    })


@app.route('/api/driver-cards/<int:card_id>', methods=['GET'])
def api_driver_cards_get(card_id: int):
    cards = _all_cards_from_csv()
    for c in cards:
        if int(c.get('id') or -1) == int(card_id):
            return jsonify({'driver_card': c})
    return jsonify({'error': 'not found'}), 404


@app.route("/api/context/framework/competencies", methods=["POST"])
def api_set_competencies():
    # Live path: proxy to upstream when mocks are off and upstream configured
    if not MOCKS_ENABLED and CONTEXT_FRAMEWORK_COMPETENCIES_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                CONTEXT_FRAMEWORK_COMPETENCIES_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock/session path
    data = request.get_json(force=True) or {}
    ids = data.get("competency_ids") or []
    replace = bool(data.get("replace"))
    state = session.get("framework_state", {})
    current = state.get("active_competencies", [])
    if replace:
        state["active_competencies"] = ids
    else:
        state["active_competencies"] = sorted(set(list(current) + ids))
    state.setdefault("framework_id", "fwk-001")
    state.setdefault("framework_name", "L&D Core Competencies")
    state["last_activity"] = datetime.utcnow().isoformat() + "Z"
    session["framework_state"] = state
    session.modified = True
    return jsonify({"ok": True, "active_competencies": state["active_competencies"]})


@app.route("/api/frameworks", methods=["GET"])
def api_frameworks_list():
    # Live path: proxy to upstream when mocks are off and upstream configured
    if not MOCKS_ENABLED and FRAMEWORKS_LIST_UPSTREAM:
        try:
            import urllib.request
            with urllib.request.urlopen(FRAMEWORKS_LIST_UPSTREAM) as resp:
                return jsonify(__import__('json').loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # In mock/dev mode, return the canonical 4 frameworks used across the UI
    if MOCKS_ENABLED:
        items = [
            {"id": 1, "name": "The Situational Leadership® Model", "slug": "situational-leadership-model"},
            {"id": 2, "name": "Goleman's Emotional Intelligence (EQ)", "slug": "goleman-emotional-intelligence-eq"},
            {"id": 3, "name": "The Five Practices of Exemplary Leadership", "slug": "five-practices-of-exemplary-leadership"},
            {"id": 4, "name": "Strengths-Based Leadership", "slug": "strengths-based-leadership"},
        ]
        return jsonify({"items": items})
    # If backend is available, serve real frameworks from DB
    try:
        if BACKEND_AVAILABLE and backend_models is not None:
            Framework = getattr(backend_models, 'Framework', None)
            if Framework is not None:
                rows = Framework.query.order_by(Framework.sort_order, Framework.name).all()
                items = [{"id": r.id, "name": r.name} for r in rows]
                return jsonify({"items": items})
    except Exception:
        # fall through to mock
        pass
    # Mock list (fallback)
    items = [
        {"id": 1, "name": "The Situational Leadership® Model", "slug": "situational-leadership-model"},
        {"id": 2, "name": "Goleman's Emotional Intelligence (EQ)", "slug": "goleman-emotional-intelligence-eq"},
        {"id": 3, "name": "The Five Practices of Exemplary Leadership", "slug": "five-practices-of-exemplary-leadership"},
        {"id": 4, "name": "Strengths-Based Leadership", "slug": "strengths-based-leadership"},
    ]
    return jsonify({"items": items})


@app.route("/api/frameworks/<framework_id>/tree", methods=["GET"])
def api_framework_tree(framework_id):
    # Live path: proxy if mocks are off and upstream configured. Supports {framework_id} in URL.
    if not MOCKS_ENABLED and FRAMEWORKS_TREE_UPSTREAM:
        try:
            import urllib.request
            url = FRAMEWORKS_TREE_UPSTREAM.replace("{framework_id}", framework_id)
            with urllib.request.urlopen(url) as resp:
                return jsonify(__import__('json').loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock
    # Minimal demo tree
    tree = {
        "id": framework_id,
        "name": "L&D Core Competencies",
        "competencies": [
            {
                "id": "communication",
                "name": "Communication",
                "concepts": [{"name": "Clarity"}, {"name": "Feedback"}],
                "metrics": [
                    {"id": "m-comm-01", "name": "Communication Clarity Score"},
                    {"id": "m-comm-02", "name": "Feedback Loop Completion"},
                ],
            },
            {
                "id": "coaching",
                "name": "Coaching",
                "concepts": [{"name": "Adoption"}, {"name": "Quality"}],
                "metrics": [
                    {"id": "m-coach-01", "name": "Coaching Quality Index"},
                    {"id": "m-coach-02", "name": "Coaching Session Adoption"},
                ],
            },
        ],
    }
    return jsonify(tree)


@app.route("/api/frameworks/<framework_id>/competencies", methods=["GET"])
def api_framework_competencies(framework_id):
    """Provide competencies for a framework.
    If the backend DB is available, query real competencies. Otherwise return a small mock list.
    Supports optional include=metrics to align with the DB-backed endpoint signature.
    """
    include = (request.args.get('include') or '').lower()
    include_metrics = 'metrics' in include
    # Try DB-backed first
    if BACKEND_AVAILABLE and backend_app and backend_models:
        try:
            with backend_app.app_context():
                Framework = getattr(backend_models, 'Framework', None)
                Competency = getattr(backend_models, 'Competency', None)
                if Framework is None or Competency is None:
                    raise RuntimeError('models not available')
                # Accept int IDs or string slugs
                comp_query = Competency.query
                try:
                    fid = int(framework_id)
                    comp_query = comp_query.filter(Competency.framework_id == fid)
                    fw = Framework.query.get(fid)
                except Exception:
                    # fallback by slug
                    fw = Framework.query.filter(Framework.slug == str(framework_id)).first()
                    if fw:
                        comp_query = comp_query.filter(Competency.framework_id == fw.id)
                comps = comp_query.order_by(Competency.sort_order, Competency.name).all()
                def comp_to_dict(c):
                    d = {"id": c.id, "name": c.name, "slug": getattr(c, 'slug', None)}
                    if include_metrics:
                        # Provide minimal metric info if relationship exists
                        try:
                            d["metrics"] = [
                                {"id": m.id, "name": m.name}
                                for m in (getattr(c, 'metrics', []) or [])
                            ]
                        except Exception:
                            d["metrics"] = []
                    return d
                return jsonify({
                    "framework": {"id": getattr(fw, 'id', framework_id), "name": getattr(fw, 'name', None)},
                    "competencies": [comp_to_dict(c) for c in comps],
                    "count": len(comps),
                })
        except Exception:
            # fall through to mock
            pass
    # Mock fallback
    # Map canonical frameworks to representative competencies
    fw_slug = None
    try:
        # Derive slug from numeric id
        fid = int(framework_id)
        slug_map = {
            1: "situational-leadership-model",
            2: "goleman-emotional-intelligence-eq",
            3: "five-practices-of-exemplary-leadership",
            4: "strengths-based-leadership",
        }
        fw_slug = slug_map.get(fid)
    except Exception:
        fw_slug = str(framework_id)

    if fw_slug == "goleman-emotional-intelligence-eq":
        comps = [
            {"id": 201, "name": "Self-Awareness"},
            {"id": 202, "name": "Self-Management"},
            {"id": 203, "name": "Social Awareness"},
            {"id": 204, "name": "Relationship Management"},
        ]
    elif fw_slug == "situational-leadership-model":
        comps = [
            {"id": 211, "name": "Directing"},
            {"id": 212, "name": "Coaching"},
            {"id": 213, "name": "Supporting"},
            {"id": 214, "name": "Delegating"},
        ]
    elif fw_slug == "five-practices-of-exemplary-leadership":
        comps = [
            {"id": 221, "name": "Model the Way"},
            {"id": 222, "name": "Inspire a Shared Vision"},
            {"id": 223, "name": "Challenge the Process"},
            {"id": 224, "name": "Enable Others to Act"},
            {"id": 225, "name": "Encourage the Heart"},
        ]
    elif fw_slug == "strengths-based-leadership":
        comps = [
            {"id": 231, "name": "Executing"},
            {"id": 232, "name": "Influencing"},
            {"id": 233, "name": "Relationship Building"},
            {"id": 234, "name": "Strategic Thinking"},
        ]
    else:
        comps = [
            {"id": 101, "name": "Communication"},
            {"id": 102, "name": "Coaching"},
            {"id": 103, "name": "Self-Management"},
        ]
    if include_metrics:
        for c in comps:
            c["metrics"] = []
    return jsonify({"framework": {"id": framework_id}, "competencies": comps, "count": len(comps)})


@app.route("/api/smart-recommendations/generate", methods=["POST"])
def api_recommend_generate():
    # Live path: proxy
    if not MOCKS_ENABLED and SMART_RECS_GENERATE_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                SMART_RECS_GENERATE_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock
    data = request.get_json(force=True) or {}
    scope = data.get("scope") or "global"
    # Simple context-aware stub: pick metrics based on active competencies
    state = session.get("framework_state", {})
    comps = state.get("active_competencies", [])
    recs = []
    if not comps:
        recs = [
            {"id": "m-eng-03", "name": "Learner Engagement Index", "score": 0.78},
            {"id": "m-comm-01", "name": "Communication Clarity Score", "score": 0.72},
        ]
    else:
        if "communication" in comps:
            recs.append({"id": "m-comm-01", "name": "Communication Clarity Score", "score": 0.86})
        if "coaching" in comps:
            recs.append({"id": "m-coach-02", "name": "Coaching Session Adoption", "score": 0.81})
    return jsonify({"scope": scope, "recommendations": recs})


@app.route("/api/smart-recommendations/interact", methods=["POST"])
def api_recommend_interact():
    # Live path: proxy
    if not MOCKS_ENABLED and SMART_RECS_INTERACT_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                SMART_RECS_INTERACT_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock log to session
    # Collect lightweight interaction logs in session for demo
    data = request.get_json(force=True) or {}
    logs = session.setdefault("rec_interactions", [])
    logs.append({"ts": datetime.utcnow().isoformat() + "Z", **data})
    session.modified = True
    return jsonify({"ok": True})


@app.route("/api/dynamic-reports", methods=["POST"]) 
def api_dynamic_report_start():
    # Clean up stale jobs before starting a new one
    _cleanup_stale_report_jobs(max_age_seconds=3600)
    # Live path: proxy
    if not MOCKS_ENABLED and DYNAMIC_REPORTS_START_UPSTREAM:
        try:
            import urllib.request, json as _json
            req = urllib.request.Request(
                DYNAMIC_REPORTS_START_UPSTREAM,
                data=_json.dumps(request.get_json(force=True) or {}).encode('utf-8'),
                headers={'Content-Type': 'application/json'},
                method='POST'
            )
            with urllib.request.urlopen(req) as resp:
                return jsonify(_json.loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # If backend is available, generate a real PDF synchronously using the new final_plan template
    try:
        title = (request.get_json(silent=True) or {}).get('title') or 'Final Developmental Plan'
    except Exception:
        title = 'Final Developmental Plan'

    jobs = session.setdefault("report_jobs", {})
    job_id = f"job-{len(jobs)+1}"
    # Default mock entry
    jobs[job_id] = {
        "status": "running",
        "progress": 0,
        "created": datetime.utcnow().isoformat() + "Z",
        "started": datetime.utcnow().timestamp(),
    }

    # Attempt real generation if backend is available
    if BACKEND_AVAILABLE and backend_app is not None and backend_models is not None:
        try:
            with backend_app.app_context():
                # Lazy import to avoid circulars
                from app.services.report_generator import DynamicReportGenerator, ReportConfig  # type: ignore
                LDOutcome = getattr(backend_models, 'LDOutcome')
                Metric = getattr(backend_models, 'Metric')
                Framework = getattr(backend_models, 'Framework')

                # Collect plan items from session
                plan_items = session.get('context_plan_items', {}).get('data', [])
                driver_items = [it for it in plan_items if it.get('kind') == 'driver']
                bias_items = [it for it in plan_items if it.get('kind') == 'bias']
                metric_items = [it for it in plan_items if it.get('kind') == 'metric']

                # Selected metric IDs (from drivers/biases/metrics source_id)
                selected_metric_ids = []
                for it in (driver_items + bias_items + metric_items):
                    try:
                        mid = int(it.get('source_id'))
                        if mid not in selected_metric_ids:
                            selected_metric_ids.append(mid)
                    except Exception:
                        continue

                # Outcome and framework context from session framework_state
                fw_state = session.get('framework_state') or {}
                outcome_id = fw_state.get('outcome_id') or None
                framework_id = fw_state.get('framework_id') or None

                # Resolve names (best-effort)
                outcome_obj = LDOutcome.query.get(int(outcome_id)) if outcome_id else None
                framework_obj = Framework.query.get(int(framework_id)) if framework_id else None

                # Build extended generation_context
                drivers_ctx = []
                for it in driver_items:
                    try:
                        mid = int(it.get('source_id')) if it.get('source_id') is not None else None
                    except Exception:
                        mid = None
                    name = it.get('label') or (Metric.query.get(mid).name if (mid and Metric.query.get(mid)) else 'Driver')
                    drivers_ctx.append({
                        'name': name,
                        'metric_id': mid,
                        'priority': it.get('meta', {}).get('priority') if isinstance(it.get('meta'), dict) else None,
                    })
                nudges_ctx = []
                for it in bias_items:
                    try:
                        mid = int(it.get('source_id')) if it.get('source_id') is not None else None
                    except Exception:
                        mid = None
                    nudges_ctx.append({
                        'title': it.get('label') or 'Nudge',
                        'metric_id': mid,
                        'description': (it.get('meta') or {}).get('description') if isinstance(it.get('meta'), dict) else None,
                    })

                gen_ctx = {
                    'role_profile': {},  # Optional in dev
                    'framework_focus': ({'id': framework_obj.id, 'name': framework_obj.name, 'slug': framework_obj.slug} if framework_obj else {}),
                    'target_outcome': ({'id': outcome_obj.id, 'name': outcome_obj.name} if outcome_obj else {}),
                    'drivers': drivers_ctx,
                    'nudges': nudges_ctx,
                    'proficiency': {},  # Optional; could be wired from /api/proficiency later
                }

                # Build ReportConfig and generate
                config = ReportConfig(
                    title=title,
                    template_type='final_plan',
                    selected_outcomes=([int(outcome_obj.id)] if outcome_obj else []),
                    selected_metrics=selected_metric_ids,
                    ai_recommendations=[],
                    session_id=session.get('admin_username') or session.get('session_id') or 'dev',
                    generation_context=gen_ctx,
                )
                generator = DynamicReportGenerator()
                report = generator.generate_report(config)

                # Compute a download URL from the PDF path
                pdf_path = getattr(report, 'pdf_path', None) or ''
                download_url = None
                try:
                    # Expecting path like .../ld-metrics-translator/app/static/reports/filename.pdf
                    if pdf_path and 'static' in pdf_path.replace('\\','/'):
                        idx = pdf_path.replace('\\','/').split('/static/', 1)
                        if len(idx) == 2:
                            download_url = '/static/' + idx[1]
                except Exception:
                    download_url = None

                jobs[job_id] = {
                    'status': 'completed',
                    'progress': 100,
                    'created': datetime.utcnow().isoformat() + 'Z',
                    'download_url': download_url or '/sample.pdf',
                    'report_id': getattr(report, 'id', None),
                }
        except Exception as e:
            # Fall back to mock progression if backend generation fails
            jobs[job_id] = {
                'status': 'running',
                'progress': 0,
                'created': datetime.utcnow().isoformat() + 'Z',
                'error': str(e),
            }
    # Save job state
    session["report_jobs"] = jobs
    session.modified = True
    return jsonify({"job_id": job_id})


@app.route("/api/dynamic-reports/<job_id>/status", methods=["GET"]) 
def api_dynamic_report_status(job_id):
    # Clean up stale jobs before reporting status
    _cleanup_stale_report_jobs(max_age_seconds=3600)
    # Live path: proxy (supports {job_id} replacement)
    if not MOCKS_ENABLED and DYNAMIC_REPORTS_STATUS_UPSTREAM:
        try:
            import urllib.request
            url = DYNAMIC_REPORTS_STATUS_UPSTREAM.replace("{job_id}", job_id)
            with urllib.request.urlopen(url) as resp:
                return jsonify(__import__('json').loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Clean up stale jobs before reporting status
    _cleanup_stale_report_jobs(max_age_seconds=3600)
    # Mock status
    jobs = session.get("report_jobs", {})
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    # If real job info present, return it; otherwise simulate progress
    status = (job.get("status") or "running").lower()
    progress = int(job.get("progress") or 0)
    download_url = job.get("download_url")
    if status != 'completed' and progress < 100:
        # Simulate progress over ~6 seconds when running
        elapsed = max(0, datetime.utcnow().timestamp() - job.get("started", 0))
        progress = min(100, int((elapsed / 6.0) * 100))
        if progress >= 100:
            status = 'completed'
    resp = {
        "status": status,
        "progress": 100 if status == "completed" else progress,
        "download_url": download_url or "/sample.pdf",
        "title": job.get("title"),
    }
    # save back
    jobs[job_id] = job
    session["report_jobs"] = jobs
    session.modified = True
    return jsonify(resp)


@app.route('/api/metrics', methods=['GET'])
def api_metrics_list_db_first():
    """Prefer DB-backed list even when mocks are on. Fallback to empty list.
    Supports optional query params: per_page, q/name/search (case-insensitive contains).
    """
    if BACKEND_AVAILABLE and backend_app and backend_models:
        try:
            from sqlalchemy import func  # type: ignore
            per_page = int(request.args.get('per_page') or 20)
            q = (request.args.get('q') or request.args.get('name') or request.args.get('search') or '').strip()
            with backend_app.app_context():
                query = backend_models.Metric.query
                if q:
                    query = query.filter(backend_models.Metric.name.ilike(f"%{q}%"))
                items = query.limit(per_page).all()
                return jsonify({
                    'metrics': [m.to_dict() for m in items],
                    'count': len(items)
                })
        except Exception as e:
            # fall through to mock if any error
            pass
    # Mock fallback (no list in demo; return empty set)
    return jsonify({'metrics': [], 'count': 0})


@app.route("/api/metrics/<metric_id>", methods=["GET"])
def api_metric_detail(metric_id):
    # Prefer DB-backed response even if mocks are enabled
    if BACKEND_AVAILABLE and backend_app and backend_models:
        try:
            with backend_app.app_context():
                m = backend_models.Metric.query.get(int(metric_id))
                if m:
                    return jsonify({'metric': m.to_dict()})
                # If DB is available but the record is missing, gracefully fall back to mock details
        except Exception:
            # fall back to mock below
            pass
    # Mock demo fallback when backend unavailable
    details = {
        "id": metric_id,
        "name": {
            "m-comm-01": "Communication Clarity Score",
            "m-comm-02": "Feedback Loop Completion",
            "m-coach-01": "Coaching Quality Index",
            "m-coach-02": "Coaching Session Adoption",
            "m-eng-03": "Learner Engagement Index",
        }.get(metric_id, f"Metric {metric_id}"),
        "description": "Demo metric used for local UI testing. Replace with real details from your backend.",
        "category": "Behavioral",
        "type": "KPI",
        "tags": ["demo", "stub"],
    }
    return jsonify(details)


@app.route("/sample.pdf")
def sample_pdf():
    maybe = _require_mocks()
    if maybe: return maybe
    # Return a tiny valid PDF file from memory for demo purposes
    pdf_bytes = (
        b"%PDF-1.4\n"
        b"1 0 obj<<>>endobj\n"
        b"2 0 obj<< /Length 44 >>stream\nBT /F1 12 Tf 72 720 Td (Demo PDF Report) Tj ET\nendstream endobj\n"
        b"3 0 obj<< /Type /Page /Parent 4 0 R /Contents 2 0 R /Resources<< /Font<< /F1 5 0 R >> >> >>endobj\n"
        b"4 0 obj<< /Type /Pages /Kids [3 0 R] /Count 1 /MediaBox [0 0 612 792] >>endobj\n"
        b"5 0 obj<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>endobj\n"
        b"6 0 obj<< /Type /Catalog /Pages 4 0 R >>endobj\n"
        b"xref\n0 7\n0000000000 65535 f \n0000000010 00000 n \n0000000051 00000 n \n0000000151 00000 n \n0000000308 00000 n \n0000000392 00000 n \n0000000463 00000 n \ntrailer<< /Root 6 0 R /Size 7 >>\nstartxref\n527\n%%EOF"
    )
    resp = make_response(pdf_bytes)
    resp.headers["Content-Type"] = "application/pdf"
    resp.headers["Content-Disposition"] = "attachment; filename=report.pdf"
    return resp


# --------- Debug Endpoints ---------
@app.route("/api/debug/env", methods=["GET"])
def api_debug_env():
    """Expose selected environment and configuration for debugging/demo."""
    info = {
        "mocks_enabled": MOCKS_ENABLED,
        "context_state_upstream": bool(CONTEXT_STATE_UPSTREAM),
        "context_system_upstream": bool(CONTEXT_SYSTEM_UPSTREAM),
        "context_metrics_select_upstream": bool(CONTEXT_METRICS_SELECT_UPSTREAM),
        "context_metrics_deselect_upstream": bool(CONTEXT_METRICS_DESELECT_UPSTREAM),
        "context_framework_competencies_upstream": bool(CONTEXT_FRAMEWORK_COMPETENCIES_UPSTREAM),
        "frameworks_tree_upstream": bool(FRAMEWORKS_TREE_UPSTREAM),
        "smart_recs_generate_upstream": bool(SMART_RECS_GENERATE_UPSTREAM),
        "smart_recs_interact_upstream": bool(SMART_RECS_INTERACT_UPSTREAM),
        "dynamic_reports_start_upstream": bool(DYNAMIC_REPORTS_START_UPSTREAM),
        "dynamic_reports_status_upstream": bool(DYNAMIC_REPORTS_STATUS_UPSTREAM),
    }
    return jsonify(info)


@app.route("/api/debug/routes_main", methods=["GET"])
def api_debug_routes():
    """List registered routes on the Flask app for quick inspection."""
    rules = []
    try:
        for rule in app.url_map.iter_rules():
            rules.append({
                "endpoint": rule.endpoint,
                "methods": sorted(m for m in rule.methods if m not in {"HEAD", "OPTIONS"}),
                "rule": str(rule),
            })
    except Exception as e:
        return jsonify({"error": "route_introspection_failed", "detail": str(e)}), 500
    # Sort for stable output
    rules.sort(key=lambda r: r["rule"]) 
    return jsonify({"routes": rules})

# ---------------- Additional mock endpoints to support local UI ----------------

# Context initialization used by context-manager.js (dev/demo only)
@app.route("/api/context/initialize", methods=["POST"])
def api_context_initialize():
    """Initialize lightweight context in session for dev/demo.
    Mirrors the shape expected by context-manager.js but keeps it minimal.
    """
    payload = request.get_json(silent=True) or {}
    session.setdefault("_init_events", []).append({
        "ts": datetime.utcnow().isoformat() + "Z",
        "page": payload.get("page") or request.headers.get("Referer") or "unknown"
    })
    session.modified = True
    return jsonify({
        "success": True,
        "session": {"is_authenticated": False, "last_activity": datetime.utcnow().isoformat() + "Z"},
        "preferences": {},
        "initialized_page": payload.get("page") or "unknown"
    })


# Frontend calls for session history; provide a no-op stub to avoid 404 spam
@app.route("/api/context/recent-sessions", methods=["GET"])
def api_context_recent_sessions():
    try:
        # Return a minimal, empty list. Extend later if you want persistence.
        return jsonify({"sessions": [], "count": 0})
    except Exception as e:
        return jsonify({"error": "failed", "detail": str(e)}), 500


# Frontend calls to persist lightweight context; store in Flask session (dev/demo only)
@app.route("/api/context/store", methods=["POST"])
def api_context_store():
    try:
        data = request.get_json(silent=True) or {}
        bucket = session.setdefault("_context_events", [])
        bucket.append({"ts": datetime.utcnow().isoformat() + "Z", **data})
        session.modified = True
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


@app.route('/api/types', methods=['GET'])
def api_metric_types_list():
    items = [
        {"id": "behavioral", "name": "Behavioral"},
        {"id": "operational", "name": "Operational"},
        {"id": "kpi", "name": "KPI"},
    ]
    return jsonify({"items": items, "count": len(items)})


# ---------------- Session-backed Plan Items (dev/demo only) ----------------

def _ensure_plan_items():
    if 'context_plan_items' not in session or not isinstance(session.get('context_plan_items'), dict):
        session['context_plan_items'] = {'data': []}
    data = session['context_plan_items'].get('data')
    if not isinstance(data, list):
        session['context_plan_items'] = {'data': []}
        data = session['context_plan_items']['data']
    return data


@app.route('/api/context/plan/items', methods=['GET'])
def dev_plan_items_list():
    items = list(_ensure_plan_items())
    return jsonify({'success': True, 'items': items, 'count': len(items)})


@app.route('/api/context/plan/items', methods=['POST'])
def dev_plan_items_add():
    data = request.get_json(silent=True) or {}
    kind = (data.get('kind') or '').strip().lower()
    label = (data.get('label') or '').strip()
    source_id = data.get('source_id')
    meta = data.get('meta') or {}
    source_page = (data.get('source_page') or '').strip()
    if not kind or not label:
        return jsonify({'success': False, 'error': 'kind and label are required'}), 400
    allowed = {"driver", "bias", "metric", "outcome", "competency"}
    if kind not in allowed:
        return jsonify({'success': False, 'error': f"Invalid kind '{kind}'. Must be one of {sorted(allowed)}"}), 400
    items = _ensure_plan_items()
    new_id = (items[-1]['id'] + 1) if items else 1
    item = {
        'id': int(new_id),
        'session_id': 'dev',
        'kind': kind,
        'label': label,
        'source_id': source_id,
        'meta': meta,
        'source_page': source_page,
        'added_at': datetime.utcnow().isoformat() + 'Z',
    }
    items.append(item)
    session['context_plan_items'] = {'data': items}
    session.modified = True
    return jsonify({'success': True, 'item': item})


@app.route('/api/context/plan/items/<int:item_id>', methods=['DELETE'])
def dev_plan_items_remove(item_id: int):
    items = _ensure_plan_items()
    idx = next((i for i, it in enumerate(items) if it.get('id') == int(item_id)), None)
    if idx is None:
        return jsonify({'success': False, 'error': 'not found'}), 404
    items.pop(idx)
    session['context_plan_items'] = {'data': items}
    session.modified = True
    return jsonify({'success': True, 'removed_id': item_id})


@app.route('/api/context/plan/items', methods=['DELETE'])
def dev_plan_items_clear():
    session['context_plan_items'] = {'data': []}
    session.modified = True
    return jsonify({'success': True})


# ---------------- Minimal Metrics list for legacy UI (dev/demo) ----------------

@app.route('/api/metrics', methods=['GET'])
def api_metrics_list():
    """Return a small demo metrics list compatible with legacy app.js.
    Supports filters via query params: q, outcome (multi), type (multi).
    """
    # Demo catalog
    metrics = [
        {"id": 1, "name": "Training Completion Rate", "description": "Percent of learners completing assigned modules.", "example": "Module A completion within 30 days.", "outcome_id": 1, "outcome_name": "Engagement", "metric_type_id": 1, "metric_type_name": "Behavioral"},
        {"id": 2, "name": "Assessment Score", "description": "Average post-training assessment score.", "example": "Average score across cohorts.", "outcome_id": 2, "outcome_name": "Performance", "metric_type_id": 2, "metric_type_name": "Operational"},
        {"id": 3, "name": "Learner Engagement Index", "description": "Composite engagement KPI.", "example": "Clicks, time-on-task, reactions.", "outcome_id": 1, "outcome_name": "Engagement", "metric_type_id": 3, "metric_type_name": "KPI"},
        {"id": 4, "name": "Coaching Session Adoption", "description": "Share of employees engaged in coaching.", "example": "Sessions per employee per month.", "outcome_id": 3, "outcome_name": "Enablement", "metric_type_id": 2, "metric_type_name": "Operational"},
    ]

    # Filters
    q = (request.args.get('q') or '').strip().lower()
    outcome_ids = set()
    type_ids = set()
    try:
        outcome_ids = {int(x) for x in request.args.getlist('outcome') if str(x).strip()}
    except Exception:
        pass
    try:
        type_ids = {int(x) for x in request.args.getlist('type') if str(x).strip()}
    except Exception:
        pass

    def matches(m):
        if q and (q not in m['name'].lower() and q not in m['description'].lower()):
            return False
        if outcome_ids and m['outcome_id'] not in outcome_ids:
            return False
        if type_ids and m['metric_type_id'] not in type_ids:
            return False
        return True

    filtered = [m for m in metrics if matches(m)]
    return jsonify({"metrics": filtered, "count": len(filtered)})

if __name__ == "__main__":
    debug = os.environ.get("FLASK_DEBUG", "1") == "1"
    # Disable the reloader to avoid duplicate processes on Windows (watchdog/windowsapi)
    # which can make the server hard to stop with Ctrl+C.
    app.run(debug=debug, port=8080, use_reloader=False)

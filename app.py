from flask import Flask, render_template, jsonify, session
from flask import request, redirect, url_for
from flask import make_response
from datetime import datetime
import os
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SUB_APP_DIR = os.path.join(BASE_DIR, 'ld-metrics-translator')
TEMPLATES_DIR = os.path.join(SUB_APP_DIR, 'templates')
STATIC_DIR = os.path.join(SUB_APP_DIR, 'static')

# Point Flask to the sub-app's templates and static assets to ensure we serve the latest UI
app = Flask(
    __name__,
    template_folder=TEMPLATES_DIR if os.path.isdir(TEMPLATES_DIR) else None,
    static_folder=STATIC_DIR if os.path.isdir(STATIC_DIR) else None
)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key")
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0  # disable static caching in dev
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
    # Expose feature flags for UI
    return {
        "mocks_enabled": MOCKS_ENABLED,
        "prod_parity": prod_parity,
        "DRIVER_CARDS_V1": True,
        "UI_TABS_V2": True,
        "WORKFLOW_STRIP": False,
    }


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

# Alias endpoints to match blueprint-style names used in templates (main.*)
app.add_url_rule('/', endpoint='main.index', view_func=dashboard)
app.add_url_rule('/', endpoint='main.dashboard', view_func=dashboard)
app.add_url_rule('/diagnostics', endpoint='main.diagnostics', view_func=diagnostics)
app.add_url_rule('/plan-builder', endpoint='main.plan_builder', view_func=plan_builder)
app.add_url_rule('/playbook', endpoint='main.playbook', view_func=playbook)


@app.route("/plan/report")
def plan_report():
    """Simple report page that can start and monitor a dynamic report job."""
    return render_template("plan_report.html")

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


@app.route("/api/analyze-event", methods=["POST"])
def api_analyze_event():
    maybe = _require_mocks()
    if maybe: return maybe
    payload = request.get_json(force=True) or {}
    desc = (payload.get("description") or "").strip()
    summary = (
        "Analysis summary: " + (desc[:140] + ("..." if len(desc) > 140 else "") if desc else "No description provided.")
    )
    drivers = ["Engagement", "Relevance", "Practice"]
    competencies = ["Communication", "Coaching"]
    recommended_metrics = [
        {"id": "m-comm-01", "name": "Communication Clarity Score", "tag": "Behavioral"},
        {"id": "m-coach-02", "name": "Coaching Session Adoption", "tag": "Operational"},
        {"id": "m-eng-03", "name": "Learner Engagement Index", "tag": "Behavioral"},
    ]
    return jsonify({
        "summary": summary,
        "drivers": drivers,
        "competencies": competencies,
        "recommended_metrics": recommended_metrics,
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
    # Mock job
    jobs = session.setdefault("report_jobs", {})
    job_id = f"job-{len(jobs)+1}"
    jobs[job_id] = {
        "status": "running",
        "started": datetime.utcnow().timestamp(),
        "title": (request.json or {}).get("title") or "Development Plan",
    }
    session.modified = True
    return jsonify({"job_id": job_id})


@app.route("/api/dynamic-reports/<job_id>/status", methods=["GET"])
def api_dynamic_report_status(job_id):
    # Live path: proxy (supports {job_id} replacement)
    if not MOCKS_ENABLED and DYNAMIC_REPORTS_STATUS_UPSTREAM:
        try:
            import urllib.request
            url = DYNAMIC_REPORTS_STATUS_UPSTREAM.replace("{job_id}", job_id)
            with urllib.request.urlopen(url) as resp:
                return jsonify(__import__('json').loads(resp.read().decode('utf-8')))
        except Exception as e:
            return jsonify({"error": "upstream_unavailable", "detail": str(e)}), 502
    # Mock status
    jobs = session.get("report_jobs", {})
    job = jobs.get(job_id)
    if not job:
        return jsonify({"error": "not found"}), 404
    # Simulate progress over ~6 seconds
    elapsed = max(0, datetime.utcnow().timestamp() - job.get("started", 0))
    progress = min(100, int((elapsed / 6.0) * 100))
    if progress >= 100:
        job["status"] = "completed"
    status = job.get("status")
    resp = {
        "status": status,
        "progress": 100 if status == "completed" else progress,
        "download_url": "/sample.pdf",
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
    app.run(debug=debug, port=8080)

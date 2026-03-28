from functools import wraps
from flask import Blueprint, jsonify, request, session, current_app, abort
from app.models import AdminUser, Metric, LDOutcome, MetricType, ReportTemplate, DynamicReport, ReportAnalytics, Framework, Competency, UserSession, competency_metrics
from app.models import ClientRetroItem, ClientPullRequest, ClientSurveyResponse
from app.models import ClientCompany, ClientEngagement
from app.models import (
    RoleProfile,
    RoleKnowledge,
    RoleSkill,
    RoleAbility,
    RoleOtherRequirement,
    RoleOutcome,
    RoleCompetencyTarget,
    RoleAssignment,
)
from app import db
from app.ollama_integration import recommendation_engine, report_generator, event_analyzer
from app.services import knowledge_base
from app.services import behavioral_biases
from app.database import create_event_analysis, get_recent_event_analyses
from sqlalchemy import or_, func, text
from sqlalchemy.orm import aliased
import json
import time
import os
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from threading import Lock
from uuid import uuid4
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

_EVENT_ANALYSIS_EXECUTOR = ThreadPoolExecutor(max_workers=2)
_EVENT_ANALYSIS_JOBS: dict[str, dict] = {}
_EVENT_ANALYSIS_JOBS_LOCK = Lock()

_EVENT_ANALYSIS_MAX_ACTIVE = 2
_EVENT_ANALYSIS_MAX_QUEUE_SECONDS = 180


def _parse_iso_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        v = value.strip()
        if v.endswith('Z'):
            v = v[:-1]
        return datetime.fromisoformat(v)
    except Exception:
        return None


def _event_job_sweep_stale_queued(now: datetime | None = None) -> None:
    now_dt = now or datetime.utcnow()
    with _EVENT_ANALYSIS_JOBS_LOCK:
        for job in _EVENT_ANALYSIS_JOBS.values():
            if not isinstance(job, dict):
                continue
            if job.get('status') != 'queued':
                continue
            created = _parse_iso_utc(job.get('created_at'))
            if not created:
                continue
            age = (now_dt - created).total_seconds()
            if age <= _EVENT_ANALYSIS_MAX_QUEUE_SECONDS:
                continue
            job['status'] = 'failed'
            job['finished_at'] = now_dt.isoformat() + 'Z'
            job['error'] = (
                f"Analysis job was stuck in queue for {int(age)}s. "
                "Please retry. If this persists, restart the server (executor may be stalled)."
            )


def _event_job_set(job_id: str, **updates) -> None:
    with _EVENT_ANALYSIS_JOBS_LOCK:
        job = _EVENT_ANALYSIS_JOBS.get(job_id)
        if not job:
            return
        job.update(updates)


def _active_workspace_ids() -> tuple[int | None, int | None]:
    try:
        client_id = session.get('active_client_id')
        engagement_id = session.get('active_engagement_id')
        return (int(client_id) if client_id else None, int(engagement_id) if engagement_id else None)
    except Exception:
        return (None, None)


def _report_workspace_match_or_404(report: DynamicReport, *, route: str) -> None:
    """Strict workspace isolation: return 404 on mismatch, but warn server-side."""
    try:
        active_client_id, active_engagement_id = _active_workspace_ids()
        if not active_client_id or not active_engagement_id:
            logger.warning(
                "Workspace mismatch (no active workspace): route=%s report_id=%s report_client_id=%s report_engagement_id=%s",
                route,
                getattr(report, 'id', None),
                getattr(report, 'client_company_id', None),
                getattr(report, 'client_engagement_id', None),
            )
            abort(404)

        if getattr(report, 'client_company_id', None) is not None and getattr(report, 'client_engagement_id', None) is not None:
            if int(report.client_company_id) == int(active_client_id) and int(report.client_engagement_id) == int(active_engagement_id):
                return

        # Fallback for legacy rows: attempt to match using stamped path or generation_context slugs
        try:
            from app.workspace_stamp import get_active_workspace, workspace_from_pdf_path, safe_component
            ws = get_active_workspace() or {}
            want_client = safe_component(ws.get('client_slug') or '', default='')
            want_eng = safe_component(ws.get('engagement_slug') or '', default='')

            ctx = {}
            try:
                if getattr(report, 'generation_context', None):
                    ctx = report.generation_context
                    if isinstance(ctx, str):
                        ctx = json.loads(ctx)
                    if not isinstance(ctx, dict):
                        ctx = {}
            except Exception:
                ctx = {}

            have_client = safe_component((ctx.get('client_slug') if isinstance(ctx, dict) else None) or '', default='')
            have_eng = safe_component((ctx.get('engagement_slug') if isinstance(ctx, dict) else None) or '', default='')
            if not (have_client and have_eng):
                pws = workspace_from_pdf_path(getattr(report, 'pdf_path', None)) or {}
                have_client = safe_component(pws.get('client_slug') or '', default='')
                have_eng = safe_component(pws.get('engagement_slug') or '', default='')

            if want_client and want_eng and have_client and have_eng and want_client == have_client and want_eng == have_eng:
                return
        except Exception:
            pass

        logger.warning(
            "Workspace mismatch: route=%s report_id=%s active_client_id=%s active_engagement_id=%s report_client_id=%s report_engagement_id=%s",
            route,
            getattr(report, 'id', None),
            active_client_id,
            active_engagement_id,
            getattr(report, 'client_company_id', None),
            getattr(report, 'client_engagement_id', None),
        )
        abort(404)
    except Exception:
        abort(404)


def _event_job_get(job_id: str) -> dict | None:
    with _EVENT_ANALYSIS_JOBS_LOCK:
        job = _EVENT_ANALYSIS_JOBS.get(job_id)
        return dict(job) if job else None


def _run_event_analysis_job(
    app,
    job_id: str,
    event_description: str,
    selected_metrics: list,
    role_context: dict | None,
    client_ip: str,
    enable_event_kb: bool,
    kb_context,
    kb_tier_limit: int,
    kb_related_limit: int,
) -> None:
    _event_job_set(job_id, status='running', started_at=datetime.utcnow().isoformat() + 'Z')

    with app.app_context():
        try:
            check_fn = getattr(event_analyzer.ollama, '_check_availability', None)
            if callable(check_fn):
                check_fn()

            if not event_analyzer.ollama.available:
                raise RuntimeError(
                    f"Ollama is not available at {getattr(event_analyzer.ollama, 'base_url', 'http://localhost:11434')}. "
                    "Start Ollama and ensure the configured model is pulled."
                )

            analysis = event_analyzer.analyze_event(
                event_description,
                selected_metrics=selected_metrics,
                role_context=role_context,
            )

            generated_by = 'ai'

            kb_payload = {'strong': [], 'related': [], 'biases': []}
            kb_bias_limit = 5
            if enable_event_kb:
                kb_bias_limit = min(5, kb_related_limit)
                kb_payload['strong'] = knowledge_base.serialize_resources(
                    knowledge_base.get_resources_by_tier('t1t2', limit=kb_tier_limit)
                )
                kb_payload['related'] = knowledge_base.serialize_resources(
                    knowledge_base.get_resources_for_context(kb_context, max_results=kb_related_limit)
                )

            bias_keywords = []
            if selected_metrics:
                bias_keywords = [
                    str(m.get('name')).strip()
                    for m in selected_metrics
                    if isinstance(m, dict) and m.get('name')
                ]

            bias_text_parts = []
            if event_description:
                bias_text_parts.append(event_description)
            bias_text_parts.extend(bias_keywords)
            bias_search_text = " ".join(part for part in bias_text_parts if part).strip()

            bias_results = behavioral_biases.search_biases(
                text=bias_search_text or None,
                keywords=bias_keywords or None,
                limit=kb_bias_limit,
            )
            if not bias_results:
                bias_results = behavioral_biases.get_random_biases(limit=kb_bias_limit)
            kb_payload['biases'] = behavioral_biases.serialize_biases(bias_results)

            response_payload = {
                'success': True,
                'analysis': analysis,
                'generated_by': generated_by,
                'ollama_status': 'available',
                'timestamp': time.time(),
                'kb': kb_payload
            }

            stored_analysis = create_event_analysis(
                event_description=event_description,
                analysis_result=str(response_payload['analysis']),
                generated_by=generated_by,
                success=True,
                ip_address=client_ip
            )
            response_payload['analysis_id'] = stored_analysis.id

            _event_job_set(
                job_id,
                status='succeeded',
                finished_at=datetime.utcnow().isoformat() + 'Z',
                result=response_payload,
            )

        except Exception as analysis_error:
            error_msg = str(analysis_error)
            try:
                create_event_analysis(
                    event_description=event_description,
                    generated_by='error',
                    success=False,
                    error_message=error_msg,
                    ip_address=client_ip
                )
            except Exception:
                pass

            _event_job_set(
                job_id,
                status='failed',
                finished_at=datetime.utcnow().isoformat() + 'Z',
                error=error_msg,
            )

api = Blueprint('api', __name__, url_prefix='/api')


def _slugify(value: str) -> str:
    s = (value or '').strip().lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = re.sub(r'-{2,}', '-', s).strip('-')
    return s


def _unique_client_slug(base: str) -> str:
    slug = _slugify(base)
    if not slug:
        slug = 'client'
    candidate = slug
    n = 2
    while ClientCompany.query.filter_by(slug=candidate).first():
        candidate = f"{slug}-{n}"
        n += 1
    return candidate


def _workspace_state_payload():
    client_id = session.get('active_client_id')
    engagement_id = session.get('active_engagement_id')

    client = None
    engagement = None
    try:
        if client_id:
            cc = ClientCompany.query.get(int(client_id))
            if cc:
                client = {'id': cc.id, 'name': cc.name, 'slug': cc.slug}
        if engagement_id:
            ce = ClientEngagement.query.get(int(engagement_id))
            if ce:
                engagement = {
                    'id': ce.id,
                    'client_company_id': ce.client_company_id,
                    'name': ce.name,
                    'start_date': ce.start_date.isoformat() if ce.start_date else None,
                    'end_date': ce.end_date.isoformat() if ce.end_date else None,
                }
    except Exception:
        client = None
        engagement = None

    return {
        'active_client': client,
        'active_engagement': engagement,
    }


@api.route('/workspace/state', methods=['GET'])
def workspace_state():
    return jsonify({'success': True, **_workspace_state_payload()}), 200


@api.route('/workspace/clients', methods=['GET'])
def workspace_clients_list():
    try:
        clients = ClientCompany.query.order_by(ClientCompany.name.asc()).all()
        return jsonify({
            'success': True,
            'clients': [{'id': c.id, 'name': c.name, 'slug': c.slug} for c in clients],
            **_workspace_state_payload(),
        }), 200
    except Exception as e:
        logger.error(f"Error listing clients: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to list clients'}), 500


@api.route('/workspace/clients', methods=['POST'])
def workspace_clients_create():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'success': False, 'error': 'name is required'}), 400
        slug = _unique_client_slug(name)
        client = ClientCompany(name=name, slug=slug)
        db.session.add(client)
        db.session.commit()

        session['active_client_id'] = int(client.id)
        session.pop('active_engagement_id', None)
        session.modified = True

        return jsonify({
            'success': True,
            'client': {'id': client.id, 'name': client.name, 'slug': client.slug},
            **_workspace_state_payload(),
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating client: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create client'}), 500


@api.route('/workspace/clients/<int:client_id>/engagements', methods=['GET'])
def workspace_engagements_list(client_id: int):
    try:
        engagements = (
            ClientEngagement.query
            .filter(ClientEngagement.client_company_id == int(client_id))
            .order_by(ClientEngagement.created_date.desc())
            .limit(200)
            .all()
        )
        return jsonify({
            'success': True,
            'engagements': [
                {
                    'id': e.id,
                    'client_company_id': e.client_company_id,
                    'name': e.name,
                    'start_date': e.start_date.isoformat() if e.start_date else None,
                    'end_date': e.end_date.isoformat() if e.end_date else None,
                }
                for e in engagements
            ],
            **_workspace_state_payload(),
        }), 200
    except Exception as e:
        logger.error(f"Error listing engagements: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to list engagements'}), 500


@api.route('/workspace/select', methods=['POST'])
def workspace_select():
    try:
        data = request.get_json(silent=True) or {}
        client_id = data.get('client_id')
        engagement_id = data.get('engagement_id')

        if client_id is not None and str(client_id).strip() != '':
            cc = ClientCompany.query.get(int(client_id))
            if not cc:
                return jsonify({'success': False, 'error': 'Client not found'}), 404
            session['active_client_id'] = int(cc.id)
        else:
            session.pop('active_client_id', None)
            session.pop('active_engagement_id', None)

        if engagement_id is not None and str(engagement_id).strip() != '':
            ce = ClientEngagement.query.get(int(engagement_id))
            if not ce:
                return jsonify({'success': False, 'error': 'Engagement not found'}), 404
            if session.get('active_client_id') and int(ce.client_company_id) != int(session.get('active_client_id')):
                return jsonify({'success': False, 'error': 'Engagement does not belong to active client'}), 400
            session['active_engagement_id'] = int(ce.id)
        else:
            session.pop('active_engagement_id', None)

        session.modified = True
        return jsonify({'success': True, **_workspace_state_payload()}), 200
    except Exception as e:
        logger.error(f"Error selecting workspace: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to select workspace'}), 500


@api.route('/workspace/engagements', methods=['POST'])
def workspace_engagements_create():
    try:
        data = request.get_json(silent=True) or {}
        client_id = data.get('client_id') or session.get('active_client_id')
        name = (data.get('name') or '').strip()
        if not client_id:
            return jsonify({'success': False, 'error': 'client_id is required'}), 400
        if not name:
            return jsonify({'success': False, 'error': 'name is required'}), 400

        cc = ClientCompany.query.get(int(client_id))
        if not cc:
            return jsonify({'success': False, 'error': 'Client not found'}), 404

        engagement = ClientEngagement(client_company_id=int(cc.id), name=name)
        db.session.add(engagement)
        db.session.commit()

        session['active_client_id'] = int(cc.id)
        session['active_engagement_id'] = int(engagement.id)
        session.modified = True

        return jsonify({
            'success': True,
            'engagement': {
                'id': engagement.id,
                'client_company_id': engagement.client_company_id,
                'name': engagement.name,
                'start_date': engagement.start_date.isoformat() if engagement.start_date else None,
                'end_date': engagement.end_date.isoformat() if engagement.end_date else None,
            },
            **_workspace_state_payload(),
        }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating engagement: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to create engagement'}), 500

def login_required(f):
    """Decorator to require authentication for API endpoints."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = authenticate_user()
        if not user:
            return jsonify({
                'error': 'Authentication required',
                'success': False,
                'login_url': '/login'
            }), 401
        return f(*args, **kwargs)
    return decorated_function


def _iso(dt):
    try:
        return dt.isoformat() if dt else None
    except Exception:
        return None


def _parse_optional_iso_datetime(value: str | None):
    if not value:
        return None
    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        return None


def _parse_limit_offset(default_limit: int = 200, max_limit: int = 1000):
    try:
        limit = int(request.args.get('limit', default_limit))
    except Exception:
        limit = default_limit
    try:
        offset = int(request.args.get('offset', 0))
    except Exception:
        offset = 0
    limit = max(1, min(limit, max_limit))
    offset = max(0, offset)
    return limit, offset


def _event_feed_item(source_type: str, item_id: int, occurred_at, team: str | None, category: str | None, text_value: str, source: str | None, extra: dict | None = None):
    payload = {
        'id': f"{source_type}:{item_id}",
        'source_type': source_type,
        'source_id': item_id,
        'occurred_at': _iso(occurred_at),
        'team': team,
        'category': category,
        'text': text_value,
        'source': source,
    }
    if extra:
        payload.update(extra)
    return payload


@api.route('/client-data/retros', methods=['GET'])
@login_required
def list_client_retros():
    """List imported client retrospective items."""
    try:
        limit, offset = _parse_limit_offset()
        team = (request.args.get('team') or '').strip()
        source = (request.args.get('source') or '').strip()
        since = _parse_optional_iso_datetime(request.args.get('since'))

        query = ClientRetroItem.query
        if team:
            query = query.filter(ClientRetroItem.team == team)
        if source:
            query = query.filter(ClientRetroItem.source == source)
        if since:
            query = query.filter(ClientRetroItem.imported_at >= since)

        total = query.count()
        rows = (
            query.order_by(ClientRetroItem.imported_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return jsonify({
            'success': True,
            'count': len(rows),
            'total': total,
            'items': [
                {
                    'id': r.id,
                    'retro_date': _iso(r.retro_date),
                    'team': r.team,
                    'category': r.category,
                    'text': r.text,
                    'action_owner': r.action_owner,
                    'action_status': r.action_status,
                    'source': r.source,
                    'imported_at': _iso(r.imported_at),
                }
                for r in rows
            ],
            'timestamp': time.time(),
        }), 200
    except Exception as e:
        logger.error(f"Error listing client retros: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to list client retros', 'details': str(e)}), 500


@api.route('/client-data/pull-requests', methods=['GET'])
@login_required
def list_client_pull_requests():
    """List imported client pull request records."""
    try:
        limit, offset = _parse_limit_offset()
        team = (request.args.get('team') or '').strip()
        source = (request.args.get('source') or '').strip()
        since = _parse_optional_iso_datetime(request.args.get('since'))

        query = ClientPullRequest.query
        if team:
            query = query.filter(ClientPullRequest.team == team)
        if source:
            query = query.filter(ClientPullRequest.source == source)
        if since:
            query = query.filter(ClientPullRequest.imported_at >= since)

        total = query.count()
        rows = (
            query.order_by(ClientPullRequest.imported_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return jsonify({
            'success': True,
            'count': len(rows),
            'total': total,
            'items': [
                {
                    'id': r.id,
                    'pr_id': r.pr_id,
                    'url': r.url,
                    'created_at': _iso(r.created_at),
                    'merged_at': _iso(r.merged_at),
                    'author': r.author,
                    'comments_count': r.comments_count,
                    'additions': r.additions,
                    'deletions': r.deletions,
                    'team': r.team,
                    'source': r.source,
                    'imported_at': _iso(r.imported_at),
                }
                for r in rows
            ],
            'timestamp': time.time(),
        }), 200
    except Exception as e:
        logger.error(f"Error listing client pull requests: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to list client pull requests', 'details': str(e)}), 500


@api.route('/client-data/survey-responses', methods=['GET'])
@login_required
def list_client_survey_responses():
    """List imported client survey responses."""
    try:
        limit, offset = _parse_limit_offset()
        team = (request.args.get('team') or '').strip()
        source = (request.args.get('source') or '').strip()
        since = _parse_optional_iso_datetime(request.args.get('since'))

        query = ClientSurveyResponse.query
        if team:
            query = query.filter(ClientSurveyResponse.team == team)
        if source:
            query = query.filter(ClientSurveyResponse.source == source)
        if since:
            query = query.filter(ClientSurveyResponse.imported_at >= since)

        total = query.count()
        rows = (
            query.order_by(ClientSurveyResponse.imported_at.desc())
            .offset(offset)
            .limit(limit)
            .all()
        )

        return jsonify({
            'success': True,
            'count': len(rows),
            'total': total,
            'items': [
                {
                    'id': r.id,
                    'submitted_at': _iso(r.submitted_at),
                    'survey_name': r.survey_name,
                    'question': r.question,
                    'answer': r.answer,
                    'team': r.team,
                    'source': r.source,
                    'imported_at': _iso(r.imported_at),
                }
                for r in rows
            ],
            'timestamp': time.time(),
        }), 200
    except Exception as e:
        logger.error(f"Error listing client survey responses: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to list client survey responses', 'details': str(e)}), 500


@api.route('/event-feed', methods=['GET'])
@login_required
def event_feed():
    """Generate a simple unified Event Feed from imported client datasets.

    Query params:
    - sources: comma-separated of retros,pull_requests,survey_responses (default retros)
    - team: exact match
    - source: exact match
    - limit: max events returned (default 200)
    """
    try:
        limit, _ = _parse_limit_offset(default_limit=200, max_limit=1000)
        team = (request.args.get('team') or '').strip()
        source = (request.args.get('source') or '').strip()
        sources = (request.args.get('sources') or 'retros').strip()
        selected = {s.strip().lower() for s in sources.split(',') if s.strip()}

        items: list[dict] = []

        if 'retros' in selected:
            query = ClientRetroItem.query
            if team:
                query = query.filter(ClientRetroItem.team == team)
            if source:
                query = query.filter(ClientRetroItem.source == source)
            rows = query.order_by(ClientRetroItem.imported_at.desc()).limit(limit).all()
            for r in rows:
                occurred = r.retro_date or r.imported_at
                items.append(
                    _event_feed_item(
                        'retro',
                        r.id,
                        occurred,
                        r.team,
                        r.category,
                        r.text,
                        r.source,
                        extra={
                            'action_owner': r.action_owner,
                            'action_status': r.action_status,
                        },
                    )
                )

        if 'pull_requests' in selected:
            query = ClientPullRequest.query
            if team:
                query = query.filter(ClientPullRequest.team == team)
            if source:
                query = query.filter(ClientPullRequest.source == source)
            rows = query.order_by(ClientPullRequest.imported_at.desc()).limit(limit).all()
            for r in rows:
                occurred = r.merged_at or r.created_at or r.imported_at
                text_bits = [f"PR {r.pr_id}"]
                if r.author:
                    text_bits.append(f"by {r.author}")
                if r.merged_at:
                    text_bits.append("merged")
                text_value = " ".join(text_bits)
                items.append(
                    _event_feed_item(
                        'pull_request',
                        r.id,
                        occurred,
                        r.team,
                        'Pull Request',
                        text_value,
                        r.source,
                        extra={
                            'pr_id': r.pr_id,
                            'url': r.url,
                            'author': r.author,
                            'comments_count': r.comments_count,
                            'additions': r.additions,
                            'deletions': r.deletions,
                        },
                    )
                )

        if 'survey_responses' in selected:
            query = ClientSurveyResponse.query
            if team:
                query = query.filter(ClientSurveyResponse.team == team)
            if source:
                query = query.filter(ClientSurveyResponse.source == source)
            rows = query.order_by(ClientSurveyResponse.imported_at.desc()).limit(limit).all()
            for r in rows:
                occurred = r.submitted_at or r.imported_at
                if r.question:
                    text_value = f"{r.question}: {r.answer}"
                else:
                    text_value = r.answer
                items.append(
                    _event_feed_item(
                        'survey_response',
                        r.id,
                        occurred,
                        r.team,
                        r.survey_name or 'Survey Response',
                        text_value,
                        r.source,
                        extra={
                            'survey_name': r.survey_name,
                            'question': r.question,
                        },
                    )
                )

        def sort_key(item: dict):
            s = item.get('occurred_at')
            if not s:
                return ''
            return str(s)

        items_sorted = sorted(items, key=sort_key, reverse=True)[:limit]

        return jsonify({
            'success': True,
            'count': len(items_sorted),
            'items': items_sorted,
            'timestamp': time.time(),
        }), 200
    except Exception as e:
        logger.error(f"Error generating event feed: {str(e)}")
        return jsonify({'success': False, 'error': 'Failed to generate event feed', 'details': str(e)}), 500


def admin_required(f):
    """Decorator to require an authenticated admin user for sensitive endpoints.

    It attempts a permissive check to avoid hard failures if the model changes:
    - Prefer AdminUser.is_admin if present
    - Fallback to AdminUser.role == 'admin' if available
    - Fallback to username == 'admin' as a last resort
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user = authenticate_user()
        if not user:
            return jsonify({'error': 'Authentication required', 'success': False, 'login_url': '/login'}), 401
        try:
            is_admin = bool(getattr(user, 'is_admin', False))
            if not is_admin:
                role_val = getattr(user, 'role', None)
                if isinstance(role_val, str) and role_val.strip().lower() == 'admin':
                    is_admin = True
            if not is_admin:
                username = getattr(user, 'username', '')
                if str(username).strip().lower() == 'admin':
                    is_admin = True
        except Exception:
            is_admin = False
        if not is_admin:
            return jsonify({'error': 'Forbidden: admin access required', 'success': False}), 403
        return f(*args, **kwargs)
    return decorated_function


# -------------------------------
# Helpers
# -------------------------------
def _slugify(value: str) -> str:
    """Create a simple URL-friendly slug from a string.

    Keeps letters, numbers, and single hyphens. Collapses spaces and separators to '-'.
    """
    try:
        import re
        value = (value or '').strip().lower()
        # Replace separators with hyphen
        value = re.sub(r"[\s_+/]+", "-", value)
        # Remove invalid chars
        value = re.sub(r"[^a-z0-9-]", "", value)
        # Collapse multiple hyphens
        value = re.sub(r"-+", "-", value).strip('-')
        return value or 'item'
    except Exception:
        return 'item'


def _normalize_identifier_type(value: str | None) -> str | None:
    if not value:
        return None
    v = str(value).strip().lower()
    mapping = {
        'concept': 'concept',
        'outcome': 'outcome',
        'behaviour': 'behavior',
        'behavior': 'behavior',
        'kpi': 'kpi',
    }
    return mapping.get(v)


def _parse_driver_chain(obj) -> dict | None:
    try:
        if obj is None:
            return None
        if isinstance(obj, str):
            return json.loads(obj)
        if isinstance(obj, (dict, list)):
            return obj
    except Exception:
        pass
    return None


def _build_role_context(role: RoleProfile) -> dict:
    def _map_items(collection, kind: str):
        items = []
        for item in collection:
            item_id = getattr(item, 'id', None)
            items.append({
                'id': item_id,
                'target_id': f"{kind}:{item_id}" if item_id is not None else None,
                'kind': kind,
                'name': getattr(item, 'name', None),
                'description': getattr(item, 'description', None),
                'driver_card_id': getattr(item, 'driver_card_id', None),
                'driver_card_name': getattr(getattr(item, 'driver_card', None), 'name', None),
                'target_level': getattr(item, 'target_level', None),
            })
        return items

    knowledge = _map_items(role.knowledge_items, 'knowledge')
    skills = _map_items(role.skill_items, 'skill')
    abilities = _map_items(role.ability_items, 'ability')
    outcomes = _map_items(role.outcomes, 'outcome')
    others = _map_items(role.other_requirements, 'other')

    # Flatten benchmark targets so the analyzer can link gaps back to stable IDs.
    ksao_targets = []
    for group in (knowledge, skills, abilities, others):
        for entry in group:
            if not entry.get('target_id'):
                continue
            ksao_targets.append({
                'target_id': entry.get('target_id'),
                'kind': entry.get('kind'),
                'name': entry.get('name'),
                'description': entry.get('description'),
                'target_level': entry.get('target_level'),
                'driver_card_id': entry.get('driver_card_id'),
                'driver_card_name': entry.get('driver_card_name'),
            })

    context = {
        'id': role.id,
        'name': role.name,
        'department': role.department,
        'knowledge': knowledge,
        'skills': skills,
        'abilities': abilities,
        'outcomes': outcomes,
        'others': others,
        'ksao_targets': ksao_targets,
        'competency_targets': [t.to_dict() for t in role.competency_targets],
    }
    return context


@api.route('/__debug__/routes2', methods=['GET'])
def debug_list_routes_early():
    """
    Early-registered route to list all routes. Useful if later import failures stop registration.
    """
    if not current_app.debug:
        abort(404)
    try:
        routes = []
        for rule in current_app.url_map.iter_rules():
            methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
            routes.append({
                'rule': str(rule),
                'endpoint': rule.endpoint,
                'methods': methods,
            })
        routes = sorted(routes, key=lambda r: r['rule'])
        return jsonify({'routes': routes, 'count': len(routes)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list routes', 'details': str(e)}), 500

# Track application start time for uptime calculation
start_time = time.time()


def validate_query_params(request_args):
    """Validate and sanitize query parameters."""
    errors = []
    
    # Validate outcome parameter
    outcome_id = request_args.get('outcome')
    if outcome_id:
        try:
            outcome_id = int(outcome_id)
            if not LDOutcome.query.get(outcome_id):
                errors.append(f"L&D outcome with ID {outcome_id} not found")
        except ValueError:
            errors.append("Invalid outcome ID format")
    
    # Validate type parameter
    type_id = request_args.get('type')
    if type_id:
        try:
            type_id = int(type_id)
            if not MetricType.query.get(type_id):
                errors.append(f"Metric type with ID {type_id} not found")
        except ValueError:
            errors.append("Invalid type ID format")
    
    return errors, outcome_id, type_id


@api.route('/auth_status', methods=['GET'])
def auth_status():
    """Return simple auth status for frontend checks.

    Expected by static/js/event-analysis.js as /api/auth_status.
    """
    try:
        is_authenticated = session.get('admin_user_id') is not None
        username = session.get('admin_username')
        return jsonify({
            'success': True,
            'authenticated': is_authenticated,
            'username': username
        }), 200
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@api.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for monitoring and load balancers."""
    try:
        # Check database connectivity
        db.session.execute(text('SELECT 1'))
        db_status = 'healthy'
    except Exception as e:
        db_status = f'unhealthy: {str(e)}'
    
    # Basic system info
    health_data = {
        'status': 'healthy' if db_status == 'healthy' else 'unhealthy',
        'timestamp': time.time(),
        'version': os.environ.get('APP_VERSION', '1.0.0'),
        'database': db_status,
        'uptime': time.time() - start_time if 'start_time' in globals() else 'unknown',
        'api_file': __file__,
        'api_version_marker': 'fw-crud-v1'
    }
    
    status_code = 200 if health_data['status'] == 'healthy' else 503
    return jsonify(health_data), status_code


@api.route('/metrics', methods=['GET'])
def get_metrics():
    """
    GET /api/metrics - return all metrics with optional filters
    Query parameters:
    - outcome / outcome_id: filter by L&D outcome (accepts ID or exact name, case-insensitive)
    - type / metric_type_id: filter by metric type (accepts ID or exact name, case-insensitive)
    - q / search: search term for name, description, example
    - page: page number (default: 1)
    - per_page: items per page (default: 20, max: 100)
    """
    try:
        # Support test-expected param names (IDs) first
        outcome_id = request.args.get('outcome_id', type=int) or request.args.get('outcome', type=int)
        type_id = request.args.get('metric_type_id', type=int) or request.args.get('type', type=int)

        # Also accept human-readable names for outcome/type
        resolved_outcome_name = None
        resolved_type_name = None

        # Outcome name resolution (case-insensitive exact match)
        if outcome_id is None:
            outcome_param_raw = request.args.get('outcome')
            if outcome_param_raw:
                # Only attempt name resolution if not an int
                try:
                    int(outcome_param_raw)
                except (TypeError, ValueError):
                    outcome_name_lower = outcome_param_raw.strip().lower()
                    match = LDOutcome.query.filter(func.lower(LDOutcome.name) == outcome_name_lower).all()
                    if len(match) == 1:
                        outcome_id = match[0].id
                        resolved_outcome_name = match[0].name
                    elif len(match) == 0:
                        return jsonify({
                            'error': 'Invalid outcome filter',
                            'details': f'Outcome name "{outcome_param_raw}" not found'
                        }), 400
                    else:
                        return jsonify({
                            'error': 'Ambiguous outcome filter',
                            'details': f'Multiple outcomes match name "{outcome_param_raw}"'
                        }), 400

        # Type name resolution (case-insensitive exact match)
        if type_id is None:
            type_param_raw = request.args.get('type')
            if type_param_raw is None:
                type_param_raw = request.args.get('metric_type_name')  # optional alias
            if type_param_raw:
                # Only attempt name resolution if not an int
                try:
                    int(type_param_raw)
                except (TypeError, ValueError):
                    type_name_lower = type_param_raw.strip().lower()
                    match = MetricType.query.filter(func.lower(MetricType.name) == type_name_lower).all()
                    if len(match) == 1:
                        type_id = match[0].id
                        resolved_type_name = match[0].name
                    elif len(match) == 0:
                        return jsonify({
                            'error': 'Invalid type filter',
                            'details': f'Metric type name "{type_param_raw}" not found'
                        }), 400
                    else:
                        return jsonify({
                            'error': 'Ambiguous type filter',
                            'details': f'Multiple metric types match name "{type_param_raw}"'
                        }), 400
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)  # Cap at 100
        search_query = request.args.get('search', request.args.get('q', '')).strip()
        
        # Build query with joins for efficient data loading
        query = Metric.query.join(LDOutcome).join(MetricType)
        
        # Apply filters
        if outcome_id:
            query = query.filter(Metric.outcome_id == outcome_id)
        if type_id:
            query = query.filter(Metric.metric_type_id == type_id)
        if search_query:
            query = query.filter(
                or_(
                    Metric.name.ilike(f'%{search_query}%'),
                    Metric.description.ilike(f'%{search_query}%'),
                    Metric.example.ilike(f'%{search_query}%')
                )
            )
        
        # Get paginated results
        metrics_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format response
        response = {
            'metrics': [metric.to_dict() for metric in metrics_pagination.items],
            'pagination': {
                'page': metrics_pagination.page,
                'per_page': metrics_pagination.per_page,
                'total': metrics_pagination.total,
                'pages': metrics_pagination.pages,
                'has_next': metrics_pagination.has_next,
                'has_prev': metrics_pagination.has_prev,
                'next_num': metrics_pagination.next_num,
                'prev_num': metrics_pagination.prev_num
            },
            'filters': {
                'outcome': outcome_id,
                'type': type_id,
                'search': search_query,
                'outcome_name': resolved_outcome_name,
                'type_name': resolved_type_name
            }
        }
        
        return jsonify(response), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter format',
            'details': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


# New: get a single metric by id (used by driver card demo fallback)
@api.route('/metrics/<int:metric_id>', methods=['GET'])
def get_metric(metric_id: int):
    try:
        metric = Metric.query.join(LDOutcome).join(MetricType).filter(Metric.id == metric_id).first()
        if not metric:
            return jsonify({'error': f'Metric with id {metric_id} not found'}), 404
        return jsonify({'metric': metric.to_dict()}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get metric', 'details': str(e)}), 500


# -------------------------------------------------
# Driver Cards API (feature-flagged via DRIVER_CARDS_V1)
# -------------------------------------------------

def _driver_cards_enabled():
    try:
        return bool(current_app.config.get('DRIVER_CARDS_V1'))
    except Exception:
        return False


def _load_driver_mapping():
    """Load optional mapping for kinds/tags/biases/nudges from static data files.
    Structure example (by id):
    {
      "kinds": {"1": "driver", "2": "bias", "3": "heuristic"},
      "tags": {"1": ["framework:eig", "capability:self-awareness"]},
      "biases": {"1": ["Fixed Mindset Bias"]},
      "nudges": {"1": ["Feedback Loop Nudge", "Challenge Assignment Nudge"]}
    }

    And an optional name-based file driver_cards_map_by_name.json with the same top-level keys
    mapping metric names to values; names are resolved to IDs here.
    """
    mapping = {"kinds": {}, "tags": {}, "biases": {}, "nudges": {}}
    try:
        import os, json
        data_path = os.path.join(current_app.static_folder or '', 'data', 'driver_cards_map.json')
        if os.path.isfile(data_path):
            with open(data_path, 'r', encoding='utf-8') as f:
                loaded = json.load(f)
                if isinstance(loaded, dict):
                    mapping['kinds'] = loaded.get('kinds', {}) or {}
                    mapping['tags'] = loaded.get('tags', {}) or {}
                    mapping['biases'] = loaded.get('biases', {}) or {}
                    mapping['nudges'] = loaded.get('nudges', {}) or {}
        # Optional name-based mapping for convenience during seeding
        names_path = os.path.join(current_app.static_folder or '', 'data', 'driver_cards_map_by_name.json')
        if os.path.isfile(names_path):
            try:
                with open(names_path, 'r', encoding='utf-8') as f:
                    nmap = json.load(f) or {}
                name_kinds = (nmap.get('kinds') or {}) if isinstance(nmap, dict) else {}
                name_tags = (nmap.get('tags') or {}) if isinstance(nmap, dict) else {}
                name_biases = (nmap.get('biases') or {}) if isinstance(nmap, dict) else {}
                name_nudges = (nmap.get('nudges') or {}) if isinstance(nmap, dict) else {}
                if name_kinds:
                    # Resolve names to IDs and merge
                    for mname, k in name_kinds.items():
                        m = Metric.query.filter(func.lower(Metric.name) == str(mname).strip().lower()).first()
                        if m:
                            mapping['kinds'][str(m.id)] = k
                if name_tags:
                    for mname, tags in name_tags.items():
                        m = Metric.query.filter(func.lower(Metric.name) == str(mname).strip().lower()).first()
                        if m:
                            mapping['tags'][str(m.id)] = tags
                if name_biases:
                    for mname, biases in name_biases.items():
                        m = Metric.query.filter(func.lower(Metric.name) == str(mname).strip().lower()).first()
                        if m:
                            mapping['biases'][str(m.id)] = biases
                if name_nudges:
                    for mname, nudges in name_nudges.items():
                        m = Metric.query.filter(func.lower(Metric.name) == str(mname).strip().lower()).first()
                        if m:
                            mapping['nudges'][str(m.id)] = nudges
            except Exception as e:
                logger.warning(f"Driver name-mapping load failed: {e}")
    except Exception as e:
        # Log and fallback silently
        logger.warning(f"Driver mapping load failed: {e}")
    return mapping


def _metric_to_driver_card(metric, mapping):
    mid = str(metric.id)
    raw_chain = _parse_driver_chain(getattr(metric, 'driver_chain', None)) or {}
    if not isinstance(raw_chain, dict):
        raw_chain = {}

    # Extract optional metadata stored within driver_chain._meta
    meta = raw_chain.get('_meta') if isinstance(raw_chain.get('_meta'), dict) else {}
    stage_data = {k: v for k, v in raw_chain.items() if k != '_meta'}

    kind = (mapping.get('kinds', {}).get(mid) or meta.get('kind') or 'driver').lower()
    tags = mapping.get('tags', {}).get(mid) or meta.get('tags') or []
    biases = mapping.get('biases', {}).get(mid) or meta.get('related_biases') or []
    nudges = mapping.get('nudges', {}).get(mid) or meta.get('related_nudges') or []
    additional_metric_types = meta.get('additional_metric_types') or []
    additional_metric_type_ids = meta.get('additional_metric_type_ids') or []
    data_collection = meta.get('data_collection') or getattr(metric, 'data_collection', None)
    frequency = meta.get('frequency') or getattr(metric, 'frequency', None)

    frameworks = []
    try:
        seen_fw = set()
        for comp in getattr(metric, 'competencies', []) or []:
            fw = getattr(comp, 'framework', None)
            if fw and fw.id not in seen_fw:
                frameworks.append({'id': fw.id, 'name': fw.name})
                seen_fw.add(fw.id)
    except Exception:
        pass

    # Built-in fallbacks by name (no external files required)
    try:
        name_lower = (metric.name or '').strip().lower()
        if not nudges and name_lower == 'growth mindset':
            nudges = [
                'Feedback Loop Nudge',
                'Challenge Assignment Nudge',
            ]
        if not biases and name_lower == 'growth mindset':
            biases = [
                'Fixed Mindset Bias'
            ]
    except Exception:
        pass

    driver_chain = _build_driver_chain_stages(stage_data, metric.identifier_type)

    return {
        'id': metric.id,
        'name': metric.name,
        'description': metric.description,
        'example': getattr(metric, 'example', None),
        'identifier_type': metric.identifier_type,
        'outcome': {
            'id': metric.outcome.id if metric.outcome else None,
            'name': metric.outcome.name if metric.outcome else None,
        },
        'metric_type': {
            'id': metric.metric_type.id if metric.metric_type else None,
            'name': metric.metric_type.name if metric.metric_type else None,
        },
        'kind': kind if kind in ('driver', 'bias', 'heuristic') else 'driver',
        'tags': tags,
        'related_biases': biases,
        'related_nudges': nudges,
        'driver_chain': driver_chain,
        'frameworks': frameworks,
        'classification': {
            'ld_outcome': metric.outcome.name if metric.outcome else None,
            'metric_type': metric.metric_type.name if metric.metric_type else None,
            'data_collection': data_collection,
            'frequency': frequency,
        },
        'metric_type_meta': {
            'additional_types': additional_metric_types,
            'additional_type_ids': additional_metric_type_ids,
        }
    }


def _sanitize_driver_kind(value):
    if value is None:
        return None
    try:
        v = str(value).strip().lower()
    except Exception:
        return None
    return v if v in {'driver', 'bias', 'heuristic'} else None


def _sanitize_string_list(value):
    if value is None:
        return []
    if isinstance(value, str):
        items = [value]
    elif isinstance(value, (list, tuple, set)):
        items = list(value)
    else:
        return []
    cleaned = []
    for item in items:
        if item is None:
            continue
        text = str(item).strip()
        if not text:
            continue
        cleaned.append(text)
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for item in cleaned:
        key = item.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(item)
    return unique


def _merge_driver_meta(chain_dict, overrides):
    chain_dict = dict(chain_dict or {})
    existing_meta = chain_dict.get('_meta') if isinstance(chain_dict.get('_meta'), dict) else {}
    meta = dict(existing_meta)
    for key, value in overrides.items():
        if value is None:
            continue
        meta[key] = value
    meta = {k: v for k, v in meta.items() if v is not None}
    if meta:
        chain_dict['_meta'] = meta
    elif '_meta' in chain_dict:
        chain_dict.pop('_meta', None)
    return chain_dict


def _build_driver_chain_stages(chain_dict, identifier_type):
    if not isinstance(chain_dict, dict):
        chain_dict = {}
    id_type = (identifier_type or '').lower()
    get_list = lambda key, fallback=None: list(chain_dict.get(key) or (fallback or []))
    if id_type == 'concept':
        return [
            {'key': 'drives_behaviors', 'title': 'Drives Behavior', 'items': get_list('drives_behaviors')},
            {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': get_list('measured_by_kpis')},
            {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': get_list('leads_to_outcomes')},
        ]
    if id_type == 'behavior':
        return [
            {'key': 'driven_by_concepts', 'title': 'Driven by Concept', 'items': get_list('driven_by_concepts')},
            {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': get_list('measured_by_kpis')},
            {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': get_list('leads_to_outcomes')},
        ]
    if id_type == 'kpi':
        return [
            {'key': 'measures_behaviors', 'title': 'Measures Behavior', 'items': get_list('measures_behaviors', chain_dict.get('drives_behaviors'))},
            {'key': 'indicates_concepts', 'title': 'Indicates Concept', 'items': get_list('indicates_concepts', chain_dict.get('driven_by_concepts'))},
            {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': get_list('leads_to_outcomes')},
        ]
    if id_type == 'outcome':
        return [
            {'key': 'driven_by_behaviors', 'title': 'Driven by Behavior', 'items': get_list('driven_by_behaviors', chain_dict.get('drives_behaviors'))},
            {'key': 'driven_by_concepts', 'title': 'Driven by Concept', 'items': get_list('driven_by_concepts')},
            {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': get_list('measured_by_kpis')},
        ]
    # Default ordering
    return [
        {'key': 'drives_behaviors', 'title': 'Drives Behavior', 'items': get_list('drives_behaviors')},
        {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': get_list('measured_by_kpis')},
        {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': get_list('leads_to_outcomes')},
    ]


def _coerce_int_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple, set)):
        items = value
    else:
        items = [value]
    result = []
    for item in items:
        try:
            val = int(item)
            result.append(val)
        except (TypeError, ValueError):
            continue
    # Deduplicate while preserving order
    seen = set()
    unique = []
    for val in result:
        if val in seen:
            continue
        seen.add(val)
        unique.append(val)
    return unique


def _set_metric_frameworks(metric: Metric, framework_ids):
    framework_ids = _coerce_int_list(framework_ids)
    if not framework_ids:
        metric.competencies = []
        return

    # Load competencies via frameworks
    competencies = Competency.query.filter(Competency.framework_id.in_(framework_ids)).all()
    # Ensure distinct metrics via join table
    metric.competencies = competencies


@api.route('/driver-cards', methods=['GET'])
def list_driver_cards():
    if not _driver_cards_enabled():
        abort(404)
    try:
        # Params
        q = (request.args.get('q') or '').strip()
        kind = (request.args.get('kind') or '').strip().lower()
        tags_raw = (request.args.get('tags') or '').strip()
        sort = (request.args.get('sort') or 'name').strip().lower()
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('page_size', request.args.get('per_page', 20, type=int), type=int), 100)
        framework_id = request.args.get('framework_id', type=int)
        framework_slug = (request.args.get('framework_slug') or '').strip().lower()
        competency_id = request.args.get('competency_id', type=int)
        competency_slug = (request.args.get('competency_slug') or '').strip().lower()
        # New: filter by outcome to support "Start with an Outcome" flow
        outcome_id = request.args.get('outcome_id', type=int)

        # Base query with joins
        query = Metric.query.filter(Metric.is_active.is_(True)).join(LDOutcome).join(MetricType)

        # Optional filter by Outcome
        if outcome_id:
            query = query.filter(Metric.outcome_id == outcome_id)

        # Optional filter by Framework/Competency via association table
        # Import association table lazily to avoid circular import
        from app.models import competency_metrics
        if framework_id or framework_slug or competency_id or competency_slug:
            # Join competency_metrics and competencies
            query = query.join(competency_metrics, Metric.id == competency_metrics.c.metric_id)
            query = query.join(Competency, Competency.id == competency_metrics.c.competency_id)
            if framework_id:
                query = query.join(Framework, Framework.id == Competency.framework_id).filter(Framework.id == framework_id)
            elif framework_slug:
                query = query.join(Framework, Framework.id == Competency.framework_id).filter(func.lower(Framework.slug) == framework_slug)
            if competency_id:
                query = query.filter(Competency.id == competency_id)
            elif competency_slug:
                query = query.filter(func.lower(Competency.slug) == competency_slug)
        if q:
            query = query.filter(or_(
                Metric.name.ilike(f'%{q}%'),
                Metric.description.ilike(f'%{q}%'),
                Metric.example.ilike(f'%{q}%')
            ))

        # Sorting
        if sort == 'created_date':
            query = query.order_by(Metric.created_date.desc())
        else:
            query = query.order_by(Metric.name.asc())

        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        mapping = _load_driver_mapping()

        items = []
        filter_tags = [t.strip() for t in tags_raw.split(',') if t.strip()] if tags_raw else []
        requested_kind = kind if kind in ('driver', 'bias', 'heuristic') else None

        for m in pagination.items:
            card = _metric_to_driver_card(m, mapping)
            if requested_kind and card['kind'] != requested_kind:
                continue
            if filter_tags:
                card_tags = set(card.get('tags') or [])
                if not card_tags.issuperset(filter_tags):
                    continue
            items.append(card)

        response = {
            'items': items,
            'pagination': {
                'page': pagination.page,
                'page_size': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev,
            },
            'filters': {
                'q': q,
                'kind': requested_kind or 'all',
                'tags': filter_tags,
                'sort': sort,
                'framework_id': framework_id,
                'framework_slug': framework_slug or None,
                'competency_id': competency_id,
                'competency_slug': competency_slug or None,
            }
        }
        return jsonify(response), 200
    except Exception as e:
        logger.exception("list_driver_cards failed")
        return jsonify({'error': 'Failed to list driver cards', 'details': str(e)}), 500


@api.route('/driver-cards/<int:metric_id>', methods=['GET'])
def get_driver_card(metric_id: int):
    if not _driver_cards_enabled():
        abort(404)
    try:
        metric = (
            Metric.query.join(LDOutcome)
            .join(MetricType)
            .filter(Metric.id == metric_id, Metric.is_active.is_(True))
            .first()
        )
        if not metric:
            return jsonify({'error': f'Driver card with id {metric_id} not found'}), 404
        mapping = _load_driver_mapping()
        card = _metric_to_driver_card(metric, mapping)

        # Related items: same outcome or type (limited)
        related_q = (
            Metric.query.filter(Metric.is_active.is_(True))
            .join(LDOutcome)
            .join(MetricType)
            .filter(Metric.id != metric.id)
            .limit(6)
        )
        related = []
        for m in related_q.all():
            related.append({
                'id': m.id,
                'name': m.name,
                'kind': (mapping.get('kinds', {}).get(str(m.id)) or 'driver')
            })
        card['related_items'] = related
        return jsonify({'driver_card': card}), 200
    except Exception as e:
        logger.exception("get_driver_card failed")
        return jsonify({'error': 'Failed to get driver card', 'details': str(e)}), 500


@api.route('/driver-cards', methods=['POST'])
@admin_required
def create_driver_card():
    if not _driver_cards_enabled():
        abort(404)
    try:
        data = request.get_json(silent=True) or {}

        name = (data.get('name') or '').strip()
        outcome_id = data.get('outcome_id')
        metric_type_id = data.get('metric_type_id')
        additional_metric_type_ids = _coerce_int_list(data.get('additional_metric_type_ids'))
        framework_ids = _coerce_int_list(data.get('framework_ids'))

        if not name or not outcome_id or not metric_type_id:
            return jsonify({'error': 'name, outcome_id, and metric_type_id are required'}), 400

        outcome = LDOutcome.query.get(outcome_id)
        if not outcome:
            return jsonify({'error': f'Invalid outcome_id: {outcome_id}'}), 400

        metric_type = MetricType.query.get(metric_type_id)
        if not metric_type:
            return jsonify({'error': f'Invalid metric_type_id: {metric_type_id}'}), 400

        identifier_type = _normalize_identifier_type(data.get('identifier_type')) or 'concept'
        chain = _parse_driver_chain(data.get('driver_chain')) or {}
        if not isinstance(chain, dict):
            chain = {}

        kind = _sanitize_driver_kind(data.get('kind')) or 'driver'
        tags = None
        if 'tags' in data or 'tag_list' in data:
            tags = _sanitize_string_list(data.get('tags') or data.get('tag_list'))
        biases = None
        if 'related_biases' in data or 'biases' in data:
            biases = _sanitize_string_list(data.get('related_biases') or data.get('biases'))
        nudges = None
        if 'related_nudges' in data or 'nudges' in data:
            nudges = _sanitize_string_list(data.get('related_nudges') or data.get('nudges'))

        meta_overrides = {
            'kind': kind,
            'tags': tags if tags is not None else None,
            'related_biases': biases if biases is not None else None,
            'related_nudges': nudges if nudges is not None else None,
        }
        chain = _merge_driver_meta(chain, meta_overrides)

        metric = Metric(
            name=name,
            description=data.get('description'),
            outcome_id=outcome.id,
            metric_type_id=metric_type.id,
            identifier_type=identifier_type,
            driver_chain=json.dumps(chain) if chain else None,
            measurement_method=data.get('measurement_method'),
            data_collection=data.get('data_collection'),
            success_criteria=data.get('success_criteria'),
            frequency=data.get('frequency'),
            unit_of_measure=data.get('unit_of_measure'),
            example=data.get('example'),
            data_source=data.get('data_source'),
            is_active=bool(data.get('is_active', True)),
        )

        db.session.add(metric)
        db.session.flush()

        # Link to additional metric types via metadata
        if additional_metric_type_ids:
            valid_ids = [mt.id for mt in MetricType.query.filter(MetricType.id.in_(additional_metric_type_ids)).all()]
            chain_dict = _parse_driver_chain(metric.driver_chain) or {}
            if not isinstance(chain_dict, dict):
                chain_dict = {}
            meta = chain_dict.get('_meta') if isinstance(chain_dict.get('_meta'), dict) else {}
            meta['additional_metric_type_ids'] = valid_ids
            meta['additional_metric_types'] = [MetricType.query.get(i).name for i in valid_ids if MetricType.query.get(i)]
            chain_dict['_meta'] = meta
            metric.driver_chain = json.dumps(chain_dict)

        if framework_ids:
            _set_metric_frameworks(metric, framework_ids)

        db.session.commit()

        mapping = _load_driver_mapping()
        return jsonify({'driver_card': _metric_to_driver_card(metric, mapping)}), 201
    except Exception as e:
        logger.exception('create_driver_card failed')
        db.session.rollback()
        return jsonify({'error': 'Failed to create driver card', 'details': str(e)}), 500


@api.route('/driver-cards/<int:metric_id>', methods=['PUT', 'PATCH'])
@admin_required
def update_driver_card(metric_id: int):
    if not _driver_cards_enabled():
        abort(404)
    try:
        metric = Metric.query.get(metric_id)
        if not metric or not metric.is_active:
            return jsonify({'error': f'Driver card with id {metric_id} not found'}), 404

        data = request.get_json(silent=True) or {}

        if 'name' in data and (data['name'] or '').strip():
            metric.name = data['name'].strip()
        if 'description' in data:
            metric.description = data.get('description')
        if 'measurement_method' in data:
            metric.measurement_method = data.get('measurement_method')
        if 'data_collection' in data:
            metric.data_collection = data.get('data_collection')
        if 'success_criteria' in data:
            metric.success_criteria = data.get('success_criteria')
        if 'frequency' in data:
            metric.frequency = data.get('frequency')
        if 'unit_of_measure' in data:
            metric.unit_of_measure = data.get('unit_of_measure')
        if 'example' in data:
            metric.example = data.get('example')
        if 'data_source' in data:
            metric.data_source = data.get('data_source')
        if 'is_active' in data:
            metric.is_active = bool(data.get('is_active'))
        if 'identifier_type' in data:
            metric.identifier_type = _normalize_identifier_type(data.get('identifier_type')) or metric.identifier_type

        # Manage outcome/type reassignment
        if 'outcome_id' in data and data.get('outcome_id') is not None:
            outcome = LDOutcome.query.get(data.get('outcome_id'))
            if not outcome:
                return jsonify({'error': f"Invalid outcome_id: {data.get('outcome_id')}"}), 400
            metric.outcome_id = outcome.id
        if 'metric_type_id' in data and data.get('metric_type_id') is not None:
            metric_type = MetricType.query.get(data.get('metric_type_id'))
            if not metric_type:
                return jsonify({'error': f"Invalid metric_type_id: {data.get('metric_type_id')}"}), 400
            metric.metric_type_id = metric_type.id
        additional_metric_type_ids = None
        if 'additional_metric_type_ids' in data:
            additional_metric_type_ids = _coerce_int_list(data.get('additional_metric_type_ids'))
        if additional_metric_type_ids is not None:
            chain_meta = _parse_driver_chain(metric.driver_chain) or {}
            if not isinstance(chain_meta, dict):
                chain_meta = {}
            meta = chain_meta.get('_meta') if isinstance(chain_meta.get('_meta'), dict) else {}
            if additional_metric_type_ids:
                valid_ids = [mt.id for mt in MetricType.query.filter(MetricType.id.in_(additional_metric_type_ids)).all()]
                meta['additional_metric_type_ids'] = valid_ids
                meta['additional_metric_types'] = [MetricType.query.get(i).name for i in valid_ids if MetricType.query.get(i)]
            else:
                meta.pop('additional_metric_type_ids', None)
                meta.pop('additional_metric_types', None)
            if meta:
                chain_meta['_meta'] = meta
            elif '_meta' in chain_meta:
                chain_meta.pop('_meta', None)
            metric.driver_chain = json.dumps(chain_meta)

        if 'framework_ids' in data:
            framework_ids = _coerce_int_list(data.get('framework_ids'))
            _set_metric_frameworks(metric, framework_ids or [])

        existing_chain = _parse_driver_chain(metric.driver_chain) or {}
        if not isinstance(existing_chain, dict):
            existing_chain = {}

        if 'driver_chain' in data:
            new_chain = _parse_driver_chain(data.get('driver_chain')) or {}
            chain = new_chain if isinstance(new_chain, dict) else {}
        else:
            chain = {k: v for k, v in existing_chain.items() if k != '_meta'}

        # Start meta from payload chain (if provided) otherwise existing
        meta_source = {}
        if 'driver_chain' in data and isinstance(data.get('driver_chain'), (dict, str)):
            parsed = _parse_driver_chain(data.get('driver_chain'))
            if isinstance(parsed, dict) and isinstance(parsed.get('_meta'), dict):
                meta_source = dict(parsed.get('_meta'))
        if not meta_source and isinstance(existing_chain.get('_meta'), dict):
            meta_source = dict(existing_chain.get('_meta'))

        overrides = {}
        if 'kind' in data:
            overrides['kind'] = _sanitize_driver_kind(data.get('kind')) or 'driver'
        if 'tags' in data:
            overrides['tags'] = _sanitize_string_list(data.get('tags'))
        if 'related_biases' in data:
            overrides['related_biases'] = _sanitize_string_list(data.get('related_biases'))
        if 'biases' in data and 'related_biases' not in data:
            overrides['related_biases'] = _sanitize_string_list(data.get('biases'))
        if 'related_nudges' in data:
            overrides['related_nudges'] = _sanitize_string_list(data.get('related_nudges'))
        if 'nudges' in data and 'related_nudges' not in data:
            overrides['related_nudges'] = _sanitize_string_list(data.get('nudges'))

        meta_source.update({k: v for k, v in overrides.items() if v is not None})

        final_chain = dict(chain)
        if meta_source:
            final_chain['_meta'] = meta_source
        elif '_meta' in final_chain:
            final_chain.pop('_meta', None)

        metric.driver_chain = json.dumps(final_chain) if final_chain else None

        db.session.commit()

        mapping = _load_driver_mapping()
        return jsonify({'driver_card': _metric_to_driver_card(metric, mapping)}), 200
    except Exception as e:
        logger.exception('update_driver_card failed')
        db.session.rollback()
        return jsonify({'error': 'Failed to update driver card', 'details': str(e)}), 500


@api.route('/driver-cards/<int:metric_id>', methods=['DELETE'])
@admin_required
def delete_driver_card(metric_id: int):
    if not _driver_cards_enabled():
        abort(404)
    try:
        metric = Metric.query.get(metric_id)
        if not metric:
            return jsonify({'error': f'Driver card with id {metric_id} not found'}), 404

        hard = request.args.get('hard', 'false').lower() == 'true'
        if hard:
            db.session.delete(metric)
        else:
            metric.is_active = False
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.exception('delete_driver_card failed')
        db.session.rollback()
        return jsonify({'error': 'Failed to delete driver card', 'details': str(e)}), 500


# -------------------------------------------------
# Frameworks CRUD and Competency Management
# -------------------------------------------------
@api.route('/frameworks', methods=['GET'])
def list_frameworks():
    """List frameworks.

    Query params:
    - include: 'competencies' or 'competencies,metrics' to expand relations
    - active: bool to filter is_active
    """
    try:
        include = (request.args.get('include') or '').lower()
        include_comp = 'competencies' in include
        include_metrics = 'metrics' in include
        active = request.args.get('active')

        query = Framework.query
        if active is not None:
            val = str(active).lower() in ('1', 'true', 'yes')
            query = query.filter(Framework.is_active.is_(val))

        frameworks = query.order_by(Framework.sort_order, Framework.name).all()
        return jsonify({
            'frameworks': [f.to_dict(include_competencies=include_comp, include_metrics=include_metrics) for f in frameworks],
            'count': len(frameworks)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list frameworks', 'details': str(e)}), 500


@api.route('/frameworks/<int:framework_id>', methods=['GET'])
def get_framework(framework_id: int):
    try:
        include = (request.args.get('include') or '').lower()
        include_comp = 'competencies' in include
        include_metrics = 'metrics' in include
        fw = Framework.query.get(framework_id)
        if not fw:
            return jsonify({'error': f'Framework with id {framework_id} not found'}), 404
        return jsonify({'framework': fw.to_dict(include_competencies=include_comp, include_metrics=include_metrics)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get framework', 'details': str(e)}), 500


@api.route('/frameworks', methods=['POST'])
@login_required
def create_framework():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        slug = (data.get('slug') or '').strip().lower() or _slugify(name)
        if not name:
            return jsonify({'error': 'name is required'}), 400
        # Uniqueness
        if Framework.query.filter(func.lower(Framework.name) == name.lower()).first():
            return jsonify({'error': f'Framework name "{name}" already exists'}), 400
        if Framework.query.filter(func.lower(Framework.slug) == slug.lower()).first():
            return jsonify({'error': f'Framework slug "{slug}" already exists'}), 400

        fw = Framework(
            name=name,
            slug=slug,
            description=data.get('description'),
            source=data.get('source'),
            is_builtin=bool(data.get('is_builtin', True)),
            is_active=bool(data.get('is_active', True)),
            sort_order=int(data.get('sort_order') or 0),
        )
        db.session.add(fw)
        db.session.commit()
        return jsonify({'framework': fw.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create framework', 'details': str(e)}), 500


@api.route('/frameworks/<int:framework_id>', methods=['PUT', 'PATCH'])
@login_required
def update_framework(framework_id: int):
    try:
        fw = Framework.query.get(framework_id)
        if not fw:
            return jsonify({'error': f'Framework with id {framework_id} not found'}), 404
        data = request.get_json(silent=True) or {}

        if 'name' in data and (data['name'] or '').strip():
            new_name = data['name'].strip()
            # Check uniqueness
            conflict = Framework.query.filter(func.lower(Framework.name) == new_name.lower(), Framework.id != fw.id).first()
            if conflict:
                return jsonify({'error': f'Framework name "{new_name}" already exists'}), 400
            fw.name = new_name
        if 'slug' in data and (data['slug'] or '').strip():
            new_slug = data['slug'].strip().lower()
            conflict = Framework.query.filter(func.lower(Framework.slug) == new_slug.lower(), Framework.id != fw.id).first()
            if conflict:
                return jsonify({'error': f'Framework slug "{new_slug}" already exists'}), 400
            fw.slug = new_slug
        if 'description' in data:
            fw.description = data.get('description')
        if 'source' in data:
            fw.source = data.get('source')
        if 'is_builtin' in data:
            fw.is_builtin = bool(data.get('is_builtin'))
        if 'is_active' in data:
            fw.is_active = bool(data.get('is_active'))
        if 'sort_order' in data:
            try:
                fw.sort_order = int(data.get('sort_order') or 0)
            except Exception:
                pass

        db.session.commit()
        return jsonify({'framework': fw.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update framework', 'details': str(e)}), 500


@api.route('/frameworks/<int:framework_id>', methods=['DELETE'])
@login_required
def delete_framework(framework_id: int):
    """Soft delete by default (set is_active=False). Use ?hard=true to hard delete."""
    try:
        fw = Framework.query.get(framework_id)
        if not fw:
            return jsonify({'error': f'Framework with id {framework_id} not found'}), 404
        hard = request.args.get('hard', 'false').lower() == 'true'
        if hard:
            db.session.delete(fw)
        else:
            fw.is_active = False
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete framework', 'details': str(e)}), 500


@api.route('/frameworks/<int:framework_id>/competencies', methods=['GET'])
def list_framework_competencies(framework_id: int):
    try:
        fw = Framework.query.get(framework_id)
        if not fw:
            return jsonify({'error': f'Framework with id {framework_id} not found'}), 404
        include_metrics = (request.args.get('include') or '').lower().find('metrics') >= 0
        return jsonify({
            'framework': fw.to_dict(),
            'competencies': [c.to_dict(include_metrics=include_metrics) for c in fw.competencies],
            'count': len(fw.competencies)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list competencies', 'details': str(e)}), 500


# -------------------------------
# Competencies CRUD
# -------------------------------
@api.route('/competencies', methods=['POST'])
@login_required
def create_competency():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        framework_id = data.get('framework_id')
        if not name or not framework_id:
            return jsonify({'error': 'name and framework_id are required'}), 400
        fw = Framework.query.get(framework_id)
        if not fw:
            return jsonify({'error': f'Invalid framework_id: {framework_id}'}), 400
        slug = (data.get('slug') or '').strip().lower() or _slugify(name)

        comp = Competency(
            framework_id=framework_id,
            name=name,
            slug=slug,
            description=data.get('description'),
            sort_order=int(data.get('sort_order') or 0),
        )
        db.session.add(comp)
        db.session.commit()
        return jsonify({'competency': comp.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create competency', 'details': str(e)}), 500


@api.route('/competencies/<int:competency_id>', methods=['GET'])
def get_competency(competency_id: int):
    try:
        include_metrics = (request.args.get('include') or '').lower().find('metrics') >= 0
        comp = Competency.query.get(competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        return jsonify({'competency': comp.to_dict(include_metrics=include_metrics)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get competency', 'details': str(e)}), 500


@api.route('/competencies/<int:competency_id>', methods=['PUT', 'PATCH'])
@login_required
def update_competency(competency_id: int):
    try:
        comp = Competency.query.get(competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        data = request.get_json(silent=True) or {}

        if 'framework_id' in data and data.get('framework_id') is not None:
            fw = Framework.query.get(data.get('framework_id'))
            if not fw:
                return jsonify({'error': f"Invalid framework_id: {data.get('framework_id')}"}), 400
            comp.framework_id = fw.id
        if 'name' in data and (data['name'] or '').strip():
            comp.name = data['name'].strip()
        if 'slug' in data and (data['slug'] or '').strip():
            comp.slug = data['slug'].strip().lower()
        if 'description' in data:
            comp.description = data.get('description')
        if 'sort_order' in data:
            try:
                comp.sort_order = int(data.get('sort_order') or 0)
            except Exception:
                pass

        db.session.commit()
        return jsonify({'competency': comp.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update competency', 'details': str(e)}), 500


@api.route('/competencies/<int:competency_id>', methods=['DELETE'])
@login_required
def delete_competency(competency_id: int):
    try:
        comp = Competency.query.get(competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        db.session.delete(comp)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete competency', 'details': str(e)}), 500


# -------------------------------------------------
# Role Profiles (KSAO) CRUD and management
# -------------------------------------------------

def _parse_list(val):
    if val is None:
        return []
    if isinstance(val, list):
        return val
    try:
        return json.loads(val) if isinstance(val, str) else []
    except Exception:
        return []


@api.route('/roles', methods=['GET'])
def list_roles():
    try:
        q = (request.args.get('q') or '').strip().lower()
        include = (request.args.get('include') or '').lower()
        include_ksaos = 'ksaos' in include
        include_targets = 'targets' in include
        query = RoleProfile.query
        if q:
            query = query.filter(func.lower(RoleProfile.name).like(f"%{q}%"))
        roles = query.order_by(RoleProfile.name.asc()).all()
        return jsonify({
            'roles': [r.to_dict(include_ksaos=include_ksaos, include_targets=include_targets) for r in roles],
            'count': len(roles)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list roles', 'details': str(e)}), 500


@api.route('/roles', methods=['POST'])
@admin_required
def create_role():
    try:
        data = request.get_json(silent=True) or {}
        name = (data.get('name') or '').strip()
        if not name:
            return jsonify({'error': 'name is required'}), 400
        if RoleProfile.query.filter(func.lower(RoleProfile.name) == name.lower()).first():
            return jsonify({'error': f'Role profile "{name}" already exists'}), 400
        role = RoleProfile(
            name=name,
            description=data.get('description'),
            department=data.get('department'),
            is_active=bool(data.get('is_active', True)),
        )
        db.session.add(role)
        db.session.commit()
        return jsonify({'role': role.to_dict(include_ksaos=True, include_targets=True)}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create role', 'details': str(e)}), 500


@api.route('/roles/<int:role_id>', methods=['GET'])
def get_role(role_id: int):
    try:
        include = (request.args.get('include') or '').lower()
        include_ksaos = 'ksaos' in include
        include_targets = 'targets' in include
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        payload = role.to_dict(include_ksaos=include_ksaos, include_targets=include_targets)
        return jsonify({'role': payload}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get role', 'details': str(e)}), 500


@api.route('/roles/<int:role_id>', methods=['PUT', 'PATCH'])
@admin_required
def update_role(role_id: int):
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        data = request.get_json(silent=True) or {}
        if 'name' in data and (data['name'] or '').strip():
            new_name = data['name'].strip()
            conflict = RoleProfile.query.filter(func.lower(RoleProfile.name) == new_name.lower(), RoleProfile.id != role.id).first()
            if conflict:
                return jsonify({'error': f'Role profile name "{new_name}" already exists'}), 400
            role.name = new_name
        if 'description' in data:
            role.description = data.get('description')
        if 'department' in data:
            role.department = data.get('department')
        if 'is_active' in data:
            role.is_active = bool(data.get('is_active'))
        db.session.commit()
        return jsonify({'role': role.to_dict(include_ksaos=True, include_targets=True)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update role', 'details': str(e)}), 500
@api.route('/roles/<int:role_id>', methods=['DELETE'])
@admin_required
def delete_role(role_id: int):
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        db.session.delete(role)
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete role', 'details': str(e)}), 500


@api.route('/roles/<int:role_id>/ksaos', methods=['POST'])
@admin_required
def upsert_role_ksaos(role_id: int):
    """Bulk replace K,S,A,Others for a role for wizard saves.

    Expected JSON:
    {
      "knowledge": [{"name": "Knowledge of SQL", "description": "...", "driver_card_id": 123}],
      "skills": [{"name": "Project Management", "driver_card_id": 456}],
      "abilities": [{"name": "Analytical Thinking"}],
      "others": [{"name": "Certification XYZ"}],
      "outcomes": [{"name": "Learning & Development", "driver_card_id": 789}]
    }
    """
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        data = request.get_json(silent=True) or {}

        def _parse_target_level(v):
            try:
                if v is None or v == '':
                    return None
                n = int(v)
                if 1 <= n <= 5:
                    return n
                return None
            except Exception:
                return None

        # Clear existing
        for coll in (role.knowledge_items, role.skill_items, role.ability_items, role.other_requirements, role.outcomes):
            for item in list(coll):
                db.session.delete(item)

        # Insert new
        for k in _parse_list(data.get('knowledge')):
            if (k.get('name') or '').strip():
                db.session.add(RoleKnowledge(
                    role_profile_id=role.id,
                    name=k['name'].strip(),
                    description=k.get('description'),
                    driver_card_id=k.get('driver_card_id'),
                    target_level=_parse_target_level(k.get('target_level')),
                ))
        for s in _parse_list(data.get('skills')):
            if (s.get('name') or '').strip():
                db.session.add(RoleSkill(
                    role_profile_id=role.id,
                    name=s['name'].strip(),
                    description=s.get('description'),
                    driver_card_id=s.get('driver_card_id'),
                    target_level=_parse_target_level(s.get('target_level')),
                ))
        for a in _parse_list(data.get('abilities')):
            if (a.get('name') or '').strip():
                db.session.add(RoleAbility(
                    role_profile_id=role.id,
                    name=a['name'].strip(),
                    description=a.get('description'),
                    driver_card_id=a.get('driver_card_id'),
                    target_level=_parse_target_level(a.get('target_level')),
                ))
        for o in _parse_list(data.get('others')):
            if (o.get('name') or '').strip():
                db.session.add(RoleOtherRequirement(
                    role_profile_id=role.id,
                    name=o['name'].strip(),
                    description=o.get('description'),
                    driver_card_id=o.get('driver_card_id'),
                ))
        for outcome in _parse_list(data.get('outcomes')):
            if (outcome.get('name') or '').strip():
                db.session.add(RoleOutcome(
                    role_profile_id=role.id,
                    name=outcome['name'].strip(),
                    description=outcome.get('description'),
                    driver_card_id=outcome.get('driver_card_id'),
                    target_level=_parse_target_level(outcome.get('target_level')),
                ))

        db.session.commit()
        return jsonify({'role': role.to_dict(include_ksaos=True, include_targets=False)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to upsert KSAOs', 'details': str(e)}), 500


@api.route('/roles/<int:role_id>/targets', methods=['GET'])
def list_role_targets(role_id: int):
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        return jsonify({'targets': [t.to_dict() for t in role.competency_targets], 'count': len(role.competency_targets)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list targets', 'details': str(e)}), 500


@api.route('/roles/<int:role_id>/ksao-targets', methods=['GET'])
def list_role_ksao_targets(role_id: int):
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404

        targets = []

        def add_items(items, kind: str):
            kind_slug = (kind or '').strip().lower()
            for item in items or []:
                lvl = getattr(item, 'target_level', None)
                item_id = getattr(item, 'id', None)
                targets.append({
                    'id': item_id,
                    'target_id': f"{kind_slug}:{item_id}" if item_id is not None else None,
                    'kind': kind,
                    'name': getattr(item, 'name', None) or kind,
                    'description': getattr(item, 'description', None),
                    'target_level': lvl,
                    'driver_card_id': getattr(item, 'driver_card_id', None),
                    'driver_card_name': getattr(getattr(item, 'driver_card', None), 'name', None),
                })

        add_items(role.knowledge_items, 'Knowledge')
        add_items(role.skill_items, 'Skill')
        add_items(role.ability_items, 'Ability')
        add_items(role.other_requirements, 'Other')
        add_items(role.outcomes, 'Outcome')

        targets.sort(key=lambda t: ((t.get('kind') or ''), (t.get('name') or '')))
        return jsonify({'targets': targets, 'count': len(targets)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list KSAO targets', 'details': str(e)}), 500


@api.route('/roles/<int:role_id>/targets', methods=['POST'])
@admin_required
def upsert_role_targets(role_id: int):
    """Bulk replace competency targets.

    Expected JSON: { "targets": [{"competency_id": 1, "target_level": 3, "weight": 1.0}, ...] }
    """
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        payload = request.get_json(silent=True) or {}
        targets = _parse_list(payload.get('targets'))

        # Clear existing
        for t in list(role.competency_targets):
            db.session.delete(t)

        # Insert new
        for t in targets:
            cid = t.get('competency_id')
            if not cid:
                continue
            try:
                level = int(t.get('target_level') or 3)
            except Exception:
                level = 3
            try:
                weight = float(t.get('weight') or 1.0)
            except Exception:
                weight = 1.0
            db.session.add(RoleCompetencyTarget(
                role_profile_id=role.id,
                competency_id=cid,
                target_level=level,
                weight=weight,
            ))
        db.session.commit()
        return jsonify({'targets': [t.to_dict() for t in role.competency_targets]}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to upsert targets', 'details': str(e)}), 500


@api.route('/roles/assignments', methods=['GET'])
def list_role_assignments():
    try:
        person = (request.args.get('person') or '').strip()
        q = RoleAssignment.query
        if person:
            q = q.filter(func.lower(RoleAssignment.person_identifier) == person.lower())
        items = q.order_by(RoleAssignment.assigned_date.desc()).all()
        return jsonify({'assignments': [a.to_dict() for a in items], 'count': len(items)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list assignments', 'details': str(e)}), 500


@api.route('/roles/assignments', methods=['POST'])
@admin_required
def create_role_assignment():
    try:
        data = request.get_json(silent=True) or {}
        role_id = data.get('role_profile_id') or data.get('role_id')
        person = (data.get('person_identifier') or data.get('person') or '').strip()
        if not role_id or not person:
            return jsonify({'error': 'role_profile_id and person_identifier are required'}), 400
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        # Deactivate previous active assignments for this person if requested
        if str(data.get('replace_existing', 'true')).lower() in ('true', '1', 'yes'):
            for a in RoleAssignment.query.filter_by(person_identifier=person, is_active=True).all():
                a.is_active = False
        assignment = RoleAssignment(role_profile_id=role.id, person_identifier=person, is_active=True)
        db.session.add(assignment)
        db.session.commit()
        return jsonify({'assignment': assignment.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create assignment', 'details': str(e)}), 500

# -------------------------------
# Role selection (session-scoped)
# -------------------------------

@api.route('/roles/select', methods=['GET'])
def get_selected_role():
    try:
        rid = session.get('selected_role_profile_id')
        if not rid:
            return jsonify({'selected_role_profile_id': None}), 200
        role = RoleProfile.query.get(rid)
        return jsonify({'selected_role_profile_id': rid, 'role': role.to_dict(include_ksaos=False, include_targets=False) if role else None}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get selected role', 'details': str(e)}), 500


@api.route('/roles/select', methods=['POST'])
def set_selected_role():
    try:
        data = request.get_json(silent=True) or {}
        role_id = data.get('role_profile_id') or data.get('role_id')
        if role_id is None:
            session.pop('selected_role_profile_id', None)
            return jsonify({'ok': True, 'selected_role_profile_id': None}), 200
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        session['selected_role_profile_id'] = int(role_id)
        return jsonify({'ok': True, 'selected_role_profile_id': int(role_id)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to set selected role', 'details': str(e)}), 500

@api.route('/roles/<int:role_id>/gaps', methods=['GET'])
def get_role_gaps(role_id: int):
    """Compute simple gaps vs role targets using session-scoped current proficiency.

    Current proficiency is read from session key 'competency_proficiency' as a mapping:
      { "<competency_id>": <level:int 0-5>, ... }
    Missing values default to 0. Returns list of {competency_id, competency_name, target_level, current_level, gap}.
    """
    try:
        role = RoleProfile.query.get(role_id)
        if not role:
            return jsonify({'error': f'Role with id {role_id} not found'}), 404
        prof_map = session.get('competency_proficiency') or {}
        items = []
        for t in role.competency_targets:
            cid = t.competency_id
            current = 0
            try:
                # keys may be str in session
                current = int(prof_map.get(str(cid)) or prof_map.get(cid) or 0)
            except Exception:
                current = 0
            gap = max(0, int(t.target_level or 0) - max(0, min(5, current)))
            items.append({
                'competency_id': cid,
                'competency_name': t.competency.name if t.competency else None,
                'target_level': int(t.target_level or 0),
                'current_level': max(0, min(5, current)),
                'gap': gap,
                'weight': float(t.weight or 1.0),
            })
        # simple aggregate
        total_weight = sum(x['weight'] for x in items) or 1.0
        weighted_gap = sum(x['gap'] * x['weight'] for x in items) / total_weight
        return jsonify({'gaps': items, 'weighted_gap': weighted_gap}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to compute gaps', 'details': str(e)}), 500

# -------------------------------
# Current proficiency (session)
# -------------------------------

@api.route('/proficiency', methods=['GET'])
def get_proficiency():
    """Return session-scoped competency proficiency mapping."""
    try:
        data = session.get('competency_proficiency') or {}
        return jsonify({'competency_proficiency': data}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get proficiency', 'details': str(e)}), 500


@api.route('/proficiency', methods=['POST'])
def set_proficiency():
    """Set session-scoped competency proficiency mapping.

    Expected JSON: { "competency_proficiency": { "<competency_id>": <level:int 0-5>, ... } }
    """
    try:
        payload = request.get_json(silent=True) or {}
        mapping = payload.get('competency_proficiency') or {}
        # Basic sanitize: coerce to simple dict of str->int bounded 0..5
        clean = {}
        if isinstance(mapping, dict):
            for k, v in mapping.items():
                try:
                    key = str(int(k)) if str(k).isdigit() else str(k)
                    val = int(v)
                except Exception:
                    continue
                clean[key] = max(0, min(5, val))
        session['competency_proficiency'] = clean
        return jsonify({'ok': True, 'competency_proficiency': clean}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to set proficiency', 'details': str(e)}), 500

# -------------------------------
# Reports list and detail
# -------------------------------

@api.route('/reports', methods=['GET'])
def list_reports():
    """List recent reports. Optionally filter by session via ?session_id=..."""
    try:
        active_client_id, active_engagement_id = _active_workspace_ids()
        if not active_client_id or not active_engagement_id:
            return jsonify({'reports': [], 'count': 0}), 200

        q = DynamicReport.query.filter(
            DynamicReport.client_company_id == int(active_client_id),
            DynamicReport.client_engagement_id == int(active_engagement_id),
        )
        session_id = request.args.get('session_id')
        if session_id:
            q = q.filter(DynamicReport.session_id == session_id)
        q = q.order_by(DynamicReport.created_date.desc()).limit(50)
        items = [r.to_dict(include_content=False) for r in q.all()]
        return jsonify({'reports': items, 'count': len(items)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list reports', 'details': str(e)}), 500


@api.route('/reports/<int:report_id>', methods=['GET'])
def get_report(report_id: int):
    try:
        include = (request.args.get('include') or '').lower()
        include_content = 'content' in include
        r = db.session.get(DynamicReport, report_id)
        if not r:
            return jsonify({'error': f'Report with id {report_id} not found'}), 404
        _report_workspace_match_or_404(r, route='/api/reports/<id>')
        return jsonify({'report': r.to_dict(include_content=include_content)}), 200
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        return jsonify({'error': 'Failed to get report', 'details': str(e)}), 500

# -------------------------------
# Competency <-> Metric association management
# -------------------------------
@api.route('/competencies/<int:competency_id>/metrics', methods=['GET'])
def get_competency_metrics(competency_id: int):
    try:
        comp = db.session.get(Competency, competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        return jsonify({
            'competency': comp.to_dict(),
            'metrics': [m.to_dict() for m in comp.metrics],
            'count': len(comp.metrics)
        }), 200
    except Exception as e:
        return jsonify({'error': 'Failed to get competency metrics', 'details': str(e)}), 500


@api.route('/competencies/<int:competency_id>/metrics', methods=['PUT'])
@login_required
def set_competency_metrics(competency_id: int):
    """Replace a competency's metric associations with a provided list of metric IDs.

    Body: { metric_ids: [int] }
    """
    try:
        comp = db.session.get(Competency, competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        data = request.get_json(silent=True) or {}
        metric_ids = data.get('metric_ids') or []
        if not isinstance(metric_ids, list):
            return jsonify({'error': 'metric_ids must be a list'}), 400
        metrics = Metric.query.filter(Metric.id.in_(metric_ids)).all() if metric_ids else []
        comp.metrics = metrics
        db.session.commit()
        return jsonify({'competency': comp.to_dict(include_metrics=True)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to set competency metrics', 'details': str(e)}), 500


@api.route('/competencies/<int:competency_id>/metrics/add', methods=['POST'])
@login_required
def add_metrics_to_competency(competency_id: int):
    try:
        comp = db.session.get(Competency, competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        data = request.get_json(silent=True) or {}
        metric_ids = data.get('metric_ids') or []
        if not isinstance(metric_ids, list) or not metric_ids:
            return jsonify({'error': 'metric_ids list required'}), 400
        metrics = Metric.query.filter(Metric.id.in_(metric_ids)).all()
        # Add missing ones
        existing_ids = {m.id for m in comp.metrics}
        for m in metrics:
            if m.id not in existing_ids:
                comp.metrics.append(m)
        db.session.commit()
        return jsonify({'competency': comp.to_dict(include_metrics=True)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to add metrics to competency', 'details': str(e)}), 500


@api.route('/competencies/<int:competency_id>/metrics/remove', methods=['POST'])
@login_required
def remove_metrics_from_competency(competency_id: int):
    try:
        comp = db.session.get(Competency, competency_id)
        if not comp:
            return jsonify({'error': f'Competency with id {competency_id} not found'}), 404
        data = request.get_json(silent=True) or {}
        metric_ids = data.get('metric_ids') or []
        if not isinstance(metric_ids, list) or not metric_ids:
            return jsonify({'error': 'metric_ids list required'}), 400
        remaining = [m for m in comp.metrics if m.id not in set(metric_ids)]
        comp.metrics = remaining
        db.session.commit()
        return jsonify({'competency': comp.to_dict(include_metrics=True)}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to remove metrics from competency', 'details': str(e)}), 500

@api.route('/metrics/search', methods=['GET'])
def search_metrics():
    """
    GET /api/metrics/search?q=<query> - full-text search across metrics
    Query parameters:
    - q: search term (required)
    - page: page number (default: 1)
    - per_page: items per page (default: 20, max: 100)
    """
    try:
        search_query = request.args.get('q', '').strip()
        if not search_query:
            return jsonify({
                'error': 'Missing required parameter',
                'details': 'Search query parameter "q" is required'
            }), 400
        
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 20, type=int), 100)
        
        # Perform search using model method that returns a SQLAlchemy query
        query = Metric.search_query(search_query)
        
        # Get paginated results
        metrics_pagination = query.paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format response
        response = {
            'metrics': [metric.to_dict() for metric in metrics_pagination.items],
            'pagination': {
                'page': metrics_pagination.page,
                'per_page': metrics_pagination.per_page,
                'total': metrics_pagination.total,
                'pages': metrics_pagination.pages,
                'has_next': metrics_pagination.has_next,
                'has_prev': metrics_pagination.has_prev,
                'next_num': metrics_pagination.next_num,
                'prev_num': metrics_pagination.prev_num
            },
            'search_query': search_query
        }
        
        return jsonify(response), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter format',
            'details': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@api.route('/metrics/autocomplete', methods=['GET'])
def autocomplete_metrics():
    """
    GET /api/metrics/autocomplete?q=<query> - Get autocomplete suggestions for metrics
    Returns formatted suggestions with Title Case names and descriptions
    Query parameters:
    - q: search term (required, minimum 2 characters)
    - limit: maximum number of suggestions (default: 8, max: 15)
    """
    try:
        search_query = request.args.get('q', '').strip()
        if not search_query:
            return jsonify({
                'error': 'Missing required parameter',
                'details': 'Search query parameter "q" is required'
            }), 400
        
        if len(search_query) < 2:
            return jsonify({
                'suggestions': [],
                'query': search_query
            }), 200
        
        # Get limit parameter
        limit = min(request.args.get('limit', 8, type=int), 15)
        
        # Perform search using existing search functionality (query object)
        query = Metric.search_query(search_query).limit(limit)
        metrics = query.all()
        
        # Format suggestions with Title Case names and descriptions
        suggestions = []
        for metric in metrics:
            # Convert name to Title Case
            title_case_name = metric.name.title()
            
            # Create short description (first sentence or up to 80 chars)
            description = metric.description or ""
            if description:
                # Get first sentence or truncate at 80 chars
                first_sentence = description.split('.')[0]
                if len(first_sentence) > 80:
                    description = first_sentence[:77] + "..."
                else:
                    description = first_sentence + ("." if not first_sentence.endswith('.') else "")
            else:
                description = f"A {metric.metric_type.name.lower()} metric for {metric.outcome.name.lower()}"
            
            suggestions.append({
                'id': metric.id,
                'name': title_case_name,
                'original_name': metric.name,
                'description': description,
                'outcome': metric.outcome.name,
                'type': metric.metric_type.name,
                'url': f'/metric/{metric.id}'
            })
        
        return jsonify({
            'suggestions': suggestions,
            'query': search_query,
            'count': len(suggestions)
        }), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid parameter format',
            'details': str(e)
        }), 400
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@api.route('/outcomes', methods=['GET'])
def get_outcomes():
    """
    GET /api/outcomes - return all L&D outcomes
    """
    try:
        # Filters and pagination per tests
        search = request.args.get('search', '').strip()
        category = request.args.get('category')
        level = request.args.get('level')
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 1000, type=int), 1000)

        query = LDOutcome.query
        if category:
            query = query.filter(LDOutcome.category == category)
        if level:
            query = query.filter(LDOutcome.level == level)
        if search:
            pattern = f"%{search}%"
            query = query.filter(or_(LDOutcome.name.ilike(pattern), LDOutcome.description.ilike(pattern)))

        query = query.order_by(LDOutcome.name)
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)

        response = {
            'outcomes': [o.to_dict() for o in pagination.items],
            'total': pagination.total,
        }
        # Include pagination metadata optionally
        if request.args.get('page') or request.args.get('per_page'):
            response['pagination'] = {
                'page': pagination.page,
                'per_page': pagination.per_page,
                'total': pagination.total,
                'pages': pagination.pages,
            }

        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Internal server error',
            'details': str(e)
        }), 500


@api.route('/types', methods=['GET'])
def get_metric_types():
    """
    GET /api/types - return all metric types
    """
    try:
        category = request.args.get('category')
        query = MetricType.query
        if category:
            query = query.filter(MetricType.category == category)
        types = query.all()
        return jsonify({
            'metric_types': [{
                'id': mt.id,
                'name': mt.name,
                'description': mt.description,
                'category': mt.category,
                'metrics_count': len(mt.metrics)
            } for mt in types]
        })
    except Exception as e:
        return jsonify({
            'error': 'Failed to fetch metric types',
            'details': str(e)
        }), 500


@api.route('/recommendations', methods=['POST'])
def get_recommendations():
    """
    POST /api/recommendations - Generate intelligent metric recommendations
    Request body:
    {
        "categories": [1, 2],
        "outcomes": [1, 3],
        "metrics": [5, 7],
        "context": "performance_enhancement"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Extract selection data
        category_ids = data.get('categories', [])
        outcome_ids = data.get('outcomes', [])
        metric_ids = data.get('metrics', [])
        context = data.get('context', 'general')
        
        # Generate recommendations based on selections
        # Use internal rule-based generator (avoid name collision with route below)
        recommendations = generate_rule_based_recommendations(
            category_ids, outcome_ids, metric_ids, context
        )
        
        return jsonify({
            'recommendations': recommendations,
            'context': context,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate recommendations',
            'details': str(e)
        }), 500


def generate_rule_based_recommendations(category_ids, outcome_ids, metric_ids, context):
    """Rule-based recommendation generator used by /api/recommendations.

    Note: Named distinctly to avoid colliding with the
    `/api/smart-recommendations/generate` route function defined later in this module.
    """
    recommendations = {
        'primary': [],
        'secondary': [],
        'synergies': [],
        'insights': []
    }
    
    # Get actual database objects
    categories = MetricType.query.filter(MetricType.id.in_(category_ids)).all() if category_ids else []
    outcomes = LDOutcome.query.filter(LDOutcome.id.in_(outcome_ids)).all() if outcome_ids else []
    selected_metrics = Metric.query.filter(Metric.id.in_(metric_ids)).all() if metric_ids else []
    
    # Rule 1: If no selections, provide foundational recommendations
    if not categories and not outcomes:
        recommendations['primary'] = [
            {
                'title': 'Start with Employee Engagement',
                'metrics': ['Active Participation Rate', 'Voluntary Learning Hours'],
                'reasoning': 'Engagement is the foundation of all successful L&D programs.',
                'priority': 'high',
                'type': 'behavioral'
            },
            {
                'title': 'Measure Training Effectiveness',
                'metrics': ['Completion Rate', 'Time to Competency'],
                'reasoning': 'Essential operational metrics for program ROI.',
                'priority': 'high',
                'type': 'operational'
            }
        ]
        return recommendations


# Detail endpoints expected by tests
@api.route('/outcomes/<int:outcome_id>', methods=['GET'])
def get_outcome_by_id(outcome_id):
    outcome = LDOutcome.query.get(outcome_id)
    if not outcome:
        return jsonify({'error': f'Outcome with id {outcome_id} not found'}), 404
    return jsonify(outcome.to_dict()), 200


@api.route('/types/<int:type_id>', methods=['GET'])
def get_metric_type_by_id(type_id):
    metric_type = MetricType.query.get(type_id)
    if not metric_type:
        return jsonify({'error': f'Metric type with id {type_id} not found'}), 404
    return jsonify(metric_type.to_dict()), 200


@api.route('/metrics/<int:metric_id>', methods=['GET'])
def get_metric_by_id(metric_id):
    metric = Metric.query.get(metric_id)
    if not metric:
        return jsonify({'error': f'Metric with id {metric_id} not found'}), 404
    return jsonify(metric.to_dict()), 200


# -------------------------------
# Metrics CRUD (admin only)
# -------------------------------
@api.route('/metrics', methods=['POST'])
@login_required
def create_metric():
    """
    POST /api/metrics
    Body: { name, outcome_id, metric_type_id, description?, measurement_method?, data_collection?,
            success_criteria?, frequency?, unit_of_measure?, example?, data_source?, is_active?,
            competency_ids?: [int] }
    """
    try:
        data = request.get_json(silent=True) or {}

        name = (data.get('name') or '').strip()
        outcome_id = data.get('outcome_id')
        metric_type_id = data.get('metric_type_id')
        if not name or not outcome_id or not metric_type_id:
            return jsonify({'error': 'name, outcome_id, and metric_type_id are required'}), 400

        # Validate foreign keys
        outcome = LDOutcome.query.get(outcome_id)
        if not outcome:
            return jsonify({'error': f'Invalid outcome_id: {outcome_id}'}), 400
        mtype = MetricType.query.get(metric_type_id)
        if not mtype:
            return jsonify({'error': f'Invalid metric_type_id: {metric_type_id}'}), 400

        identifier_type = _normalize_identifier_type(data.get('identifier_type'))
        driver_chain = _parse_driver_chain(data.get('driver_chain'))

        metric = Metric(
            name=name,
            description=data.get('description'),
            outcome_id=outcome.id,
            metric_type_id=mtype.id,
            identifier_type=identifier_type,
            driver_chain=json.dumps(driver_chain) if isinstance(driver_chain, (dict, list)) else None,
            measurement_method=data.get('measurement_method'),
            data_collection=data.get('data_collection'),
            success_criteria=data.get('success_criteria'),
            frequency=data.get('frequency'),
            unit_of_measure=data.get('unit_of_measure'),
            example=data.get('example'),
            data_source=data.get('data_source'),
            is_active=bool(data.get('is_active', True)),
        )

        # Optional competency associations
        competency_ids = data.get('competency_ids') or []
        if isinstance(competency_ids, list) and competency_ids:
            comps = Competency.query.filter(Competency.id.in_(competency_ids)).all()
            # Replace associations
            metric.competencies = comps

        db.session.add(metric)
        db.session.commit()
        return jsonify({'metric': metric.to_dict()}), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create metric', 'details': str(e)}), 500


@api.route('/metrics/<int:metric_id>', methods=['PUT', 'PATCH'])
@login_required
def update_metric(metric_id: int):
    """
    PUT/PATCH /api/metrics/<id>
    Body: updatable fields { name?, outcome_id?, metric_type_id?, description?, measurement_method?,
            data_collection?, success_criteria?, frequency?, unit_of_measure?, example?, data_source?,
            is_active?, competency_ids?: [int] }
    """
    try:
        metric = Metric.query.get(metric_id)
        if not metric:
            return jsonify({'error': f'Metric with id {metric_id} not found'}), 404

        data = request.get_json(silent=True) or {}

        if 'name' in data and (data['name'] or '').strip():
            metric.name = data['name'].strip()
        if 'description' in data:
            metric.description = data.get('description')
        if 'measurement_method' in data:
            metric.measurement_method = data.get('measurement_method')
        if 'data_collection' in data:
            metric.data_collection = data.get('data_collection')
        if 'success_criteria' in data:
            metric.success_criteria = data.get('success_criteria')
        if 'frequency' in data:
            metric.frequency = data.get('frequency')
        if 'unit_of_measure' in data:
            metric.unit_of_measure = data.get('unit_of_measure')
        if 'example' in data:
            metric.example = data.get('example')
        if 'data_source' in data:
            metric.data_source = data.get('data_source')
        if 'is_active' in data:
            metric.is_active = bool(data.get('is_active'))
        if 'identifier_type' in data:
            metric.identifier_type = _normalize_identifier_type(data.get('identifier_type'))
        if 'driver_chain' in data:
            dc = _parse_driver_chain(data.get('driver_chain'))
            metric.driver_chain = json.dumps(dc) if isinstance(dc, (dict, list)) else None

        # Update foreign keys if provided
        if 'outcome_id' in data and data.get('outcome_id') is not None:
            outcome = LDOutcome.query.get(data.get('outcome_id'))
            if not outcome:
                return jsonify({'error': f"Invalid outcome_id: {data.get('outcome_id')}"}), 400
            metric.outcome_id = outcome.id
        if 'metric_type_id' in data and data.get('metric_type_id') is not None:
            mtype = MetricType.query.get(data.get('metric_type_id'))
            if not mtype:
                return jsonify({'error': f"Invalid metric_type_id: {data.get('metric_type_id')}"}), 400
            metric.metric_type_id = mtype.id

        # Replace competency associations if provided
        if 'competency_ids' in data:
            competency_ids = data.get('competency_ids') or []
            if isinstance(competency_ids, list) and competency_ids:
                comps = Competency.query.filter(Competency.id.in_(competency_ids)).all()
                metric.competencies = comps
            else:
                metric.competencies = []

        db.session.commit()
        return jsonify({'metric': metric.to_dict()}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update metric', 'details': str(e)}), 500


@api.route('/metrics/<int:metric_id>', methods=['DELETE'])
@login_required
def delete_metric(metric_id: int):
    """
    DELETE /api/metrics/<id>
    Soft-delete by default (set is_active=False). Use ?hard=true to hard delete.
    """
    try:
        metric = Metric.query.get(metric_id)
        if not metric:
            return jsonify({'error': f'Metric with id {metric_id} not found'}), 404

        hard = request.args.get('hard', 'false').lower() == 'true'
        if hard:
            db.session.delete(metric)
        else:
            metric.is_active = False
        db.session.commit()
        return jsonify({'success': True}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete metric', 'details': str(e)}), 500


@api.route('/translate', methods=['POST'])
def translate_metrics():
    # Validate content type
    if not request.is_json:
        return jsonify({'error': 'Invalid or missing JSON body'}), 400
    try:
        data = request.get_json(silent=True)
    except Exception:
        data = None
    if not data:
        return jsonify({'error': 'Invalid JSON payload'}), 400

    outcome_id = data.get('outcome_id')
    metric_type_id = data.get('metric_type_id')
    if not outcome_id or not metric_type_id:
        return jsonify({'error': 'Both outcome_id and metric_type_id are required'}), 400

    outcome = LDOutcome.query.get(outcome_id)
    if not outcome:
        return jsonify({'error': f'Invalid outcome_id: {outcome_id}'}), 400
    metric_type = MetricType.query.get(metric_type_id)
    if not metric_type:
        return jsonify({'error': f'Invalid metric_type_id: {metric_type_id}'}), 400

    # Produce simple deterministic suggestions used for tests
    suggestions = [
        {
            'name': f'{outcome.name} - {metric_type.name} Suggestion 1',
            'description': f'Measure {outcome.name.lower()} using a {metric_type.name.lower()} approach.',
            'measurement_method': 'Survey',
            'data_collection': 'Monthly',
            'success_criteria': '80%'
        }
    ]
    return jsonify({'suggestions': suggestions}), 200


# JSON error handlers for API blueprint
@api.errorhandler(404)
def api_handle_404(e):
    return jsonify({'error': 'Resource not found'}), 404


@api.errorhandler(405)
def api_handle_405(e):
    return jsonify({'error': 'Method not allowed'}), 405


# ---------------------------------------------
# Metric Card - enriched response aggregation
# ---------------------------------------------
@api.route('/metric-cards/<int:metric_id>', methods=['GET'])
def get_metric_card(metric_id: int):
    """Return a fully enriched metric card structure for UI rendering.

    Includes:
    - identifier_type label
    - associated frameworks (via competencies)
    - ordered driver chain based on identifier_type
    - classification details mapping existing fields
    """
    try:
        metric = Metric.query.join(LDOutcome).join(MetricType).filter(Metric.id == metric_id).first()
        if not metric:
            return jsonify({'error': f'Metric card with id {metric_id} not found'}), 404

        base = metric.to_dict()

        id_type = (base.get('identifier_type') or '').lower()
        chain = base.get('driver_chain') or {}
        # Build ordered stages according to identifier type
        stages = []
        if id_type == 'concept':
            stages = [
                {'key': 'drives_behaviors', 'title': 'Drives Behavior', 'items': chain.get('drives_behaviors') or []},
                {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': chain.get('measured_by_kpis') or []},
                {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': chain.get('leads_to_outcomes') or []},
            ]
        elif id_type == 'behavior':
            stages = [
                {'key': 'driven_by_concepts', 'title': 'Driven by Concept', 'items': chain.get('driven_by_concepts') or []},
                {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': chain.get('measured_by_kpis') or []},
                {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': chain.get('leads_to_outcomes') or []},
            ]
        elif id_type == 'kpi':
            stages = [
                {'key': 'measures_behaviors', 'title': 'Measures Behavior', 'items': chain.get('measures_behaviors') or chain.get('drives_behaviors') or []},
                {'key': 'indicates_concepts', 'title': 'Indicates Concept', 'items': chain.get('indicates_concepts') or chain.get('driven_by_concepts') or []},
                {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': chain.get('leads_to_outcomes') or []},
            ]
        elif id_type == 'outcome':
            stages = [
                {'key': 'driven_by_behaviors', 'title': 'Driven by Behavior', 'items': chain.get('driven_by_behaviors') or chain.get('drives_behaviors') or []},
                {'key': 'driven_by_concepts', 'title': 'Driven by Concept', 'items': chain.get('driven_by_concepts') or []},
                {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': chain.get('measured_by_kpis') or []},
            ]
        else:
            # Fallback neutral ordering
            stages = [
                {'key': 'drives_behaviors', 'title': 'Drives Behavior', 'items': chain.get('drives_behaviors') or []},
                {'key': 'measured_by_kpis', 'title': 'Measured by KPI', 'items': chain.get('measured_by_kpis') or []},
                {'key': 'leads_to_outcomes', 'title': 'Leads to Outcome', 'items': chain.get('leads_to_outcomes') or []},
            ]

        card = {
            'id': base['id'],
            'title': base['name'],
            'description': base.get('description'),
            'identifier_type': id_type or 'concept',
            'outcome': {'id': base.get('outcome_id'), 'name': base.get('outcome_name')},
            'metric_type': {'id': base.get('metric_type_id'), 'name': base.get('metric_type_name')},
            'associated_frameworks': base.get('associated_frameworks') or [],
            'driver_chain': stages,
            'classification': {
                'ld_outcome': base.get('outcome_name'),
                'metric_type': base.get('metric_type_name'),
                'data_collection': base.get('data_collection'),
                'frequency': base.get('frequency'),
            },
        }
        return jsonify({'metric_card': card}), 200
    except Exception as e:
        logger.exception('get_metric_card failed')
        return jsonify({'error': 'Failed to get metric card', 'details': str(e)}), 500
    
    # Rule 2: Single category recommendations
    if len(categories) == 1:
        category = categories[0]
        category_name = category.name.lower()
        
        if 'operational' in category_name:
            recommendations['primary'].append({
                'title': 'Operational Excellence Focus',
                'metrics': ['Training ROI', 'Cost per Employee', 'Performance Improvement'],
                'reasoning': 'Operational metrics provide clear business value and efficiency tracking.',
                'priority': 'high',
                'type': 'operational'
            })
            recommendations['secondary'].append({
                'title': 'Consider Adding Behavioral Insights',
                'metrics': ['Employee Satisfaction', 'Engagement Score'],
                'reasoning': 'Behavioral metrics complement operational data with human insights.',
                'priority': 'medium',
                'type': 'behavioral'
            })
        
        elif 'behavioral' in category_name:
            recommendations['primary'].append({
                'title': 'Human-Centered Approach',
                'metrics': ['Learning Motivation', 'Peer Collaboration', 'Cultural Adoption'],
                'reasoning': 'Behavioral metrics reveal the human side of learning effectiveness.',
                'priority': 'high',
                'type': 'behavioral'
            })
            recommendations['secondary'].append({
                'title': 'Add Scientific Validation',
                'metrics': ['Memory Retention', 'Cognitive Load'],
                'reasoning': 'Neuroscience metrics provide scientific backing for behavioral observations.',
                'priority': 'medium',
                'type': 'neuroscience'
            })
        
        elif 'neuroscience' in category_name:
            recommendations['primary'].append({
                'title': 'Science-Based Learning',
                'metrics': ['Memory Consolidation', 'Attention Span', 'Neuroplasticity Index'],
                'reasoning': 'Neuroscience metrics provide evidence-based insights into learning processes.',
                'priority': 'high',
                'type': 'neuroscience'
            })
            recommendations['secondary'].append({
                'title': 'Connect to Business Outcomes',
                'metrics': ['Performance Metrics', 'Productivity Gains'],
                'reasoning': 'Operational metrics help translate scientific insights into business value.',
                'priority': 'medium',
                'type': 'operational'
            })
    
    # Rule 3: Multiple category synergies
    if len(categories) >= 2:
        category_types = [cat.name.lower() for cat in categories]
        
        if 'operational' in str(category_types) and 'behavioral' in str(category_types):
            recommendations['synergies'].append({
                'title': 'Performance & Culture Balance',
                'combination': ['operational', 'behavioral'],
                'synergy_score': 0.85,
                'metrics': ['ROI + Engagement', 'Efficiency + Satisfaction', 'Results + Culture'],
                'reasoning': 'Combining operational efficiency with behavioral insights creates comprehensive L&D measurement.'
            })
        
        if 'neuroscience' in str(category_types):
            recommendations['synergies'].append({
                'title': 'Scientific Learning Optimization',
                'combination': category_types,
                'synergy_score': 0.92,
                'metrics': ['Cognitive Load + Performance', 'Memory + Retention', 'Attention + Engagement'],
                'reasoning': 'Neuroscience provides the scientific foundation for optimizing all other metrics.'
            })
    
    # Rule 4: Outcome-specific recommendations
    for outcome in outcomes:
        outcome_name = outcome.name.lower()
        
        if 'engagement' in outcome_name:
            recommendations['insights'].append({
                'title': 'Employee Engagement Strategy',
                'outcome': outcome.name,
                'recommended_metrics': ['Voluntary Participation', 'Learning Satisfaction', 'Peer Interaction'],
                'success_factors': ['Intrinsic motivation', 'Social learning', 'Recognition programs'],
                'priority': 'high'
            })
        
        elif 'performance' in outcome_name:
            recommendations['insights'].append({
                'title': 'Performance Enhancement Focus',
                'outcome': outcome.name,
                'recommended_metrics': ['Skill Assessment', 'Productivity Gains', 'Quality Metrics'],
                'success_factors': ['Clear objectives', 'Regular feedback', 'Practical application'],
                'priority': 'high'
            })
        
        elif 'retention' in outcome_name:
            recommendations['insights'].append({
                'title': 'Retention Improvement Strategy',
                'outcome': outcome.name,
                'recommended_metrics': ['Career Development', 'Internal Mobility', 'Job Satisfaction'],
                'success_factors': ['Growth opportunities', 'Work-life balance', 'Recognition'],
                'priority': 'high'
            })
    
    # Rule 5: Context-specific recommendations
    if context == 'performance_enhancement':
        recommendations['insights'].append({
            'title': 'Performance-Driven Learning',
            'context': context,
            'recommended_approach': 'Focus on measurable skill improvements and productivity gains',
            'key_metrics': ['Time to Proficiency', 'Performance Scores', 'Error Reduction'],
            'timeline': '3-6 months for visible results'
        })
    
    elif context == 'culture_transformation':
        recommendations['insights'].append({
            'title': 'Culture Change Through Learning',
            'context': context,
            'recommended_approach': 'Emphasize behavioral metrics and social learning indicators',
            'key_metrics': ['Collaboration Index', 'Knowledge Sharing', 'Cultural Adoption'],
            'timeline': '6-12 months for cultural shifts'
        })
    
    return recommendations


def generate_external_concept_recommendations(selected_metrics, context, org_context):
    """Generate recommendations for concepts NOT in the database based on selected metrics."""
    
    # Extract metric names and descriptions for AI context
    metric_info = []
    for metric in selected_metrics:
        metric_info.append({
            'name': metric.name,
            'description': metric.description,
            'outcome': metric.outcome.name,
            'type': metric.metric_type.name
        })
    
    # Try AI-powered recommendations first
    if recommendation_engine.ollama.available:
        ai_recommendations = _generate_ai_external_recommendations(metric_info, context, org_context)
        if ai_recommendations:
            return ai_recommendations
    
    # Fallback to rules-based external recommendations
    return _generate_rules_external_recommendations(metric_info, context, org_context)


def _generate_ai_external_recommendations(metric_info, context, org_context):
    """Generate AI-powered external concept recommendations."""
    try:
        system_prompt = """You are an expert Learning & Development consultant. Based on selected metrics, 
        suggest 3-5 related concepts that are NOT already in the user's database but would complement 
        their current metrics. Focus on practical, measurable concepts with clear definitions.
        
        Return your response in JSON format:
        {
            "recommendations": [
                {
                    "concept": "Concept Name",
                    "definition": "Clear, practical definition",
                    "relevance": "Why this relates to selected metrics",
                    "measurement_approach": "How to measure this concept"
                }
            ]
        }"""
        
        user_prompt = f"""
        Based on these selected L&D metrics, suggest related concepts NOT in the database:
        
        Selected Metrics:
        {chr(10).join([f"- {m['name']}: {m['description']}" for m in metric_info])}
        
        Context: {context}
        Organization Context: {org_context}
        
        Suggest 3-5 complementary concepts that would enhance this metric selection.
        Focus on concepts like mindfulness, cognitive load, psychological safety, etc.
        """
        
        response = recommendation_engine.ollama.generate(
            model=recommendation_engine.model_name,
            prompt=user_prompt,
            system_prompt=system_prompt,
            format="json",
            temperature=0.7
        )
        
        if response:
            import json
            try:
                parsed_response = json.loads(response)
                return parsed_response.get('recommendations', [])
            except json.JSONDecodeError:
                logger.warning("Failed to parse AI response as JSON, falling back to rules")
                return None
                
    except Exception as e:
        logger.error(f"AI external recommendations failed: {str(e)}")
        return None


def _generate_rules_external_recommendations(metric_info, context, org_context):
    """Generate rules-based external concept recommendations."""
    
    # Analyze selected metrics to determine focus areas
    metric_names = [m['name'].lower() for m in metric_info]
    metric_types = [m['type'].lower() for m in metric_info]
    outcomes = [m['outcome'].lower() for m in metric_info]
    
    recommendations = []
    
    # Rule 1: If attention/focus metrics are selected, suggest mindfulness
    if any('attention' in name or 'focus' in name for name in metric_names):
        recommendations.append({
            'concept': 'Mindfulness',
            'definition': 'Being present and aware in the workplace; the practice of focused attention and emotional regulation',
            'relevance': 'Directly enhances attention and focus capabilities measured in your selected metrics',
            'measurement_approach': 'Mindfulness surveys, attention span tests, stress level assessments'
        })
    
    # Rule 2: If engagement metrics are selected, suggest psychological safety
    if any('engagement' in name or 'participation' in name for name in metric_names):
        recommendations.append({
            'concept': 'Psychological Safety',
            'definition': 'The belief that one can speak up without risk of punishment or humiliation',
            'relevance': 'Creates the foundation for authentic engagement and participation in learning activities',
            'measurement_approach': 'Team climate surveys, speaking-up frequency, error reporting rates'
        })
    
    # Rule 3: If cognitive/memory metrics are selected, suggest cognitive load
    if any('memory' in name or 'cognitive' in name or 'retention' in name for name in metric_names):
        recommendations.append({
            'concept': 'Cognitive Load',
            'definition': 'The mental effort required to process information; managing complexity in learning materials',
            'relevance': 'Optimizing cognitive load improves memory retention and learning effectiveness',
            'measurement_approach': 'Task complexity ratings, mental effort scales, performance under different load conditions'
        })
    
    # Rule 4: If performance metrics are selected, suggest flow state
    if any('performance' in name or 'productivity' in name for name in metric_names):
        recommendations.append({
            'concept': 'Flow State',
            'definition': 'The mental state of complete immersion and optimal performance in an activity',
            'relevance': 'Flow states maximize performance and learning efficiency in your measured areas',
            'measurement_approach': 'Flow experience questionnaires, time-on-task metrics, performance quality indicators'
        })
    
    # Rule 5: If behavioral metrics are present, suggest emotional intelligence
    if any('behavioral' in mtype for mtype in metric_types):
        recommendations.append({
            'concept': 'Emotional Intelligence',
            'definition': 'The ability to recognize, understand, and manage emotions in oneself and others',
            'relevance': 'Underlies many behavioral metrics and interpersonal learning effectiveness',
            'measurement_approach': 'EQ assessments, 360-degree feedback, conflict resolution success rates'
        })
    
    # Rule 6: Context-specific recommendations
    if 'remote' in org_context.lower() or 'virtual' in org_context.lower():
        recommendations.append({
            'concept': 'Digital Wellness',
            'definition': 'Healthy technology use patterns and managing digital overwhelm in remote work environments',
            'relevance': 'Critical for remote workforce effectiveness and sustainable learning practices',
            'measurement_approach': 'Screen time analytics, digital break frequency, virtual meeting fatigue scores'
        })
    
    # Ensure we have at least 3 recommendations
    if len(recommendations) < 3:
        default_recommendations = [
            {
                'concept': 'Growth Mindset',
                'definition': 'The belief that abilities and intelligence can be developed through effort and learning',
                'relevance': 'Fundamental to all learning and development initiatives',
                'measurement_approach': 'Mindset surveys, response to challenges, learning goal orientation'
            },
            {
                'concept': 'Self-Efficacy',
                'definition': 'Confidence in one\'s ability to execute behaviors necessary to produce specific performance attainments',
                'relevance': 'Drives motivation and persistence in learning activities',
                'measurement_approach': 'Self-efficacy scales, goal achievement rates, challenge-seeking behavior'
            }
        ]
        
        for rec in default_recommendations:
            if len(recommendations) < 5 and rec not in recommendations:
                recommendations.append(rec)
    
    return recommendations[:5]  # Return max 5 recommendations


@api.route('/ai-recommendations', methods=['POST'])
def get_ai_recommendations():
    """
    POST /api/ai-recommendations - Generate AI-powered recommendations
    Request body:
    {
        "categories": [1, 2],
        "outcomes": [1, 3],
        "context": "performance improvement"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        selections = {
            'categories': data.get('categories', []),
            'outcomes': data.get('outcomes', []),
            'metrics': data.get('metrics', [])
        }
        context = data.get('context', '')
        
        recommendations = recommendation_engine.generate_recommendations(selections, context)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'generated_by': 'ai' if recommendation_engine.ollama.available else 'rules',
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate AI recommendations',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations', methods=['POST'])
def get_smart_recommendations():
    """
    POST /api/smart-recommendations - Generate smart AI recommendations based on selected metric cards
    Request body:
    {
        "selected_metrics": [1, 5, 12],
        "context": "performance improvement",
        "organization_context": "tech company with remote workforce"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        selected_metric_ids = data.get('selected_metrics', [])
        context = data.get('context', '')
        org_context = data.get('organization_context', '')
        
        if not selected_metric_ids:
            return jsonify({'error': 'At least one metric must be selected'}), 400
        
        # Get selected metrics from database
        selected_metrics = Metric.query.filter(Metric.id.in_(selected_metric_ids)).all()
        if not selected_metrics:
            return jsonify({'error': 'No valid metrics found for the provided IDs'}), 400
        
        # Generate smart recommendations for concepts NOT in database
        recommendations = generate_external_concept_recommendations(selected_metrics, context, org_context)
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'selected_metrics_count': len(selected_metrics),
            'generated_by': 'ai' if recommendation_engine.ollama.available else 'rules',
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Smart recommendations error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate smart recommendations',
            'details': str(e)
        }), 500


@api.route('/dynamic-reports', methods=['POST'])
def create_dynamic_report():
    """
    POST /api/dynamic-reports - Create and generate a dynamic PDF report
    Request body:
    {
        "title": "Q4 L&D Metrics Report",
        "template_type": "comprehensive",
        "selected_outcomes": [1, 2, 3],
        "selected_metrics": [5, 7, 12, 15],
        "ai_recommendations": [...],
        "session_id": 123,
        "generation_context": {...}
    }
    """
    try:
        from app.services.report_generator import DynamicReportGenerator, ReportConfig
        from app.workspace_stamp import get_active_workspace
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['title', 'template_type', 'selected_outcomes', 'selected_metrics', 'session_id']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Validate template type
        if data['template_type'] not in ['comprehensive', 'basic']:
            return jsonify({
                'error': 'Invalid template_type',
                'details': 'Must be either "comprehensive" or "basic"'
            }), 400
        
        # Create report configuration
        gen_ctx = data.get('generation_context', {}) or {}
        ws = get_active_workspace() or {}
        if not ws.get('active_client_id') or not ws.get('active_engagement_id'):
            return jsonify({
                'error': 'Active workspace required',
                'details': 'Select a client and engagement before generating a saved report.'
            }), 400
        if ws.get('active_client_id') and not gen_ctx.get('client_company_id'):
            gen_ctx['client_company_id'] = ws.get('active_client_id')
        if ws.get('active_engagement_id') and not gen_ctx.get('client_engagement_id'):
            gen_ctx['client_engagement_id'] = ws.get('active_engagement_id')
        if ws.get('client_slug') and not gen_ctx.get('client_slug'):
            gen_ctx['client_slug'] = ws.get('client_slug')
        if ws.get('engagement_slug') and not gen_ctx.get('engagement_slug'):
            gen_ctx['engagement_slug'] = ws.get('engagement_slug')

        config = ReportConfig(
            title=data['title'],
            template_type=data['template_type'],
            selected_outcomes=data['selected_outcomes'],
            selected_metrics=data['selected_metrics'],
            ai_recommendations=data.get('ai_recommendations', []),
            session_id=data['session_id'],
            generation_context=gen_ctx
        )
        
        # Generate report
        generator = DynamicReportGenerator()
        report = generator.generate_report(config)
        
        return jsonify({
            'success': True,
            'report': report.to_dict(),
            'message': 'Report generation completed successfully'
        }), 201
        
    except Exception as e:
        logger.error(f"Dynamic report creation error: {str(e)}")
        return jsonify({
            'error': 'Failed to create dynamic report',
            'details': str(e)
        }), 500


@api.route('/dynamic-reports/<int:report_id>', methods=['GET'])
def get_dynamic_report(report_id):
    """GET /api/dynamic-reports/<id> - Get dynamic report details"""
    try:
        report = db.session.get(DynamicReport, report_id)
        if not report:
            return jsonify({'error': f'Report with id {report_id} not found'}), 404
        _report_workspace_match_or_404(report, route='/api/dynamic-reports/<id>')
        include_content = request.args.get('include_content', 'false').lower() == 'true'
        
        return jsonify({
            'success': True,
            'report': report.to_dict(include_content=include_content)
        }), 200
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        return jsonify({
            'error': 'Failed to retrieve report',
            'details': str(e)
        }), 500


@api.route('/dynamic-reports/<int:report_id>/download', methods=['GET'])
def download_dynamic_report(report_id):
    """GET /api/dynamic-reports/<id>/download - Download PDF report"""
    try:
        from flask import send_file
        from app.workspace_stamp import stamp_filename, workspace_from_pdf_path, get_active_workspace
        
        report = db.session.get(DynamicReport, report_id)
        if not report:
            return jsonify({'error': f'Report with id {report_id} not found'}), 404
        _report_workspace_match_or_404(report, route='/api/dynamic-reports/<id>/download')
        
        if not report.pdf_path or not os.path.exists(report.pdf_path):
            return jsonify({
                'error': 'PDF file not found',
                'details': 'Report may still be generating or file was deleted'
            }), 404
        
        # Increment download counter
        report.increment_download()

        ws = workspace_from_pdf_path(report.pdf_path) or get_active_workspace()
        download_name = stamp_filename(f"{report.title.replace(' ', '_')}.pdf", workspace=ws)
        
        return send_file(
            report.pdf_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        return jsonify({
            'error': 'Failed to download report',
            'details': str(e)
        }), 500


@api.route('/dynamic-reports/<int:report_id>/progress', methods=['GET'])
def get_report_progress(report_id):
    """GET /api/dynamic-reports/<id>/progress - Get report generation progress"""
    try:
        report = db.session.get(DynamicReport, report_id)
        if not report:
            return jsonify({'error': f'Report with id {report_id} not found'}), 404
        _report_workspace_match_or_404(report, route='/api/dynamic-reports/<id>/progress')
        
        return jsonify({
            'success': True,
            'progress': {
                'status': report.generation_status,
                'progress': report.generation_progress,
                'estimated_pages': report.estimated_pages,
                'created_date': report.created_date.isoformat() if report.created_date else None,
                'generated_date': report.generated_date.isoformat() if report.generated_date else None
            }
        }), 200
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        return jsonify({
            'error': 'Failed to get report progress',
            'details': str(e)
        }), 500


@api.route('/dynamic-reports/session/<session_id>', methods=['GET'])
def get_session_reports(session_id):
    """GET /api/dynamic-reports/session/<id> - Get all reports for a session"""
    try:
        active_client_id, active_engagement_id = _active_workspace_ids()
        if not active_client_id or not active_engagement_id:
            return jsonify({'success': True, 'reports': [], 'total': 0, 'session_id': session_id})
        # Query reports for session
        reports = (
            DynamicReport.query
            .filter(
                DynamicReport.session_id == str(session_id),
                DynamicReport.client_company_id == int(active_client_id),
                DynamicReport.client_engagement_id == int(active_engagement_id),
            )
            .order_by(DynamicReport.created_date.desc())
            .all()
        )
        return jsonify({
            'success': True,
            'reports': [r.to_dict() for r in reports],
            'total': len(reports),
            'session_id': session_id
        })
        
    except Exception as e:
        if isinstance(e, HTTPException):
            raise
        return jsonify({
            'error': 'Failed to retrieve session reports',
            'details': str(e)
        }), 500


@api.route('/report-templates', methods=['GET'])
def get_report_templates():
    """GET /api/report-templates - Get available report templates"""
    try:
        templates = ReportTemplate.query.filter_by(is_active=True).all()
        
        return jsonify({
            'success': True,
            'templates': [template.to_dict() for template in templates],
            'count': len(templates)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve report templates',
            'details': str(e)
        }), 500


@api.route('/report-templates', methods=['POST'])
def create_report_template():
    """POST /api/report-templates - Create a new report template"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        # Validate required fields
        required_fields = ['name', 'template_type', 'sections']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({
                'error': 'Missing required fields',
                'missing_fields': missing_fields
            }), 400
        
        # Create template
        template = ReportTemplate(
            name=data['name'],
            description=data.get('description', ''),
            template_type=data['template_type'],
            sections=json.dumps(data['sections']),
            styling=json.dumps(data.get('styling', {})),
            created_by=data.get('created_by')
        )
        
        db.session.add(template)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'template': template.to_dict(),
            'message': 'Template created successfully'
        }), 201
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to create report template',
            'details': str(e)
        }), 500


@api.route('/report-analytics/<int:report_id>', methods=['GET'])
def get_report_analytics(report_id):
    """GET /api/report-analytics/<id> - Get analytics for a specific report"""
    try:
        report = DynamicReport.query.get_or_404(report_id)
        analytics = report.analytics
        
        if not analytics:
            return jsonify({
                'success': True,
                'analytics': None,
                'message': 'No analytics available for this report'
            }), 200
        
        return jsonify({
            'success': True,
            'analytics': analytics.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve report analytics',
            'details': str(e)
        }), 500


@api.route('/report-analytics/summary', methods=['GET'])
def get_analytics_summary():
    """GET /api/report-analytics/summary - Get overall analytics summary"""
    try:
        # Get basic statistics
        total_reports = DynamicReport.query.count()
        completed_reports = DynamicReport.query.filter_by(generation_status='completed').count()
        failed_reports = DynamicReport.query.filter_by(generation_status='failed').count()
        
        # Get template usage
        template_usage = db.session.query(
            ReportTemplate.name,
            func.count(DynamicReport.id).label('usage_count')
        ).join(DynamicReport).group_by(ReportTemplate.name).all()
        
        # Get recent reports
        recent_reports = DynamicReport.query.order_by(
            DynamicReport.created_date.desc()
        ).limit(5).all()
        
        return jsonify({
            'success': True,
            'summary': {
                'total_reports': total_reports,
                'completed_reports': completed_reports,
                'failed_reports': failed_reports,
                'success_rate': (completed_reports / total_reports * 100) if total_reports > 0 else 0,
                'template_usage': [
                    {'template': name, 'count': count} 
                    for name, count in template_usage
                ],
                'recent_reports': [report.to_dict() for report in recent_reports]
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve analytics summary',
            'details': str(e)
        }), 500


@api.route('/generate-report', methods=['POST'])
def generate_report():
    """
    POST /api/generate-report - Generate AI-powered L&D report
    Request body:
    {
        "metrics": ["Employee Engagement Score", "Training Completion Rate"],
        "outcomes": ["Performance Improvement", "Skill Development"],
        "context": "Q4 performance review context"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No JSON data provided'}), 400
        
        metrics = data.get('metrics', [])
        outcomes = data.get('outcomes', [])
        context = data.get('context', '')
        
        if not metrics:
            return jsonify({'error': 'At least one metric must be selected'}), 400
        
        report_content = report_generator.generate_report_content(metrics, outcomes, context)
        
        return jsonify({
            'success': True,
            'report_content': report_content,
            'generated_by': 'ai' if report_generator.ollama.available else 'template',
            'timestamp': time.time(),
            'metrics_count': len(metrics),
            'outcomes_count': len(outcomes)
        })
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to generate report',
            'details': str(e)
        }), 500


def authenticate_user():
    """Check if user is authenticated via session or API key."""
    # Check for API key in headers
    api_key = request.headers.get('X-API-Key')
    if api_key:
        user = AdminUser.query.filter_by(api_key=api_key).first()
        if user and user.is_active:
            return user
    
    # Check for session authentication
    admin_session_id = session.get('admin_user_id') or session.get('user_id')
    if admin_session_id:
        user = AdminUser.query.get(admin_session_id)
        if user and user.is_active:
            return user
    
    return None

@api.route('/auth/login', methods=['POST'])
def login():
    """
    POST /api/auth/login - Authenticate user for AI event analysis
    Request body:
    {
        "username": "admin",
        "password": "password"
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({'error': 'No JSON data provided', 'success': False}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({'error': 'Username and password are required', 'success': False}), 400
    
    user = AdminUser.query.filter_by(username=username).first()
    if not user or not user.check_password(password) or not user.is_active:
        return jsonify({'error': 'Invalid username or password', 'success': False}), 401
    
    # Create session
    session['user_id'] = user.id
    session.permanent = True
    
    return jsonify({
        'success': True,
        'user': user.to_dict(),
        'message': 'Login successful'
    })

@api.route('/auth/logout', methods=['POST'])
def logout():
    """Log out the current user."""
    session.pop('user_id', None)
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@api.route('/auth/status', methods=['GET'])
def auth_status_v2():
    """Check if user is authenticated.

    Note: This route exists alongside `/api/auth_status` which is used by the
    frontend. The function name was changed to avoid Flask endpoint name
    collisions within the same blueprint.
    """
    user = authenticate_user()
    if user:
        return jsonify({
            'authenticated': True,
            'user': user.to_dict(),
            'success': True
        })
    return jsonify({'authenticated': False, 'success': True})

@api.route('/analyze-event', methods=['POST', 'OPTIONS'])
def analyze_event():
    """
    POST /api/analyze-event - Analyze workplace event for L&D insights
    Anonymous access allowed. If the user is authenticated, their session may be used for
    enhanced features (e.g., personalized history) while anonymous users are still permitted
    to analyze events. The request IP is stored for basic abuse monitoring.
    
    Headers:
    - X-API-Key: <api_key> (optional)
    
    Request body:
    {
        "event_description": "Team struggled with project deadline due to communication issues"
    }
    """
    if request.method == 'OPTIONS':
        return jsonify({'success': True}), 200

    logger.info("Processing event analysis request")

    data = request.get_json(force=True, silent=True)
    if data is None or not isinstance(data, dict):
        return jsonify({
            'error': 'Invalid JSON data in request',
            'success': False
        }), 400

    event_description = data.get('event_description')
    if not event_description or not isinstance(event_description, str):
        return jsonify({
            'error': 'Event description is required and must be a string',
            'success': False
        }), 400

    event_description = event_description.strip()
    if not event_description:
        return jsonify({
            'error': 'Event description cannot be empty',
            'success': False
        }), 400

    selected_metrics = data.get('selected_metrics', [])
    logger.info(f"Selected metrics for context: {len(selected_metrics)} metrics")

    role_profile_id = data.get('role_profile_id')
    role_context = None
    if role_profile_id is not None:
        try:
            role_id_int = int(role_profile_id)
            role = RoleProfile.query.get(role_id_int)
            if role:
                role_context = _build_role_context(role)
            else:
                logger.info(f"Role profile not found for role_profile_id={role_profile_id}")
        except Exception as e:
            logger.info(f"Unable to parse role_profile_id={role_profile_id}: {e}")

    check_fn = getattr(event_analyzer.ollama, '_check_availability', None)
    if callable(check_fn):
        check_fn()
    if not event_analyzer.ollama.available:
        return jsonify({
            'success': False,
            'error': 'LLM unavailable. Ollama is not reachable.',
            'ollama_status': 'unavailable',
            'timestamp': time.time(),
        }), 503

    client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))

    enable_event_kb = bool(current_app.config.get('ENABLE_EVENT_KB'))
    kb_context = data.get('kb_context')
    kb_tier_limit = int(data.get('kb_tier_limit', 5))
    kb_related_limit = int(data.get('kb_related_limit', 10))

    # Avoid piling up queued jobs when the executor is saturated (common when Ollama stalls).
    # If the pool is busy, return a fast response so the UI can show a clear error instead of spinning indefinitely.
    try:
        _event_job_sweep_stale_queued()
        with _EVENT_ANALYSIS_JOBS_LOCK:
            active = [
                j for j in _EVENT_ANALYSIS_JOBS.values()
                if isinstance(j, dict) and j.get('status') in ('queued', 'running')
            ]
        if len(active) >= _EVENT_ANALYSIS_MAX_ACTIVE:
            return jsonify({
                'success': False,
                'error': 'Event analysis is busy (a previous analysis is still running). Please wait for it to finish and try again.',
                'status': 'busy',
                'active_jobs': [j.get('id') for j in active if j.get('id')],
                'timestamp': time.time(),
            }), 429
    except Exception:
        pass

    job_id = uuid4().hex
    now_iso = datetime.utcnow().isoformat() + 'Z'
    with _EVENT_ANALYSIS_JOBS_LOCK:
        _EVENT_ANALYSIS_JOBS[job_id] = {
            'id': job_id,
            'status': 'queued',
            'created_at': now_iso,
            'started_at': None,
            'finished_at': None,
            'error': None,
            'result': None,
        }

    app_obj = current_app._get_current_object()
    _EVENT_ANALYSIS_EXECUTOR.submit(
        _run_event_analysis_job,
        app_obj,
        job_id,
        event_description,
        selected_metrics,
        role_context,
        client_ip,
        enable_event_kb,
        kb_context,
        kb_tier_limit,
        kb_related_limit,
    )

    return jsonify({
        'success': True,
        'job_id': job_id,
        'status': 'queued',
        'timestamp': time.time(),
    }), 202


@api.route('/analyze-event/<job_id>', methods=['GET'])
def analyze_event_job_status(job_id: str):
    _event_job_sweep_stale_queued()
    job = _event_job_get(job_id)
    if not job:
        return jsonify({
            'success': False,
            'error': 'Job not found',
        }), 404

    status = job.get('status')
    if status == 'succeeded':
        payload = job.get('result') or {}
        return jsonify(payload), 200

    if status == 'failed':
        return jsonify({
            'success': False,
            'status': 'failed',
            'error': job.get('error') or 'Analysis failed',
            'timestamp': time.time(),
        }), 200

    return jsonify({
        'success': True,
        'status': status,
        'job_id': job_id,
        'created_at': job.get('created_at'),
        'started_at': job.get('started_at'),
        'timestamp': time.time(),
    }), 200


@api.route('/knowledge/biases', methods=['GET'])
def get_bias_knowledge():
    if not current_app.config.get('ENABLE_EVENT_KB'):
        return jsonify({
            'success': True,
            'items': [],
            'total': 0
        })

    query = (request.args.get('q') or '').strip()
    limit = max(1, min(request.args.get('limit', 10, type=int), 25))

    try:
        biases = behavioral_biases.search_biases(text=query or None, limit=limit)
        if not biases:
            biases = behavioral_biases.get_random_biases(limit=limit)

        items = behavioral_biases.serialize_biases(biases)

        return jsonify({
            'success': True,
            'items': items,
            'total': len(items)
        })
    except Exception as e:
        logger.error("Error fetching bias knowledge: %s", e)
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve bias knowledge'
        }), 500


@api.route('/ollama-status', methods=['GET'])
def ollama_status():
    """
    GET /api/ollama-status - Check Ollama availability and models
    """
    try:
        # Refresh availability check
        recommendation_engine.ollama._check_availability()
        
        return jsonify({
            'available': recommendation_engine.ollama.available,
            'models': recommendation_engine.ollama.list_models() if recommendation_engine.ollama.available else [],
            'base_url': recommendation_engine.ollama.base_url,
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'available': False,
            'error': str(e),
            'timestamp': time.time()
        })


# Error handlers for the API blueprint
@api.errorhandler(404)
def api_not_found(error):
    """Handle 404 errors for API routes."""
    return jsonify({
        'error': 'Not found',
        'details': 'The requested API endpoint was not found'
    }), 404


@api.errorhandler(405)
def api_method_not_allowed(error):
    """Handle 405 errors for API routes."""
    return jsonify({
        'error': 'Method not allowed',
        'details': 'The HTTP method is not allowed for this endpoint'
    }), 405


@api.errorhandler(500)
def api_internal_error(error):
    """Handle 500 errors for API routes."""
    db.session.rollback()
    return jsonify({
        'error': 'Internal server error',
        'details': 'An unexpected error occurred'
    }), 500


@api.route('/event-analyses/recent', methods=['GET'])
def get_recent_analyses():
    """
    GET /api/event-analyses/recent?limit=<limit>
    Get recent successful event analyses for display
    """
    try:
        limit = min(int(request.args.get('limit', 5)), 20)  # Max 20 results
        
        recent_analyses = get_recent_event_analyses(limit=limit)
        
        # Format for frontend consumption
        analyses_data = []
        for analysis in recent_analyses:
            analyses_data.append({
                'id': analysis.id,
                'event_description': analysis.event_description,
                'created_date': analysis.created_date.isoformat() if analysis.created_date else None,
                'generated_by': analysis.generated_by,
                # Truncate description for display
                'display_text': analysis.event_description[:100] + '...' if len(analysis.event_description) > 100 else analysis.event_description
            })
        
        return jsonify({
            'success': True,
            'analyses': analyses_data,
            'count': len(analyses_data),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving recent analyses: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve recent analyses',
            'details': str(e)
        }), 500


@api.route('/event-analyses/<int:analysis_id>', methods=['GET'])
def get_analysis_by_id(analysis_id):
    """
    GET /api/event-analyses/<id>
    Get a specific event analysis by ID
    """
    try:
        analysis = EventAnalysis.query.get(analysis_id)
        
        if not analysis:
            return jsonify({
                'success': False,
                'error': 'Analysis not found'
            }), 404
        
        return jsonify({
            'success': True,
            'analysis': analysis.to_dict(),
            'timestamp': time.time()
        })
        
    except Exception as e:
        logger.error(f"Error retrieving analysis {analysis_id}: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve analysis',
            'details': str(e)
        }), 500


def to_title_case(text):
    """Convert text to Title Case, handling special cases for L&D terminology."""
    if not text:
        return text
    
    # Special cases for L&D terminology
    special_cases = {
        'l&d': 'L&D',
        'kpi': 'KPI',
        'roi': 'ROI',
        'hr': 'HR',
        'ai': 'AI',
        'it': 'IT'
    }
    
    # Convert to title case
    title_text = text.title()
    
    # Apply special cases
    for key, value in special_cases.items():
        title_text = re.sub(r'\b' + key.title() + r'\b', value, title_text, flags=re.IGNORECASE)
    
    return title_text


@api.route('/autocomplete', methods=['GET'])
def autocomplete():
    """
    GET /api/autocomplete?q=<query>&limit=<limit>
    Enhanced autocomplete endpoint for search suggestions with Title Case formatting
    """
    try:
        query = request.args.get('q', '').strip()
        limit = min(int(request.args.get('limit', 8)), 20)  # Max 20 suggestions
        
        if not query or len(query) < 2:
            return jsonify({
                'suggestions': [],
                'query': query,
                'count': 0
            })
        
        # Search metrics with relevance scoring
        search_term = f"%{query.lower()}%"
        
        # Query with relevance scoring (name matches score higher)
        metrics = db.session.query(
            Metric,
            # Score: name match = 3, description match = 1
            (func.case(
                (func.lower(Metric.name).like(search_term), 3),
                else_=1
            )).label('relevance_score')
        ).join(LDOutcome).join(MetricType).filter(
            or_(
                func.lower(Metric.name).like(search_term),
                func.lower(Metric.description).like(search_term),
                func.lower(LDOutcome.name).like(search_term),
                func.lower(MetricType.name).like(search_term)
            )
        ).order_by(
            db.text('relevance_score DESC'),
            Metric.name
        ).limit(limit).all()
        
        suggestions = []
        for metric, score in metrics:
            # Create title case name and description
            title_name = to_title_case(metric.name)
            description = metric.description[:100] + ('...' if len(metric.description) > 100 else '')
            
            suggestions.append({
                'id': metric.id,
                'name': title_name,
                'description': description,
                'outcome': to_title_case(metric.outcome.name),
                'type': to_title_case(metric.metric_type.name),
                'relevance_score': score,
                'url': f'/metric/{metric.id}'
            })
        
        return jsonify({
            'suggestions': suggestions,
            'query': query,
            'count': len(suggestions)
        })
        
    except Exception as e:
        logger.error(f"Autocomplete error: {str(e)}")
        return jsonify({
            'error': 'Failed to fetch suggestions',
            'suggestions': [],
            'query': query,
            'count': 0
        }), 500


# Context Management API Endpoints

@api.route('/context/session', methods=['GET'])
def get_session_info():
    """
    GET /api/context/session - Get current session information
    """
    try:
        from app.context_manager import context_manager
        
        session = context_manager.get_or_create_session()
        stats = context_manager.get_session_stats()
        
        return jsonify({
            'success': True,
            'session': session.to_dict(),
            'stats': stats
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return jsonify({
            'error': 'Failed to get session information',
            'details': str(e)
        }), 500


@api.route('/context/store', methods=['POST'])
def store_context():
    """
    POST /api/context/store - Store context data
    Request body:
    {
        "context_type": "search",
        "context_key": "last_query",
        "context_data": {"query": "engagement", "filters": {}},
        "expires_in_hours": 24
    }
    """
    try:
        from app.context_manager import context_manager
        from datetime import timedelta
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        context_type = data.get('context_type')
        context_key = data.get('context_key')
        context_data = data.get('context_data')
        expires_in_hours = data.get('expires_in_hours')
        
        if not all([context_type, context_key, context_data]):
            return jsonify({
                'error': 'Missing required fields',
                'required': ['context_type', 'context_key', 'context_data']
            }), 400
        
        # Calculate expiration
        expires_in = None
        if expires_in_hours:
            expires_in = timedelta(hours=expires_in_hours)
        
        context = context_manager.store_context(
            context_type=context_type,
            context_key=context_key,
            context_data=context_data,
            expires_in=expires_in
        )
        
        return jsonify({
            'success': True,
            'context': context.to_dict()
        }), 200
        
    except Exception as e:
        logger.error(f"Error storing context: {str(e)}")
        return jsonify({
            'error': 'Failed to store context',
            'details': str(e)
        }), 500


@api.route('/context/get/<context_type>/<context_key>', methods=['GET'])
def get_context(context_type, context_key):
    """
    GET /api/context/get/<context_type>/<context_key> - Get specific context data
    """
    try:
        from app.context_manager import context_manager
        
        context_data = context_manager.get_context(context_type, context_key)
        
        if context_data is None:
            return jsonify({
                'success': False,
                'message': 'Context not found or expired'
            }), 404
        
        return jsonify({
            'success': True,
            'context_type': context_type,
            'context_key': context_key,
            'context_data': context_data
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting context: {str(e)}")
        return jsonify({
            'error': 'Failed to get context',
            'details': str(e)
        }), 500


@api.route('/context/metrics/select', methods=['POST'])
def select_metric():
    """
    POST /api/context/metrics/select - Select a metric for current session
    Request body:
    {
        "metric_id": 123,
        "selection_type": "manual",
        "context_tags": ["performance", "engagement"]
    }
    """
    try:
        from app.context_manager import context_manager
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        metric_id = data.get('metric_id')
        selection_type = data.get('selection_type', 'manual')
        context_tags = data.get('context_tags')
        
        if not metric_id:
            return jsonify({'error': 'metric_id is required'}), 400
        
        selected, selection = context_manager.select_metric(
            metric_id=metric_id,
            selection_type=selection_type,
            context_tags=context_tags
        )
        
        return jsonify({
            'success': True,
            'selected': selected,
            'selection': selection.to_dict(),
            'action': 'selected' if selected else 'deselected'
        }), 200
        
    except ValueError as e:
        return jsonify({
            'error': 'Invalid metric ID',
            'details': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error selecting metric: {str(e)}")
        return jsonify({
            'error': 'Failed to select metric',
            'details': str(e)
        }), 500


@api.route('/context/metrics/selected', methods=['GET'])
def get_selected_metrics():
    """
    GET /api/context/metrics/selected - Get all selected metrics for current session
    """
    try:
        from app.context_manager import context_manager
        
        selections = context_manager.get_selected_metrics()
        
        return jsonify({
            'success': True,
            'selected_metrics': selections,
            'count': len(selections)
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting selected metrics: {str(e)}")
        return jsonify({
            'error': 'Failed to get selected metrics',
            'details': str(e)
        }), 500


@api.route('/context/initialize', methods=['POST'])
def initialize_context():
    """
    POST /api/context/initialize - Initialize context for page load
    Request body:
    {
        "page": "dashboard",
        "user_agent": "Mozilla/5.0...",
        "preferences": {...}
    }
    """
    try:
        from app.context_manager import context_manager
        
        data = request.get_json() or {}
        page = data.get('page', 'unknown')
        preferences = data.get('preferences', {})
        
        # Get or create session
        session = context_manager.get_or_create_session()
        
        # Store page context
        page_context = {
            'page': page,
            'initialized_at': time.time(),
            'user_agent': request.headers.get('User-Agent', ''),
            'referrer': request.headers.get('Referer', '')
        }
        
        context_manager.store_context(
            context_type='page',
            context_key='current',
            context_data=page_context
        )
        
        # Store preferences if provided
        if preferences:
            context_manager.store_user_preferences(preferences)
        
        # Get current state
        current_preferences = context_manager.get_user_preferences()
        selected_metrics = context_manager.get_selected_metrics()
        
        return jsonify({
            'success': True,
            'session': session.to_dict(),
            'preferences': current_preferences,
            'selected_metrics': selected_metrics,
            'initialization_time': time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Error initializing context: {str(e)}")
        return jsonify({
            'error': 'Failed to initialize context',
            'details': str(e)
        }), 500


# Smart AI Recommendations API Endpoints

@api.route('/smart-recommendations/generate', methods=['POST'])
def generate_smart_recommendations():
    """
    POST /api/smart-recommendations/generate - Generate context-aware recommendations
    Request body:
    {
        "session_id": "session_uuid",
        "recommendation_type": "metric",  // 'metric', 'outcome', 'analysis'
        "context_data": {
            "search_query": "engagement metrics",
            "current_page": "metrics_selection"
        },
        "limit": 5
    }
    """
    try:
        from app.recommendation_service import recommendation_service
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        session_id = data.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Get or create session
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        recommendation_type = data.get('recommendation_type', 'metric')
        context_data = data.get('context_data', {})
        limit = min(data.get('limit', 5), 10)  # Cap at 10
        
        # Generate recommendations
        recommendations = recommendation_service.generate_recommendations(
            session_id=session.id,
            context_data=context_data,
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'session_id': session_id,
            'recommendation_type': recommendation_type,
            'count': len(recommendations),
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Error generating smart recommendations: {str(e)}")
        return jsonify({
            'error': 'Failed to generate recommendations',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations/interact', methods=['POST'])
def record_recommendation_interaction():
    """
    POST /api/smart-recommendations/interact - Record user interaction with recommendation
    Request body:
    {
        "recommendation_id": 123,
        "interaction_type": "clicked",  // 'viewed', 'clicked', 'dismissed', 'accepted'
        "additional_data": {}
    }
    """
    try:
        from app.recommendation_service import recommendation_service
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        recommendation_id = data.get('recommendation_id')
        interaction_type = data.get('interaction_type')
        
        if not recommendation_id or not interaction_type:
            return jsonify({'error': 'recommendation_id and interaction_type are required'}), 400
        
        if interaction_type not in ['viewed', 'clicked', 'dismissed', 'accepted']:
            return jsonify({'error': 'Invalid interaction_type'}), 400
        
        additional_data = data.get('additional_data', {})
        
        success = recommendation_service.record_user_interaction(
            recommendation_id=recommendation_id,
            interaction_type=interaction_type,
            additional_data=additional_data
        )
        
        if success:
            return jsonify({
                'success': True,
                'recommendation_id': recommendation_id,
                'interaction_type': interaction_type,
                'timestamp': time.time()
            }), 200
        else:
            return jsonify({'error': 'Failed to record interaction'}), 400
        
    except Exception as e:
        logger.error(f"Error recording interaction: {str(e)}")
        return jsonify({
            'error': 'Failed to record interaction',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations/feedback', methods=['POST'])
def add_recommendation_feedback():
    """
    POST /api/smart-recommendations/feedback - Add user feedback for recommendation
    Request body:
    {
        "recommendation_id": 123,
        "feedback_type": "useful",  // 'useful', 'not_useful', 'rating', 'irrelevant'
        "feedback_value": "5",  // Optional rating value or category
        "feedback_text": "This was very helpful"  // Optional comment
    }
    """
    try:
        from app.recommendation_service import recommendation_service
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        recommendation_id = data.get('recommendation_id')
        feedback_type = data.get('feedback_type')
        
        if not recommendation_id or not feedback_type:
            return jsonify({'error': 'recommendation_id and feedback_type are required'}), 400
        
        feedback_value = data.get('feedback_value')
        feedback_text = data.get('feedback_text')
        client_ip = request.environ.get('HTTP_X_FORWARDED_FOR', request.environ.get('REMOTE_ADDR', 'unknown'))
        
        feedback = recommendation_service.add_feedback(
            recommendation_id=recommendation_id,
            feedback_type=feedback_type,
            feedback_value=feedback_value,
            feedback_text=feedback_text,
            ip_address=client_ip
        )
        
        if feedback:
            return jsonify({
                'success': True,
                'feedback_id': feedback.id,
                'recommendation_id': recommendation_id,
                'feedback_type': feedback_type,
                'timestamp': time.time()
            }), 200
        else:
            return jsonify({'error': 'Failed to add feedback'}), 400
        
    except Exception as e:
        logger.error(f"Error adding feedback: {str(e)}")
        return jsonify({
            'error': 'Failed to add feedback',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations/preferences', methods=['POST'])
def update_user_preferences():
    """
    POST /api/smart-recommendations/preferences - Update user preferences
    Request body:
    {
        "session_id": "session_uuid",
        "preferences": {
            "metric_type": {
                "key": "preferred_types",
                "value": ["Operational KPI", "Behavioral Metric"],
                "weight": 0.8
            },
            "outcome": {
                "key": "focus_areas",
                "value": ["Employee Engagement", "Performance"],
                "weight": 0.9
            }
        }
    }
    """
    try:
        from app.recommendation_service import recommendation_service
        
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        session_id = data.get('session_id')
        preferences = data.get('preferences', {})
        
        if not session_id:
            return jsonify({'error': 'session_id is required'}), 400
        
        # Get session
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        success = recommendation_service.update_user_preferences(
            session_id=session.id,
            preferences=preferences
        )
        
        if success:
            return jsonify({
                'success': True,
                'session_id': session_id,
                'preferences_updated': len(preferences),
                'timestamp': time.time()
            }), 200
        else:
            return jsonify({'error': 'Failed to update preferences'}), 400
        
    except Exception as e:
        logger.error(f"Error updating preferences: {str(e)}")
        return jsonify({
            'error': 'Failed to update preferences',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations/analytics', methods=['GET'])
def get_recommendation_analytics():
    """
    GET /api/smart-recommendations/analytics?session_id=<session_id>
    Get analytics for recommendations in a session
    """
    try:
        from app.recommendation_service import recommendation_service
        
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id parameter is required'}), 400
        
        # Get session
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        analytics = recommendation_service.get_recommendation_analytics(session.id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'analytics': analytics,
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting analytics: {str(e)}")
        return jsonify({
            'error': 'Failed to get analytics',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations/history', methods=['GET'])
def get_recommendation_history():
    """
    GET /api/smart-recommendations/history?session_id=<session_id>&type=<type>&limit=<limit>
    Get recommendation history for a session
    """
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id parameter is required'}), 400
        
        # Get session
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        recommendation_type = request.args.get('type')
        limit = min(int(request.args.get('limit', 20)), 50)  # Cap at 50
        
        # Get recommendations
        recommendations = Recommendation.get_for_session(
            session_id=session.id,
            recommendation_type=recommendation_type,
            limit=limit
        )
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'recommendations': [rec.to_dict() for rec in recommendations],
            'count': len(recommendations),
            'filters': {
                'type': recommendation_type,
                'limit': limit
            },
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recommendation history: {str(e)}")
        return jsonify({
            'error': 'Failed to get recommendation history',
            'details': str(e)
        }), 500


@api.route('/smart-recommendations/active', methods=['GET'])
def get_active_recommendations():
    """
    GET /api/smart-recommendations/active?session_id=<session_id>&type=<type>
    Get active (not dismissed) recommendations for a session
    """
    try:
        session_id = request.args.get('session_id')
        if not session_id:
            return jsonify({'error': 'session_id parameter is required'}), 400
        
        # Get session
        session = UserSession.query.filter_by(session_id=session_id).first()
        if not session:
            return jsonify({'error': 'Session not found'}), 404
        
        recommendation_type = request.args.get('type')
        
        # Get active recommendations
        recommendations = Recommendation.get_active_for_session(
            session_id=session.id,
            recommendation_type=recommendation_type
        )
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'recommendations': [rec.to_dict() for rec in recommendations],
            'count': len(recommendations),
            'filters': {
                'type': recommendation_type
            },
            'timestamp': time.time()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting active recommendations: {str(e)}")
        return jsonify({
            'error': 'Failed to get active recommendations',
            'details': str(e)
        }), 500


# Context Management API Endpoints
@api.route('/context/recent-sessions', methods=['GET'])
def get_recent_sessions():
    """GET /api/context/recent-sessions - Get recent user sessions"""
    try:
        limit = min(request.args.get('limit', 10, type=int), 50)
        
        # For now, return mock data since we don't have session storage implemented
        # In a full implementation, this would query a sessions table
        recent_sessions = []
        
        # Check if there are any existing session IDs in localStorage that we can reference
        # This is a placeholder implementation
        return jsonify({
            'success': True,
            'sessions': recent_sessions,
            'count': len(recent_sessions)
        }), 200
        
    except Exception as e:
        return jsonify({
            'error': 'Failed to retrieve recent sessions',
            'details': str(e)
        }), 500


 


@api.route('/__debug__/routes', methods=['GET'])
@api.route('/debug/routes', methods=['GET'])
def debug_list_routes():
    """
    GET /api/__debug__/routes?only_api=true
    Returns the app's registered routes to diagnose routing issues.
    """
    if not current_app.debug:
        abort(404)
    try:
        routes = []
        for rule in current_app.url_map.iter_rules():
            methods = sorted([m for m in rule.methods if m not in ('HEAD', 'OPTIONS')])
            routes.append({
                'rule': str(rule),
                'endpoint': rule.endpoint,
                'methods': methods,
            })
        only_api = str(request.args.get('only_api', 'true')).lower() == 'true'
        if only_api:
            routes = [r for r in routes if r['rule'].startswith('/api')]
        routes = sorted(routes, key=lambda r: r['rule'])
        return jsonify({'routes': routes, 'count': len(routes)}), 200
    except Exception as e:
        return jsonify({'error': 'Failed to list routes', 'details': str(e)}), 500


 

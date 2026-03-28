import os
import re
from flask import has_request_context, session

from app import db
from app.models import ClientCompany, ClientEngagement


def safe_component(value: str | None, default: str = '') -> str:
    s = (value or '').strip().lower()
    s = re.sub(r'[^a-z0-9]+', '_', s)
    s = re.sub(r'_{2,}', '_', s).strip('_')
    return s or default


def short_id(value: str | int | None, length: int = 8) -> str:
    if value is None:
        return ''
    s = str(value).strip()
    if not s:
        return ''
    s = re.sub(r'[^a-zA-Z0-9]+', '', s)
    return s[: max(1, int(length or 8))]


def get_active_workspace() -> dict:
    """Return active workspace info from the Flask session (best-effort)."""
    if not has_request_context():
        return {}

    client_id = session.get('active_client_id')
    engagement_id = session.get('active_engagement_id')
    session_id = session.get('session_id')

    out: dict = {
        'active_client_id': int(client_id) if client_id else None,
        'active_engagement_id': int(engagement_id) if engagement_id else None,
        'session_id': str(session_id) if session_id else None,
        'session_short': short_id(session_id),
    }

    try:
        if client_id:
            cc = db.session.get(ClientCompany, int(client_id))
            if cc:
                out.update({
                    'client_slug': safe_component(getattr(cc, 'slug', None) or cc.name, default='client'),
                    'client_name': cc.name,
                })
        if engagement_id:
            ce = db.session.get(ClientEngagement, int(engagement_id))
            if ce:
                out.update({
                    'engagement_slug': safe_component(ce.name, default='engagement'),
                    'engagement_name': ce.name,
                    'client_company_id': ce.client_company_id,
                })
    except Exception:
        pass

    return out


def workspace_from_pdf_path(pdf_path: str | None) -> dict:
    if not pdf_path:
        return {}

    p = str(pdf_path).replace('\\', '/')
    parts = [x for x in p.split('/') if x]

    for i in range(len(parts) - 1):
        if parts[i] == 'static' and parts[i + 1] == 'reports':
            client_slug = parts[i + 2] if i + 2 < len(parts) else ''
            engagement_slug = parts[i + 3] if i + 3 < len(parts) else ''
            out = {}
            if client_slug:
                out['client_slug'] = safe_component(client_slug)
            if engagement_slug:
                out['engagement_slug'] = safe_component(engagement_slug)
            return out

    return {}


def build_stamp(workspace: dict | None = None, include_session: bool = True) -> str:
    ws = workspace or get_active_workspace()

    parts = []
    client_slug = safe_component(ws.get('client_slug') or '', default='')
    engagement_slug = safe_component(ws.get('engagement_slug') or '', default='')
    if client_slug:
        parts.append(client_slug)
    if engagement_slug:
        parts.append(engagement_slug)

    if include_session:
        sess = ws.get('session_short') or short_id(ws.get('session_id'))
        if sess:
            parts.append(f"s{safe_component(sess)}")

    return '__'.join([p for p in parts if p])


def stamp_filename(filename: str, workspace: dict | None = None, include_session: bool = True) -> str:
    if not filename:
        return filename

    stamp = build_stamp(workspace=workspace, include_session=include_session)
    if not stamp:
        return filename

    if filename.startswith(stamp + '__'):
        return filename

    base, ext = os.path.splitext(filename)
    return f"{stamp}__{base}{ext}"

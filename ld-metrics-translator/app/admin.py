REQUIRED_DRIVER_CARD_METRIC_TYPES = {
    'Behavioral Observation': 'Direct observation of behaviors linked to the driver.',
    'Self-Assessment/Survey': 'Self-reported ratings or survey responses.',
    'Peer/360 Feedback': 'Feedback collected from peers or 360 assessments.',
    'Objective KPI': 'Objective key performance indicators collected from systems.',
    'Output/Deliverable Quality': 'Quality checks on deliverables or outputs.',
    'Formal Assessment/Test': 'Standardized or formal assessments and tests.'
}


def ensure_required_metric_types():
    existing = {mt.name: mt for mt in MetricType.query.filter(MetricType.name.in_(REQUIRED_DRIVER_CARD_METRIC_TYPES.keys())).all()}
    created = []
    for name, description in REQUIRED_DRIVER_CARD_METRIC_TYPES.items():
        if name in existing:
            continue
        metric_type = MetricType(name=name, description=description)
        db.session.add(metric_type)
        created.append(metric_type)
    if created:
        db.session.commit()
        names = ', '.join(mt.name for mt in created)
        try:
            log_admin_action('AUTO_CREATE_METRIC_TYPES', f'Created missing driver card metric types: {names}')
        except Exception:
            pass

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, PasswordField, BooleanField, HiddenField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional, Email
from wtforms import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import Metric, LDOutcome, MetricType, AdminUser, AuditLog, Framework, Competency, ClientRetroItem, ClientPullRequest, ClientSurveyResponse
from app.models import ClientCompany, ClientDataInventoryItem
from app.models_behavioral_bias import BehavioralBias
from app import db
import csv
import json
import io
from datetime import datetime, timezone
from functools import wraps
import os
import re
from sqlalchemy import or_

admin = Blueprint('admin', __name__, url_prefix='/admin')

# ------------------------------------------------------------
# Helpers
# ------------------------------------------------------------
def slugify(value: str) -> str:
    """Simple slug generator: lowercase, replace non-alnum with hyphens, collapse dashes."""
    if not value:
        return ''
    value = value.lower().strip()
    value = re.sub(r'[^a-z0-9]+', '-', value)
    value = re.sub(r'-{2,}', '-', value).strip('-')
    return value or ''

def unique_framework_slug(base: str) -> str:
    """Ensure unique slug for Frameworks."""
    slug = slugify(base)
    if not slug:
        slug = 'framework'
    if not Framework.query.filter_by(slug=slug).first():
        return slug
    i = 2
    while True:
        candidate = f"{slug}-{i}"
        if not Framework.query.filter_by(slug=candidate).first():
            return candidate
        i += 1

def unique_competency_slug(framework_id: int, base: str) -> str:
    """Ensure slug uniqueness within a framework for readability (DB does not enforce global uniqueness)."""
    slug = slugify(base)
    if not slug:
        slug = 'competency'
    if not Competency.query.filter_by(framework_id=framework_id, slug=slug).first():
        return slug

    i = 2
    while True:
        candidate = f"{slug}-{i}"
        if not Competency.query.filter_by(framework_id=framework_id, slug=candidate).first():
            return candidate
        i += 1

def _parse_optional_datetime(value):
    if value is None:
        return None

    s = str(value).strip()
    if not s:
        return None
    try:
        return datetime.fromisoformat(s.replace('Z', '+00:00'))
    except Exception:
        pass
    for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
        try:
            return datetime.strptime(s, fmt)
        except Exception:
            continue
    return None


def unique_client_slug(base: str, client_id: int | None = None) -> str:
    slug = slugify(base)
    if not slug:
        slug = 'client'

    query = ClientCompany.query.filter_by(slug=slug)
    if client_id:
        query = query.filter(ClientCompany.id != client_id)
    if not query.first():
        return slug

    i = 2
    while True:
        candidate = f"{slug}-{i}"
        query = ClientCompany.query.filter_by(slug=candidate)
        if client_id:
            query = query.filter(ClientCompany.id != client_id)
        if not query.first():
            return candidate
        i += 1

def _normalize_csv_row(row: dict) -> dict:
    normalized = {}
    try:
        items = row.items()
    except Exception:
        return normalized
    for k, v in items:
        if k is None:
            continue
        nk = str(k).strip().lstrip('\ufeff').lower()
        if nk and nk not in normalized:
            normalized[nk] = v
    return normalized

def _csv_dict_reader_from_text(text: str) -> csv.DictReader:
    normalized_text = text or ''
    if ('\n' not in normalized_text) and ('\\n' in normalized_text):
        normalized_text = normalized_text.replace('\\r\\n', '\n').replace('\\n', '\n')

    sample = normalized_text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=[',', ';', '\t', '|'])
    except Exception:
        dialect = csv.excel
    stream = io.StringIO(normalized_text, newline=None)
    return csv.DictReader(stream, dialect=dialect)


def unique_bias_slug(base: str, bias_id: int | None = None) -> str:
    """Ensure slug uniqueness for behavioral biases."""
    slug = slugify(base)
    if not slug:
        slug = 'bias'

    query = BehavioralBias.query.filter_by(slug=slug)
    if bias_id:
        query = query.filter(BehavioralBias.id != bias_id)
    if not query.first():
        return slug

    i = 2
    while True:
        candidate = f"{slug}-{i}"
        query = BehavioralBias.query.filter_by(slug=candidate)
        if bias_id:
            query = query.filter(BehavioralBias.id != bias_id)
        if not query.first():
            return candidate
        i += 1


def parse_list_field(value):
    """Parse comma/newline/semicolon separated text into a list of unique items preserving order."""
    if not value:
        return []
    items = []
    seen = set()
    normalized = str(value).replace(';', '\n')
    for line in normalized.splitlines():
        parts = [part.strip() for part in line.split(',')]
        for part in parts:
            if part and part.lower() not in seen:
                seen.add(part.lower())
                items.append(part)
    return items

def admin_required(f):
    """Decorator to require admin authentication."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_user_id' not in session:
            flash('Please log in to access the admin panel.', 'error')
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

def log_admin_action(action, details=None):
    """Log admin actions for audit trail."""
    if 'admin_user_id' in session:
        log = AuditLog(
            admin_user_id=session['admin_user_id'],
            action=action,
            details=details or '',
            created_date=datetime.now(timezone.utc),
            ip_address=request.remote_addr
        )
        db.session.add(log)
        db.session.commit()

# Forms
class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

class AdminUserForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[Length(min=6, max=100)])
    is_active = BooleanField('Active')

class MetricForm(FlaskForm):
    name = StringField('Name or Concept', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[DataRequired()])
    example = TextAreaField('Example', validators=[Optional()])
    ld_outcome_id = SelectField('L & D Outcome', coerce=int, validators=[DataRequired()])
    metric_type_id = SelectField('Metric Type', coerce=int, validators=[DataRequired()])

class LDOutcomeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])

class MetricTypeForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=100)])
    description = TextAreaField('Description', validators=[Optional()])


class BehavioralBiasForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    short_description = TextAreaField('Short Description', validators=[Optional(), Length(max=500)])
    detailed_description = TextAreaField('Detailed Description', validators=[Optional()])
    countermeasures = TextAreaField('Countermeasures (one per line)', validators=[Optional()])
    tags = TextAreaField('Tags (comma or newline separated)', validators=[Optional()])
    trigger_keywords = TextAreaField('Trigger Keywords (one per line)', validators=[Optional()])
    model_framework = StringField('Behavioral Model / Framework', validators=[Optional(), Length(max=255)])
    source_reference = StringField('Source Reference', validators=[Optional(), Length(max=255)])
    is_active = BooleanField('Active', default=True)

class FrameworkForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    source = StringField('Source', validators=[Optional(), Length(max=200)])
    is_active = BooleanField('Active')
    sort_order = IntegerField('Sort Order', validators=[Optional()])

class CompetencyForm(FlaskForm):
    name = StringField('Name', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Description', validators=[Optional()])
    sort_order = IntegerField('Sort Order', validators=[Optional()])
    framework_id = SelectField('Framework', coerce=int, validators=[DataRequired()])
    metric_ids = SelectMultipleField('Associated Metrics', coerce=int, validators=[Optional()])

class BulkImportForm(FlaskForm):
    file = FileField('CSV File', validators=[
        DataRequired(),
        FileAllowed(['csv'], 'CSV files only!')
    ])
    import_type = SelectField('Import Type', choices=[
        ('metrics', 'Metrics'),
        ('outcomes', 'L&D Outcomes'),
        ('types', 'Metric Types'),
        ('retros', 'Client Retrospective Items'),
        ('pull_requests', 'Client Pull Requests'),
        ('survey_responses', 'Client Survey Responses'),
        ('client_inventory', 'Client Data Inventory Items')
    ], validators=[DataRequired()])


class ClientCompanyForm(FlaskForm):
    name = StringField('Client Name', validators=[DataRequired(), Length(max=200)])
    industry = StringField('Industry', validators=[Optional(), Length(max=200)])
    notes = TextAreaField('Notes', validators=[Optional()])


class ClientInventoryItemForm(FlaskForm):
    data_category = StringField('Data Category', validators=[DataRequired(), Length(max=200)])
    data_point = StringField('Specific Data Point', validators=[DataRequired(), Length(max=255)])
    collected_status = SelectField('Collected?', choices=[
        ('yes', 'Yes'),
        ('partial', 'Partially'),
        ('no', 'No'),
    ], validators=[DataRequired()])
    system_location = StringField('Location / System', validators=[Optional(), Length(max=255)])
    access_method = StringField('Access Method & Notes', validators=[Optional(), Length(max=255)])
    sensitivity = SelectField('Sensitivity', choices=[
        ('', '—'),
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
    ], validators=[Optional()])
    anonymity = SelectField('Anonymity', choices=[
        ('', '—'),
        ('unknown', 'Unknown'),
        ('anonymous', 'Anonymous'),
        ('not_anonymous', 'Not anonymous'),
        ('reidentification_risk', 'Re-identification risk'),
    ], validators=[Optional()])
    notes = TextAreaField('Notes', validators=[Optional()])

# Authentication routes
@admin.route('/login', methods=['GET', 'POST'])
def login():
    """Admin login page."""
    form = LoginForm()
    if form.validate_on_submit():
        user = AdminUser.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data) and user.is_active:
            session['admin_user_id'] = user.id
            session['admin_username'] = user.username
            log_admin_action('LOGIN', f'User {user.username} logged in')
            flash('Logged in successfully!', 'success')
            return redirect(url_for('admin.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('admin/login.html', form=form)

@admin.route('/logout')
@admin_required
def logout():
    """Admin logout."""
    username = session.get('admin_username', 'Unknown')
    log_admin_action('LOGOUT', f'User {username} logged out')
    session.pop('admin_user_id', None)
    session.pop('admin_username', None)
    flash('Logged out successfully!', 'success')
    return redirect(url_for('admin.login'))

# Dashboard
@admin.route('/')
@admin.route('/dashboard')
@admin_required
def dashboard():
    """Admin dashboard with statistics."""
    stats = {
        'total_metrics': Metric.query.count(),
        'total_outcomes': LDOutcome.query.count(),
        'total_types': MetricType.query.count(),
        'total_admin_users': AdminUser.query.count(),
        'total_client_retro_items': ClientRetroItem.query.count(),
        'total_client_pull_requests': ClientPullRequest.query.count(),
        'total_client_survey_responses': ClientSurveyResponse.query.count(),
        'recent_metrics': Metric.query.order_by(Metric.created_date.desc()).limit(5).all(),
        'recent_audit_logs': AuditLog.query.order_by(AuditLog.created_date.desc()).limit(10).all()
    }
    
    return render_template('admin/dashboard.html', stats=stats)


def _default_client_inventory_seed() -> list[dict]:
    return [
        {
            'data_category': 'Performance Reviews',
            'data_point': 'Manager ratings',
            'collected_status': 'yes',
            'system_location': 'Google Forms',
            'access_method': 'Google Drive',
            'sensitivity': 'high',
        },
        {
            'data_category': 'Performance Reviews',
            'data_point': 'Qualitative comments',
            'collected_status': 'yes',
            'system_location': 'Google Docs/Sheets',
            'access_method': 'Google Drive',
            'sensitivity': 'high',
        },
        {
            'data_category': 'Performance Reviews',
            'data_point': 'Goal attainment',
            'collected_status': 'no',
            'sensitivity': 'high',
        },
        {
            'data_category': '360-Degree Feedback',
            'data_point': 'Anonymous peer/report feedback',
            'collected_status': 'partial',
            'system_location': 'Google Forms',
            'access_method': 'Google Drive (Google Docs)',
            'sensitivity': 'high',
            'anonymity': 'anonymous',
        },
        {
            'data_category': 'Project Retrospectives',
            'data_point': 'Notes (what went well / improve) + action items',
            'collected_status': 'yes',
            'system_location': 'ClickUp',
            'access_method': 'ClickUp permissions',
            'sensitivity': 'medium',
        },
        {
            'data_category': 'Customer/Client Feedback',
            'data_point': 'CSAT/NPS scores + qualitative feedback',
            'collected_status': 'no',
            'sensitivity': 'medium',
        },
        {
            'data_category': 'Project Management Data',
            'data_point': 'Cycle time / rework rate / on-time delivery / bugs',
            'collected_status': 'no',
            'sensitivity': 'medium',
        },
        {
            'data_category': 'Code Repository Data (Devs)',
            'data_point': 'Test coverage % / code churn / PR comments/cycles',
            'collected_status': 'yes',
            'system_location': 'Git + PR system',
            'access_method': 'Platform export / APIs later',
            'sensitivity': 'medium',
        },
        {
            'data_category': 'Employee Engagement Surveys',
            'data_point': 'Engagement scores + anonymized comments',
            'collected_status': 'partial',
            'system_location': 'Google Forms + ClickUp anon form',
            'access_method': 'Google Forms and ClickUp',
            'sensitivity': 'high',
            'anonymity': 'anonymous',
        },
        {
            'data_category': 'HRIS Data',
            'data_point': 'Turnover rate / absenteeism / promotion velocity',
            'collected_status': 'no',
            'sensitivity': 'high',
        },
        {
            'data_category': 'Exit Interview Data',
            'data_point': 'Reasons for leaving + feedback on management/culture',
            'collected_status': 'partial',
            'sensitivity': 'high',
            'anonymity': 'reidentification_risk',
        },
    ]


@admin.route('/clients')
@admin_required
def clients_admin():
    clients = ClientCompany.query.order_by(ClientCompany.name.asc()).all()
    return render_template('admin/clients.html', clients=clients)


@admin.route('/clients/new', methods=['GET', 'POST'])
@admin_required
def clients_admin_new():
    form = ClientCompanyForm()
    if form.validate_on_submit():
        name = (form.name.data or '').strip()
        if ClientCompany.query.filter_by(name=name).first():
            flash('Client already exists.', 'error')
            return render_template('admin/client_new.html', form=form)

        client = ClientCompany(
            name=name,
            slug=unique_client_slug(name),
            industry=(form.industry.data or '').strip() or None,
            notes=(form.notes.data or '').strip() or None,
        )
        db.session.add(client)
        db.session.flush()

        for seed in _default_client_inventory_seed():
            db.session.add(ClientDataInventoryItem(
                client_company_id=client.id,
                data_category=seed.get('data_category') or 'General',
                data_point=seed.get('data_point') or 'Data point',
                collected_status=(seed.get('collected_status') or 'no'),
                system_location=seed.get('system_location'),
                access_method=seed.get('access_method'),
                sensitivity=seed.get('sensitivity'),
                anonymity=seed.get('anonymity'),
                notes=seed.get('notes'),
            ))

        db.session.commit()
        log_admin_action('ADD_CLIENT', f'Added client: {client.name}')
        flash('Client created. Default inventory checklist added.', 'success')
        return redirect(url_for('admin.client_detail_admin', client_id=client.id))

    return render_template('admin/client_new.html', form=form)


@admin.route('/clients/<int:client_id>')
@admin_required
def client_detail_admin(client_id: int):
    client = ClientCompany.query.get_or_404(client_id)
    items = ClientDataInventoryItem.query.filter_by(client_company_id=client.id).order_by(
        ClientDataInventoryItem.data_category.asc(),
        ClientDataInventoryItem.data_point.asc(),
    ).all()

    yes_count = len([i for i in items if (i.collected_status or '').lower() == 'yes'])
    partial_count = len([i for i in items if (i.collected_status or '').lower() == 'partial'])
    no_count = len([i for i in items if (i.collected_status or '').lower() == 'no'])

    form = ClientInventoryItemForm()
    form.collected_status.data = 'no'
    return render_template(
        'admin/client_detail.html',
        client=client,
        items=items,
        form=form,
        inventory_stats={'yes': yes_count, 'partial': partial_count, 'no': no_count, 'total': len(items)},
    )


@admin.route('/clients/<int:client_id>/inventory', methods=['POST'])
@admin_required
def client_inventory_add_admin(client_id: int):
    client = ClientCompany.query.get_or_404(client_id)
    form = ClientInventoryItemForm()
    if not form.validate_on_submit():
        flash('Please complete required fields for the inventory item.', 'error')
        return redirect(url_for('admin.client_detail_admin', client_id=client.id))

    item = ClientDataInventoryItem(
        client_company_id=client.id,
        data_category=(form.data_category.data or '').strip(),
        data_point=(form.data_point.data or '').strip(),
        collected_status=form.collected_status.data,
        system_location=(form.system_location.data or '').strip() or None,
        access_method=(form.access_method.data or '').strip() or None,
        sensitivity=(form.sensitivity.data or '').strip() or None,
        anonymity=(form.anonymity.data or '').strip() or None,
        notes=(form.notes.data or '').strip() or None,
    )
    db.session.add(item)
    db.session.commit()
    log_admin_action('ADD_CLIENT_INVENTORY_ITEM', f'{client.name}: {item.data_category} / {item.data_point}')
    flash('Inventory item added.', 'success')
    return redirect(url_for('admin.client_detail_admin', client_id=client.id))


@admin.route('/clients/<int:client_id>/inventory/<int:item_id>/update', methods=['POST'])
@admin_required
def client_inventory_update_admin(client_id: int, item_id: int):
    client = ClientCompany.query.get_or_404(client_id)
    item = ClientDataInventoryItem.query.get_or_404(item_id)
    if item.client_company_id != client.id:
        flash('Invalid inventory item for this client.', 'error')
        return redirect(url_for('admin.client_detail_admin', client_id=client.id))

    def _clean(v):
        s = (v or '').strip()
        return s or None

    # Keep required fields safe
    data_category = _clean(request.form.get('data_category'))
    data_point = _clean(request.form.get('data_point'))
    collected_status = (request.form.get('collected_status') or '').strip().lower()
    if not data_category or not data_point or collected_status not in ('yes', 'no', 'partial'):
        flash('Update failed: missing required fields.', 'error')
        return redirect(url_for('admin.client_detail_admin', client_id=client.id))

    item.data_category = data_category
    item.data_point = data_point
    item.collected_status = collected_status
    item.system_location = _clean(request.form.get('system_location'))
    item.access_method = _clean(request.form.get('access_method'))
    item.sensitivity = _clean(request.form.get('sensitivity'))
    item.anonymity = _clean(request.form.get('anonymity'))
    item.notes = _clean(request.form.get('notes'))
    db.session.commit()

    log_admin_action('UPDATE_CLIENT_INVENTORY_ITEM', f'{client.name}: {item.data_category} / {item.data_point}')
    flash('Inventory item updated.', 'success')
    return redirect(url_for('admin.client_detail_admin', client_id=client.id))


@admin.route('/clients/<int:client_id>/inventory/<int:item_id>/delete', methods=['POST'])
@admin_required
def client_inventory_delete_admin(client_id: int, item_id: int):
    client = ClientCompany.query.get_or_404(client_id)
    item = ClientDataInventoryItem.query.get_or_404(item_id)
    if item.client_company_id != client.id:
        flash('Invalid inventory item for this client.', 'error')
        return redirect(url_for('admin.client_detail_admin', client_id=client.id))
    label = f'{item.data_category} / {item.data_point}'
    db.session.delete(item)
    db.session.commit()
    log_admin_action('DELETE_CLIENT_INVENTORY_ITEM', f'{client.name}: {label}')
    flash('Inventory item deleted.', 'success')
    return redirect(url_for('admin.client_detail_admin', client_id=client.id))


def _gap_priority(item: ClientDataInventoryItem) -> str:
    key = (item.data_point or '').strip().lower()
    cat = (item.data_category or '').strip().lower()
    if 'goal attainment' in key:
        return 'P0'
    if 'csat' in key or 'nps' in key:
        return 'P0'
    if 'cycle time' in key or 'on-time' in key or 'rework' in key or 'bugs' in key:
        return 'P0'
    if 'turnover' in key or 'absenteeism' in key or 'promotion' in key:
        return 'P0'
    if 'exit interview' in cat:
        return 'P1'
    if '360' in cat:
        return 'P1'
    return 'P2'


def _gap_why_and_next(item: ClientDataInventoryItem) -> tuple[str, str]:
    key = (item.data_point or '').strip().lower()
    cat = (item.data_category or '').strip().lower()
    if 'goal attainment' in key:
        return (
            'Without goal attainment, performance discussions become subjective and hard to link to outcomes.',
            'Define 3–5 role-aligned goals per cycle, add a simple scoring rubric, and capture it in the same review workflow.'
        )
    if 'csat' in key or 'nps' in key:
        return (
            'Without customer feedback, it is difficult to connect talent initiatives to client value and retention.',
            'Start with a lightweight CSAT/NPS pulse after key deliveries; store monthly aggregates and a few example comments.'
        )
    if 'cycle time' in key or 'on-time' in key or 'rework' in key or 'bugs' in key:
        return (
            'Delivery metrics create a measurable link between ways-of-working, capability gaps, and business outcomes.',
            'Pick 2–3 delivery metrics (cycle time, rework, defects) and agree on definitions + a monthly export cadence.'
        )
    if 'turnover' in key or 'absenteeism' in key or 'promotion' in key:
        return (
            'HRIS signals help quantify talent risk (retention, wellbeing, progression) and validate whether interventions work.',
            'Request monthly aggregates by team (where possible) and define minimum sample sizes to protect confidentiality.'
        )
    if 'exit interview' in cat:
        return (
            'Exit data is high-signal but can be non-anonymous and easily re-identifiable in small teams.',
            'Only analyze aggregates; add a rule to suppress results for small samples and separate identifiers from narratives.'
        )
    if '360' in cat:
        return (
            'Partial 360 coverage makes comparisons unreliable and can bias leadership conclusions.',
            'Standardize the 360 instrument and rollout; track coverage by team before benchmarking.'
        )
    return (
        'This datapoint improves visibility into drivers of performance and engagement.',
        'Start with a manual export/import (CSV) and standardize the fields before considering integrations.'
    )


@admin.route('/clients/<int:client_id>/gap-report')
@admin_required
def client_gap_report_admin(client_id: int):
    client = ClientCompany.query.get_or_404(client_id)
    items = ClientDataInventoryItem.query.filter_by(client_company_id=client.id).all()

    yes_items = [i for i in items if (i.collected_status or '').lower() == 'yes']
    partial_items = [i for i in items if (i.collected_status or '').lower() == 'partial']
    no_items = [i for i in items if (i.collected_status or '').lower() == 'no']

    gaps = [i for i in items if (i.collected_status or '').lower() in ('no', 'partial')]
    gaps_sorted = sorted(gaps, key=lambda it: (_gap_priority(it), (it.data_category or ''), (it.data_point or '')))

    gap_rows = []
    for g in gaps_sorted:
        why, nxt = _gap_why_and_next(g)
        gap_rows.append({
            'id': g.id,
            'category': g.data_category,
            'data_point': g.data_point,
            'status': g.collected_status,
            'priority': _gap_priority(g),
            'system_location': g.system_location,
            'access_method': g.access_method,
            'sensitivity': g.sensitivity,
            'anonymity': g.anonymity,
            'why': why,
            'next_step': nxt,
        })

    roadmap = {
        'phase_1': [
            'Confirm definitions for the P0 datapoints and agree on owners.',
            'Start manual exports (CSV) from existing systems and load into a single inventory baseline.',
            'Generate an initial gap report and align on 1–3 quick-win interventions.'
        ],
        'phase_2': [
            'Standardize collection across teams (coverage + cadence).',
            'Add light governance: naming conventions, retention, and access rules.',
            'Run the diagnostic monthly and track movement in agreed metrics.'
        ],
        'phase_3': [
            'Automate collection via integrations/APIs where ROI justifies it.',
            'Build dashboards once the data is stable and definitions are trusted.',
            'Expand to benchmark comparisons across teams/roles if appropriate.'
        ],
    }

    stats = {
        'total': len(items),
        'yes': len(yes_items),
        'partial': len(partial_items),
        'no': len(no_items),
        'gaps': len(gaps),
    }

    return render_template(
        'admin/client_gap_report.html',
        client=client,
        stats=stats,
        gap_rows=gap_rows,
        roadmap=roadmap,
    )


@admin.route('/clients/<int:client_id>/export/inventory.csv')
@admin_required
def client_inventory_export_csv_admin(client_id: int):
    from flask import make_response
    client = ClientCompany.query.get_or_404(client_id)
    items = ClientDataInventoryItem.query.filter_by(client_company_id=client.id).order_by(
        ClientDataInventoryItem.data_category.asc(),
        ClientDataInventoryItem.data_point.asc(),
    ).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'client',
        'data_category',
        'data_point',
        'collected_status',
        'system_location',
        'access_method',
        'sensitivity',
        'anonymity',
        'notes',
        'updated_date',
    ])
    for it in items:
        writer.writerow([
            client.name,
            it.data_category,
            it.data_point,
            it.collected_status,
            it.system_location or '',
            it.access_method or '',
            it.sensitivity or '',
            it.anonymity or '',
            it.notes or '',
            it.updated_date.strftime('%Y-%m-%d %H:%M:%S') if it.updated_date else '',
        ])

    resp = make_response(output.getvalue())
    safe = slugify(client.slug or client.name)
    resp.headers['Content-Disposition'] = f'attachment; filename={safe}_inventory.csv'
    resp.headers['Content-type'] = 'text/csv'
    log_admin_action('EXPORT_CLIENT_INVENTORY', f'{client.name}')
    return resp


@admin.route('/clients/<int:client_id>/export/gap_report.csv')
@admin_required
def client_gap_report_export_csv_admin(client_id: int):
    from flask import make_response
    client = ClientCompany.query.get_or_404(client_id)
    items = ClientDataInventoryItem.query.filter_by(client_company_id=client.id).all()
    gaps = [i for i in items if (i.collected_status or '').lower() in ('no', 'partial')]
    gaps_sorted = sorted(gaps, key=lambda it: (_gap_priority(it), (it.data_category or ''), (it.data_point or '')))

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        'client',
        'priority',
        'data_category',
        'data_point',
        'status',
        'why_it_matters',
        'recommended_next_step',
        'system_location',
        'access_method',
        'sensitivity',
        'anonymity',
    ])
    for g in gaps_sorted:
        why, nxt = _gap_why_and_next(g)
        writer.writerow([
            client.name,
            _gap_priority(g),
            g.data_category,
            g.data_point,
            g.collected_status,
            why,
            nxt,
            g.system_location or '',
            g.access_method or '',
            g.sensitivity or '',
            g.anonymity or '',
        ])

    resp = make_response(output.getvalue())
    safe = slugify(client.slug or client.name)
    resp.headers['Content-Disposition'] = f'attachment; filename={safe}_gap_report.csv'
    resp.headers['Content-type'] = 'text/csv'
    log_admin_action('EXPORT_CLIENT_GAP_REPORT', f'{client.name}')
    return resp


@admin.route('/client-data')
@admin_required
def client_data_admin():
    stats = {
        'retros': ClientRetroItem.query.count(),
        'pull_requests': ClientPullRequest.query.count(),
        'survey_responses': ClientSurveyResponse.query.count(),
    }
    return render_template('admin/client_data.html', stats=stats)


@admin.route('/client-data/retros')
@admin_required
def client_data_retros_admin():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    team = (request.args.get('team') or '').strip()
    source = (request.args.get('source') or '').strip()
    q = (request.args.get('q') or '').strip()

    query = ClientRetroItem.query
    if team:
        query = query.filter(ClientRetroItem.team == team)
    if source:
        query = query.filter(ClientRetroItem.source == source)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                ClientRetroItem.text.ilike(pattern),
                ClientRetroItem.category.ilike(pattern),
            )
        )

    pagination = query.order_by(ClientRetroItem.imported_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        'admin/client_data_retros.html',
        items=pagination,
        filters={'team': team, 'source': source, 'q': q, 'per_page': per_page},
    )


@admin.route('/client-data/surveys')
@admin_required
def client_data_surveys_admin():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    team = (request.args.get('team') or '').strip()
    source = (request.args.get('source') or '').strip()
    q = (request.args.get('q') or '').strip()

    query = ClientSurveyResponse.query
    if team:
        query = query.filter(ClientSurveyResponse.team == team)
    if source:
        query = query.filter(ClientSurveyResponse.source == source)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                ClientSurveyResponse.answer.ilike(pattern),
                ClientSurveyResponse.question.ilike(pattern),
                ClientSurveyResponse.survey_name.ilike(pattern),
            )
        )

    pagination = query.order_by(ClientSurveyResponse.imported_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        'admin/client_data_surveys.html',
        items=pagination,
        filters={'team': team, 'source': source, 'q': q, 'per_page': per_page},
    )


@admin.route('/client-data/pull-requests')
@admin_required
def client_data_pull_requests_admin():
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 50, type=int)
    team = (request.args.get('team') or '').strip()
    source = (request.args.get('source') or '').strip()
    q = (request.args.get('q') or '').strip()

    query = ClientPullRequest.query
    if team:
        query = query.filter(ClientPullRequest.team == team)
    if source:
        query = query.filter(ClientPullRequest.source == source)
    if q:
        pattern = f"%{q}%"
        query = query.filter(
            or_(
                ClientPullRequest.pr_id.ilike(pattern),
                ClientPullRequest.author.ilike(pattern),
                ClientPullRequest.url.ilike(pattern),
            )
        )

    pagination = query.order_by(ClientPullRequest.imported_at.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )

    return render_template(
        'admin/client_data_pull_requests.html',
        items=pagination,
        filters={'team': team, 'source': source, 'q': q, 'per_page': per_page},
    )


@admin.route('/event-feed')
@admin.route('/event-feed/')
@admin_required
def event_feed_admin():
    return render_template('admin/event_feed.html')


@admin.route('/event-feed/report')
@admin.route('/event-feed/report/')
@admin_required
def event_feed_report_admin():
    job_id = (request.args.get('job_id') or '').strip()
    if not job_id:
        flash('Missing job_id for diagnostic report.', 'error')
        return redirect(url_for('admin.event_feed_admin'))
    return render_template('admin/event_feed_report.html', job_id=job_id)

# Metrics management
@admin.route('/metrics')
@admin_required
def metrics():
    """List all metrics with pagination and search."""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    search = request.args.get('search', '')
    
    query = Metric.query
    if search:
        query = query.filter(
            Metric.name.contains(search) |
            Metric.description.contains(search)
        )
    
    metrics_pagination = query.order_by(Metric.name).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    return render_template('admin/metrics.html', 
                         metrics=metrics_pagination,
                         search=search)

@admin.route('/metrics/add', methods=['GET', 'POST'])
@admin_required
def add_metric():
    """Add a new metric."""
    form = MetricForm()
    form.ld_outcome_id.choices = [(o.id, o.name) for o in LDOutcome.query.all()]
    form.metric_type_id.choices = [(t.id, t.name) for t in MetricType.query.all()]
    
    if form.validate_on_submit():
        metric = Metric(
            name=form.name.data,
            description=form.description.data,
            example=form.example.data,
            outcome_id=form.ld_outcome_id.data,
            metric_type_id=form.metric_type_id.data
        )
        db.session.add(metric)
        db.session.commit()
        
        log_admin_action('ADD_METRIC', f'Added metric: {metric.name}')
        flash('Metric added successfully!', 'success')
        return redirect(url_for('admin.metrics'))
    
    return render_template('admin/metric_form.html', form=form, title='Add Metric')

@admin.route('/metrics/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_metric(id):
    """Edit an existing metric."""
    metric = Metric.query.get_or_404(id)
    form = MetricForm(obj=metric)
    form.ld_outcome_id.choices = [(o.id, o.name) for o in LDOutcome.query.all()]
    form.metric_type_id.choices = [(t.id, t.name) for t in MetricType.query.all()]
    
    if form.validate_on_submit():
        old_name = metric.name
        # Populate fields explicitly to handle schema difference (form.ld_outcome_id -> model.outcome_id)
        metric.name = form.name.data
        metric.description = form.description.data
        metric.example = form.example.data
        metric.outcome_id = form.ld_outcome_id.data
        metric.metric_type_id = form.metric_type_id.data
        metric.updated_date = datetime.now(timezone.utc)
        db.session.commit()
        
        log_admin_action('EDIT_METRIC', f'Edited metric: {old_name} -> {metric.name}')
        flash('Metric updated successfully!', 'success')
        return redirect(url_for('admin.metrics'))
    
    return render_template('admin/metric_form.html', form=form, metric=metric, title='Edit Metric')

@admin.route('/metrics/<int:id>/delete', methods=['POST'])
@admin_required
def delete_metric(id):
    """Delete a metric."""
    metric = Metric.query.get_or_404(id)
    name = metric.name
    db.session.delete(metric)
    db.session.commit()
    
    log_admin_action('DELETE_METRIC', f'Deleted metric: {name}')
    flash('Metric deleted successfully!', 'success')
    return redirect(url_for('admin.metrics'))

# L&D Outcomes management
@admin.route('/outcomes')
@admin_required
def outcomes():
    """List all L&D outcomes."""
    outcomes = LDOutcome.query.order_by(LDOutcome.name).all()
    return render_template('admin/outcomes.html', outcomes=outcomes)

@admin.route('/outcomes/add', methods=['GET', 'POST'])
@admin_required
def add_outcome():
    """Add a new L&D outcome."""
    form = LDOutcomeForm()
    
    if form.validate_on_submit():
        outcome = LDOutcome(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(outcome)
        db.session.commit()
        
        log_admin_action('ADD_OUTCOME', f'Added L&D outcome: {outcome.name}')
        flash('L&D Outcome added successfully!', 'success')
        return redirect(url_for('admin.outcomes'))
    
    return render_template('admin/outcome_form.html', form=form, title='Add L&D Outcome')

@admin.route('/outcomes/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_outcome(id):
    """Edit an existing L&D outcome."""
    outcome = LDOutcome.query.get_or_404(id)
    form = LDOutcomeForm(obj=outcome)
    
    if form.validate_on_submit():
        old_name = outcome.name
        form.populate_obj(outcome)
        db.session.commit()
        
        log_admin_action('EDIT_OUTCOME', f'Edited L&D outcome: {old_name} -> {outcome.name}')
        flash('L&D Outcome updated successfully!', 'success')
        return redirect(url_for('admin.outcomes'))
    
    return render_template('admin/outcome_form.html', form=form, outcome=outcome, title='Edit L&D Outcome')

@admin.route('/outcomes/<int:id>/delete', methods=['POST'])
@admin_required
def delete_outcome(id):
    """Delete an L&D outcome."""
    outcome = LDOutcome.query.get_or_404(id)
    
    # Check if outcome has associated metrics
    if len(outcome.metrics) > 0:
        flash(f'Cannot delete outcome "{outcome.name}" because it has {len(outcome.metrics)} associated metrics.', 'error')
        return redirect(url_for('admin.outcomes'))
    
    name = outcome.name
    db.session.delete(outcome)
    db.session.commit()
    
    log_admin_action('DELETE_OUTCOME', f'Deleted L&D outcome: {name}')
    flash('L&D Outcome deleted successfully!', 'success')
    return redirect(url_for('admin.outcomes'))

# Metric Types management
@admin.route('/types')
@admin_required
def metric_types():
    """List all metric types."""
    types = MetricType.query.order_by(MetricType.name).all()
    return render_template('admin/metric_types.html', types=types)

@admin.route('/types/add', methods=['GET', 'POST'])
@admin_required
def add_metric_type():
    """Add a new metric type."""
    form = MetricTypeForm()
    
    if form.validate_on_submit():
        metric_type = MetricType(
            name=form.name.data,
            description=form.description.data
        )
        db.session.add(metric_type)
        db.session.commit()

        log_admin_action('ADD_TYPE', f'Added metric type: {metric_type.name}')
        flash('Metric Type added successfully!', 'success')
        return redirect(url_for('admin.metric_types'))

    return render_template('admin/metric_type_form.html', form=form, title='Add Metric Type')


# Behavioral Biases management
@admin.route('/behavioral-biases')
@admin_required
def behavioral_biases():
    """List behavioral biases."""
    items = BehavioralBias.query.order_by(BehavioralBias.name).all()
    return render_template('admin/behavioral_biases.html', biases=items)


@admin.route('/behavioral-biases/add', methods=['GET', 'POST'])
@admin_required
def add_behavioral_bias():
    """Add a new behavioral bias."""
    form = BehavioralBiasForm()
    if form.validate_on_submit():
        bias = BehavioralBias(
            name=form.name.data,
            slug=unique_bias_slug(form.name.data),
            short_description=form.short_description.data,
            detailed_description=form.detailed_description.data,
            model_framework=form.model_framework.data,
            source_reference=form.source_reference.data,
            is_active=form.is_active.data,
        )
        bias.set_countermeasures(parse_list_field(form.countermeasures.data))
        bias.set_tags(parse_list_field(form.tags.data))
        bias.set_trigger_keywords(parse_list_field(form.trigger_keywords.data))

        db.session.add(bias)
        db.session.commit()
        log_admin_action('ADD_BEHAVIORAL_BIAS', f'Added bias: {bias.name}')
        flash('Behavioral bias added successfully!', 'success')
        return redirect(url_for('admin.behavioral_biases'))

    return render_template('admin/behavioral_bias_form.html', form=form, title='Add Behavioral Bias')


@admin.route('/behavioral-biases/<int:bias_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_behavioral_bias(bias_id):
    """Edit an existing behavioral bias."""
    bias = BehavioralBias.query.get_or_404(bias_id)
    form = BehavioralBiasForm(
        name=bias.name,
        short_description=bias.short_description,
        detailed_description=bias.detailed_description,
        countermeasures='\n'.join(bias.countermeasures_list),
        tags='\n'.join(bias.tags_list),
        trigger_keywords='\n'.join(bias.trigger_keywords_list),
        model_framework=bias.model_framework,
        source_reference=bias.source_reference,
        is_active=bias.is_active,
    )

    if form.validate_on_submit():
        old_name = bias.name
        bias.name = form.name.data
        bias.slug = unique_bias_slug(form.name.data, bias.id)
        bias.short_description = form.short_description.data
        bias.detailed_description = form.detailed_description.data
        bias.model_framework = form.model_framework.data
        bias.source_reference = form.source_reference.data
        bias.is_active = form.is_active.data
        bias.set_countermeasures(parse_list_field(form.countermeasures.data))
        bias.set_tags(parse_list_field(form.tags.data))
        bias.set_trigger_keywords(parse_list_field(form.trigger_keywords.data))

        db.session.commit()
        log_admin_action('EDIT_BEHAVIORAL_BIAS', f'Edited bias: {old_name} -> {bias.name}')
        flash('Behavioral bias updated successfully!', 'success')
        return redirect(url_for('admin.behavioral_biases'))

    return render_template('admin/behavioral_bias_form.html', form=form, title='Edit Behavioral Bias', bias=bias)


@admin.route('/behavioral-biases/<int:bias_id>/delete', methods=['POST'])
@admin_required
def delete_behavioral_bias(bias_id):
    """Delete a behavioral bias."""
    bias = BehavioralBias.query.get_or_404(bias_id)
    name = bias.name

    db.session.delete(bias)
    db.session.commit()

    log_admin_action('DELETE_BEHAVIORAL_BIAS', f'Deleted bias: {name}')
    flash('Behavioral bias deleted successfully!', 'success')
    return redirect(url_for('admin.behavioral_biases'))


# Frameworks management
@admin.route('/frameworks')
@admin_required
def frameworks():
    """List all frameworks."""
    items = Framework.query.order_by(Framework.sort_order, Framework.name).all()
    return render_template('admin/frameworks.html', frameworks=items)

@admin.route('/frameworks/add', methods=['GET', 'POST'])
@admin_required
def add_framework():
    form = FrameworkForm()
    if form.validate_on_submit():
        fw = Framework(
            name=form.name.data,
            description=form.description.data,
            source=form.source.data,
            is_active=form.is_active.data,
            sort_order=form.sort_order.data or 0,
        )
        # Generate slug
        fw.slug = unique_framework_slug(fw.name)
        db.session.add(fw)
        db.session.commit()
        log_admin_action('ADD_FRAMEWORK', f'Added framework: {fw.name}')
        flash('Framework added successfully!', 'success')
        return redirect(url_for('admin.frameworks'))
    return render_template('admin/framework_form.html', form=form, title='Add Framework')

@admin.route('/frameworks/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_framework(id):
    fw = Framework.query.get_or_404(id)
    form = FrameworkForm(obj=fw)
    if form.validate_on_submit():
        old_name = fw.name
        fw.name = form.name.data
        fw.description = form.description.data
        fw.source = form.source.data
        fw.is_active = form.is_active.data
        fw.sort_order = form.sort_order.data or 0
        # If name changed, optionally update slug (only if conflicts unlikely). Keep stable unless empty.
        if not fw.slug:
            fw.slug = unique_framework_slug(fw.name)
        fw.updated_date = datetime.now(timezone.utc)
        db.session.commit()
        log_admin_action('EDIT_FRAMEWORK', f'Edited framework: {old_name} -> {fw.name}')
        flash('Framework updated successfully!', 'success')
        return redirect(url_for('admin.frameworks'))
    return render_template('admin/framework_form.html', form=form, framework=fw, title='Edit Framework')

@admin.route('/frameworks/<int:id>/delete', methods=['POST'])
@admin_required
def delete_framework(id):
    fw = Framework.query.get_or_404(id)
    name = fw.name
    db.session.delete(fw)
    db.session.commit()
    log_admin_action('DELETE_FRAMEWORK', f'Deleted framework: {name}')
    flash('Framework deleted successfully!', 'success')
    return redirect(url_for('admin.frameworks'))

# Driver Cards management
@admin.route('/driver-cards')
@admin_required
def driver_cards():
    if not current_app.config.get('DRIVER_CARDS_V1'):
        flash('Driver Cards feature flag is disabled. Enable DRIVER_CARDS_V1 to manage Driver Cards.', 'warning')
        return redirect(url_for('admin.dashboard'))

    # Ensure the required metric types exist before rendering the form
    ensure_required_metric_types()

    outcomes = LDOutcome.query.order_by(LDOutcome.name).all()
    metric_types = MetricType.query.order_by(MetricType.name).all()
    frameworks = Framework.query.order_by(Framework.name).all()
    return render_template(
        'admin/driver_cards.html',
        outcomes=outcomes,
        metric_types=metric_types,
        frameworks=frameworks,
    )

# Competencies management
@admin.route('/frameworks/<int:framework_id>/competencies')
@admin_required
def competencies(framework_id):
    fw = Framework.query.get_or_404(framework_id)
    comps = Competency.query.filter_by(framework_id=framework_id).order_by(Competency.sort_order, Competency.name).all()
    return render_template('admin/competencies.html', framework=fw, competencies=comps)

@admin.route('/frameworks/<int:framework_id>/competencies/add', methods=['GET', 'POST'])
@admin_required
def add_competency(framework_id):
    fw = Framework.query.get_or_404(framework_id)
    form = CompetencyForm()
    form.framework_id.choices = [(f.id, f.name) for f in Framework.query.order_by(Framework.name).all()]
    form.metric_ids.choices = [(m.id, m.name) for m in Metric.query.order_by(Metric.name).all()]
    form.framework_id.data = fw.id
    if form.validate_on_submit():
        comp = Competency(
            framework_id=form.framework_id.data,
            name=form.name.data,
            description=form.description.data,
            sort_order=form.sort_order.data or 0,
        )
        # Generate slug for competency
        comp.slug = unique_competency_slug(comp.framework_id, comp.name)
        # Set metric associations
        selected_ids = set(form.metric_ids.data or [])
        comp.metrics = [m for m in Metric.query.filter(Metric.id.in_(selected_ids)).all()]
        db.session.add(comp)
        db.session.commit()
        log_admin_action('ADD_COMPETENCY', f'Added competency: {comp.name} (Framework: {fw.name})')
        flash('Competency added successfully!', 'success')
        return redirect(url_for('admin.competencies', framework_id=comp.framework_id))
    return render_template('admin/competency_form.html', form=form, framework=fw, title='Add Competency')

@admin.route('/competencies/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_competency(id):
    comp = Competency.query.get_or_404(id)
    form = CompetencyForm(obj=comp)
    form.framework_id.choices = [(f.id, f.name) for f in Framework.query.order_by(Framework.name).all()]
    form.metric_ids.choices = [(m.id, m.name) for m in Metric.query.order_by(Metric.name).all()]
    # Pre-select current metric ids
    if request.method == 'GET':
        form.metric_ids.data = [m.id for m in comp.metrics]
    if form.validate_on_submit():
        old_name = comp.name
        comp.framework_id = form.framework_id.data
        comp.name = form.name.data
        comp.description = form.description.data
        comp.sort_order = form.sort_order.data or 0
        # Ensure slug present; update if empty or name changed and slug matches old name
        if not comp.slug or slugify(old_name) == comp.slug:
            comp.slug = unique_competency_slug(comp.framework_id, comp.name)
        # Update metric associations
        selected_ids = set(form.metric_ids.data or [])
        comp.metrics = [m for m in Metric.query.filter(Metric.id.in_(selected_ids)).all()]
        db.session.commit()
        log_admin_action('EDIT_COMPETENCY', f'Edited competency: {old_name} -> {comp.name}')
        flash('Competency updated successfully!', 'success')
        return redirect(url_for('admin.competencies', framework_id=comp.framework_id))
    fw = Framework.query.get(comp.framework_id)
    return render_template('admin/competency_form.html', form=form, framework=fw, competency=comp, title='Edit Competency')

@admin.route('/competencies/<int:id>/delete', methods=['POST'])
@admin_required
def delete_competency(id):
    comp = Competency.query.get_or_404(id)
    fw_id = comp.framework_id
    name = comp.name
    db.session.delete(comp)
    db.session.commit()
    log_admin_action('DELETE_COMPETENCY', f'Deleted competency: {name}')
    flash('Competency deleted successfully!', 'success')
    return redirect(url_for('admin.competencies', framework_id=fw_id))
    
    return render_template('admin/metric_type_form.html', form=form, title='Add Metric Type')

# ------------------------------------------------------------
# Role Architect (Admin entry) — reuse public templates
# ------------------------------------------------------------

@admin.route('/roles')
@admin_required
def roles_admin():
    """Admin entry to Role Architect library."""
    # Pass is_admin=True so templates show create/edit affordances
    if (request.args.get('saved') or '').strip() in ('1', 'true', 'yes'):
        flash('Role Profile saved successfully!', 'success')
    return render_template('roles_list.html', title='Role Architect', is_admin=True)


@admin.route('/roles/new')
@admin_required
def roles_admin_new():
    """Admin entry to Role Profile wizard."""
    return render_template('role_wizard.html', title='New Role Profile', is_admin=True)

@admin.route('/types/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_metric_type(id):
    """Edit an existing metric type."""
    metric_type = MetricType.query.get_or_404(id)
    form = MetricTypeForm(obj=metric_type)
    
    if form.validate_on_submit():
        old_name = metric_type.name
        form.populate_obj(metric_type)
        db.session.commit()
        
        log_admin_action('EDIT_TYPE', f'Edited metric type: {old_name} -> {metric_type.name}')
        flash('Metric Type updated successfully!', 'success')
        return redirect(url_for('admin.metric_types'))
    
    return render_template('admin/metric_type_form.html', form=form, metric_type=metric_type, title='Edit Metric Type')

@admin.route('/types/<int:id>/delete', methods=['POST'])
@admin_required
def delete_metric_type(id):
    """Delete a metric type."""
    metric_type = MetricType.query.get_or_404(id)
    
    # Check if type has associated metrics
    if len(metric_type.metrics) > 0:
        flash(f'Cannot delete type "{metric_type.name}" because it has {len(metric_type.metrics)} associated metrics.', 'error')
        return redirect(url_for('admin.metric_types'))
    
    name = metric_type.name
    db.session.delete(metric_type)
    db.session.commit()
    
    log_admin_action('DELETE_TYPE', f'Deleted metric type: {name}')
    flash('Metric Type deleted successfully!', 'success')
    return redirect(url_for('admin.metric_types'))

# Bulk Import/Export
@admin.route('/import', methods=['GET', 'POST'])
@admin_required
def bulk_import():
    """Bulk import data from CSV files."""
    form = BulkImportForm()
    
    if form.validate_on_submit():
        file = form.file.data
        import_type = form.import_type.data
        
        try:
            # Read CSV file
            csv_text = file.stream.read().decode("utf-8-sig")
            csv_input = _csv_dict_reader_from_text(csv_text)
            
            imported_count = 0
            errors = []
            
            if import_type == 'metrics':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        # Validate required fields
                        if not all(k in row for k in ['name', 'description', 'outcome', 'metric_type']):
                            errors.append(f'Row {row_num}: Missing required fields')
                            continue
                        
                        # Find or create L&D outcome
                        outcome = LDOutcome.query.filter_by(name=row['outcome'].strip()).first()
                        if not outcome:
                            outcome = LDOutcome(name=row['outcome'].strip())
                            db.session.add(outcome)
                            db.session.flush()
                        
                        # Find or create metric type
                        metric_type = MetricType.query.filter_by(name=row['metric_type'].strip()).first()
                        if not metric_type:
                            metric_type = MetricType(name=row['metric_type'].strip())
                            db.session.add(metric_type)
                            db.session.flush()
                        
                        # Create metric
                        metric = Metric(
                            name=row['name'].strip(),
                            description=row['description'].strip(),
                            example=row.get('example', '').strip(),
                            outcome_id=outcome.id,
                            metric_type_id=metric_type.id
                        )
                        db.session.add(metric)
                        imported_count += 1
                        
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')
            
            elif import_type == 'outcomes':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        if 'name' not in row:
                            errors.append(f'Row {row_num}: Missing name field')
                            continue
                        
                        # Check if outcome already exists
                        existing = LDOutcome.query.filter_by(name=row['name'].strip()).first()
                        if existing:
                            errors.append(f'Row {row_num}: Outcome "{row["name"]}" already exists')
                            continue
                        
                        outcome = LDOutcome(
                            name=row['name'].strip(),
                            description=row.get('description', '').strip()
                        )
                        db.session.add(outcome)
                        imported_count += 1
                        
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')
            
            elif import_type == 'types':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        if 'name' not in row:
                            errors.append(f'Row {row_num}: Missing name field')
                            continue
                        
                        # Check if type already exists
                        existing = MetricType.query.filter_by(name=row['name'].strip()).first()
                        if existing:
                            errors.append(f'Row {row_num}: Type "{row["name"]}" already exists')
                            continue
                        
                        metric_type = MetricType(
                            name=row['name'].strip(),
                            description=row.get('description', '').strip()
                        )
                        db.session.add(metric_type)
                        imported_count += 1
                        
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')

            elif import_type == 'retros':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        r = _normalize_csv_row(row)
                        text = (r.get('text') or r.get('retro_text') or r.get('item') or r.get('retro_item') or r.get('comment') or r.get('description') or r.get('notes') or '').strip()
                        if not text:
                            errors.append(f'Row {row_num}: Missing text field')
                            continue
                        retro = ClientRetroItem(
                            retro_date=_parse_optional_datetime(r.get('retro_date') or r.get('date') or r.get('created_at') or r.get('timestamp')),
                            team=(r.get('team') or r.get('squad') or r.get('group') or r.get('project') or '').strip() or None,
                            category=(r.get('category') or r.get('type') or r.get('theme') or '').strip() or None,
                            text=text,
                            action_owner=(r.get('action_owner') or r.get('owner') or r.get('assignee') or '').strip() or None,
                            action_status=(r.get('action_status') or r.get('status') or '').strip() or None,
                            source=(r.get('source') or r.get('system') or '').strip() or None,
                            raw_json=json.dumps(row),
                        )
                        db.session.add(retro)
                        imported_count += 1
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')

            elif import_type == 'pull_requests':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        r = _normalize_csv_row(row)
                        pr_id = (r.get('pr_id') or r.get('pr_number') or r.get('number') or r.get('id') or '').strip()
                        if not pr_id:
                            errors.append(f'Row {row_num}: Missing pr_id field')
                            continue
                        pr = ClientPullRequest(
                            pr_id=pr_id,
                            url=(r.get('url') or r.get('html_url') or r.get('link') or '').strip() or None,
                            created_at=_parse_optional_datetime(r.get('created_at') or r.get('created') or r.get('opened_at') or r.get('timestamp')),
                            merged_at=_parse_optional_datetime(r.get('merged_at') or r.get('merged') or r.get('closed_at')),
                            author=(r.get('author') or r.get('user') or r.get('created_by') or '').strip() or None,
                            comments_count=int(r['comments_count']) if (r.get('comments_count') or '').strip().isdigit() else (int(r['comments']) if (r.get('comments') or '').strip().isdigit() else None),
                            additions=int(r['additions']) if (r.get('additions') or '').strip().isdigit() else None,
                            deletions=int(r['deletions']) if (r.get('deletions') or '').strip().isdigit() else None,
                            team=(r.get('team') or r.get('squad') or r.get('group') or '').strip() or None,
                            source=(r.get('source') or r.get('system') or '').strip() or None,
                            raw_json=json.dumps(row),
                        )
                        db.session.add(pr)
                        imported_count += 1
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')

            elif import_type == 'survey_responses':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        r = _normalize_csv_row(row)
                        answer = (r.get('answer') or r.get('response') or r.get('value') or '').strip()
                        if not answer:
                            errors.append(f'Row {row_num}: Missing answer field')
                            continue
                        survey = ClientSurveyResponse(
                            submitted_at=_parse_optional_datetime(r.get('submitted_at') or r.get('timestamp') or r.get('submitted') or r.get('created_at')),
                            survey_name=(r.get('survey_name') or r.get('form') or r.get('survey') or '').strip() or None,
                            question=(r.get('question') or r.get('prompt') or r.get('item') or '').strip() or None,
                            answer=answer,
                            team=(r.get('team') or r.get('squad') or r.get('group') or '').strip() or None,
                            source=(r.get('source') or r.get('system') or '').strip() or None,
                            raw_json=json.dumps(row),
                        )
                        db.session.add(survey)
                        imported_count += 1
                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')

            elif import_type == 'client_inventory':
                for row_num, row in enumerate(csv_input, start=2):
                    try:
                        r = _normalize_csv_row(row)

                        client_name = (r.get('client') or r.get('client_name') or r.get('company') or r.get('company_name') or '').strip()
                        if not client_name:
                            errors.append(f'Row {row_num}: Missing client field')
                            continue

                        data_category = (r.get('data_category') or r.get('category') or '').strip()
                        data_point = (r.get('data_point') or r.get('datapoint') or r.get('item') or r.get('field') or '').strip()
                        if not data_category or not data_point:
                            errors.append(f'Row {row_num}: Missing data_category or data_point field')
                            continue

                        client = ClientCompany.query.filter_by(name=client_name).first()
                        if not client:
                            client = ClientCompany(
                                name=client_name,
                                slug=unique_client_slug(client_name),
                                industry=(r.get('industry') or '').strip() or None,
                                notes=(r.get('client_notes') or r.get('notes') or '').strip() or None,
                            )
                            db.session.add(client)
                            db.session.flush()

                        status = (r.get('collected_status') or r.get('status') or '').strip().lower()
                        if status not in ('yes', 'no', 'partial'):
                            status = 'no'

                        existing = ClientDataInventoryItem.query.filter_by(
                            client_company_id=client.id,
                            data_category=data_category,
                            data_point=data_point,
                        ).first()

                        if existing:
                            existing.collected_status = status
                            existing.system_location = (r.get('system_location') or r.get('system') or r.get('location') or '').strip() or None
                            existing.access_method = (r.get('access_method') or r.get('access') or '').strip() or None
                            existing.sensitivity = (r.get('sensitivity') or '').strip() or None
                            existing.anonymity = (r.get('anonymity') or '').strip() or None
                            existing.notes = (r.get('item_notes') or '').strip() or None
                        else:
                            item = ClientDataInventoryItem(
                                client_company_id=client.id,
                                data_category=data_category,
                                data_point=data_point,
                                collected_status=status,
                                system_location=(r.get('system_location') or r.get('system') or r.get('location') or '').strip() or None,
                                access_method=(r.get('access_method') or r.get('access') or '').strip() or None,
                                sensitivity=(r.get('sensitivity') or '').strip() or None,
                                anonymity=(r.get('anonymity') or '').strip() or None,
                                notes=(r.get('item_notes') or '').strip() or None,
                            )
                            db.session.add(item)

                        imported_count += 1

                    except Exception as e:
                        errors.append(f'Row {row_num}: {str(e)}')
            
            # Commit changes
            db.session.commit()
            
            log_admin_action('BULK_IMPORT', f'Imported {imported_count} {import_type}')
            
            if imported_count > 0:
                flash(f'Successfully imported {imported_count} {import_type}!', 'success')
            else:
                flash('No rows were imported. This usually means the CSV had headers but 0 data rows, or the required column names did not match.', 'info')
            
            if errors:
                flash(f'Import completed with {len(errors)} errors. See details below.', 'warning')
                return render_template('admin/import.html', form=form, errors=errors)
            
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Import failed: {str(e)}', 'error')
    
    return render_template('admin/import.html', form=form)

@admin.route('/export/<string:data_type>')
@admin_required
def export_data(data_type):
    """Export data to CSV format."""
    from flask import make_response
    
    output = io.StringIO()
    
    if data_type == 'metrics':
        writer = csv.writer(output)
        writer.writerow(['name', 'description', 'example', 'outcome', 'metric_type', 'created_date'])
        
        metrics = Metric.query.join(LDOutcome).join(MetricType).all()
        for metric in metrics:
            writer.writerow([
                metric.name,
                metric.description,
                metric.example or '',
                metric.outcome.name,
                metric.metric_type.name,
                metric.created_date.strftime('%Y-%m-%d %H:%M:%S')
            ])
    
    elif data_type == 'outcomes':
        writer = csv.writer(output)
        writer.writerow(['name', 'description', 'created_date', 'metrics_count'])
        
        outcomes = LDOutcome.query.all()
        for outcome in outcomes:
            writer.writerow([
                outcome.name,
                outcome.description or '',
                outcome.created_date.strftime('%Y-%m-%d %H:%M:%S'),
                len(outcome.metrics)
            ])
    
    elif data_type == 'types':
        writer = csv.writer(output)
        writer.writerow(['name', 'description', 'created_date', 'metrics_count'])
        
        types = MetricType.query.all()
        for metric_type in types:
            writer.writerow([
                metric_type.name,
                metric_type.description or '',
                metric_type.created_date.strftime('%Y-%m-%d %H:%M:%S'),
                len(metric_type.metrics)
            ])
    
    else:
        flash('Invalid export type.', 'error')
        return redirect(url_for('admin.dashboard'))
    
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = f'attachment; filename={data_type}_export.csv'
    response.headers['Content-type'] = 'text/csv'
    
    log_admin_action('EXPORT_DATA', f'Exported {data_type} data')
    
    return response

# User Management
@admin.route('/users')
@admin_required
def admin_users():
    """List all admin users."""
    users = AdminUser.query.order_by(AdminUser.username).all()
    return render_template('admin/users.html', users=users)

@admin.route('/users/add', methods=['GET', 'POST'])
@admin_required
def add_admin_user():
    """Add a new admin user."""
    form = AdminUserForm()
    
    if form.validate_on_submit():
        # Check if username already exists
        existing_user = AdminUser.query.filter_by(username=form.username.data).first()
        if existing_user:
            flash('Username already exists.', 'error')
            return render_template('admin/user_form.html', form=form, title='Add Admin User')
        
        user = AdminUser(
            username=form.username.data,
            email=form.email.data,
            is_active=form.is_active.data
        )
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        log_admin_action('ADD_USER', f'Added admin user: {user.username}')
        flash('Admin user added successfully!', 'success')
        return redirect(url_for('admin.admin_users'))
    
    return render_template('admin/user_form.html', form=form, title='Add Admin User')

@admin.route('/users/<int:id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_admin_user(id):
    """Edit an existing admin user."""
    user = AdminUser.query.get_or_404(id)
    form = AdminUserForm(obj=user)
    form.password.validators = [Optional(), Length(min=6, max=100)]  # Make password optional for editing
    
    if form.validate_on_submit():
        old_username = user.username
        user.username = form.username.data
        user.email = form.email.data
        user.is_active = form.is_active.data
        
        if form.password.data:
            user.set_password(form.password.data)
        
        db.session.commit()
        
        log_admin_action('EDIT_USER', f'Edited admin user: {old_username} -> {user.username}')
        flash('Admin user updated successfully!', 'success')
        return redirect(url_for('admin.admin_users'))
    
    return render_template('admin/user_form.html', form=form, user=user, title='Edit Admin User')

@admin.route('/users/<int:id>/delete', methods=['POST'])
@admin_required
def delete_admin_user(id):
    """Delete an admin user."""
    user = AdminUser.query.get_or_404(id)
    
    # Prevent deleting the current user
    if user.id == session.get('admin_user_id'):
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin.admin_users'))
    
    username = user.username
    db.session.delete(user)
    db.session.commit()
    
    log_admin_action('DELETE_USER', f'Deleted admin user: {username}')
    flash('Admin user deleted successfully!', 'success')
    return redirect(url_for('admin.admin_users'))

# Audit Logs
@admin.route('/audit')
@admin_required
def audit_logs():
    """View audit logs with pagination."""
    page = request.args.get('page', 1, type=int)
    per_page = 50
    
    logs_pagination = AuditLog.query.order_by(AuditLog.created_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    # Compute summary counts for current page to avoid Jinja 'match' test
    page_items = logs_pagination.items or []
    summary = {
        'login': sum(1 for l in page_items if l.action == 'LOGIN'),
        'add': sum(1 for l in page_items if 'ADD' in (l.action or '')),
        'edit': sum(1 for l in page_items if 'EDIT' in (l.action or '')),
        'delete': sum(1 for l in page_items if 'DELETE' in (l.action or '')),
    }
    
    return render_template('admin/audit.html', logs=logs_pagination, summary=summary)

# API endpoints for AJAX operations
@admin.route('/api/preview', methods=['POST'])
@admin_required
def preview_import():
    """Preview CSV import data."""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file provided'}), 400
    
    file = request.files['file']
    import_type = request.form.get('import_type')
    
    try:
        csv_text = file.stream.read().decode("utf-8-sig")
        csv_input = _csv_dict_reader_from_text(csv_text)

        headers = list(csv_input.fieldnames or [])

        preview_data = []
        total_rows = 0
        for row in csv_input:
            total_rows += 1
            if len(preview_data) < 10:
                preview_data.append(dict(row))

        return jsonify({
            'success': True,
            'data': preview_data,
            'headers': headers,
            'total_rows': total_rows,
            'import_type': import_type,
        })
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@admin.route('/api/stats')
@admin_required
def api_stats():
    """Get dashboard statistics via API."""
    stats = {
        'total_metrics': Metric.query.count(),
        'total_outcomes': LDOutcome.query.count(),
        'total_types': MetricType.query.count(),
        'total_admin_users': AdminUser.query.count()
    }
    return jsonify(stats)

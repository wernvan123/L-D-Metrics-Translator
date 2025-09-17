from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session, current_app
from flask_wtf import FlaskForm, CSRFProtect
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, TextAreaField, SelectField, IntegerField, PasswordField, BooleanField, HiddenField, SelectMultipleField
from wtforms.validators import DataRequired, Length, Optional, Email
from wtforms import ValidationError
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from app.models import Metric, LDOutcome, MetricType, AdminUser, AuditLog, Framework, Competency
from app import db
import csv
import json
import io
from datetime import datetime, timezone
from functools import wraps
import os
import re

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
        ('types', 'Metric Types')
    ], validators=[DataRequired()])

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
        'recent_metrics': Metric.query.order_by(Metric.created_date.desc()).limit(5).all(),
        'recent_audit_logs': AuditLog.query.order_by(AuditLog.created_date.desc()).limit(10).all()
    }
    
    return render_template('admin/dashboard.html', stats=stats)

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
            stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
            csv_input = csv.DictReader(stream)
            
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
            
            # Commit changes
            db.session.commit()
            
            log_admin_action('BULK_IMPORT', f'Imported {imported_count} {import_type}')
            
            if imported_count > 0:
                flash(f'Successfully imported {imported_count} {import_type}!', 'success')
            
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
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    import_type = request.form.get('import_type')
    
    try:
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_input = csv.DictReader(stream)
        
        preview_data = []
        for i, row in enumerate(csv_input):
            if i >= 10:  # Limit preview to 10 rows
                break
            preview_data.append(dict(row))
        
        return jsonify({
            'success': True,
            'data': preview_data,
            'headers': list(preview_data[0].keys()) if preview_data else []
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 400

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

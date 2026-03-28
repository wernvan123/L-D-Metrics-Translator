"""
PDF Generation Routes for L&D Metrics Translator
Handles PDF report generation requests and downloads.
"""

from flask import Blueprint, request, jsonify, send_file, current_app
from app.models import Metric, LDOutcome, MetricType
from app.pdf_service import PDFReportGenerator
from app import db
from app.workspace_stamp import stamp_filename
import io
import json
from datetime import datetime

pdf_bp = Blueprint('pdf', __name__, url_prefix='/pdf')


@pdf_bp.route('/generate-report', methods=['POST'])
def generate_comprehensive_report():
    """
    Generate a comprehensive PDF report based on user selections.
    
    Expected JSON payload:
    {
        "metric_ids": [1, 2, 3],
        "recommendations": {...},
        "user_selections": {
            "categories": ["1", "2"],
            "outcomes": ["1", "3"],
            "context": "performance_enhancement"
        },
        "report_type": "comprehensive"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Extract data
        metric_ids = data.get('metric_ids', [])
        recommendations = data.get('recommendations', {})
        user_selections = data.get('user_selections', {})
        report_type = data.get('report_type', 'comprehensive')
        
        # Validate metric IDs
        if not metric_ids:
            return jsonify({'error': 'At least one metric must be selected'}), 400
        
        # Fetch metrics from database
        metrics = Metric.query.filter(Metric.id.in_(metric_ids)).all()
        if not metrics:
            return jsonify({'error': 'No valid metrics found'}), 404
        
        # Generate PDF
        pdf_generator = PDFReportGenerator()
        
        if report_type == 'summary':
            pdf_buffer = pdf_generator.generate_quick_summary(metrics)
            filename = stamp_filename(f"LD_Metrics_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        else:
            pdf_buffer = pdf_generator.generate_metrics_report(
                selected_metrics=metrics,
                recommendations=recommendations,
                user_selections=user_selections
            )
            filename = stamp_filename(f"LD_Metrics_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        # Return PDF as download
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.exception(f"PDF generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate PDF report',
            'details': str(e)
        }), 500


@pdf_bp.route('/generate-from-selections', methods=['POST'])
def generate_from_current_selections():
    """
    Generate PDF report from current UI selections without explicit metric IDs.
    
    Expected JSON payload:
    {
        "categories": ["1", "2"],
        "outcomes": ["1", "3"],
        "metrics": ["5", "7"],
        "neuroscience": ["9"],
        "recommendations": {...},
        "report_type": "comprehensive"
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Extract selections
        category_ids = data.get('categories', [])
        outcome_ids = data.get('outcomes', [])
        metric_ids = data.get('metrics', [])
        neuroscience_ids = data.get('neuroscience', [])
        recommendations = data.get('recommendations', {})
        report_type = data.get('report_type', 'comprehensive')
        
        # Build query based on selections
        query = Metric.query.join(LDOutcome).join(MetricType)
        filters_applied = False
        
        if category_ids:
            query = query.filter(MetricType.id.in_(category_ids))
            filters_applied = True
        
        if outcome_ids:
            query = query.filter(LDOutcome.id.in_(outcome_ids))
            filters_applied = True
        
        if metric_ids:
            specific_metrics = Metric.query.filter(Metric.id.in_(metric_ids)).all()
            if specific_metrics:
                metrics = specific_metrics
            else:
                metrics = query.all() if filters_applied else []
        else:
            metrics = query.all() if filters_applied else []
        
        # Include neuroscience metrics if selected
        if neuroscience_ids:
            neuroscience_metrics = Metric.query.filter(Metric.id.in_(neuroscience_ids)).all()
            existing_ids = {m.id for m in metrics}
            for nm in neuroscience_metrics:
                if nm.id not in existing_ids:
                    metrics.append(nm)
        
        if not metrics:
            return jsonify({'error': 'No metrics found matching your selections'}), 404
        
        # Prepare user selections summary
        user_selections = {
            'categories': category_ids,
            'outcomes': outcome_ids,
            'metrics': metric_ids,
            'neuroscience': neuroscience_ids,
            'total_selected': len(metrics)
        }
        
        # Generate PDF
        pdf_generator = PDFReportGenerator()
        
        if report_type == 'summary':
            pdf_buffer = pdf_generator.generate_quick_summary(metrics)
            filename = stamp_filename(f"LD_Metrics_Summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        else:
            pdf_buffer = pdf_generator.generate_metrics_report(
                selected_metrics=metrics,
                recommendations=recommendations,
                user_selections=user_selections
            )
            filename = stamp_filename(f"LD_Metrics_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
        
    except Exception as e:
        current_app.logger.error(f"PDF generation from selections error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate PDF report from selections',
            'details': str(e)
        }), 500


@pdf_bp.route('/preview-metrics', methods=['POST'])
def preview_selected_metrics():
    """
    Preview which metrics would be included in the PDF report.
    
    Returns JSON with metric details for preview before generating PDF.
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body required'}), 400
        
        # Extract selections (same logic as generate_from_current_selections)
        category_ids = data.get('categories', [])
        outcome_ids = data.get('outcomes', [])
        metric_ids = data.get('metrics', [])
        neuroscience_ids = data.get('neuroscience', [])
        
        # Build query
        query = Metric.query.join(LDOutcome).join(MetricType)
        filters_applied = False
        
        if category_ids:
            query = query.filter(MetricType.id.in_(category_ids))
            filters_applied = True
        
        if outcome_ids:
            query = query.filter(LDOutcome.id.in_(outcome_ids))
            filters_applied = True
        
        if metric_ids:
            specific_metrics = Metric.query.filter(Metric.id.in_(metric_ids)).all()
            if specific_metrics:
                metrics = specific_metrics
            else:
                metrics = query.all() if filters_applied else []
        else:
            metrics = query.all() if filters_applied else []
        
        # Include neuroscience metrics
        if neuroscience_ids:
            neuroscience_metrics = Metric.query.filter(Metric.id.in_(neuroscience_ids)).all()
            existing_ids = {m.id for m in metrics}
            for nm in neuroscience_metrics:
                if nm.id not in existing_ids:
                    metrics.append(nm)
        
        # Format response
        metrics_data = []
        for metric in metrics:
            metrics_data.append({
                'id': metric.id,
                'name': metric.name,
                'description': metric.description,
                'category': metric.metric_type.name,
                'outcome': metric.outcome.name,
                'example': metric.example
            })
        
        # Group by category for better organization
        metrics_by_category = {}
        for metric_data in metrics_data:
            category = metric_data['category']
            if category not in metrics_by_category:
                metrics_by_category[category] = []
            metrics_by_category[category].append(metric_data)
        
        return jsonify({
            'total_metrics': len(metrics),
            'metrics_by_category': metrics_by_category,
            'metrics': metrics_data,
            'summary': {
                'categories': len(set(m['category'] for m in metrics_data)),
                'outcomes': len(set(m['outcome'] for m in metrics_data)),
                'total': len(metrics_data)
            }
        })
        
    except Exception as e:
        current_app.logger.error(f"Metrics preview error: {str(e)}")
        return jsonify({
            'error': 'Failed to preview metrics',
            'details': str(e)
        }), 500


@pdf_bp.route('/generate-comparison', methods=['POST'])
def generate_comparison_report():
    """Generate a comparison PDF for two reports with summary and key changes.

    Expected JSON payload:
    {
        "a_report": {"title": "Baseline: Q1 Report (July 15, 2025)", "date": "2025-07-15"},
        "b_report": {"title": "Follow-up: Q3 Report (September 15, 2025)", "date": "2025-09-15"},
        "summary_html": "<p>Summary...</p>",
        "key_changes": [
            {"label": "Strategic Acumen", "change": 25, "note": "..."},
            {"label": "Delegation Effectiveness Score", "change": 40 }
        ],
        "filename": "LD_Comparison_Report.pdf"
    }
    """
    try:
        data = request.get_json() or {}
        a_report = data.get('a_report') or {}
        b_report = data.get('b_report') or {}
        summary_html = data.get('summary_html') or ''
        key_changes = data.get('key_changes') or []
        filename = stamp_filename(data.get('filename') or f"LD_Comparison_Report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")

        pdf_generator = PDFReportGenerator()
        pdf_buffer = pdf_generator.generate_comparison_report(
            a_report=a_report,
            b_report=b_report,
            summary_html=summary_html,
            key_changes=key_changes
        )
        return send_file(
            pdf_buffer,
            as_attachment=True,
            download_name=filename,
            mimetype='application/pdf'
        )
    except Exception as e:
        current_app.logger.exception(f"Comparison PDF generation error: {str(e)}")
        return jsonify({
            'error': 'Failed to generate comparison PDF',
            'details': str(e)
        }), 500


@pdf_bp.route('/health', methods=['GET'])
def pdf_health_check():
    """Health check for PDF generation service."""
    try:
        # Test PDF generation with minimal data
        pdf_generator = PDFReportGenerator()
        test_buffer = io.BytesIO()
        
        # Simple test - just create the generator
        return jsonify({
            'status': 'healthy',
            'service': 'PDF Generation',
            'timestamp': datetime.now().isoformat(),
            'features': [
                'Comprehensive reports',
                'Quick summaries', 
                'Professional formatting',
                'Charts and tables',
                'Implementation roadmaps'
            ]
        })
        
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e),
            'timestamp': datetime.now().isoformat()
        }), 500


# Error handlers for PDF blueprint
@pdf_bp.errorhandler(404)
def pdf_not_found(error):
    """Handle 404 errors for PDF routes."""
    return jsonify({
        'error': 'PDF endpoint not found',
        'available_endpoints': [
            '/pdf/generate-report',
            '/pdf/generate-from-selections', 
            '/pdf/preview-metrics',
            '/pdf/generate-comparison',
            '/pdf/health'
        ]
    }), 404


@pdf_bp.errorhandler(500)
def pdf_internal_error(error):
    """Handle 500 errors for PDF routes."""
    return jsonify({
        'error': 'PDF generation service error',
        'details': 'An unexpected error occurred during PDF processing'
    }), 500

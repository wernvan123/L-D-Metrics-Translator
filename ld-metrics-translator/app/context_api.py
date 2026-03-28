"""
Context Management API Blueprint
Handles authentication-aware context storage and retrieval for the L&D Metrics Translator
"""

from flask import Blueprint, request, jsonify, session as flask_session
from app.context_manager import context_manager
from app.models import Metric, Framework, Competency
from app import db
import logging
from datetime import timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)

context_api = Blueprint('context_api', __name__, url_prefix='/api/context')


@context_api.route('/session', methods=['GET'])
def get_session_info():
    """Get current session information and authentication status."""
    try:
        stats = context_manager.get_session_stats()
        preferences = context_manager.get_user_preferences()
        
        return jsonify({
            'success': True,
            'session': stats,
            'preferences': preferences,
            'is_authenticated': stats.get('is_authenticated', False),
            'admin_user_id': stats.get('admin_user_id')
        })
        
    except Exception as e:
        logger.error(f"Error getting session info: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve session information'
        }), 500


@context_api.route('/initialize', methods=['POST'])
def initialize_context():
    """Initialize context for a new session or page load."""
    try:
        data = request.get_json() or {}
        page = data.get('page', 'unknown')
        preferences = data.get('preferences', {})
        
        # Store initialization context
        init_context = {
            'page': page,
            'initialized_at': context_manager.get_session_stats()['last_activity'],
            'user_agent': request.headers.get('User-Agent', ''),
            'referrer': request.headers.get('Referer', '')
        }
        
        context_manager.store_context(
            'system', 'initialization', init_context
        )
        
        # Update preferences if provided
        if preferences:
            current_prefs = context_manager.get_user_preferences()
            current_prefs.update(preferences)
            context_manager.store_user_preferences(current_prefs)
        
        # Get session stats and preferences
        stats = context_manager.get_session_stats()
        final_preferences = context_manager.get_user_preferences()
        
        return jsonify({
            'success': True,
            'session': stats,
            'preferences': final_preferences,
            'initialized_page': page
        })
        
    except Exception as e:
        logger.error(f"Error initializing context: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to initialize context'
        }), 500


@context_api.route('/store', methods=['POST'])
def store_context():
    """Store context data for the current session."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data is required'
            }), 400
        
        context_type = data.get('context_type')
        context_key = data.get('context_key')
        context_data = data.get('context_data')
        expires_in_hours = data.get('expires_in_hours')
        
        if not all([context_type, context_key, context_data]):
            return jsonify({
                'success': False,
                'error': 'context_type, context_key, and context_data are required'
            }), 400
        
        # Calculate expiration
        expires_in = None
        if expires_in_hours:
            expires_in = timedelta(hours=expires_in_hours)
        
        # Store context
        context = context_manager.store_context(
            context_type=context_type,
            context_key=context_key,
            context_data=context_data,
            expires_in=expires_in
        )
        
        return jsonify({
            'success': True,
            'context_id': context.id,
            'stored_at': context.created_date.isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error storing context: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to store context: {str(e)}'
        }), 500


@context_api.route('/get/<context_type>/<context_key>', methods=['GET'])
def get_context(context_type: str, context_key: str):
    """Retrieve context data for the current session."""
    try:
        context_data = context_manager.get_context(context_type, context_key)
        
        if context_data is None:
            return jsonify({
                'success': False,
                'error': 'Context not found or expired'
            }), 404
        
        return jsonify({
            'success': True,
            'context_type': context_type,
            'context_key': context_key,
            'context_data': context_data
        })
        
    except Exception as e:
        logger.error(f"Error retrieving context: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve context'
        }), 500


@context_api.route('/all', methods=['GET'])
def get_all_contexts():
    """Get all contexts for the current session."""
    try:
        contexts = context_manager.get_all_contexts()
        
        return jsonify({
            'success': True,
            'contexts': contexts,
            'count': len(contexts)
        })
        
    except Exception as e:
        logger.error(f"Error retrieving all contexts: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve contexts'
        }), 500


@context_api.route('/clear', methods=['DELETE'])
def clear_contexts():
    """Clear all contexts for the current session."""
    try:
        success = context_manager.clear_session_contexts()
        
        return jsonify({
            'success': success,
            'message': 'Session contexts cleared' if success else 'Failed to clear contexts'
        })
        
    except Exception as e:
        logger.error(f"Error clearing contexts: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear contexts'
        }), 500


@context_api.route('/preferences', methods=['GET', 'POST'])
def handle_preferences():
    """Get or update user preferences."""
    try:
        if request.method == 'GET':
            preferences = context_manager.get_user_preferences()
            return jsonify({
                'success': True,
                'preferences': preferences
            })
        
        else:  # POST
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Preferences data is required'
                }), 400
            
            # Update preferences
            context_manager.store_user_preferences(data)
            updated_preferences = context_manager.get_user_preferences()
            
            return jsonify({
                'success': True,
                'preferences': updated_preferences,
                'message': 'Preferences updated successfully'
            })
            
    except Exception as e:
        logger.error(f"Error handling preferences: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to handle preferences'
        }), 500


@context_api.route('/metrics/select', methods=['POST'])
def select_metric():
    """Select or deselect a metric for the current session."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data is required'
            }), 400
        
        metric_id = data.get('metric_id')
        selection_type = data.get('selection_type', 'manual')
        context_tags = data.get('context_tags', [])
        
        if not metric_id:
            return jsonify({
                'success': False,
                'error': 'metric_id is required'
            }), 400
        
        # Select/deselect metric
        selected, selection = context_manager.select_metric(
            metric_id=metric_id,
            selection_type=selection_type,
            context_tags=context_tags
        )
        
        return jsonify({
            'success': True,
            'selected': selected,
            'metric_id': metric_id,
            'selection_id': selection.id,
            'action': 'selected' if selected else 'deselected'
        })
        
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error selecting metric: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to select metric'
        }), 500


@context_api.route('/metrics/selected', methods=['GET'])
def get_selected_metrics():
    """Get all selected metrics for the current session."""
    try:
        selected_metrics = context_manager.get_selected_metrics()
        
        return jsonify({
            'success': True,
            'selected_metrics': selected_metrics,
            'count': len(selected_metrics)
        })
        
    except Exception as e:
        logger.error(f"Error getting selected metrics: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve selected metrics'
        }), 500


@context_api.route('/metrics/clear', methods=['DELETE'])
def clear_selected_metrics():
    """Clear all selected metrics for the current session."""
    try:
        success = context_manager.clear_metric_selections()
        
        return jsonify({
            'success': success,
            'message': 'Metric selections cleared' if success else 'Failed to clear selections'
        })
        
    except Exception as e:
        logger.error(f"Error clearing metric selections: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear metric selections'
        }), 500


@context_api.route('/event-analysis/store', methods=['POST'])
def store_event_analysis():
    """Store event analysis with authentication awareness."""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'Request data is required'
            }), 400
        
        event_description = data.get('event_description', '').strip()
        analysis_result = data.get('analysis_result', '').strip()
        generated_by = data.get('generated_by', 'ai_model')
        success = data.get('success', True)
        error_message = data.get('error_message')
        
        if not event_description:
            return jsonify({
                'success': False,
                'error': 'event_description is required'
            }), 400
        
        # Store event analysis
        analysis = context_manager.store_event_analysis(
            event_description=event_description,
            analysis_result=analysis_result,
            generated_by=generated_by,
            success=success,
            error_message=error_message
        )
        
        return jsonify({
            'success': True,
            'analysis_id': analysis.id,
            'stored_at': analysis.created_date.isoformat(),
            'is_anonymous': analysis.is_anonymous
        })
        
    except Exception as e:
        logger.error(f"Error storing event analysis: {str(e)}")
        return jsonify({
            'success': False,
            'error': f'Failed to store event analysis: {str(e)}'
        }), 500


@context_api.route('/event-analysis/history', methods=['GET'])
def get_event_analysis_history():
    """Get event analysis history based on authentication status."""
    try:
        limit = request.args.get('limit', 10, type=int)
        limit = min(limit, 50)  # Cap at 50 results
        
        history = context_manager.get_event_analysis_history(limit=limit)
        
        return jsonify({
            'success': True,
            'history': history,
            'count': len(history),
            'is_authenticated': flask_session.get('admin_user_id') is not None
        })
        
    except Exception as e:
        logger.error(f"Error getting event analysis history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve event analysis history'
        }), 500


@context_api.route('/event-analysis/clear', methods=['DELETE'])
def clear_event_analysis_history():
    """Clear event analysis history based on authentication status."""
    try:
        success = context_manager.clear_event_analysis_history()
        
        return jsonify({
            'success': success,
            'message': 'Event analysis history cleared' if success else 'Failed to clear history'
        })
        
    except Exception as e:
        logger.error(f"Error clearing event analysis history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to clear event analysis history'
        }), 500


@context_api.route('/auth-status', methods=['GET'])
def get_auth_status():
    """Get current authentication status and user information."""
    try:
        admin_user_id = flask_session.get('admin_user_id')
        admin_username = flask_session.get('admin_username')
        is_authenticated = admin_user_id is not None
        
        return jsonify({
            'success': True,
            'is_authenticated': is_authenticated,
            'admin_user_id': admin_user_id,
            'admin_username': admin_username,
            'session_id': context_manager.get_session_id()
        })
        
    except Exception as e:
        logger.error(f"Error getting auth status: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to retrieve authentication status'
        }), 500


# ---------------------------------------------
# Framework-centric context endpoints
# ---------------------------------------------

@context_api.route('/framework/select', methods=['POST'])
def select_framework():
    """Persist selected framework in session context."""
    try:
        data = request.get_json() or {}
        framework_id = data.get('framework_id')
        if not framework_id:
            return jsonify({'success': False, 'error': 'framework_id is required'}), 400
        fw = Framework.query.get(framework_id)
        if not fw:
            return jsonify({'success': False, 'error': 'Framework not found'}), 404
        stored = context_manager.set_selected_framework(int(framework_id))
        return jsonify({'success': True, 'selected_framework': stored, 'framework': fw.to_dict()})
    except Exception as e:
        logger.error(f"Error selecting framework: {e}")
        return jsonify({'success': False, 'error': 'Failed to select framework'}), 500


@context_api.route('/framework/competencies', methods=['POST'])
def set_framework_competencies():
    """Persist active competencies for the currently selected framework."""
    try:
        data = request.get_json() or {}
        competency_ids = data.get('competency_ids') or []
        if not isinstance(competency_ids, list):
            return jsonify({'success': False, 'error': 'competency_ids must be a list'}), 400
        # Filter to existing competency IDs only (defensive)
        valid_ids = [c.id for c in Competency.query.filter(Competency.id.in_(competency_ids)).all()]
        stored = context_manager.set_active_competencies(valid_ids)
        return jsonify({'success': True, 'active_competencies': stored, 'count': len(valid_ids)})
    except Exception as e:
        logger.error(f"Error setting competencies: {e}")
        return jsonify({'success': False, 'error': 'Failed to set competencies'}), 500


@context_api.route('/framework/state', methods=['GET'])
def get_framework_state():
    """Return selected framework and active competencies from session context."""
    try:
        sel = context_manager.get_selected_framework() or {}
        active_ids = context_manager.get_active_competencies() or []
        framework = None
        competencies = []
        if sel and 'framework_id' in sel:
            fw = Framework.query.get(sel['framework_id'])
            if fw:
                framework = fw.to_dict()
        if active_ids:
            competencies = [c.to_dict(include_metrics=False) for c in Competency.query.filter(Competency.id.in_(active_ids)).all()]
        return jsonify({
            'success': True,
            'selected_framework': sel,
            'framework': framework,
            'active_competency_ids': active_ids,
            'active_competencies': competencies,
        })
    except Exception as e:
        logger.error(f"Error getting framework state: {e}")
        return jsonify({'success': False, 'error': 'Failed to get framework state'}), 500


@context_api.route('/framework/state', methods=['POST'])
def set_framework_state():
    """Persist framework-related state in the session (used by Plan Builder).

    Accepts (best-effort):
    - framework_id: int | null
    - active_competencies: [int] (or competency_ids)
    - outcome_id: int | null
    """
    try:
        data = request.get_json(silent=True) or {}

        # framework_id: set or clear
        if 'framework_id' in data:
            fw_id = data.get('framework_id')
            if fw_id is None or str(fw_id).strip() == '':
                flask_session.pop('context_framework_selected', None)
            else:
                fw = Framework.query.get(int(fw_id))
                if not fw:
                    return jsonify({'success': False, 'error': 'Framework not found'}), 404
                context_manager.set_selected_framework(int(fw_id))

        # active competencies: set or clear
        if 'active_competencies' in data or 'competency_ids' in data:
            competency_ids = data.get('active_competencies')
            if competency_ids is None:
                competency_ids = data.get('competency_ids')
            if competency_ids is None:
                competency_ids = []
            if not isinstance(competency_ids, list):
                return jsonify({'success': False, 'error': 'active_competencies must be a list'}), 400
            if not competency_ids:
                flask_session.pop('context_framework_active_competencies', None)
            else:
                valid_ids = [c.id for c in Competency.query.filter(Competency.id.in_(competency_ids)).all()]
                context_manager.set_active_competencies(valid_ids)

        # outcome_id: store or clear (Plan Builder uses same endpoint)
        if 'outcome_id' in data:
            outcome_id = data.get('outcome_id')
            if outcome_id is None or str(outcome_id).strip() == '':
                flask_session.pop('context_framework_selected_outcome', None)
            else:
                context_manager.store_context('framework', 'selected_outcome', {
                    'outcome_id': int(outcome_id),
                })

        flask_session.modified = True
        return get_framework_state()
    except Exception as e:
        logger.error(f"Error setting framework state: {e}")
        return jsonify({'success': False, 'error': 'Failed to set framework state'}), 500


# ---------------------------------------------
# Plan Items (session-backed)
# ---------------------------------------------

@context_api.route('/plan/items', methods=['GET'])
def plan_items_list():
    """Return current plan items for this session."""
    try:
        items = context_manager.list_plan_items()
        return jsonify({'success': True, 'items': items, 'count': len(items)})
    except Exception as e:
        logger.error(f"Error listing plan items: {e}")
        return jsonify({'success': False, 'error': 'Failed to list plan items'}), 500


@context_api.route('/plan/items', methods=['POST'])
def plan_items_add():
    """Add a new item to the session plan items."""
    try:
        data = request.get_json() or {}
        kind = (data.get('kind') or '').strip()
        label = (data.get('label') or '').strip()
        source_id = data.get('source_id')
        meta = data.get('meta') or {}
        source_page = (data.get('source_page') or '').strip()
        if not kind or not label:
            return jsonify({'success': False, 'error': 'kind and label are required'}), 400
        item = context_manager.add_plan_item(kind=kind, label=label, source_id=source_id, meta=meta, source_page=source_page)
        return jsonify({'success': True, 'item': item})
    except ValueError as e:
        return jsonify({'success': False, 'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error adding plan item: {e}")
        return jsonify({'success': False, 'error': 'Failed to add plan item'}), 500


@context_api.route('/plan/items/<int:item_id>', methods=['DELETE'])
def plan_items_remove(item_id: int):
    """Remove a plan item by id for this session."""
    try:
        ok = context_manager.remove_plan_item(item_id)
        return jsonify({'success': ok, 'removed_id': item_id})
    except Exception as e:
        logger.error(f"Error removing plan item {item_id}: {e}")
        return jsonify({'success': False, 'error': 'Failed to remove plan item'}), 500


@context_api.route('/plan/items', methods=['DELETE'])
def plan_items_clear():
    """Clear all plan items for this session."""
    try:
        ok = context_manager.clear_plan_items()
        return jsonify({'success': ok})
    except Exception as e:
        logger.error(f"Error clearing plan items: {e}")
        return jsonify({'success': False, 'error': 'Failed to clear plan items'}), 500
